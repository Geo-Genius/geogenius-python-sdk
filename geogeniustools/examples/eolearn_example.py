from eolearn.core import FeatureType, LinearWorkflow, EOExecutor, SaveToDisk, OverwritePermission, EOTask
from eolearn.io import ExportToTiff
from sentinelhub import BBoxSplitter, BBox, CRS, CustomUrlParam

from geogeniustools.eolearn.geogenius_data import GeogeniusEOPatch
from geogeniustools.eolearn.geogenius_io import ImportFromGeogenius
from geogeniustools.images.obs_image import OBSImage
from shapely.geometry import box
from shapely.geometry import Polygon
import numpy as np
import os


def get_current_folder(str):
    return os.path.abspath(str)


if __name__ == '__main__':

    img = OBSImage('obs://obs-tiff-test/retile_china/ng47_05_41.tif')
    print("bounds: {}".format(img.bounds))
    print("shape {}".format(img.shape))
    image_box = box(img.bounds[0], img.bounds[1], img.bounds[2], img.bounds[3])

    # Split the image into 3 * 3 tiles
    bbox_splitter = BBoxSplitter([image_box], img.proj, (3, 3))

    bbox_list = np.array(bbox_splitter.get_bbox_list())
    info_list = np.array(bbox_splitter.get_info_list())

    # Obtain patchIDs
    patchIDs = []
    for idx, [bbox, info] in enumerate(zip(bbox_list, info_list)):
        patchIDs.append(idx)

    # Check if final size is 3x3
    if len(patchIDs) != 9:
        print('Warning! Use a different central patch ID, this one is on the border.')

    # Change the order of the patches (used for plotting later)
    patchIDs = np.transpose(np.fliplr(np.array(patchIDs).reshape(3, 3))).ravel()

    # Prepare info of selected EOPatches
    geometries = [Polygon(bbox.get_polygon()) for bbox in bbox_list[patchIDs]]

    # Print selected EOPatches boundary
    idxs_x = [info['index_x'] for info in info_list[patchIDs]]
    idxs_y = [info['index_y'] for info in info_list[patchIDs]]
    for (x, y, geo) in zip(idxs_x, idxs_y, geometries):
        print("x:{} y:{} geometry:{}".format(x, y, geo))

    # Fill EOPatches with data from geogenius platform:
    # Define ImportFromGeogenius task
    add_data = ImportFromGeogenius(feature=(FeatureType.DATA, 'BANDS'), geogenius_image=img)
    # Define Save EOPatch Task
    path_out = get_current_folder("eopatches")
    if not os.path.isdir(path_out):
        os.makedirs(path_out)
    save = SaveToDisk(path_out, overwrite_permission=OverwritePermission.OVERWRITE_PATCH)

    # patch = add_data.execute(bbox=bbox_list[patchIDs][0])
    # save.execute(patch, eopatch_folder="1")

    # Define workflow
    workflow = LinearWorkflow(add_data, save)

    # Execute the workflow
    # define additional parameters of the workflow
    execution_args = []
    for idx, bbox in enumerate(bbox_list[patchIDs]):
        execution_args.append({
            add_data: {'bbox': bbox},
            save: {'eopatch_folder': 'eopatch_{}'.format(idx)}
        })

    executor = EOExecutor(workflow, execution_args, save_logs=True)
    executor.run(workers=5, multiprocess=False)

    # should install graphviz
    # executor.make_report()

    # Load GeogeniusEOPatch
    eopatch = GeogeniusEOPatch.load(path=os.path.join(path_out, 'eopatch_{}'.format(0)), lazy_loading=True)
    print(eopatch)
    # Print data
    print(eopatch.get_feature(FeatureType.DATA, 'BANDS'))

    # Convert all patches to tiff
    tiff_out = get_current_folder("tiff")
    if not os.path.isdir(tiff_out):
        os.makedirs(tiff_out)
    export_to_tiff = ExportToTiff(feature=(FeatureType.DATA, 'BANDS'), folder=tiff_out)
    for idx, bbox in enumerate(bbox_list[patchIDs]):
        patch_patch = os.path.join(path_out, 'eopatch_{}'.format(idx))
        sub_patch = GeogeniusEOPatch.load(path=os.path.join(path_out, 'eopatch_{}'.format(idx)), lazy_loading=True)
        export_to_tiff.execute(eopatch=sub_patch, filename='eopatch_{}.tiff'.format(idx))





