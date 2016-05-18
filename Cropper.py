import os
import math
from PIL import Image, ImageTk, ImageDraw
import cv2
from pylab import *
import Tkinter as tk
import re
import tkMessageBox
import csv
import rotate_image as rotate
import Question

class Cropper:
    """
    loads a list of image filenames and goes through them
    first you crop the whole_image
    then you crop (optionally) a detail, these are saved as image_detail.jpg in
    the designated output path.
    """

    def __init__(self, window, question_definitions, image_paths, output_path,
                 crop_csv, event_name, flip, zoom_factor):
        # initializing globals that don't change
        self.window = window
        self.image_paths = image_paths[:]
        self.directory = output_path
        self.crop_csv = crop_csv
        self.event_name = event_name
        # initializing global variables
        self.whole_image = True
        # image globals: vertical flip and zoom
        self.flip = flip
        self.zoom_factor = zoom_factor
        # globals related to the crop boundary box
        # if below is True you can draw the box
        self.continue_drag = True
        # at the start the box does not exist
        self.rect_x1 = None
        self.rect_x2 = None
        self.rect_y1 = None
        self.rect_y2 = None
        self.line_offset = 15
        # rotation constants
        self.start_angle = 0
        self.angle = 0
        self.cropped_images = []
        self.rows_to_write = []

        # adding buttons for controlling the cropper
        self.destroybutton = tk.Button(self.window,
                                       text="destroy the drawing <b>",
                                       command=self.remove_drawings)
        self.finishbutton = tk.Button(self.window,
                                      text="finish (WARNING: skips all "
                                           "images!)",
                                      command=self.setup_detail_cropper,
                                      foreground="red")
        self.flipbutton = tk.Button(self.window,
                                    text="flip image <f>",
                                    command=self.flip_image)
        self.nextbutton = tk.Button(self.window,
                                    text="crop and next image <space>",
                                    command=self.next_image)
        self.skipbutton = tk.Button(self.window,
                                    text="skip image <q>",
                                    command=self.skip_image)

        # adding buttons as defined in the parameters
        self.questions = []
        for question in question_definitions:
            target = Question.Question(
                name=question['name'],
                answers=question['answers'],
                description=question['description'],
                master=self.window,
                use_open_ended=question['open_ended']
            )
            self.questions.append(target)

        # adding buttons to the grid
        nr_columns = len(self.questions)
        if(nr_columns % 2 == 1):
            nr_columns += 1
        for idx in range(len(self.questions)):
            target = self.questions[idx]
            target.frame.grid(row=1, column=idx)

        self.destroybutton.grid(row=3, column=0)
        self.finishbutton.grid(row=4, column=0, columnspan=2)
        self.flipbutton.grid(row=2, column=0)
        self.nextbutton.grid(row=2, column=1)
        self.skipbutton.grid(row=3, column=1)
        # binding keys and mouse actions
        self.window.bind("<space>", self.space_handler)
        self.window.bind("<Key>", self.keypress_handler)
        self.window.bind("<MouseWheel>", self.mousewheel_handler)
        self.window.bind("<Shift-MouseWheel>", self.shift_mousewheel_handler)
        self.window.bind("<Control-MouseWheel>",
                         self.control_mousewheel_handler)

    def run(self):
        # running the first image
        self.pop_image()
        self.load_image()
        self.draw_image()

    # drawing the image ##################################

    def pop_image(self):
        """
        pops the next image path from the list, appends it to the finished
        images list self.current_image is the filename of the image currently
        being processed
        """
        self.current_load_path = self.image_paths.pop(0)
        self.current_image = os.path.split(self.current_load_path)[1]

    def next_image(self):
        """
        defines what happens when you click next image
        """
        # if anything was clicked, try to process tags
        answers = [q.get_answer() != '' for q in self.questions]
        if (any(answers) or (self.rect_x1 is not None)):
            if self.check_data_input():
                self.crop_image()
            else:
                return
        # if no imgs left, open detail cropper
        if len(self.image_paths) == 0:
            self.setup_detail_cropper()
            return
        # if imgs left, run next image
        # and redraw old rectangle
        self.pop_image()
        self.load_image()
        self.draw_image()
        self.redraw_rectangle(self.center_rectangle)

    def skip_image(self):
        """
        skips the image and draws another if any are left
        this code can be rewritten somewhere else, but I'm adding it as a quick fix
        """
        if len(self.image_paths) == 0:
            self.setup_detail_cropper()
        else:
            self.pop_image()
            self.load_image()
            self.draw_image()
            # redraw the old rectangle if it exists
            try:
                self.redraw_rectangle(self.center_rectangle)
            except AttributeError:
                pass

    def load_image(self):
        """
        loads the active image and does the transformations
        flips it if the flag is true
        """
        # loading image
        self.raw_image = cv2.imread(self.current_load_path, 1)
        # flipping it if flip flag is true
        if self.flip:
            self.raw_image = cv2.flip(self.raw_image, 1)
        # converting from openCV format to PIL format
        b, g, r = cv2.split(self.raw_image)
        self.image = cv2.merge((r, g, b))
        if self.zoom_factor is not 1:
            self.image = cv2.resize(self.image,
                                    dsize=None,
                                    fx=self.zoom_factor,
                                    fy=self.zoom_factor,
                                    interpolation=cv2.INTER_NEAREST)
        self.image = Image.fromarray(self.image)
        self.image_width = self.image.size[0]
        self.image_height = self.image.size[1]
        # converting to Tkinter format
        self.image_tk = ImageTk.PhotoImage(image=self.image)

    def draw_image(self):
        """
        loads and draws the image on the canvas
        """
        # destroying old canvas, except at beginning when it doesn't exists
        try:
            self.canvas.destroy()
        except AttributeError:
            pass
        # setting up new canvas
        self.canvas = tk.Canvas(self.window,
                                width=self.image_width,
                                height=self.image_height)
        self.canvas.grid(row=0, column=0, columnspan=2)
        if self.whole_image:
            self.canvas.bind("<Button-1>", self.click_handler)
            self.canvas.bind("<B1-Motion>", self.drag_handler)
            self.canvas.bind("<ButtonRelease-1>", self.release_handler)
            self.canvas.bind("<Button3-Motion>", self.button3_drag_handler)
            self.canvas.bind("<Button-3>", self.button3_click_handler)
            self.canvas.bind("<ButtonRelease-3>", self.button3_release_handler)
        else:
            self.canvas.bind("<Button-1>", self.detail_click_handler)
            self.canvas.bind("<B1-Motion>", self.detail_drag_handler)
            self.canvas.bind("<ButtonRelease-1>", self.detail_release_handler)
        self.window.wm_title(self.current_load_path)
        # drawing image
        self.canvas.create_image(0, 0, image = self.image_tk, anchor = tk.NW)

    def flip_image(self):
        """
        flips the image vertically (left to right)
        works by re-loading the image with the flip = True param and redrawing it
        """
        # remove rotation line and redraw image, if it exists
        try:
            self.remove_drawings()
        except AttributeError:
            pass
        # set global flip to True and load image again
        self.flip = not self.flip
        self.load_image()
        self.draw_image()

    ############ drawing ##################################

    def click_handler(self, event):
        """
        first click is saved as the first point of the rectangle
        if rectangle exists, click will re-position the rectangle
        """
        if self.rect_x1 == None:
            self.rect_x1 = event.x
            self.rect_y1 = event.y
        else:
            self.redraw_rectangle((event.x, event.y))

    def redraw_rectangle(self, new_center):
        """
        redraws the rectangle stored in the global vars rect_x1
        and rotates it with the current angle
        the provided point is the new center
        """
        if self.rect_x1 is not None and self.rect_x2 is not None:
            points = self.transform_points([(self.rect_x1,
                                             self.rect_y1),
                                            (self.rect_x2,
                                             self.rect_y2)],
                                           self.center_rectangle)
            self.rect_x1 = points[0][0] + new_center[0]
            self.rect_y1 = points[0][1] + new_center[1]
            self.rect_x2 = points[1][0] + new_center[0]
            self.rect_y2 = points[1][1] + new_center[1]
            self.center_rectangle = new_center
            self.rotate_rectangle()
            self.draw_helpline()
            
    def drag_handler(self, event):
        """
        draws a rectangle and a helpline
        """
        if self.continue_drag:
            self.rect_x2 = event.x
            self.rect_y2 = event.y
            rectangle_points = [(self.rect_x1, self.rect_y1),
            (self.rect_x1, self.rect_y2),
            (self.rect_x2, self.rect_y2),
            (self.rect_x2, self.rect_y1)]
            self.draw_rectangle(rectangle_points)
            # forcing x1 and y1 to be upperleft
            self.draw_helpline()
            self.rect_final_point1 = (self.rect_x1, self.rect_y1)
            self.rect_final_point2 = (self.rect_x1, self.rect_y2)
            self.rect_final_point3 = (self.rect_x2, self.rect_y2)
            self.rect_final_point4 = (self.rect_x2, self.rect_y1)
        else:
            self.redraw_rectangle((event.x, event.y))

    def release_handler(self, event):
        """
        stops the drawing of the rectangle
        """
        # if only one click was registered, without drag
        # disregard that click
        if self.rect_x2 is None:
            self.rect_x1 = None
            self.rect_y1 = None
        else:
            self.continue_drag = False

    def remove_drawings(self):
        """
        removes the rectangle and the helpline
        resets their globals
        """
        if self.whole_image:
            try:
                self.canvas.delete(self.boundary)
                self.canvas.delete(self.center_dot)
                self.rect_x1 = None
                self.rect_x2 = None
                self.rect_y1 = None
                self.rect_y2 = None
                self.canvas.delete(self.line_bot)
                self.canvas.delete(self.line_right)
                self.canvas.delete(self.line_top)
                self.canvas.delete(self.line_left)
                self.start_angle = 0
                self.angle = 0
            except AttributeError:
                pass
        elif self.rotation_state:
            self.canvas.delete(self.rotation_line)
            self.line1 = None
            self.line2 = None
        else:
            self.canvas.delete(self.boundary)
            self.canvas.delete(self.center_dot)
            self.rect_x1 = None
            self.rect_x2 = None
            self.rect_y1 = None
            self.rect_y2 = None
            self.canvas.delete(self.line_bot)
            self.canvas.delete(self.line_right)
            self.canvas.delete(self.line_top)
            self.canvas.delete(self.line_left)
        self.continue_drag = True

    def draw_helpline(self):
        """
        draws lines inside the crop rectangle
        that are used to ensure uniform crop padding
        """
        
        upperleft, lowerright = self.enforce_corners([(self.rect_x1, self.rect_y1),
                                                     (self.rect_x1, self.rect_y2),
                                                     (self.rect_x2, self.rect_y2),
                                                     (self.rect_x2, self.rect_y1)])
        # draws the helpline
        self.line_bot_point1 = (upperleft[0], lowerright[1] - self.line_offset)
        self.line_bot_point2 = (lowerright[0], lowerright[1] - self.line_offset)
        self.line_right_point1 = (upperleft[0] + self.line_offset, upperleft[1])
        self.line_right_point2 = (upperleft[0] + self.line_offset, lowerright[1])
        self.line_top_point1 = (upperleft[0], upperleft[1] + self.line_offset)
        self.line_top_point2 = (lowerright[0], upperleft[1] + self.line_offset)
        self.line_left_point1 = (lowerright[0] - self.line_offset, upperleft[1])
        self.line_left_point2 = (lowerright[0] - self.line_offset, lowerright[1])
        try:
            self.canvas.delete(self.line_bot)
            self.canvas.delete(self.line_right)
            self.canvas.delete(self.line_top)
            self.canvas.delete(self.line_left)
        except AttributeError:
            pass
        if angle == 0:
            self.line_bot = self.canvas.create_line(self.line_bot_point1[0],
                                                    self.line_bot_point1[1],
                                                    self.line_bot_point2[0],
                                                    self.line_bot_point2[1],
                                                    fill = "Red", dash = 3)
            self.line_right = self.canvas.create_line(self.line_right_point1[0],
                                                    self.line_right_point1[1],
                                                    self.line_right_point2[0],
                                                    self.line_right_point2[1],
                                                    fill = "Red", dash = 3)
            self.line_top = self.canvas.create_line(self.line_top_point1[0],
                                                    self.line_top_point1[1],
                                                    self.line_top_point2[0],
                                                    self.line_top_point2[1],
                                                    fill = "Red", dash = 3)
            self.line_left = self.canvas.create_line(self.line_left_point1[0],
                                                    self.line_left_point1[1],
                                                    self.line_left_point2[0],
                                                    self.line_left_point2[1],
                                                    fill = "Red", dash = 3)
        else:
            new_line_bot_point1 = self.rotate_point(self.line_bot_point1[0],
                                                     self.line_bot_point1[1],
                                                     self.center_rectangle,
                                                     self.angle)
            new_line_bot_point2 = self.rotate_point(self.line_bot_point2[0],
                                                     self.line_bot_point2[1],
                                                     self.center_rectangle,
                                                     self.angle)
            new_line_right_point1 = self.rotate_point(self.line_right_point1[0],
                                                     self.line_right_point1[1],
                                                     self.center_rectangle,
                                                     self.angle)
            new_line_right_point2 = self.rotate_point(self.line_right_point2[0],
                                                     self.line_right_point2[1],
                                                     self.center_rectangle,
                                                     self.angle)
            new_line_top_point1 = self.rotate_point(self.line_top_point1[0],
                                                     self.line_top_point1[1],
                                                     self.center_rectangle,
                                                     self.angle)
            new_line_top_point2 = self.rotate_point(self.line_top_point2[0],
                                                     self.line_top_point2[1],
                                                     self.center_rectangle,
                                                     self.angle)
            new_line_left_point1 = self.rotate_point(self.line_left_point1[0],
                                                     self.line_left_point1[1],
                                                     self.center_rectangle,
                                                     self.angle)
            new_line_left_point2 = self.rotate_point(self.line_left_point2[0],
                                                     self.line_left_point2[1],
                                                     self.center_rectangle,
                                                     self.angle)
            self.line_bot = self.canvas.create_line(new_line_bot_point1[0],
                                                    new_line_bot_point1[1],
                                                    new_line_bot_point2[0],
                                                    new_line_bot_point2[1],
                                                    fill = "Red", dash = 3)
            self.line_right = self.canvas.create_line(new_line_right_point1[0],
                                                      new_line_right_point1[1],
                                                      new_line_right_point2[0],
                                                      new_line_right_point2[1],
                                                      fill = "Red", dash = 3)
            self.line_top = self.canvas.create_line(new_line_top_point1[0],
                                                      new_line_top_point1[1],
                                                      new_line_top_point2[0],
                                                      new_line_top_point2[1],
                                                      fill = "Red", dash = 3)
            self.line_left = self.canvas.create_line(new_line_left_point1[0],
                                                      new_line_left_point1[1],
                                                      new_line_left_point2[0],
                                                      new_line_left_point2[1],
                                                      fill = "Red", dash = 3)

    ############ rotating the rectangle ######################################

    def button3_click_handler(self, event):
        """
        rotation is done by recording the up/down movements when right button is pressed
        the click handler stores the initial right button click
        movement = vertical offset from initial click
        """
        self.rect_rotate_start_y = event.y


    def button3_drag_handler(self, event):
        """
        rotates the rectangle using up/down right button drag
        amount of rotation is defined as the up/down offset of the drag from the initial click
        """
        # if clause checks whether there is a rectangle drawn
        if self.rect_x1 is not None:
            self.rect_rotate_stop_y = event.y
            # angle_change is the offset from the initial click to the last drag
            self.angle_change = ((self.rect_rotate_stop_y -
                                 self.rect_rotate_start_y) /
                                 float(self.image.size[1] / 2))
            # the start angle is stored in a global var
            # so you can continue changing the angle from where you left off
            self.angle = self.angle_change + self.start_angle
            # rotates the rectangle and redraws it
            self.rotate_rectangle()
            self.draw_helpline()

    def button3_release_handler(self, event):
        """
        resets the global vars required for the rotation of the crop rectangle
        and stores the last angle so that you can continue where you left off
        """
        # if clause checks whether there is a rectangle drawn
        if self.rect_x1 is not None:
            self.rect_rotate_start_y = None
            self.rect_rotate_stop_y = None
            self.start_angle += self.angle_change

    def rotate_rectangle(self):
        """
        the complete rotation is done thusly:
            - initial coords are stored as self.rect_x1
            - when you drag the mouse, the up down offset is recorded
            - initial coords are rotated by this offset and stored as temp vars
            - when mouse is released, current offset is added to the new offset
        this method:
            - calculates the new, rotated rectangle coords
            - rotation always starts from the initial coords
            - redraws the rectangle
        """
        self.rect_final_point1 = self.rotate_point(self.rect_x1,
                                                   self.rect_y1,
                                                   self.center_rectangle,
                                                   self.angle)
        self.rect_final_point2 = self.rotate_point(self.rect_x2,
                                                   self.rect_y1,
                                                   self.center_rectangle,
                                                   self.angle)
        self.rect_final_point3 = self.rotate_point(self.rect_x2,
                                                   self.rect_y2,
                                                   self.center_rectangle,
                                                   self.angle)
        self.rect_final_point4 = self.rotate_point(self.rect_x1,
                                                   self.rect_y2,
                                                   self.center_rectangle,
                                                   self.angle)
        self.canvas.delete(self.boundary)
        self.draw_rectangle([self.rect_final_point1,
                            self.rect_final_point2,
                            self.rect_final_point3,
                            self.rect_final_point4])

    def draw_rectangle(self, points):
        """
        convenience function to create a rectangle
        """
        try:
            self.canvas.delete(self.boundary)
            self.canvas.delete(self.center_dot)
        except AttributeError:
            pass
        self.boundary = self.canvas.create_polygon(points[0][0], points[0][1],
                                                   points[1][0], points[1][1],
                                                   points[2][0], points[2][1],
                                                   points[3][0], points[3][1],
                                                   outline = "red",
                                                   fill = "")
        self.calc_rect_center()
        self.center_dot = self.canvas.create_oval(self.center_rectangle[0] - 5,
                                                  self.center_rectangle[1] - 5,
                                                  self.center_rectangle[0] + 5,
                                                  self.center_rectangle[1] + 5,
                                                  outline = "Red",
                                                  width = 1.5)

    def rotate_point(self, x, y, center, angle_radians):
        """
        rotates the given x and y coords around the center
        for use in coordinate systems where upperleft corner is 0, 0
        """
        x -= center[0]
        y -= center[1]
        _x = x * math.cos(angle_radians) + y * math.sin(angle_radians)
        _y = -x * math.sin(angle_radians) + y * math.cos(angle_radians)
        return _x + center[0], _y + center[1]

    def mousewheel_handler(self, event):
        """
        resizes the bounding rectangle and redraws helplines
        """
        offset = event.delta / 60
        self.rect_x1 = self.rect_x1 - offset
        self.rect_y1 = self.rect_y1 - offset
        self.rect_x2 = self.rect_x2 + offset
        self.rect_y2 = self.rect_y2 + offset
        self.rotate_rectangle()
        self.draw_helpline()

    def shift_mousewheel_handler(self, event):
        """
        resizes the width of the bounding rectangle
        """
        offset = event.delta / 60
        self.rect_x1 = self.rect_x1 - offset
        self.rect_x2 = self.rect_x2 + offset
        self.rotate_rectangle()
        self.draw_helpline()

    def control_mousewheel_handler(self, event):
        """
        resizes the height of the bounding rectangle
        """
        offset = event.delta / 60
        self.rect_y1 = self.rect_y1 - offset
        self.rect_y2 = self.rect_y2 + offset
        self.rotate_rectangle()
        self.draw_helpline()

    ############ helper functions ######################################

    def calc_rect_center(self):
        """
        calculates the center of the rectangle
        saves it in a global tuple
        """
        center_x = 1 / float(2) * (self.rect_x1 + self.rect_x2)
        center_y = 1 / float(2) * (self.rect_y1 + self.rect_y2)
        center_x = round(center_x)
        center_y = round(center_y)
        self.center_rectangle = (center_x, center_y)

    def transform_points(self, point_list, center):
        """
        transforms points as offset from center
        returns a list of tuples
        """
        transformed_points = []
        for point in point_list:
            point = (point[0] - center[0], point[1] - center[1])
            transformed_points.append(point)
        return transformed_points

    ############### cropping and storing data #####################################

    def crop_image(self):
        """
        saves the image part defined by the rectangle
        """
        # strange bug, if you don't redraw the boundary rectangle the points
        # become floats. This is a quick fix
        self.rect_x1 = int(self.rect_x1)
        self.rect_y1 = int(self.rect_y1)
        self.rect_x2 = int(self.rect_x2)
        self.rect_y2 = int(self.rect_y2)

        # if there was rotation, rotate
        if self.angle != 0:
            self.rotated_raw_image = rotate.rotate_image(self.raw_image,
                                                    -math.degrees(self.angle),
                                                    cv2.INTER_AREA)
            upperleft, lowerright = self.get_crop_boundary()
        # else use the original image and the initial coords
        else:
            self.rotated_raw_image = self.raw_image
            upperleft, lowerright = self.enforce_corners([(self.rect_x1, self.rect_y1),
                                                         (self.rect_x2, self.rect_y2)])

        upperleft, lowerright = self.correct_for_outside_boundary(upperleft, lowerright)
        cropped = self.rotated_raw_image[
            upperleft[1]:lowerright[1],
            upperleft[0]:lowerright[0]
        ]
        # saving the crop
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        save_path = (os.path.join(self.directory, self.current_image))
        cv2.imwrite(save_path, cropped)
        # cropped images are added to a list for the detail_cropper later to use
        self.cropped_images.append([save_path, self.current_image])
        # save the crop data
        row_to_write = (
            [self.event_name] +
            [self.current_image] +
            ["{0:.2f}".format(round(-math.degrees(self.angle), 2))] +
            [int(upperleft[0])] +
            [int(upperleft[1])] +
            [int(lowerright[0])] +
            [int(lowerright[1])] +
            [int(self.flip)]
        )
        for question in self.questions:
            row_to_write.append(question.get_answer())
        self.rows_to_write.append(row_to_write)

    def get_crop_boundary(self):
        """
        returns the crop boundary
            - starts with the initial non-rotated coords
            - defines them as offset from the center
            - calculates the coords given the offset on the rotated image
        """
        height, width = self.raw_image.shape[0:2]
        center_original = (width / 2 * self.zoom_factor,
                           height / 2 * self.zoom_factor)
        rect_original = self.transform_points([self.rect_final_point1,
                                              self.rect_final_point2,
                                              self.rect_final_point3,
                                              self.rect_final_point4],
                                              center_original)
        # rotating the bounding box around its center
        # adding the offset from the center of the rotated img
        height, width = self.rotated_raw_image.shape[0:2]
        center_rotated = (width / 2 * self.zoom_factor,
                          height / 2 * self.zoom_factor)
        new_points = []
        for point in rect_original:
            new_point = self.rotate_point(point[0], point[1],
                                          (0, 0), -self.angle)
            new_point = (int(round(new_point[0] + center_rotated[0])),
                         int(round(new_point[1] + center_rotated[1])))
            new_points.append(new_point)
        upperleft, lowerright = self.enforce_corners(new_points)
        return(upperleft, lowerright)

    def check_data_input(self):
        """
        raises an error if no crop data input and returns False
        if all good, returns True
        """
        answers = [q.get_answer() == '' for q in self.questions]
        if (any(answers)):
            tkMessageBox.showwarning("ERROR", "enter all tags!")
            return False
        if (self.rect_x1 is None or self.rect_x2 is None):
            tkMessageBox.showwarning(
                "ERROR", "draw boundary box for cropping!")
            return False
        return True

    def enforce_corners(self, point_list):
        """
        enforces the upper right and left corner for cropping to work
        returns the furthest upperleft and lowerright point from the list
        returns a list of two tuples: [(x1, y1), (x2, y2)]
        """
        upperleft = [99999, 99999]
        lowerright = [0, 0]
        for point in point_list:
            if point[0] < upperleft[0]:
                upperleft[0] = point[0]
            if point[1] < upperleft[1]:
                upperleft[1] = point[1]
            if point[0] > lowerright[0]:
                lowerright[0] = point[0]
            if point[1] > lowerright[1]:
                lowerright[1] = point[1]
        return [tuple(upperleft), tuple(lowerright)]

    def parse_image_order(self):
        """
        gets the image id from the filename (the _001 part from image0001_001.jpg)
        """
        match = re.search("_[0-9]+\.", self.current_load_path)
        start = match.start()
        end = match.end() - 1
        return(self.current_load_path[start:end])

    #### handlers ############################

    def space_handler(self, event):
        """
        on space, switch image
        """
        self.next_image()
       
    def keypress_handler(self, event):
        """
        destroys crop selection when pressing d
        """
        if event.char == "b":
            self.remove_drawings()
        elif event.char == "f":
            self.flip_image()
        elif event.char == "w":
            new_center = (self.center_rectangle[0],
                          self.center_rectangle[1] - 2)
            self.redraw_rectangle(new_center)
        elif event.char == "s":
            new_center = (self.center_rectangle[0],
                          self.center_rectangle[1] + 2)
            self.redraw_rectangle(new_center)
        elif event.char == "a":
            new_center = (self.center_rectangle[0] - 2,
                          self.center_rectangle[1])
            self.redraw_rectangle(new_center)
        elif event.char == "d":
            new_center = (self.center_rectangle[0] + 2,
                          self.center_rectangle[1])
            self.redraw_rectangle(new_center)
        elif event.char == "q" and self.whole_image:
            self.skip_image()
        elif event.char == "q" and not self.whole_image:
            self.detail_skip_image()
        elif event.char == "r" and not self.whole_image and self.rotation_state:
            self.go_to_rotate()

    #### managing states of the GUI ######################

    def deselect_buttons(self):
        """
        deselects buttons from all the external questions
        """
        for q in self.questions:
            q.deselect_buttons()

    #### detail cropper logic #########################################

    def setup_detail_cropper(self):
        """
        creates the detail cropper interface in the same window window as the
        whole image cropper
        """
        # save to csv and close everything if there are no imgs to crop
        if len(self.cropped_images) == 0:
             self.detail_write_and_exit()
             return
        # destroys all widgets from whole image Cropper
        for widget in self.window.winfo_children():
            widget.destroy()
        # initializing globals
        self.whole_image = False
        # image globals, vertical flip and zoom
        self.flip = False
        self.zoom_factor = 2
        # detail order, for csv writing
        self.detail_order = 0
        # globals related to the crop boundary box
        # if below is true, you can draw the box
        self.continue_drag = True
        # at the start the box does not exist
        self.rect_x1 = None
        self.rect_x2 = None
        self.rect_y1 = None
        self.rect_y2 = None
        # the rotation line does not exist
        self.line1 = None
        self.line2 = None
        self.angle = 0
        # initializing buttons
        self.destroybutton = tk.Button(self.window,
                                       text="destroy the drawing <b>",
                                       command=self.remove_drawings)
        self.finishbutton = tk.Button(self.window,
                                      text="finish (WARNING: skips all "
                                           "images!)",
                                      command=self.detail_write_and_exit,
                                      foreground="red")
        self.flipbutton = tk.Button(self.window,
                                    text="flip image <f>",
                                    command=self.flip_image)
        self.nextbutton = tk.Button(self.window,
                                    text="crop and next image <space>",
                                    command=self.detail_rotate_image)
        self.skipbutton = tk.Button(self.window,
                                    text="skip image <q>",
                                    command=self.detail_skip_image)
        self.flipbutton.grid(row=1, column=0)
        self.destroybutton.grid(row=2, column=0)
        self.nextbutton.grid(row=1, column=1)
        self.skipbutton.grid(row=2, column=1)
        self.finishbutton.grid(row=3, column=0, columnspan=2)
        # resetting space handler handlers
        self.window.bind("<space>", self.detail_space_handler)
        # drawing first image
        self.detail_pop_image()
        self.load_image()
        self.draw_image()
        # setting rotation state
        self.set_rotation_state()

####### main logic ########################################

    def detail_pop_image(self):
        """
        pops the next image path and sets up the new image name (current_image)
        """
        path_and_name = self.cropped_images.pop(0)
        self.current_load_path = path_and_name[0]
        self.current_image = path_and_name[1].replace("_shoe", "_detail")

    def detail_next_image(self):
        """
        defines what happens when you want to go to next image
        crops detail and saves info if bounding box is drawn
        if no images left, writes the data in the csv and ends the program
        """
        # if bounding box drawn, crop
        if self.rect_x1 is not None and self.rect_x2 is not None:
            self.detail_crop_image()
        # if no images left, exit
        if len(self.cropped_images) == 0:
            self.detail_write_and_exit()
            return
        # if images left, show next image
        self.detail_pop_image()
        self.load_image()
        self.draw_image()
        # setting to rotation
        self.set_rotation_state()

    def detail_skip_image(self):
        """
        skips the image and draws the next one
        if no images left, writes the data in the csv and ends the program
        """
        # if no images left, exit
        if len(self.cropped_images) == 0:
            self.detail_write_and_exit()
            return
        self.detail_pop_image()
        self.load_image()
        self.draw_image()
        self.set_rotation_state()

    def detail_crop_image(self):
        """
        saves the image part defined by the rectangle
        """
        # define the crop boundary
        upperleft, lowerright = self.enforce_corners([(self.rect_x1, self.rect_y1),
                                                      (self.rect_x2, self.rect_y2)])
        upperleft, lowerright = self.detail_correct_for_zoom(upperleft, lowerright)
        upperleft, lowerright = self.correct_for_outside_boundary(upperleft, lowerright)
        # crop the image
        cropped = self.rotated_raw_image[
            upperleft[1]:lowerright[1],
            upperleft[0]:lowerright[0]]
        # append data to the current row
        split_str = self.current_image.split('.')
        split_str[0] = split_str[0] + '_detail'
        filename = '.'.join(split_str)
        data_to_append = ([filename] +
                          ["{0:.2f}".format(round(self.degrees, 2))] +
                          [upperleft[0]] +
                          [upperleft[1]] +
                          [lowerright[0]] +
                          [lowerright[1]] +
                          [int(self.flip)])
        self.rows_to_write[self.detail_order].extend(data_to_append)
        self.detail_order += 1

        # saving the cropped image
        save_path = os.path.join(self.directory, filename)
        cv2.imwrite(save_path, cropped)

    def set_rotation_state(self):
        """
        sets the cropper to its rotation state
        """
        self.line1 = None
        self.line2 = None
        self.continue_drag = True
        self.rotation_state = True
        try:
            self.gotorotatebutton.destroy()
        except AttributeError:
            pass
        # changing the next button
        self.nextbutton.config (text = "rotate image <space>", command = self.detail_rotate_image)
        self.window.bind()

    def set_crop_state(self):
        self.continue_drag = True
        self.rotation_state = False
        self.gotorotatebutton = tk.Button(self.window, text = "go to rotate <r>", command = self.go_to_rotate)
        self.gotorotatebutton.grid(row = 4, column = 0, columnspan = 2)
        self.nextbutton.config (text = "crop and next image <space>", command = self.detail_next_image)
        if self.rect_x1 is not None and self.rect_x2 is not None:
            self.draw_rectangle([(self.rect_x1, self.rect_y1),
                                (self.rect_x2, self.rect_y1),
                                (self.rect_x2, self.rect_y2),
                                (self.rect_x1, self.rect_y2)])
            self.draw_helpline()
            self.continue_drag = False

    def go_to_rotate(self):
        """
        returns state from crop to rotate
        the rotation state and how I draw images could use some refactoring to 
        be clearer, but I'm saving time now
        """
        self.set_rotation_state()
        self.draw_image()

    def detail_write_and_exit(self):
        if len(self.rows_to_write) != 0:
            csv_file = open(self.crop_csv, 'ab')
            writer_obj = csv.writer(csv_file,
                                    delimiter = ',',
                                    quotechar = '',
                                    quoting=csv.QUOTE_NONE)
            writer_obj.writerows(self.rows_to_write)
        # destroying the window
        self.window.destroy()

    #### handlers ####################################

    def detail_space_handler(self, event):
        """
        when space, crop and go to next image
        """
        if self.rotation_state:
            self.detail_rotate_image()
        else:
            self.detail_next_image()

    #### drawing in detail cropper ###########################

    def detail_click_handler(self, event):
        """
        first click is saved as the first point of the rectangle
        if rectangle exists, click will re-position the rectangle
        """
        if self.rotation_state:
            if self.line1 == None:
                self.line1 = (event.x, event.y)
        # if it is not rotation and there is no first point, save it
        else:
            if self.rect_x1 == None:
                self.rect_x1 = event.x
                self.rect_y1 = event.y
            # if there is a first point, then redraw the rectangle
            else:
                self.redraw_rectangle((event.x, event.y))
            
    def detail_drag_handler(self, event):
        """
        draws a rectangle and a helpline
        """
        if self.rotation_state and self.continue_drag:
            self.line2 = (event.x, event.y)
            try:
                self.canvas.delete(self.rotation_line)
            except AttributeError:
                pass
            self.rotation_line = self.canvas.create_line(self.line1[0],
                                                         self.line1[1],
                                                         self.line2[0],
                                                         self.line2[1],
                                                         fill = "Red")
        elif not self.rotation_state and self.continue_drag:
            self.rect_x2 = event.x
            self.rect_y2 = event.y
            self.draw_rectangle()
            self.draw_helpline()
        elif not self.rotation_state and not self.continue_drag:
            self.redraw_rectangle((event.x, event.y))

    def detail_release_handler(self, event):
        """
        stops the drawing of the rectangle
        """
        # if only one click was registered, without drag
        # disregard that click
        if self.line2 is None:
            self.line1 = None
        elif self.rect_x2 is None:
            self.rect_x1 = None
            self.rect_y1 = None
        else:
            self.continue_drag = False

    def detail_rotate_image(self):
        """
        rotates the image if a line is drawn
        """
        if self.line1 is not None and self.line2 is not None:
            self.degrees = self.calculate_degrees_rotation(self.line1[0],
                                                           self.line1[1],
                                                           self.line2[0],
                                                           self.line2[1])
            # the part below could go in a separate method
            self.raw_image = cv2.imread(self.current_load_path, 1)
            if self.flip:
                self.raw_image = cv2.flip(self.raw_image, 1)
            self.rotated_raw_image = rotate.rotate_image(self.raw_image,
                                                         self.degrees,
                                                         cv2.INTER_AREA)
            # preparing rotated image for display
            b, g, r = cv2.split(self.rotated_raw_image)
            self.rotated_image = cv2.merge((r,g,b))
            if self.zoom_factor is not 1:
                self.rotated_image = cv2.resize(self.rotated_image,
                                                dsize = None,
                                                fx = self.zoom_factor,
                                                fy = self.zoom_factor,
                                                interpolation = cv2.INTER_NEAREST)
            self.rotated_image = Image.fromarray(self.rotated_image)
            self.rotated_image_tk = ImageTk.PhotoImage(image = self.rotated_image) 
            # drawing new canvas with a different size and the image on it
            self.canvas.destroy()
            self.canvas = tk.Canvas(self.window,
                                    width = self.rotated_image.size[0],
                                    height = self.rotated_image.size[1])
            self.canvas.create_image(0, 0, image = self.rotated_image_tk, anchor = tk.NW)
            self.canvas.grid(row = 0, column = 0, columnspan = 2)
            # adjusting globals
            self.set_crop_state()
            # binding keys to the new canvas
            self.canvas.bind("<Button-1>", self.click_handler)
            self.canvas.bind("<B1-Motion>", self.drag_handler)
            self.canvas.bind("<ButtonRelease-1>", self.release_handler)        

    #### helper functions ##################################

    def calculate_degrees_rotation(self, x1, y1, x2, y2):
        """
        calculates degrees of rotation based on the slope of the drawn line
        """
        x1 = float(x1)
        x2 = float(x2)
        y1 = float(y1)
        y2 = float(y2)
        slope = (y2 - y1) / (x2 - x1)
        radians = math.atan(slope)
        degrees = math.degrees(radians)
        return degrees

    def correct_for_outside_boundary(self, upperleft, lowerright):
        """
        sets the coords to image boundaries if they are going outside of them
        returns tuple (upperleft, lowerright)
        """
        if self.whole_image:
            height, width = self.rotated_raw_image.shape[0:2]
        else:
            height, width = self.image_height, self.image_width
        if upperleft[0] < 0:
                upperleft = (0, upperleft[1])
        if upperleft[1] < 0:
                upperleft = (upperleft[0], 0)
        if lowerright[0] > width:
                lowerright = (width, lowerright[1])
        if lowerright[1] > height:
                lowerright = (lowerright[0], height)
        return (upperleft, lowerright)

    def detail_correct_for_zoom(self, upperleft, lowerright):
        """
        corrects the crop box for the zoom factor
        """
        upperleft = (int(math.floor(upperleft[0] / self.zoom_factor)),
                     int(math.floor(upperleft[1] / self.zoom_factor)))
        lowerright = (int(math.ceil(lowerright[0] / self.zoom_factor)),
                      int(math.ceil(lowerright[1] / self.zoom_factor)))
        return [upperleft, lowerright]
