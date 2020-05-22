from geogeniustools import Catalog
from geogeniustools.images.rda_image import RDAImage
from geogeniustools.rda.error import UnsupportedImageType
from geogeniustools.rda.interface import RDA

rda = RDA()


class MosaicImage(RDAImage):
    """
    Dask based access to geotiffs on Mosaic Images.

    Args:
        cat_ids(list): catalog ids of images on geogenius. Only support ObsTiff catalog id
        paths(list): obs paths of images on geogenius. Only support ObsTiff path
    Example:
        >>> img = MosaicImage(cat_ids=['543a6119-186b-473d-8c26-2b139b19b347', 'f54d3f70-39a4-4894-922e-48a68cf21b4a'])
        >>> img = MosaicImage(paths=['obs://geogenius-bucket/object-extraction-output_2_12.tif',
        'obs://geogenius-bucket/object-extraction-output_2_13.tif'])
        >>> img = MosaicImage(cat_ids=['543a6119-186b-473d-8c26-2b139b19b347'],
        paths=['obs://geogenius-bucket/object-extraction-output_2_13.tif'])
    """

    def __new__(cls, cat_ids=None, paths=None, **kwargs):
        pixel_selection = kwargs.get("pixel_selection")
        graph = cls._build_graph(cat_ids, paths, pixel_selection)
        try:
            self = super(MosaicImage, cls).__new__(cls, graph)
        except KeyError as e:
            print(e)
            raise
        self = self.aoi(**kwargs)
        self._cat_ids = cat_ids
        self._paths = paths
        self._graph = graph
        self._path = self._get_data_urls(cat_ids, paths)
        return self

    @staticmethod
    def _get_data_urls(cat_ids, paths):
        if (cat_ids is None or len(cat_ids) <= 0) and (paths is None or len(paths) <= 0):
            raise ValueError('cat_ids should be greater than 0 or obs_paths should be greater than 0')
        c = Catalog()
        data_urls = []
        if cat_ids is not None and len(cat_ids) >= 0:
            for cat_id in cat_ids:
                image = c.get(cat_id=cat_id)
                image_type = image['sourceType'].lower()
                data_url = image['dataUrl']
                if image_type != "obs1":
                    raise UnsupportedImageType('Mosaic image only support OBS tiff')
                data_urls.append(data_url)
        if paths is not None and len(paths) >= 0:
            for path in paths:
                data_urls.append(path)
        return data_urls

    @staticmethod
    def _build_graph(cat_ids, paths, pixel_selection):
        if pixel_selection is None:
            pixel_selection = "first"
        data_urls = MosaicImage._get_data_urls(cat_ids, paths)
        mosaic_images = rda.Mosaic(paths=data_urls, pixel_selection=pixel_selection)
        return mosaic_images
