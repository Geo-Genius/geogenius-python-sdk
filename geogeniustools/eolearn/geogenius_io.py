"""
Module containing tasks used for reading EOPatch from Geogenius
"""

from sentinelhub import CRS, BBox
from eolearn.core import EOTask, EOPatch
import numpy as np

from geogeniustools.eolearn.geogenius_data import _DaskArrayLoader, GeogeniusEOPatch


class ImportFromGeogenius(EOTask):
    """ Task for importing data from a Geogenius Image into an EOPatch

    The task can take an existing EOPatch and read the part of Geogenius image, which intersects with its bounding
    box, into a new feature. But if no EOPatch is given it will create a new EOPatch, if a bbox is given, it will set
    the bbox as the EOPath bbox, else read entire Geogenius image into a feature and set a bounding box of the new EOPatch.

    Note that if Geogenius image is not completely spatially aligned with location of given EOPatch it will try to fit it
    as best as possible. However it will not do any spatial resampling or interpolation on Geo-TIFF data.
    """
    def __init__(self, feature, geogenius_image, timestamp_size=None, image_dtype=None, no_data_value=0, **kwargs):
        """
        :param feature:  EOPatch feature into which data will be imported
        :type feature: (FeatureType, str)
        :param geogenius_image: A image object, the type of which is a subclass RDAImage
        :type feature: (RDAImage)
        :param timestamp_size: In case data will be imported into time-dependant feature this parameter can be used to
        specify time dimension. If not specified, time dimension will be the same as size of FeatureType.TIMESTAMP
        feature. If FeatureType.TIMESTAMP does not exist it will be set to 1.
        When converting data into a feature channels of given tiff image should be in order
        T(1)B(1), T(1)B(2), ..., T(1)B(N), T(2)B(1), T(2)B(2), ..., T(2)B(N), ..., ..., T(M)B(N)
        where T and B are the time and band indices.
        :type timestamp_size: int
        :param image_dtype: Type of data of new feature imported from tiff image
        :type image_dtype: numpy.dtype
        :param no_data_value: Values where given Geo-Tiff image does not cover EOPatch
        :type no_data_value: int or float
        """
        self.feature = self._parse_features(feature)
        self.geogenius_image = geogenius_image
        self.timestamp_size = timestamp_size
        self.image_dtype = image_dtype
        self.no_data_value = no_data_value

    def execute(self, eopatch=None, bbox=None, pixelbox=None):
        """ Execute method which adds a new feature to the EOPatch

         :param eopatch: input EOPatch or None if a new EOPatch should be created
         :type eopatch: EOPatch or None
         :param bbox: specifies the bounding box of the requested image. Coordinates must be in
         the specified coordinate reference system.
         :type bbox: BBox or None
         :param pixelbox: specifies the pixel box of the requested image. pixelbox is initialize from below
         representations: ``[min_pixel_x, min_pixel_y, max_pixel_x, max_pixel_y]``

         Note: min_pixel_x, min_pixel_y, max_pixel_x, max_pixel_y is the relative coordinates according to the image
         pixel array.
         If `bbox` is set, `pixelbox` will be ignored automatically.
         :type pixelbox: array
         :return: New EOPatch with added raster layer
         :rtype: EOPatch
         """
        if pixelbox is None or bbox is not None:
            return self._load_from_bbox(eopatch=eopatch, bbox=bbox)
        else:
            return self._load_from_pixelbox(eopatch=eopatch, pixelbox=pixelbox)

    def _load_from_bbox(self, eopatch=None, bbox=None):
        feature_type, feature_name = next(self.feature())
        if eopatch is None:
            eopatch = GeogeniusEOPatch()
            if bbox is not None:
                eopatch.bbox = bbox
        data_bounds = self.geogenius_image.bounds
        data_bbox = BBox((data_bounds[0], data_bounds[1], data_bounds[2], data_bounds[3]),
                         CRS(self.geogenius_image.proj))

        if eopatch.bbox is None:
            eopatch.bbox = data_bbox

        if data_bbox.geometry.intersects(eopatch.bbox.geometry):
            data = self.geogenius_image.aoi(
                bbox=[eopatch.bbox.min_x, eopatch.bbox.min_y, eopatch.bbox.max_x, eopatch.bbox.max_y])
            if self.image_dtype is not None:
                data = data.astype(self.image_dtype)

            if not feature_type.is_spatial():
                data = data.flatten()

            if feature_type.is_timeless():
                data = np.moveaxis(data, 0, -1)
            else:
                channels = data.shape[0]

                times = self.timestamp_size
                if times is None:
                    times = len(eopatch.timestamp) if eopatch.timestamp else 1

                if channels % times != 0:
                    raise ValueError(
                        'Cannot import as a time-dependant feature because the number of tiff image channels '
                        'is not divisible by the number of timestamps')

                data = data.reshape((times, channels // times) + data.shape[1:])
                data = np.moveaxis(data, 1, -1)
                eopatch[feature_type][feature_name] = _DaskArrayLoader(data)
                return eopatch
        else:
            raise ValueError("AOI does not intersect image: {} not in {}".format(self.geogenius_image.bounds, eopatch.bbox))

    def _check_pixelbox(self, pixelbox):
        min_pixel_x, min_pixel_y, max_pixel_x, max_pixel_y = pixelbox
        total_pixel_y, total_pixel_x = self.geogenius_image.shape[1:]
        if 0 <= min_pixel_x < total_pixel_x and 0 <= min_pixel_y < total_pixel_y and \
           min_pixel_x < max_pixel_x and min_pixel_y < max_pixel_y:
            return True
        else:
            raise ValueError(
                "Pixel box: {} is invalid according to image bounds: {}".format(pixelbox, self.geogenius_image.shape[1:]))

    def _load_from_pixelbox(self, eopatch=None, pixelbox=None):
        self._check_pixelbox(pixelbox)
        feature_type, feature_name = next(self.feature())
        if eopatch is None:
            eopatch = GeogeniusEOPatch()

        min_pixel_x, min_pixel_y, max_pixel_x, max_pixel_y = pixelbox
        data = self.geogenius_image[:,min_pixel_y:max_pixel_y, min_pixel_x:max_pixel_x]
        real_y_pixel, real_x_pixel = data.shape[1:]
        pad_x = (max_pixel_x - min_pixel_x) - real_x_pixel
        pad_y = (max_pixel_y - min_pixel_y) - real_y_pixel

        data_bounds = data.bounds
        data_bbox = BBox((data_bounds[0], data_bounds[1], data_bounds[2], data_bounds[3]),
                         CRS(self.geogenius_image.proj))
        eopatch.bbox = data_bbox

        if self.image_dtype is not None:
            data = data.astype(self.image_dtype)

        if not feature_type.is_spatial():
            data = data.flatten()

        if feature_type.is_timeless():
            data = np.moveaxis(data, 0, -1)
        else:
            channels = data.shape[0]

            times = self.timestamp_size
            if times is None:
                times = len(eopatch.timestamp) if eopatch.timestamp else 1

            if channels % times != 0:
                raise ValueError(
                    'Cannot import as a time-dependant feature because the number of tiff image channels '
                    'is not divisible by the number of timestamps')

            data = data.reshape((times, channels // times) + data.shape[1:])
            data = np.moveaxis(data, 1, -1)
            eopatch[feature_type][feature_name] = _DaskArrayLoader(data, pad_x=pad_x, pad_y=pad_y)
            return eopatch
