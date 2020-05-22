from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles

from geogeniustools.rda.error import ConvertCogError

try:
    import rasterio

    has_rasterio = True
except:
    has_rasterio = False

from functools import partial
import os

import dask
from dask.array import store
import tempfile
import numpy as np
from geogeniustools.s3 import S3
from geogeniustools.rda.util import pad

threads = int(os.environ.get('GEOGENIUS_THREADS', 64))
threaded_get = partial(dask.threaded.get, num_workers=threads)


class rio_writer(object):
    def __init__(self, dst):
        self.dst = dst

    def __setitem__(self, location, chunk):
        window = ((location[1].start, location[1].stop),
                  (location[2].start, location[2].stop))
        self.dst.write(chunk, window=window)


def to_geotiff(arr, path='./output.tif', proj=None, spec=None, bands=None, **kwargs):
    ''' Write out a geotiff file of the image

    Args:
        path (str): path to write the geotiff file to, default is ./output.tif
        proj (str): EPSG string of projection to reproject to
        spec (str): if set to 'rgb', write out color-balanced 8-bit RGB tif
        bands (list): list of bands to export. If spec='rgb' will default to RGB bands

    Returns:
        str: path the geotiff was written to'''

    assert has_rasterio, "To create geotiff images please install rasterio"

    try:
        img_md = arr.rda.metadata["image"]
        x_size = img_md["tileXSize"]
        y_size = img_md["tileYSize"]
    except (AttributeError, KeyError):
        x_size = kwargs.get("chunk_size", 256)
        y_size = kwargs.get("chunk_size", 256)

    try:
        tfm = kwargs['transform'] if 'transform' in kwargs else arr.affine
    except:
        tfm = None

    dtype = arr.dtype.name if arr.dtype.name != 'int8' else 'uint8'

    if spec is not None and spec.lower() == 'rgb':
        if bands is None:
            bands = arr._rgb_bands
        # skip if already DRA'ed
        if hasattr(arr, 'options') and not arr.options.get('dra'):
            # add the RDA HistogramDRA op to get a RGB 8-bit image
            from geogeniustools.rda.interface import RDA
            rda = RDA()
            dra = rda.HistogramDRA(arr)
            # Reset the bounds and select the bands on the new Dask
            arr = dra.aoi(bbox=arr.bounds)
        arr = arr[bands, ...].astype(np.uint8)
        dtype = 'uint8'
    else:
        if bands is not None:
            arr = arr[bands, ...]
    meta = {
        'width': arr.shape[2],
        'height': arr.shape[1],
        'count': arr.shape[0],
        'dtype': dtype,
        'driver': 'GTiff',
        'transform': tfm
    }
    if proj is not None:
        meta["crs"] = {'init': proj}

    if "tiled" in kwargs and kwargs["tiled"]:
        meta.update(blockxsize=x_size, blockysize=y_size, tiled="yes")

    with rasterio.open(path, "w", **meta) as dst:
        writer = rio_writer(dst)
        result = store(arr, writer, compute=False)
        result.compute(scheduler=threaded_get)

    return path


def to_obstiff(arr, obs_path, proj="EPSG:4326", spec=None, bands=None, **kwargs):
    temp_file = tempfile.mktemp(suffix=".tiff")
    temp_cog_file = tempfile.mktemp(suffix=".tiff")

    # save to tiff
    to_geotiff(arr, path=temp_file, proj=proj, spec=spec, bands=bands, **kwargs)

    try:
        # convert tiff to cog
        output_profile = cog_profiles.get("deflate")
        output_profile.update({"BLOCKXSIZE": 256, "BLOCKYSIZE": 256})
        config = dict(
            NUM_THREADS=8,
            GDAL_TIFF_INTERNAL_MASK=os.environ.get("GDAL_TIFF_INTERNAL_MASK", True),
            GDAL_TIFF_OVR_BLOCKSIZE=str(os.environ.get("GDAL_TIFF_OVR_BLOCKSIZE", 128))
        )
        cog_translate(temp_file, temp_cog_file, output_profile, add_mask=True, web_optimized=False, config=config)
        s3 = S3()
        return s3.upload(local_file=temp_cog_file, obs_path=obs_path)
    except Exception as e:
        raise ConvertCogError(e.__str__())
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(temp_cog_file):
            os.remove(temp_cog_file)


class TiffFactory(object):

    @staticmethod
    def generate_tiff_from_array(meta, array, obs_path):
        temp_tiff_file = tempfile.mktemp(suffix=".tiff")
        temp_cog_file = tempfile.mktemp(suffix=".tiff")

        with rasterio.open(temp_tiff_file, mode='w', driver=meta.get('driver'), width=meta.get('width'),
                           height=meta.get('height'), transform=meta.get('transform'), crs=meta.get('crs'),
                           count=meta.get('count'), nodata=meta.get('nodata'), dtype=array.dtype) as dst:
            for band in range(0, meta.get('count')):
                dst.write_band(band + 1, array[band])

        try:
            # convert tiff to cog
            output_profile = cog_profiles.get("deflate")
            output_profile.update({"BLOCKXSIZE": 256, "BLOCKYSIZE": 256})
            config = dict(
                NUM_THREADS=8,
                GDAL_TIFF_INTERNAL_MASK=os.environ.get("GDAL_TIFF_INTERNAL_MASK", True),
                GDAL_TIFF_OVR_BLOCKSIZE=str(os.environ.get("GDAL_TIFF_OVR_BLOCKSIZE", 128))
            )
            cog_translate(temp_tiff_file, temp_cog_file, output_profile, add_mask=True, web_optimized=False,
                          config=config)
            s3 = S3()
            return s3.upload(local_file=temp_cog_file, obs_path=obs_path)
        except Exception as e:
            raise ConvertCogError(e.__str__())
        finally:
            if os.path.exists(temp_tiff_file):
                os.remove(temp_tiff_file)
            if os.path.exists(temp_cog_file):
                os.remove(temp_cog_file)

    @staticmethod
    def generate_padded_tiff(meta, array, pad_width, obs_path, pad_mode='constant'):
        temp_tiff_file = tempfile.mktemp(suffix=".tiff")
        temp_cog_file = tempfile.mktemp(suffix=".tiff")
        if len(array.shape) != len(pad_width):
            raise ValueError('Pad width is invalid')
        new_width = meta.get('width') + pad_width[1][0] + pad_width[1][1]
        new_height = meta.get('height') + pad_width[2][0] + pad_width[2][1]

        padded_array, new_transform = pad(array, meta.get('transform'), pad_width=pad_width, mode=pad_mode)

        # write padded tiff
        with rasterio.open(temp_tiff_file, mode='w', driver=meta.get('driver'), width=new_width,
                           height=new_height, transform=new_transform, crs=meta.get('crs'),
                           count=meta.get('count'), nodata=meta.get('nodata'), dtype=meta.get('dtype')) as dst:
            for band in range(0, meta.get('count')):
                dst.write_band(band + 1, padded_array[band])

        try:
            # convert tiff to cog
            output_profile = cog_profiles.get("deflate")
            output_profile.update({"BLOCKXSIZE": 256, "BLOCKYSIZE": 256})
            config = dict(
                NUM_THREADS=8,
                GDAL_TIFF_INTERNAL_MASK=os.environ.get("GDAL_TIFF_INTERNAL_MASK", True),
                GDAL_TIFF_OVR_BLOCKSIZE=str(os.environ.get("GDAL_TIFF_OVR_BLOCKSIZE", 128))
            )
            cog_translate(temp_tiff_file, temp_cog_file, output_profile, nodata=0, add_mask=True, web_optimized=False,
                          config=config)
            s3 = S3()
            return s3.upload(local_file=temp_cog_file, obs_path=obs_path)
        except Exception as e:
            raise ConvertCogError(e.__str__())
        finally:
            if os.path.exists(temp_tiff_file):
                os.remove(temp_tiff_file)
            if os.path.exists(temp_cog_file):
                os.remove(temp_cog_file)


