import os
import tempfile

import math
import numpy as np
from eolearn.io import ExportToTiff
from eolearn.core import FeatureType, SaveToDisk, OverwritePermission, LinearWorkflow, EOExecutor
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from sentinelhub import BBox, CRS
from tqdm import tqdm

from geogeniustools.eolearn.geogenius_data import GeogeniusEOPatch
from geogeniustools.eolearn.geogenius_io import ImportFromGeogenius
from geogeniustools.eolearn.geogenius_tasks import IndexTask
from geogeniustools.rda.error import PatchSetError
from geogeniustools.s3 import S3


class GeogeniusPatchSet:
    """
    GeogeniusPatchSet is a collection of image patches that are generated using the'splitter' method on the
     'geogenius_image'.
    """
    def __init__(self, geogenius_image, splitter, feature=(FeatureType.DATA, 'BANDS')):
        """
        :param geogenius_image: Image resource has data values and metadata.
        :type geogenius_image: RDAImage
        :param splitter: A tool that splits the given area into smaller parts withe same pixel size. Given the area it
        calculates its bounding box and splits it into smaller bounding boxes based on xy_step_shape.
        :type splitter: PixelRangeSplitter
        :param feature: Feature to be added.
        :type feature: (FeatureType.DATA, feature_name)
        """
        self.geogenius_image = geogenius_image
        self.splitter = splitter
        self.feature = feature
        self._splitter_check()
        self.shape = self._get_tile_rows_columns()
        self.patch_index = self._load_with_index()

    def _splitter_check(self):
        if self.geogenius_image.shape[1:] != self.splitter.total_pixel_shape:
            raise Exception("image size is not along with splitter size")
        tile_pixel_rows, tile_pixel_columns = self.splitter.tile_pixel_shape
        y_step, x_step = self.splitter.xy_step_shape
        if tile_pixel_rows < y_step or tile_pixel_columns < x_step:
            raise Exception("xy_step_shape:{} not allowed greater than tile_pixel_shape: {}"
                            .format(self.splitter.xy_step_shape, self.splitter.tile_pixel_shape))

    def _load_with_index(self):
        """
        Split image to a number of EOPatches(lazy load data) with given splitter,
        and index each EOPatch using two dimension list.

        :param feature: Feature to be loaded
        :type feature: (FeatureType, feature_name) or FeatureType
        """
        add_data = ImportFromGeogenius(feature=self.feature, geogenius_image=self.geogenius_image)
        tile_rows, tile_columns = self._get_tile_rows_columns()
        self.patch_index = [[0] * tile_columns for i in range(tile_rows)]
        index_feature = IndexTask(patch_index=self.patch_index)
        workflow = LinearWorkflow(add_data, index_feature)
        execution_args = []
        bbox_list = np.array(self.splitter.get_pixel_bbox_list())
        for idx, bbox in enumerate(bbox_list):
            row = idx % tile_rows
            column = idx // tile_rows
            execution_args.append({
                add_data: {'pixelbox': bbox},
                index_feature: {"row": row, "column": column}
            })
        executor = EOExecutor(workflow, execution_args)
        executor.run(workers=1, multiprocess=False)
        return self.patch_index

    def _is_loaded(self):
        """
        Judge whether already split and index image or not.
        """
        return False if self.patch_index is None else True

    def save_to_tiff(self, file_path, feature=None, no_data_value=None, merge_method="last", padding=0):
        """
        Save indexed EOPatches to a complete tiff.

        :param feature: Feature which will be exported
        :type feature: (FeatureType, str)
        :param file_path: path to save tiff
        :type file_path: str
        :param no_data_value: Value of pixels of tiff image with no data in EOPatch
        :type no_data_value: int or float
        :param merge_method: How to merge overlap EOPatches. "last" mean latter array overwrite former array,
            "first" mean former array overwrite latter array.
        :type merge_method: str
        """
        if not feature:
            feature = self.feature
        if not self._is_loaded():
            self._load_with_index(feature=feature)
        union_patch = self._patch_joint(self.patch_index, feature=feature, merge_method=merge_method, padding=padding)
        self._assure_folder_exist(path=file_path, path_type="file")
        temp_file = tempfile.mktemp(suffix=".tiff")
        try:
            export_tiff = ExportToTiff(feature, no_data_value=no_data_value)
            export_tiff.execute(union_patch, filename=temp_file)
            self._cog_translate(src_path=temp_file, dst_path=file_path)
        except Exception as e:
            raise PatchSetError(e.__str__())
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def save_to_obstiff(self, obs_path, feature=None, no_data_value=None, merge_method="last", padding=0):
        """
        Save indexed EOPatches to a complete tiff, and upload to obs.

        :param feature: Feature which will be exported
        :type feature: (FeatureType, str)
        :param obs_path: obs path to save tiff
        :type obs_path: str
        :param no_data_value: Value of pixels of tiff image with no data in EOPatch
        :type no_data_value: int or float
        :param merge_method: How to merge overlap EOPatches. "last" mean latter array overwrite former array,
            "first" mean former array overwrite latter array.
        :type merge_method: str
        """
        if not feature:
            feature = self.feature
        temp_file = tempfile.mktemp(suffix=".tiff")
        try:
            self.save_to_tiff(temp_file, feature=feature, no_data_value=no_data_value,
                              merge_method=merge_method, padding=padding)
            s3 = S3()
            return s3.upload(local_file=temp_file, obs_path=obs_path)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    @staticmethod
    def _cog_translate(src_path, dst_path):
        """
        Convert tiff to cog.
        """
        output_profile = cog_profiles.get("deflate")
        output_profile.update(dict(BIGTIFF=os.environ.get("BIGTIFF", "IF_SAFER")))
        output_profile.update({"BLOCKXSIZE": 256, "BLOCKYSIZE": 256})
        config = dict(
            NUM_THREADS=8,
            GDAL_TIFF_INTERNAL_MASK=os.environ.get("GDAL_TIFF_INTERNAL_MASK", True),
            GDAL_TIFF_OVR_BLOCKSIZE=str(os.environ.get("GDAL_TIFF_OVR_BLOCKSIZE", 128))
        )
        cog_translate(src_path, dst_path, output_profile, add_mask=False, web_optimized=False, config=config)

    def save_patch(self, save_folder, feature=None, overwrite_permission=OverwritePermission.OVERWRITE_PATCH,
                   compress_level=0):
        """
        Save indexed EOPatches to a folder.

        :param save_folder: folder to save eopatches
        :type save_folder: str
        :param feature: Feature to be exported
        :type feature: (FeatureType, feature_name) or FeatureType
        :param overwrite_permission: Permissions to overwrite exist EOPatch.
            Permissions are in the following hierarchy:
            - `ADD_ONLY` - Only new features can be added, anything that is already saved cannot be changed.
            - `OVERWRITE_FEATURES` - Overwrite only data for features which have to be saved. The remaining content of
             saved EOPatch will stay unchanged.
            - `OVERWRITE_PATCH` - Overwrite entire content of saved EOPatch and replace it with the new content.
        :type overwrite_permission: OverwritePermission
        :param compress_level: A level of data compression and can be specified with an integer from 0 (no compression)
            to 9 (highest compression).
        :type compress_level: int
        """
        if not feature:
            feature = self.feature
        if not self._is_loaded():
            self._load_with_index(feature=feature)
        tile_rows, tile_columns = self._get_tile_rows_columns()
        self._assure_folder_exist(save_folder)
        save_task = SaveToDisk(save_folder, features=[feature, FeatureType.BBOX],
                               overwrite_permission=overwrite_permission, compress_level=compress_level)
        workflow = LinearWorkflow(save_task)
        execution_args = []
        for row in range(tile_rows):
            for column in range(tile_columns):
                execution_args.append({
                    save_task: {
                        'eopatch_folder': 'patch_{row}_{column}'.format(row=row, column=column),
                        'eopatch': self.patch_index[row][column]
                    }
                })
        executor = EOExecutor(workflow, execution_args)
        executor.run(workers=1, multiprocess=False)

    @staticmethod
    def _assure_folder_exist(path, path_type="folder"):
        abspath = os.path.abspath(path)
        if path_type == "file":
            folder_path = os.path.dirname(abspath)
        elif path_type == "folder":
            folder_path = abspath
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    def _get_tile_rows_columns(self):
        """
        Get how number of split tiles for current image.
        """
        y_step, x_step = self.splitter.xy_step_shape
        tile_rows = math.ceil(self.geogenius_image.shape[1] / y_step)
        tile_columns = math.ceil(self.geogenius_image.shape[2] / x_step)
        return tile_rows, tile_columns

    def _patch_joint(self, patch_index, feature, merge_method, padding=0):
        """
        Integrate indexed EOPatches to a complete EOPatch.

        :param patch_index: A object manager the index of EOPatches.
        :type patch_index: list
        :param merge_method: How to merge overlap EOPatches. "last" mean latter array overwrite former array,
            "first" mean former array overwrite latter array.
        :type merge_method: str
        :param padding: Discarding borders when merge overlap EOPatches. 0 mean do not discard border.
        :type padding: int
        """
        feature_type, feature_name = feature
        if feature_type != FeatureType.DATA:
            raise PatchSetError("feature type should be FeatureType.DATA")
        tile_rows, tile_columns = self._get_tile_rows_columns()
        union_array = self._get_union_array(feature_name)
        for row in tqdm(range(tile_rows)):
            for column in range(tile_columns):
                patch_array = patch_index[row][column].data[feature_name]
                self._merge_array(union_array, patch_array, row, column, merge_method=merge_method, padding=padding)
        patch = GeogeniusEOPatch()
        img_shape_array = union_array[:, :self.geogenius_image.shape[1], :self.geogenius_image.shape[2], :]
        patch.data[feature_name] = img_shape_array
        patch.bbox = self._get_img_bbox()
        return patch

    def _get_img_bbox(self):
        data_bounds = self.geogenius_image.bounds
        data_bbox = BBox((data_bounds[0], data_bounds[1], data_bounds[2], data_bounds[3]),
                         CRS(self.geogenius_image.proj))
        return data_bbox

    def _get_union_array(self, feature_name):
        tile_rows, tile_columns = self._get_tile_rows_columns()
        tile_pixel_rows, tile_pixel_columns = self.splitter.tile_pixel_shape
        y_step, x_step = self.splitter.xy_step_shape
        repeat_pixel_y = tile_pixel_rows - y_step
        repeat_pixel_x = tile_pixel_columns - x_step
        patch_shape = self.patch_index[0][0].data[feature_name].shape
        len_array_y = tile_rows * tile_pixel_rows - (tile_rows - 1) * repeat_pixel_y
        len_array_x = tile_columns * tile_pixel_columns - (tile_columns - 1) * repeat_pixel_x
        union_array = np.zeros((patch_shape[0], len_array_y, len_array_x, patch_shape[3]),
                               dtype=self.geogenius_image.dtype)
        return union_array

    def _merge_array(self, union_array, patch_array, row, column, merge_method="last", padding=0):
        """
        Merge patch_array to union_array in specific location. Union_array represent the whole tiff array,
        patch_array represent the array data for a certain EOPatch.

        :param union_array: A numpy array receive EOPatch array to merge.
        :type union_array: numpy
        :param patch_array: A numpy array merged in union_array.
        :type patch_array: numpy
        :param row: row tile number for y direction
        :type row: int
        :param column: column tile number for x direction
        :type column: int
        :param merge_method: How to merge overlap EOPatches. "last" mean latter array overwrite former array,
            "first" mean former array overwrite latter array.
        :type merge_method: str
        :param padding: Discarding borders when merge overlap EOPatches. 0 mean do not discard border.
        :type padding: int
        """
        y_step, x_step = self.splitter.xy_step_shape
        tile_pixel_rows, tile_pixel_columns = self.splitter.tile_pixel_shape
        min_pixel_x = column * x_step
        min_pixel_y = row * y_step
        len_pixel_x = patch_array.shape[2]
        len_pixel_y = patch_array.shape[1]
        max_pixel_x = min_pixel_x + len_pixel_x
        max_pixel_y = min_pixel_y + len_pixel_y
        if merge_method == "last":
            if padding > 0:
                patch_array = patch_array[:, padding:-padding, padding:-padding, :]
                union_array[:, min_pixel_y + padding:max_pixel_y - padding, min_pixel_x + padding:max_pixel_x - padding,
                :] = patch_array
            else:
                union_array[:, min_pixel_y:max_pixel_y, min_pixel_x:max_pixel_x,:] = patch_array
        elif merge_method == "first":
            repeat_pixel_y = tile_pixel_rows - y_step
            repeat_pixel_x = tile_pixel_columns - x_step
            patch_start_y = 0
            patch_start_x = 0
            if row != 0 and len_pixel_y > repeat_pixel_y:
                min_pixel_y = min_pixel_y + repeat_pixel_y
                patch_start_y = repeat_pixel_y
            if column != 0 and len_pixel_x > repeat_pixel_x:
                min_pixel_x = min_pixel_x + repeat_pixel_x
                patch_start_x = repeat_pixel_x
            if padding > 0:
                union_array[:, min_pixel_y + padding:max_pixel_y - padding, min_pixel_x + padding:max_pixel_x - padding, :] = \
                    patch_array[:, patch_start_y + padding: -padding, patch_start_x + padding: -padding, :]
            else:
                union_array[:, min_pixel_y:max_pixel_y, min_pixel_x:max_pixel_x, :] = \
                    patch_array[:, patch_start_y:, patch_start_x:, :]

    def __getitem__(self, item):
        return self.patch_index[item]

    def __setitem__(self, key, value):
        self.patch_index[key] = value

