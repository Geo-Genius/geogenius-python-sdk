import os
from collections import defaultdict
import threading
from tempfile import NamedTemporaryFile
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

try:
    from functools import lru_cache # python 3
except ImportError:
    from cachetools.func import lru_cache

from skimage.io import imread
import pycurl
import numpy as np

#import warnings
#warnings.filterwarnings('ignore')


MAX_RETRIES = 5
_curl_pool = defaultdict(pycurl.Curl)


@lru_cache(maxsize=128)
def load_url(url, shape=(8, 256, 256)):
    """ Loads a geotiff url inside a thread and returns as an ndarray """
    ext = ".tif"
    success = False
    for i in range(MAX_RETRIES):
        thread_id = threading.current_thread().ident
        _curl = _curl_pool[thread_id]
        _curl.setopt(_curl.URL, url)
        _curl.setopt(pycurl.NOSIGNAL, 1)
        with NamedTemporaryFile(prefix="geogenius", suffix=ext, delete=False) as temp: # TODO: apply correct file extension
            _curl.setopt(_curl.WRITEDATA, temp.file)
            _curl.perform()
            code = _curl.getinfo(pycurl.HTTP_CODE)
            try:
                if(code != 200):
                    raise TypeError("Request for {} returned unexpected error code: {}".format(url, code))
                temp.file.flush()
                temp.close()
                arr = imread(temp.name)
                if len(arr.shape) == 3:
                    arr = np.rollaxis(arr, 2, 0)
                else:
                    arr = np.expand_dims(arr, axis=0)
                success = True
                return arr
            except Exception as e:
                _curl.close()
                del _curl_pool[thread_id]
            finally:
                temp.close()
                os.remove(temp.name)

    if success is False:
        raise TypeError("Request for {} returned unexpected error code: {}".format(url, code))
    return arr

