import os

from geogeniustools.images.catalog_image import CatalogImage
from geogeniustools.images.mosaic_image import MosaicImage


def get_current_folder(str):
    return os.path.abspath(str)


if __name__ == '__main__':
    os.environ['ACCESS_KEY'] = "xxx"
    os.environ['SECRET_KEY'] = "xxx"
    img = MosaicImage(cat_ids=
                      ["OBS1/5c898489-3073-4d21-a6be-c7079d890a79", "OBS1/d570ce97-ddc3-4b00-b8d9-0d54b2df651c"])
    print("bounds: {}".format(img.bounds))
    print("shape {}".format(img.shape))

    img1 = CatalogImage(cat_id="OBS1/5c898489-3073-4d21-a6be-c7079d890a79")
    print("bounds: {}".format(img1.bounds))
    print("shape {}".format(img1.shape))

    img2 = CatalogImage(cat_id="OBS1/d570ce97-ddc3-4b00-b8d9-0d54b2df651c")
    print("bounds: {}".format(img2.bounds))
    print("shape {}".format(img2.shape))
    img.preview(bands=[3, 2, 1], color_map="hot", center=[109.9843619312777, 45.98256665224027], zoom=3)
