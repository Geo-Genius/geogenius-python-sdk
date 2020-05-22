from eolearn.core import FeatureType, SaveToDisk, OverwritePermission, LinearWorkflow, EOExecutor
from eolearn.io import ExportToTiff

from geogeniustools.eolearn.geogenius_areas import PixelRangeSplitter
from geogeniustools.eolearn.geogenius_data import GeogeniusEOPatch
from geogeniustools.eolearn.geogenius_io import ImportFromGeogenius
from geogeniustools.images.obs_image import OBSImage
from shapely.geometry import box
import numpy as np
import os


def get_current_folder(str):
    return os.path.abspath(str)


if __name__ == '__main__':
    img = OBSImage('obs://ai-training/data/nanning/cog/1-1.tif')
    print("bounds: {}".format(img.bounds))
    print("shape {}".format(img.shape))

    # Split the image into 1000 * 1000 tiles and the move step is 1000
    bbox_splitter = PixelRangeSplitter(img.shape[1:], (1000, 1000), (1000, 1000))
    print(len(bbox_splitter.get_pixel_bbox_list()))

    # move step is y = 500  x = 1000
    bbox_splitter = PixelRangeSplitter(img.shape[1:], (1000, 1000), (500, 1000))
    print(len(bbox_splitter.get_pixel_bbox_list()))

    # move step is equal to image size
    bbox_splitter = PixelRangeSplitter(img.shape[1:], img.shape[1:], img.shape[1:])
    print(len(bbox_splitter.get_pixel_bbox_list()))

    # move step is 1000
    bbox_splitter = PixelRangeSplitter(img.shape[1:], (256, 256), (256, 256))
    print(len(bbox_splitter.get_pixel_bbox_list()))
    print("print bbox")

    bbox_list = np.array(bbox_splitter.get_pixel_bbox_list())
    info_list = np.array(bbox_splitter.get_info_list())
    for idx, bbox in enumerate(bbox_list):
        info = info_list[idx]
        print("x {}, y {}, minx: {}, miny: {}, maxx: {}, maxy: {}".format(info['index_x'], info['index_y'], bbox[0], bbox[1], bbox[2], bbox[3]))

    # Define ImportFromGeogenius task
    add_data = ImportFromGeogenius(feature=(FeatureType.DATA, 'BANDS'), geogenius_image=img)

    path_out = get_current_folder("pixel_range_eopatches")
    if not os.path.isdir(path_out):
        os.makedirs(path_out)
    save = SaveToDisk(path_out, overwrite_permission=OverwritePermission.OVERWRITE_PATCH)

    # Define workflow
    workflow = LinearWorkflow(add_data, save)
    # Execute the workflow
    # define additional parameters of the workflow
    execution_args = []
    for idx, bbox in enumerate(bbox_list):
        # eopach = add_data.execute(pixelbox=bbox)
        # save(eopatch=eopach, eopatch_folder='eopatch_{}'.format(idx))

        execution_args.append({
            add_data: {'pixelbox': bbox},
            save: {'eopatch_folder': 'eopatch_{}'.format(idx)}
        })

    executor = EOExecutor(workflow, execution_args, save_logs=True)
    executor.run(workers=1, multiprocess=False)

    # Load GeogeniusEOPatch
    print("First EOPatch")
    eopatch = GeogeniusEOPatch.load(path=os.path.join(path_out, 'eopatch_{}'.format(0)), lazy_loading=True)
    print(eopatch.get_feature(FeatureType.DATA, 'BANDS').shape)
    print(eopatch.bbox)
    print("Second EOPatch")
    eopatch1 = GeogeniusEOPatch.load(path=os.path.join(path_out, 'eopatch_{}'.format(1)), lazy_loading=True)
    print(eopatch1.get_feature(FeatureType.DATA, 'BANDS').shape)
    print(eopatch1.bbox)

    # Convert all patches to tiff
    tiff_out = get_current_folder("pixel_range_tiff")
    if not os.path.isdir(tiff_out):
        os.makedirs(tiff_out)
    export_to_tiff = ExportToTiff(feature=(FeatureType.DATA, 'BANDS'), folder=tiff_out)
    for idx, bbox in enumerate(bbox_list):
        info = info_list[idx]
        patch_patch = os.path.join(path_out, 'eopatch_{}'.format(idx))
        sub_patch = GeogeniusEOPatch.load(path=os.path.join(path_out, 'eopatch_{}'.format(idx)), lazy_loading=True)
        export_to_tiff.execute(
            eopatch=sub_patch, filename='eopatch_{}_{}.tiff'.format(info['index_x'], info['index_y']))

