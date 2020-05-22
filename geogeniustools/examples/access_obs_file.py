from eolearn.core import FeatureType, SaveToDisk, OverwritePermission

from geogeniustools.eolearn.geogenius_areas import PixelRangeSplitter
from geogeniustools.eolearn.geogenius_io import ImportFromGeogenius
from geogeniustools.images.catalog_image import CatalogImage
from geogeniustools.images.obs_image import OBSImage
from shapely.geometry import box
import os
import numpy as np


def get_current_folder(str):
    return os.path.abspath(str)


if __name__ == '__main__':
    os.environ['ACCESS_KEY'] = "xxx"
    os.environ['SECRET_KEY'] = "xxx"
    img = CatalogImage(cat_id="OBS1/92e5a27a-177d-4c51-a2da-8d6455c4db78")
    print("bounds: {}".format(img.bounds))
    print("shape {}".format(img.shape))

    aoi = (116.2309781689422, 40.2470619989317, 116.2632549689422, 40.27933879893169)
    img = img.aoi(bbox=aoi)
    print("shape {}".format(img.shape))
    arr = img.read()
    print(arr)
