import numpy as np
from skimage.transform._geometric import GeometricTransform
from affine import Affine
from collections import Sequence
import pyproj
import rasterio


class AffineTransform(GeometricTransform):
    def __init__(self, affine, proj=None):
        self._affine = affine
        self._iaffine = None
        self.proj = proj

    def rev(self, lng, lat, z=0):
        if self._iaffine is None:
            self._iaffine = ~self._affine
        px, py = (self._iaffine * (lng, lat))
        if type(px).__name__ == 'ndarray' and type(py).__name__ == 'ndarray':
            return np.rint(np.asarray(px)), np.rint(np.asarray(py))
        else:
            return int(round(px)), int(round(py))

    def fwd(self, x, y, z=0):
        return self._affine * (x, y)

    def __call__(self, coords):
        assert isinstance(coords, np.ndarray) and len(coords.shape) == 2 and coords.shape[1] == 2
        _coords = np.copy(coords)
        self._affine.itransform(_coords)
        return _coords

    def inverse(self, coords):
        assert isinstance(coords, np.ndarray) and len(coords.shape) == 2 and coords.shape[1] == 2
        if self._iaffine is None:
            self._iaffine = ~self._affine
        _coords = np.copy(coords)
        self._iaffine.itransform(_coords)
        return _coords

    def residuals(self, src, dst):
        return super(AffineTransform, self).residuals(src, dst)

    def __add__(self, other):
        if isinstance(other, Sequence) and len(other) == 2:
            shift = np.asarray(other)
            return AffineTransform(self._affine * Affine.translation(shift[0], shift[1]), proj=self.proj)
        else:
            raise NotImplemented

    def __sub__(self, other):
        try:
            return self.__add__(-other)
        except:
            return self.__add__([-e for e in other])

    @classmethod
    def from_georef(cls, georef):
        tfm = Affine.from_gdal(georef["translateX"], georef["scaleX"], georef["shearX"],
                               georef["translateY"], georef["shearY"], georef["scaleY"])
        return cls(tfm, proj=georef["spatialReferenceSystemCode"])

CUSTOM_PRJ = {
    "EPSG:54008": "+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
}

def get_proj(prj_code):
    """
      Helper method for handling projection codes that are unknown to pyproj

      Args:
          prj_code (str): an epsg proj code

      Returns:
          projection: a pyproj projection
    """
    if prj_code in CUSTOM_PRJ:
        proj = pyproj.Proj(CUSTOM_PRJ[prj_code])
    else:
        proj = pyproj.Proj(init=prj_code)
    return proj

def pad(array, transform, pad_width, mode='constant', **kwargs):
    """pad array and adjust affine transform matrix.

    Parameters
    ----------
    array: ndarray
        Numpy ndarray, The desired shape of each image as (channel, width, height) in pixels.
    transform: Affine transform
        transform object mapping pixel space to coordinates
    pad_width: tuple
        Number of values padded or cut to the edges of each axis.
        ((before_1, after_1), ... (before_N, after_N)) unique pad widths for each axis.
        Note:number can be negative number which means cut number of pixels.
        if pad_width tuple consist of non negative numbers, means pad array,
        else if pad_width tuple consist of non negative numbers, means cut array,
        but do not support pad and cut in different dimensions at the same time.
    mode: str or function
        define the method for determining padded values
        One of the following string values or a user supplied function.

        'constant' (default)
            Pads with a constant value.
        'edge'
            Pads with the edge values of array.
        'linear_ramp'
            Pads with the linear ramp between end_value and the
            array edge value.
        'maximum'
            Pads with the maximum value of all or part of the
            vector along each axis.
        'mean'
            Pads with the mean value of all or part of the
            vector along each axis.
        'median'
            Pads with the median value of all or part of the
            vector along each axis.
        'minimum'
            Pads with the minimum value of all or part of the
            vector along each axis.
        'reflect'
            Pads with the reflection of the vector mirrored on
            the first and last values of the vector along each
            axis.
        'symmetric'
            Pads with the reflection of the vector mirrored
            along the edge of the array.
        'wrap'
            Pads with the wrap of the vector along the axis.
            The first values are used to pad the end and the
            end values are used to pad the beginning.
        'empty'
            Pads with undefined values.

            .. versionadded:: 1.17

        <function>
            Padding function, see Notes.

    Returns
    -------
    (array, transform): tuple
        Tuple of new array and affine transform
    """
    transform = rasterio.guard_transform(transform)
    padded_trans = list(transform)

    pad_x = pad_width[1][0]
    pad_y = pad_width[2][0]
    change_mode = get_change_mode(pad_width)
    if 'pad' == change_mode:
        padded_array = np.pad(array, pad_width, mode, **kwargs)
    if 'cut' == change_mode:
        bottom_x = array.shape[0] if pad_width[0][1] == 0 else pad_width[0][1]
        bottom_y = array.shape[1] if pad_width[1][1] == 0 else pad_width[1][1]
        bottom_z = array.shape[1] if pad_width[2][1] == 0 else pad_width[2][1]
        padded_array = array[-pad_width[0][0]: bottom_x, -pad_width[1][0]: bottom_y,
                       -pad_width[2][0]: bottom_z]

    padded_trans[2] -= pad_x * padded_trans[0]
    padded_trans[5] -= pad_y * padded_trans[4]
    return padded_array, rasterio.transform.Affine(*padded_trans[:6])

def get_change_mode(pad_width):
    if np.array(list(map(list, pad_width))).min() >= 0:
        return 'pad'
    elif np.array(list(map(list, pad_width))).max() <= 0:
        return 'cut'
    else:
        raise ValueError("unsupported pad_with arguments : {}".format(pad_width))

