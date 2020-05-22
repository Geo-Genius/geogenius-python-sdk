"""
GBDX Catalog Image Interface.

Contact: chris.helm@digitalglobe.com
"""
import types as pytypes

from geogeniustools.catalog import Catalog
from geogeniustools.images.obs_image import OBSImage
from geogeniustools.rda.error import UnsupportedImageType


class CatalogImage(object):
    """
    Creates an image instance matching the type of the Catalog ID.

    Args:
        catalogID (str): The source catalog ID from the platform catalog.
        bbox (list of xmin, ymin, xmax, ymax): Bounding box of image to crop to in EPSG:4326 units unless specified by `from_proj`
        proj (str): Optional EPSG projection string for the image, default is "EPSG:4326"
        from_proj (str): Optional projection string to define the coordinate system of `bbox`, default is "EPSG:4327"
        dtype (str): The dtype for the returned image (only valid for Worldview). One of: "int8", "int16", "uint16", "int32", "float32", "float64"
        band_type (str): The product spec / band type for the image returned (band_type='MS'|'Pan')
        bands (list of int): bands to include in the image. Bands are zero-indexed.
        pansharpen (bool): Whether or not to return a pansharpened image (defaults to False)
        acomp (bool): Perform atmospheric compensation on the image (defaults to False, i.e. Top of Atmosphere value)
        gsd (float): The Ground Sample Distance (GSD) of the image. Must be defined in the same projected units as the image projection.
        dra (bool): Perform Dynamic Range Adjustment (DRA) on the image. DRA will override the dtype and return int8 data.

    Attributes:
        affine (list): The image affine transformation
        bounds (list): Spatial bounds of the image
        metadata (dict): image metadata
        ntiles (int): the number of tiles composing the image
        nbytes (int): size of the image in bytes
        proj (str): The image projection as EPSG string

    Returns:
        image (ndarray): An image instance - one of IdahoImage, WV02, WV03_VNIR, LandsatImage, IkonosImage
    """

    def __new__(cls, cat_id=None, **kwargs):
        inst = cls._image_by_type(cat_id, **kwargs)
        fplg = kwargs.get("fetch_plugin")
        if fplg:
            for attrname in dir(fplg):
                if isinstance(getattr(fplg, attrname), pytypes.MethodType) and attrname in (
                        "__dask_optimize__", "__fetch__"):
                    setattr(inst, attrname, getattr(fplg, attrname))
        return inst

    @classmethod
    def _image_by_type(cls, cat_id, **kwargs):
        c = Catalog()
        image = c.get(cat_id=cat_id)
        source_type = image['sourceType'].lower()
        if source_type == 'obs1':
            return OBSImage(path=image['dataUrl'], **kwargs)
        else:
            raise UnsupportedImageType('Unsupported image type: {}'.format(str(image['sourceType'])))
