from abc import ABC

class PixelRangeSplitter(ABC):
    """ A tool that splits the given area into smaller parts withe same pixel size. Given the area it calculates its
    bounding box and splits it into smaller bounding boxes based on xy_step_shape.

       :param total_pixel_shape: Parameter that describes the total pixel size along x, y direction. It can be a tuple of the
       form `(n, m)` which means the area bounding box has `n` pixel rows and `m` pixel columns. It can also be a single
       integer `n` which is the same as `(n, n)`.
       :type total_pixel_shape: int or (int, int)
       :param tile_pixel_shape: Parameter that describes the pixel size along x, y direction per tile. It can be a tuple of the
       form `(n, m)` which means the area bounding box has `n` pixel rows and `m` pixel columns. It can also be a single
       integer `n` which is the same as `(n, n)`.
       :type tile_pixel_shape: int or (int, int)
       :param xy_step_shape: Step size for each movement in the x (or y) direction when splitting the bounding box. It
       can be a tuple of the form `(n, m)` which move `n` pixels along y direction and `m` pixels along x direction at
       each split. It can also be a single integer `n` which is the same as `(n, n)`.
       :type xy_step_shape: int or (int, int)
       """

    def __init__(self, total_pixel_shape, tile_pixel_shape, xy_step_shape, **kwargs):
        self.total_pixel_shape = self._parse_split_shape(total_pixel_shape)
        self.tile_pixel_shape = self._parse_split_shape(tile_pixel_shape)
        self.xy_step_shape = self._parse_split_shape(xy_step_shape)
        self.pixel_bbox_list = []
        self.info_list = []
        self._make_split()

    def get_pixel_bbox_list(self):
        return self.pixel_bbox_list

    def get_info_list(self):
        return self.info_list

    @staticmethod
    def _parse_split_shape(split_shape):
        """ Parses the parameter `split_shape`

        :param split_shape: The parameter `split_shape` from class initialization
        :type split_shape: int or (int, int)
        :return: A tuple of n
        :rtype: (int, int)
        :raises: ValueError
        """
        if isinstance(split_shape, int):
            return split_shape, split_shape
        if isinstance(split_shape, (tuple, list)):
            if len(split_shape) == 2 and isinstance(split_shape[0], int) and isinstance(split_shape[1], int):
                if split_shape[0] > 0 and split_shape[1] > 0:
                  return split_shape[0], split_shape[1]
                else:
                    raise ValueError("Content of split_shape {} must > 0.".format(split_shape))
            raise ValueError("Content of split_shape {} must be 2 integers.".format(split_shape))
        raise ValueError("Split shape must be an int or a tuple of 2 integers.")

    def _make_split(self):
        """ This method makes the split
        """
        total_pixel_rows, total_pixel_columns = self.total_pixel_shape

        tile_pixel_rows, tile_pixel_columns = self.tile_pixel_shape
        y_step, x_step = self.xy_step_shape
        x_index = 0

        while x_index * x_step < total_pixel_columns:
            y_index = 0
            while y_index * y_step < total_pixel_rows:
                tile_x_min = x_index * x_step
                tile_x_max = tile_x_min + tile_pixel_columns
                tile_y_min = y_index * y_step
                tile_y_max = tile_y_min + tile_pixel_rows

                bbox = [tile_x_min, tile_y_min, tile_x_max, tile_y_max]

                self.pixel_bbox_list.append(bbox)
                info = {'parent_bbox': self.total_pixel_shape,
                        'index_x': x_index,
                        'index_y': y_index}
                self.info_list.append(info)
                # move forward
                y_index = y_index + 1

            # move forward
            x_index = x_index + 1
