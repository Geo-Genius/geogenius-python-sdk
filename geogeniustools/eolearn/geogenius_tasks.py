
from eolearn.core import EOTask


class IndexTask(EOTask):
    """
    A Task index a specific EOPatch to a index object which manage a number of EOPatches.

    :param patch_index: A object manager the index of EOPatches, which is a two dimension of list
    :type patch_index: list
    """

    def __init__(self, patch_index):
        self.patch_index = patch_index

    def execute(self, eopatch, row, column):
        self.patch_index[row][column] = eopatch
