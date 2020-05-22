import datetime

import dateutil
import sentinelhub
from eolearn.core import EOPatch, FeatureType
from eolearn.core.eodata import _FeatureDict
import numpy as np


class GeogeniusEOPatch(EOPatch):

    def __setattr__(self, key, value, feature_name=None):
        """Raises TypeError if feature type attributes are not of correct type.

        In case they are a dictionary they are cast to _DaskArrayLoader class
        """
        if FeatureType.has_value(key) and not isinstance(value, _DaskArrayLoader):
            feature_type = FeatureType(key)
            value = self._parse_feature_type_value(feature_type, value)

        super().__setattr__(key, value, feature_name)

    @staticmethod
    def _parse_feature_type_value(feature_type, value):
        """ Checks or parses value which will be assigned to a feature type attribute of `EOPatch`. If the value
        cannot be parsed correctly it raises an error.

        :raises: TypeError, ValueError
        """
        if feature_type.has_dict() and isinstance(value, dict):
            return value if isinstance(value, _FeatureDictV2) else _FeatureDictV2(value, feature_type)

        if feature_type is FeatureType.BBOX:
            if value is None or isinstance(value, sentinelhub.BBox):
                return value
            if isinstance(value, (tuple, list)) and len(value) == 5:
                return sentinelhub.BBox(value[:4], crs=value[4])

        if feature_type is FeatureType.TIMESTAMP:
            if isinstance(value, (tuple, list)):
                return [timestamp if isinstance(timestamp, datetime.date) else dateutil.parser.parse(timestamp)
                        for timestamp in value]

        raise TypeError('Attribute {} requires value of type {} - '
                        'failed to parse given value'.format(feature_type, feature_type.type()))


class _DaskArrayLoader:
    """ Class taking care for loading objects from Daskarray. Its purpose is to support lazy loading
    """

    def __init__(self, dask_array, pad_x=0, pad_y=0):
        """
        :param dask_array: dask array object that load from
        :type DaskArray
        """
        self.dask_array = dask_array
        self.pad_x = pad_x
        self.pad_y = pad_y

    def load(self):
        """ Method which loads data from dask array
        """
        if self.pad_x == 0 and self.pad_y == 0:
            return self.dask_array.compute()
        else:
            data = self.dask_array.compute()
            return np.pad(data, ((0, 0), (0, self.pad_y), (0, self.pad_x), (0, 0)), 'constant')


class _FeatureDictV2(_FeatureDict):
    """A dictionary structure that holds features of certain feature type.

    It checks that features have a correct and dimension. It also supports lazy loading by accepting a function as a
    feature value, which is then called when the feature is accessed.

    :param feature_dict: A dictionary of feature names and values
    :type feature_dict: dict(str: object)
    :param feature_type: Type of features
    :type feature_type: FeatureType
    """

    def __getitem__(self, feature_name, load=True):
        """Implements lazy loading."""
        value = super().__getitem__(feature_name)

        if isinstance(value, _DaskArrayLoader) and load:
            value = value.load()
            self[feature_name] = value
            return value

        return value

    def _parse_feature_value(self, value):
        """ Checks if value fits the feature type. If not it tries to fix it or raise an error

        :raises: ValueError
        """
        if isinstance(value, _DaskArrayLoader):
            return value

        return super()._parse_feature_value(value)
