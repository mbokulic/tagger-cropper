import glob
import os
from PIL import Image, ImageDraw
from pylab import *
import cv2
import numpy

class Montage:
    """
    Make a montage from a group of filenames:

    fnames          A list of names of the image files
    montage_size    (width, height), desired size of montage
                    will not be exactly that, rounding errors
    row_to_column   (n, m) integers, tell you what the
                    'aspect ratio' of the montage will be,
                    i.e. how many pics in rows, how many in
                    columns
    force_square    should the input images be streched to
                    squares?
    every_nth_image if you want to reduce the nr of images in the montage

    all input images are expected to be of same size
    """
    def __init__(self,
                 fnames,
                 montage_size,
                 row_to_column,
                 force_square=True,
                 every_nth_image=1):
        # will get every nth image
        if every_nth_image is not 1:
            fnames = [fnames[idx] for idx in range(len(fnames))
                      if idx % every_nth_image == 0]
        self.fnames = fnames
        self.nr_images = len(fnames)
        self.montage_size = montage_size
        self.row_to_column = row_to_column
        self.force_square = force_square
        self.define_montage_dimensions()
        self.define_image_dim(self.montage_size,
                              self.ncols,
                              self.nrows)
        if self.force_square:
            self.resize_factor = None
 
    def draw_montage(self):
        """
        returns a PIL image
        """
        # need to resize montage based on calculated photo dimension
        width = self.montage_size[0]
        height = self.montage_size[1]
        if self.photow * self.ncols > self.montage_size[0]:
            width = self.photow * self.ncols
        if self.photoh * self.nrows > self.montage_size[1]:
            height = self.photoh * self.nrows
        self.montage = numpy.full(shape = (height, width, 3),
                             fill_value = 0,
                             dtype = numpy.uint8)
        count = 0
        # Insert each thumb:
        for irow in range(self.nrows):
            for icol in range(self.ncols):
                left = icol * self.photow
                right = left + self.photow
                upper = irow * self.photoh
                lower = upper + self.photoh
                try:
                    # Read in an image and resize
                    image = cv2.imread(self.fnames[count])
                    image = self.resize_image(image,
                                              self.photow,
                                              self.photoh,
                                              self.force_square)
                except IndexError:
                    break
                self.montage[upper:lower, left:right] = image
                count += 1
        b, g, r = cv2.split(self.montage)
        self.montage = cv2.merge((r, g, b))
        self.montage = Image.fromarray(self.montage)
        return self.montage

    def save_montage(self, path):
        self.montage.save(path)

    def resize_image(self, image, target_width, target_height, force_square):
        """
        :param image:          openCV image (numpy array)
        :param target_width:   width of target img you resize 'into'
        :param target_height:  height of target img
        :param force_square:   should the input image be forced into
                               a square or padded with black
        :return:               resized openCV image (numpy array)
        """
        if force_square:
            image = cv2.resize(image, dsize = (target_width, target_height))
            return image
        else:
            # this here could benefit with performance improvements since it
            # does too many calculations: all images are of same size
            image_height, image_width = image.shape[:2]
            whole_image = numpy.full(shape = (target_width, target_height, 3),
                                     fill_value = 0,
                                     dtype = numpy.uint8)
            if image_width > image_height:
                self.resize_factor = float(target_width) / image_width
                image_height = target_height * (float(image_height) / image_width)
                image_height = int(image_height)
                image_width = target_width
                start = target_height/2 - image_height/2
                image = cv2.resize(image, dsize = (image_width, image_height))
                whole_image[start:(start + image_height), 0:image_width] = image
            else:
                self.resize_factor = float(target_height) / image_height
                image_width = target_width * (float(image_width) / image_height)
                image_width = int(image_width)
                image_height = target_height
                start = target_width/2 - image_width / 2
                image = cv2.resize(image, dsize = (image_width, image_height))
                whole_image[0:image_height, start:(start + image_width)] = image
            return whole_image

    def get_resize_factor(self):
        return self.resize_factor

    def get_image_center_from_coords(self, x, y):
        """
        returns the center of the image when given the x, y coords that are inside the borders of the montage
        will return center even if there is no image (i.e, there is only blank space)
        """
        if x > self.montage_size[0] or y > self.montage_size[1] or x < 0 or y < 0:
            return None
        order = self.get_image_index(x, y)
        indices = self.get_image_indices(order)
        center_start = (self.photow / 2, self.photoh / 2)
        image_center = (center_start[0] + indices[1] * self.photow,
                        center_start[1] + indices[0] * self.photoh)
        return image_center

    def get_image_index(self, x, y):
        """
        Returns the order (start from 1) of the image given the x, y coords.
        Coords have to be inside the borders of the montage.
        Will return an index even if there is no image in that part of the
        montage.
        """
        if x > self.montage_size[0] or y > self.montage_size[1] or x < 0 or y < 0:
            return None
        col = (x - 1) / self.photow
        row = (y - 1) / self.photoh
        image_order = (row) * self.ncols + col + 1
        return image_order

    def get_image_indices(self, image_order):
        """
        returns image row and col indices when given the order of the image
        row and col are Python style, starting from 0
        """
        row = image_order / self.ncols
        if image_order % self.ncols != 0:
            row += 1
        col = image_order - (row - 1) * self.ncols
        return (row - 1, col - 1)

    def get_image_center_from_order(self, image_order):
        """
        returns the center of the image when given the x, y coords that are inside the borders of the montage
        will return center even if there is no image (i.e, there is only blank space)
        """
        indices = self.get_image_indices(image_order)
        center_start = (self.photow / 2, self.photoh / 2)
        image_center = (center_start[0] + indices[1] * self.photow,
                        center_start[1] + indices[0] * self.photoh)
        return image_center

    def get_multiple_image_centers(self, index_list):
        """
        returns the centers of the images indexed by the index_list
        will return center even if there is no image (i.e, there is only blank space)
        """
        centers = []
        for idx in index_list:
            centers.append(self.get_image_center_from_order(idx))
        return centers

    def get_size(self):
        """
        returns the size of the montage, output is a tuple
        """
        return self.montage_size

    def get_image_size(self):
        """
        Returns the size of the individual image on the montage.
        Output is a tuple
        """
        return (self.photow, self.photoh)

    def get_nr_images(self):
        """
        returns the number of imgs on the montage
        """
        return len(self.fnames)

    def define_montage_dimensions(self):
        """
        calculates the dimensions for the montage
        for now pretty simple: 3 rows and as many columns as needed
        """
        images_fit = self.row_to_column[0] * self.row_to_column[1]
        order = 1
        while images_fit < self.nr_images:
            order += 1
            images_fit = self.row_to_column[0] * self.row_to_column[1] * order**2
        self.ncols = self.row_to_column[1] * order
        self.nrows = self.row_to_column[0] * order
 
    def define_image_dim(self, image_size, ncols, nrows):
        """
        defines the photo dimensions based on image size and nr of cols and rows
        the final image size will not be exact to the input because of rounding
        """
        photo_dimension = round(float(image_size[0]) / float(ncols))
        photo_dimension = int(photo_dimension)
        self.photow = photo_dimension
        self.photoh = photo_dimension

    def get_whole_image_center(self):
        '''
        :return: center coords of the first unresized image. It is assumed all
        images are of the same size.
        '''
        image = cv2.imread(self.fnames[0])
        image_height, image_width = image.shape[:2]
        return (image_width / 2, image_height / 2)

if __name__ == "__main__":
    filenames = [
        r'C:\Users\Marko\Desktop\remove this folder\output\nms\image0000130\image0000130_007.jpg',
        r'C:\Users\Marko\Desktop\remove this folder\output\nms\image0000130\image0000130_008.jpg',
        r'C:\Users\Marko\Desktop\remove this folder\output\nms\image0000130\image0000130_009.jpg',
        r'C:\Users\Marko\Desktop\remove this folder\output\nms\image0000130\image0000130_010.jpg',
        r'C:\Users\Marko\Desktop\remove this folder\output\nms\image0000130\image0000130_011.jpg',
        r'C:\Users\Marko\Desktop\remove this folder\output\nms\image0000130\image0000130_012.jpg',
        r'C:\Users\Marko\Desktop\remove this folder\output\nms\image0000130\image0000130_013.jpg',
        r'C:\Users\Marko\Desktop\remove this folder\output\nms\image0000130\image0000130_014.jpg']
    img = Montage(filenames, (800, 400), (1, 2), False, 1)
    image = img.draw_montage()
    img.save_montage(r'C:\Users\Marko\Desktop\work folder\shoe_detector_example.jpg')

