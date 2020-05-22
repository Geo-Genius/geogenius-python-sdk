from geogeniustools.images.rda_image import RDAImage
from geogeniustools.rda.interface import RDA

rda = RDA()


class OBSImage(RDAImage):
    """
    Dask based access to geotiffs on OBS.

    Args:
        path (string): path to the geotiff file in S3.
        proj (string): destination EPSG string, e.g. 'EPSG:4326'
            Perform optional reprojection if needed.
        src_proj (string): source EPSG string
            Define the source projection if it can't be automatically determined.

    Example:
        >>> img = OBSImage('obs://landsat-pds/c1/L8/139/045/LC08_L1TP_139045_20170304_20170316_01_T1/LC08_L1TP_139045_20170304_20170316_01_T1_B3.TIF')
    """

    def __new__(cls, path, **kwargs):
        graph = cls._build_graph(path, kwargs.get("proj", None), kwargs.get("src_proj", None))
        cls._path = path
        try:
            self = super(OBSImage, cls).__new__(cls, graph)
        except KeyError as e:
            print(e)
            raise
        self = self.aoi(**kwargs)
        self._path = path
        self._graph = graph
        return self

    @staticmethod
    def _build_graph(path, proj=None, src_proj=None):
        s3 = rda.GdalImageRead(path=path)
        params = {
            "Dest pixel-to-world transform": "",
            "Resampling Kernel": "INTERP_BILINEAR",
            "Source SRS Code": "",
            "Source pixel-to-world transform": "",
            "Dest SRS Code": "",
            "Background Values": "[0]"
        }
        if proj is not None:
            params['Dest SRS Code'] = proj
            if src_proj is not None:
                params['Source SRS Code'] = src_proj
            s3 = rda.Reproject(s3, **params)
        return s3
