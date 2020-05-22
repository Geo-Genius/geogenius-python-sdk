import math
import os

from geogeniustools.rda.env_variable import PUBLIC_RDA_ENDPOINT

try:
    from rio_hist.match import histogram_match as rio_match

    has_rio = True
except ImportError:
    has_rio = False

import mercantile
from shapely.geometry import box

import numpy as np

try:
    from matplotlib import pyplot as plt

    has_pyplot = True
except:
    has_pyplot = False

try:
    from mapboxgl.viz import RasterTilesViz as rtv, RasterTilesListViz as rtlv

    has_mapboxgl = True
except:
    has_mapboxgl = False


class PlotMixin(object):

    def rgb(self, **kwargs):
        """
        Convert the image to a 3 band RGB for plotting

        This method shares the same arguments as plot(). It will perform visual adjustment on the
        image and prepare the data for plotting in MatplotLib. Values are converted to an
        appropriate precision and the axis order is changed to put the band axis last.
        """

        if "bands" in kwargs:
            use_bands = kwargs["bands"]
            assert len(use_bands) == 3, 'Plot method only supports single or 3-band outputs'
            del kwargs["bands"]
        else:
            use_bands = self._rgb_bands
        if kwargs.get('blm') == True:
            return self.histogram_match(use_bands, **kwargs)
        # if not specified or DRA'ed, default to a 2-98 stretch
        if "histogram" not in kwargs:
            if "stretch" not in kwargs:
                if hasattr(self, "options") and not self.options.get('dra'):
                    kwargs['stretch'] = [2, 98]
            return self.histogram_stretch(use_bands, **kwargs)
        elif kwargs["histogram"] == "equalize":
            return self.histogram_equalize(use_bands, **kwargs)
        # elif kwargs["histogram"] == "match":
        #     return self.histogram_match(use_bands, **kwargs)
        elif kwargs["histogram"] == "minmax":
            return self.histogram_stretch(use_bands, stretch=[0, 100], **kwargs)
        # DRA'ed images should be left alone if not explicitly adjusted
        elif kwargs["histogram"] == "ignore" or (hasattr(self, "options") and self.options.get('dra')):
            data = self._read(self[use_bands, ...], **kwargs)
            return np.rollaxis(data, 0, 3)
        else:
            raise KeyError('Unknown histogram parameter, use "equalize", "match", "minmax", or "ignore"')

    def histogram_equalize(self, use_bands, **kwargs):
        """
        Equalize and the histogram and normalize value range
        Equalization is on all three bands, not per-band
        """
        data = self._read(self[use_bands, ...], **kwargs)
        data = np.rollaxis(data.astype(np.float32), 0, 3)
        flattened = data.flatten()
        if 0 in data:
            masked = np.ma.masked_values(data, 0).compressed()
            image_histogram, bin_edges = np.histogram(masked, 256)
        else:
            image_histogram, bin_edges = np.histogram(flattened, 256)
        bins = (bin_edges[:-1] + bin_edges[1:]) / 2.0
        cdf = image_histogram.cumsum()
        cdf = cdf / float(cdf[-1])
        image_equalized = np.interp(flattened, bins, cdf).reshape(data.shape)
        if 'stretch' in kwargs or 'gamma' in kwargs:
            return self._histogram_stretch(image_equalized, **kwargs)
        else:
            return image_equalized

    def histogram_match(self, use_bands, blm_source=None, **kwargs):
        """Match the histogram to existing imagery"""
        assert has_rio, "To match image histograms please install rio_hist"
        data = self._read(self[use_bands, ...], **kwargs)
        data = np.rollaxis(data.astype(np.float32), 0, 3)
        if 0 in data:
            data = np.ma.masked_values(data, 0)
        bounds = self._reproject(box(*self.bounds), from_proj=self.proj, to_proj="EPSG:4326").bounds
        if blm_source == 'browse':
            from geogeniustools.images.browse_image import BrowseImage
            ref = BrowseImage(self.cat_id, bbox=bounds).read()
        else:
            from geogeniustools.images.tms_image import TmsImage
            tms = TmsImage(zoom=self._calc_tms_zoom(self.affine[0]), bbox=bounds, **kwargs)
            ref = np.rollaxis(tms.read(), 0, 3)
        out = np.dstack([rio_match(data[:, :, idx], ref[:, :, idx].astype(np.double) / 255.0)
                         for idx in range(data.shape[-1])])
        if 'stretch' in kwargs or 'gamma' in kwargs:
            return self._histogram_stretch(out, **kwargs)
        else:
            return out

    def histogram_stretch(self, use_bands, **kwargs):
        """ entry point for contrast stretching """
        data = self._read(self[use_bands, ...], **kwargs)
        data = np.rollaxis(data.astype(np.float32), 0, 3)
        return self._histogram_stretch(data, **kwargs)

    def _histogram_stretch(self, data, **kwargs):
        """ perform a contrast stretch and/or gamma adjustment """
        limits = {}
        # get the image min-max statistics
        for x in range(3):
            band = data[:, :, x]
            try:
                limits[x] = np.percentile(band, kwargs.get("stretch", [0, 100]))
            except IndexError:
                # this band has no dynamic range and cannot be stretched
                return data
        # compute the stretch
        for x in range(3):
            band = data[:, :, x]
            if 0 in band:
                band = np.ma.masked_values(band, 0).compressed()
            top = limits[x][1]
            bottom = limits[x][0]
            if top != bottom:  # catch divide by zero
                data[:, :, x] = (data[:, :, x] - bottom) / float(top - bottom) * 255.0
        data = np.clip(data, 0, 255).astype("uint8")
        # gamma adjust
        if "gamma" in kwargs:
            invGamma = 1.0 / kwargs['gamma']
            lut = np.array([((i / 255.0) ** invGamma) * 255
                            for i in np.arange(0, 256)]).astype("uint8")
            data = np.take(lut, data)
        return data

    def ndvi(self, **kwargs):
        """
        Calculates Normalized Difference Vegetation Index using NIR and Red of an image.

        Returns: numpy array with ndvi values
        """
        data = self._read(self[self._ndvi_bands, ...]).astype(np.float32)
        return (data[0, :, :] - data[1, :, :]) / (data[0, :, :] + data[1, :, :])

    def ndwi(self):
        """
        Calculates Normalized Difference Water Index using Coastal and NIR2 bands for WV02, WV03.
        For Landsat8 and sentinel2 calculated by using Green and NIR bands.

        Returns: numpy array of ndwi values
        """
        data = self._read(self[self._ndwi_bands, ...]).astype(np.float32)
        return (data[1, :, :] - data[0, :, :]) / (data[0, :, :] + data[1, :, :])

    def plot(self, spec="rgb", **kwargs):
        """ Plot the image with MatplotLib

        Plot sizing includes default borders and spacing. If the image is shown in Jupyter the outside whitespace will be automatically cropped to save size, resulting in a smaller sized image than expected.

        Histogram options:
            * 'equalize': performs histogram equalization on the image.
            * 'minmax': stretch the pixel range to the minimum and maximum input pixel values. Equivalent to stretch=[0,100].
            * 'match': match the histogram to the Maps API imagery. Pass the additional keyword blm_source='browse' to match to the Browse Service (image thumbnail) instead.
            * 'ignore': Skip dynamic range adjustment, in the event the image is already correctly balanced and the values are in the correct range.

        Gamma values greater than 1 will brighten the image midtones, values less than 1 will darken the midtones.

        Plots generated with the histogram options of 'match' and 'equalize' can be combined with the stretch and gamma options. The stretch and gamma adjustments will be applied after the histogram adjustments.

        Args:
            w (float or int): width of plot in inches at 72 dpi, default is 10
            h (float or int): height of plot in inches at 72 dpi, default is 10
            title (str): Title to use on the plot
            fontsize (int): Size of title font, default is 22. Size is measured in points.
            bands (list): bands to use for plotting, such as bands=[4,2,1]. Defaults to the image's natural RGB bands. This option is useful for generating pseudocolor images when passed a list of three bands. If only a single band is provided, a colormapped plot will be generated instead.
            cmap (str): MatPlotLib colormap name to use for single band images. Default is colormap='Grey_R'.
            histogram (str): either 'equalize', 'minmax', 'match', or ignore
            stretch (list): stretch the histogram between two percentile values, default is [2,98]
            gamma (float): adjust image gamma, default is 1.0
        """

        if self.shape[0] == 1 or ("bands" in kwargs and len(kwargs["bands"]) == 1):
            if "cmap" in kwargs:
                cmap = kwargs["cmap"]
                del kwargs["cmap"]
            else:
                cmap = "Greys_r"
            self._plot(tfm=self._single_band, cmap=cmap, **kwargs)
        else:
            if spec == "rgb" and self._has_token(**kwargs):
                self._plot(tfm=self.rgb, **kwargs)
            else:
                self._plot(tfm=getattr(self, spec), **kwargs)

    def _has_token(self, **kwargs):
        if "access_token" in kwargs or "MAPBOX_API_KEY" in os.environ:
            return True
        else:
            return False

    def _plot(self, tfm=lambda x: x, **kwargs):
        assert has_pyplot, "To plot images please install matplotlib"
        assert self.shape[1] and self.shape[-1], "No data to plot, dimensions are invalid {}".format(str(self.shape))

        f, ax1 = plt.subplots(1, figsize=(kwargs.get("w", 10), kwargs.get("h", 10)))
        ax1.axis('off')
        ax1.set_title(kwargs.get('title', ''), fontsize=kwargs.get('fontsize', 22))
        plt.imshow(tfm(**kwargs), interpolation='nearest', cmap=kwargs.get("cmap", None))
        plt.show(block=False)

    def _read(self, data, **kwargs):
        if hasattr(data, 'read'):
            return data.read(**kwargs)
        else:
            return data.compute(scheduler=threaded_get)

    def _single_band(self, **kwargs):
        arr = self._read(self, **kwargs)
        return arr[0, :, :]

    def _calc_tms_zoom(self, scale):
        for z in range(15, 20):
            b = mercantile.bounds(0, 0, z)
            if scale > math.sqrt((b.north - b.south) * (b.east - b.west) / (256 * 256)):
                return z

    def preview(self,
                bands=None,
                height='500px',
                bounds=None,
                center=None,
                min_zoom=0,
                max_zoom=22,
                zoom=None,
                color_map=None,
                gamma=None,
                saturation=None,
                contrast=None,
                bias=None,
                ext='png',
                nodata=None):
        """ Preview the image with Mapboxgj-jupyter

        Args:
            bands (list): bands to use for preview, such as bands=[4,2,1]. Defaults to the image's natural RGB bands
            height (str): height of map div, default is '500px'
            bounds (list): bounds of tile such as [0, 0, 1, 1], default if the bounds of image
            center (list): center of map of which the unit is degree such as [0, 0], default is the center of bounds
            min_zoom (int): min zoom of map. default is 0
            max_zoom (int): max zoom of map, default is 22
            zoom (int): initial zoom of map, default is the same with min_zoom
            color_map (str): color map of tile such as 'hot' ans 'rgb', default depend on the tile service
            gamma (float): brightness of tile of which the value is between [0.8, 2.4]
            saturation (float): saturation of tile of which the value is between [0, 2]
            contrast (float): contrast of tile of which the value is between [0, 30], and used with bias
            bias (float): bias of tile of which the value is between [0, 1] and used with contrast
            ext (str): format of tile, supported is ["png", "jpg"], default is png
            nodata (float): nodata value of tile, default depend on the image
        """

        assert has_mapboxgl, "To preview images please install mapboxgl"
        assert self.shape[1] and self.shape[-1], "No data to preview, dimensions are invalid {}".format(str(self.shape))
        assert self._path, "No data path to preview for image type {}".format(self.__class__.__name__)
        assert ext in ["png", "jpg"], "Don't support the ext type {}".format(ext)

        if not bounds:
            bounds = list(self.bounds)
        if not center:
            center = [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2]
        if not zoom:
            zoom = min_zoom
        tile_args = ""
        if bands:
            assert len(bands) <= 3, 'Preview method only supports less than 3 band'
            band_list = []
            for band in bands:
                assert isinstance(band, int), "band index must be integer-like: {}".format(band)
                band_list.append(str(band))
            tile_args += "&bands={}".format(",".join(band_list))
        if color_map:
            tile_args += "&colorMap={}".format(color_map)
        if gamma:
            assert 0.8 <= gamma <= 2.4, "gamma must be between [0.8, 2.4]".format(gamma)
            tile_args += "&gamma={}".format(gamma)
        if saturation:
            assert 0 <= saturation <= 2, "saturation must be between [0, 2]".format(saturation)
            tile_args += "&saturation={}".format(saturation)
        if contrast:
            assert 0 <= contrast <= 30, "contrast must be between [0, 30]".format(contrast)
            tile_args += "&contrast={}".format(contrast)
        if bias:
            assert 0 <= bias <= 1, "bias must be between [0, 1]".format(bias)
            tile_args += "&bias={}".format(bias)
        if nodata:
            assert isinstance(nodata, float) or isinstance(nodata, int), "nodata must be float-like: {}".format(nodata)
            tile_args += "&nodata={}".format(nodata)
        access_token = os.getenv('MAPBOX_ACCESS_TOKEN',
                                 'pk.eyJ1IjoibmlyYW44MTQ4MDQxMDIiLCJhIjoiY2p5aTB3eHFkMDUyZzNlcnl6cjFvYjVieSJ9.U8WSU9l43y1VR1Z26tWbIw')
        if isinstance(self._path, list):
            tiles_list = []
            for path in self._path:
                tiles = dict()
                tiles["tiles_minzoom"] = min_zoom
                tiles["tiles_maxzoom"] = max_zoom
                tiles["tiles_bounds"] = bounds
                tiles["tiles_url"] = "%(base_url)s/image/tile/{x}/{y}/{z}?url=%(data_url)s&ext=%(ext)s%(tile_args)s" % {
                    'base_url': PUBLIC_RDA_ENDPOINT,
                    'data_url': path,
                    'ext': ext,
                    'tile_args': tile_args
                }
                tiles_list.append(tiles)
            rtlv(access_token=access_token,
                 tiles_list=tiles_list,
                 height=height,
                 zoom=zoom,
                 center=center).show()
        else:
            tiles_url = "%(base_url)s/image/tile/{x}/{y}/{z}?url=%(data_url)s&ext=%(ext)s%(tile_args)s" % {
                'base_url': PUBLIC_RDA_ENDPOINT,
                'data_url': self._path,
                'ext': ext,
                'tile_args': tile_args
            }
            rtv(access_token=access_token,
                tiles_url=tiles_url,
                tiles_bounds=bounds,
                tiles_minzoom=min_zoom,
                tiles_maxzoom=max_zoom,
                height=height,
                zoom=zoom,
                center=center).show()


class BandMethodsTemplate(object):
    @property
    def _rgb_bands(self):
        raise NotImplementedError("RGB bands undefined for image type {}".format(self.__class__.__name__))

    @property
    def _ndvi_bands(self):
        raise NotImplementedError("NDVI bands undefined for image type {}".format(self.__class__.__name__))

    @property
    def _ndwi_bands(self):
        raise NotImplementedError("NDWI bands undefined for image type {}".format(self.__class__.__name__))
