import Tkinter as tk
import tkMessageBox
import os
import time
import csv
import sys
from PIL import Image, ImageTk
from Montage import *
from Image_list import *
from Cropper import *
from tkFileDialog import askdirectory
import Question
from config import *


class Group_tagger:
    """
    defines the gui when tagging whole groups (i.e., montages)
    needs an Image_list class object which contains some of the logic
    """

    def __init__(self,
                 master,
                 group_question_definitions,
                 image_question_definitions,
                 image_dir,
                 output_path,
                 size_of_group=None):

        if image_dir is None:
            image_dir = askdirectory(
                title='set directory where the images are located')
        if output_path is None:
            output_path = askdirectory(
                title='set dir where you want to save the output data')

        self.master = master
        self.image_question_definitions = image_question_definitions
        self.image_list = Image_list(directory=image_dir,
                                     size_of_group=size_of_group)

        # creating the crop path
        self.crop_output_path = os.path.join(output_path, 'crop')
        if not os.path.exists(self.crop_output_path):
            os.makedirs(self.crop_output_path)

        # creating the csv paths
        self.group_csv = os.path.join(output_path, "groups.csv")
        self.crop_csv = os.path.join(output_path, "crop.csv")

        # opening an old csv file or creating a new one if there isn't any
        # the tagging will start where the csv file says it left off
        try:
            csv_file = open(self.group_csv, 'r')
            reader = csv.DictReader(csv_file)
            for row in reader:
                last_group_name = row["group_id"]
            self.image_list.setup_list(last_group_name)
            print "MESSAGE: successfully loaded old csv file!\n"

        except (IOError, IndexError, NameError):
            if raw_input('The program will create a new groups.csv file '
                         'and remove others. Do you want to continue?\n'
                         'Type y to continue:') != 'y':
                sys.exit()
            print "\n"

            csv_file = open(self.group_csv, 'wb')
            writer_obj = csv.writer(
                csv_file, delimiter=',', quotechar='', quoting=csv.QUOTE_NONE)
            column_names = [q['name'] for q in group_question_definitions]
            column_names.insert(0, 'group_id')
            writer_obj.writerow(column_names)

            # if no group.csv file, delete old crop.csv and create new
            try:
                os.remove(self.crop_csv)
            except OSError:
                pass
            csv_file = open(self.crop_csv, 'wb')
            writer_obj = csv.writer(csv_file,
                                    delimiter=',',
                                    quotechar='',
                                    quoting=csv.QUOTE_NONE)
            column_names = [
                "group_id",
                "image_filename",
                "rotation_degrees",
                "upperleft_x", "upperleft_y",
                "lowerright_x", "lowerright_y",
                "flip_state",
                "logo_filename",
                "rotation_degrees_detail",
                "upperleft_x_detail", "upperleft_y_detail",
                "lowerright_x_detail", "lowerright_y_detail",
                "flip_state_detail"
            ]
            for question_def in self.image_question_definitions:
                column_names.append(question_def['name'])
            writer_obj.writerow(column_names)

        # location of click when selecting images
        self.shift_x1 = None
        self.shift_y1 = None
        self.shift_x2 = None
        self.shift_y2 = None

        # drawing the gui for the tags
        self.questions = []
        for question_def in group_question_definitions:
            question = Question.Question(
                name=question_def['name'],
                answers=question_def['answers'],
                description=question_def['description'],
                use_open_ended=question_def['open_ended'],
                master=self.master)
            self.questions.append(question)

        # next image button
        self.nextbutton = tk.Button(
            master, text="next group", command=self.next_group)

        # button for switching between selection and ignoring
        self.selectbutton = tk.Button(
            master, text="switch to\ndeselect",
            command=self.switch_ignore_select, background="#02cf12"
        )

        # organizing all the elements in a layout
        n = len(self.questions)
        for idx in range(n):
            self.questions[idx].frame.grid(row=1, column=idx)
        self.nextbutton.grid(row=2, column=0, columnspan=n)
        self.selectbutton.grid(row=0, column=n + 1)

        self.master.bind("<space>", self.space_handler)

    def space_handler(self, event):
        self.nextbutton.invoke()

    def next_group(self):
        """
        this (somewhat ugly) method contains the logic of the program
        Defines what happens when you click "next image"
        """
        # process_tags method returns False if not all tags were entered
        # if so, do not go futher

        if self.process_tags() is False:
            return
        # setting flip state for the cropper
        flip = False

        # the text input and buttons for nr of groups
        # are separated. Text input overrides buttons
        if GROUPING:
            target_question = self.questions[0]
            nr_groups = int(target_question.get_answer())
        else:
            nr_groups = 1

        if nr_groups != 0:
            # run cropper if there are images you want to crop
            self.run_cropper(flip)

        # current group is repeated with multiple groups
        if self.image_list.get_repeat_state():
            # state when current image is repeated
            if self.image_list.get_next_repeat_state():
                # if next group is repeated, then disable grouping button
                self.toggle_groupbutton(on=False)
                self.deselect_buttons(deselect_group=False)
            else:
                # if next group is not repeated, then enable grouping button
                self.toggle_groupbutton(on=True)
                self.deselect_buttons()
        elif nr_groups > 1:
            # if more than one group
            # add repeated groups to list, disable grouping button
            self.image_list.repeat_group(times=nr_groups - 1)
            self.deselect_buttons(deselect_group=False)
            self.toggle_groupbutton(on=False)
        else:
            self.deselect_buttons()
        # close GUI if no images are left
        if self.image_list.no_groups_left():
            if tkMessageBox.askyesno(
                "No images left",
                "do you want to quit? (crop the images first!)"
            ):
                self.master.destroy()
            return
        # draw the next image
        self.image_list.get_next_group()
        self.draw_montage(repeated=self.image_list.get_repeat_state())

    def run_cropper(self, flip):
        """
        runs Cropper in a separate window
        """
        window = tk.Toplevel(self.master)
        window.grab_set()
        window.focus()
        self.cropper = Cropper(
            window,
            self.image_question_definitions,
            self.image_list.get_current_filenames(),
            os.path.join(self.crop_output_path,
                         self.image_list.get_relative_dir()),
            self.crop_csv,
            self.image_list.get_current_group(),
            flip,
            ZOOM_LEVEL)
        self.cropper.run()
        self.master.wait_window(window)

    def deselect_buttons(self, deselect_group=True):
        """
        deselects all buttons. Has a boolean tag whether to deselect the
        groupbutton
        """
        start_index = 0
        if GROUPING:
            if not deselect_group:
                start_index = 1

        for question in self.questions[start_index:]:
            question.deselect_buttons()

    def toggle_groupbutton(self, on=True):
        """
        convenience function for turning off the groupbutton
        """
        if GROUPING:
            if on:
                self.questions[0].enable_buttons()
            else:
                self.questions[0].disable_buttons()

    def draw_montage(self, repeated=False):
        """
        draws a montage, binds the montage to its handler, except if the group
        is repeated. Sets up the dictionary that saves the selection state for
        each image
        """
        if repeated:
            self.master.wm_title(self.image_list.get_current_group())
            self.canvas.delete(tk.ALL)
            self.canvas.create_image(
                0, 0, image=self.image_tk, anchor=tk.NW)
        else:
            self.filenames = self.image_list.get_current_filenames()
            self.image = Montage(self.filenames,
                                 (MONTAGE_WIDTH, MONTAGE_HEIGHT),
                                 (1, 2),
                                 False)
            self.image_tk = ImageTk.PhotoImage(self.image.draw_montage())
            try:
                self.canvas.delete(tk.ALL)
            except AttributeError:
                self.canvas = tk.Canvas(self.master,
                                        width=self.image.get_size()[0],
                                        height=self.image.get_size()[1])
                self.canvas.grid(row=0,
                                 column=0,
                                 columnspan=len(self.questions) + 1)
            self.canvas.create_image(0, 0, image=self.image_tk, anchor=tk.NW)
            self.master.wm_title(
                self.image_list.get_current_group() +
                ' | ' +
                self.image_list.get_percent_complete() +
                ' complete | ' +
                str(self.image_list.get_nr_groups_complete()) +
                ' image groups done')
            self.canvas.bind("<Button-1>", self.montage_click)
            self.canvas.bind("<Shift-Button-1>", self.shift_click_handler)
            self.canvas.bind("<Control-Button-1>", self.control_click_handler)
        # create dict image_order(start from 1):selection_state
        # at first none are selected
        self.image_selection_states = {
            index: False for index in range(1, self.image.get_nr_images() + 1)}
        # set shiftclick selection behavior to deselect
        self.deselect = False

    def switch_ignore_select(self):
        """
        for shift-click and control-click switches between deselecting or
        selecting imgs. Default is select
        """
        self.deselect = not self.deselect
        if self.deselect:
            self.selectbutton.config(background = "#ff8c8c", text = "switch to\nselect")
        else:
            self.selectbutton.config(background = "#02cf12", text = "switch to\ndeselect")
        # deletes previous drawings from canvas
        self.canvas.delete(tk.ALL)
        self.canvas.create_image(0, 0, image = self.image_tk, anchor = tk.NW)
        # sets selection states to all imgs being deselected
        if self.deselect:
            self.image_selection_states = {index:True for index in range(1, self.image.get_nr_images() + 1)}
        else:
            self.image_selection_states = {index:False for index in range(1, self.image.get_nr_images() + 1)}

    def shift_click_handler(self, event):
        """
        when you shift-click on an image in the montage, and then shift click
        on another these and all imgs between them will be either deselected or
        selected from images to crop and a cross or a checkmark will be drawn
        across them
        """
        # setting the first image
        if self.shift_x1 is None:
            self.shift_x1 = event.x
            self.shift_y1 = event.y
        # setting the second image and running other code
        elif self.shift_x2 is None:
            self.shift_x2 = event.x
            self.shift_y2 = event.y
            # getting the order for start and end imgs
            order1 = self.image.get_image_index(self.shift_x1, self.shift_y1)
            order2 = self.image.get_image_index(self.shift_x2, self.shift_y2)
            # generating a list of indices based on start and end orders
            if order1 < order2:
                index_list = range(order1, order2 + 1)
            elif order1 > order2:
                index_list = range(order2, order1 + 1)
            else:
                index_list = [order1]
            # taking the intersection btw chosen tiles and actual imgs, this removes empty imgs
            index_list = set(index_list).intersection(self.image_selection_states.keys())
            # reversing the selection state for the selected imgs
            for idx in index_list:
                self.image_selection_states[idx] = not self.image_selection_states[idx]
            # updating the selection in image_list
            self.image_list.add_remove_filenames(self.image_selection_states)
            # drawing crosses or checkmarks
            self.draw_selection_states()
            # resetting the keys
            self.shift_x1 = None
            self.shift_y1 = None
            self.shift_x2 = None
            self.shift_y2 = None

    def control_click_handler(self, event):
        """
        when you control-click on an image in the montage
        it will be either deselected or selected from images to crop
        and a cross or a checkmark will be drawn across it
        """
        index = self.image.get_image_index(event.x, event.y)
        self.image_selection_states[index] = not self.image_selection_states[index]
        self.image_list.add_remove_filenames(self.image_selection_states)
        self.draw_selection_states()

    def draw_selection_states(self):
        """
        will draw a cross across deselected imgs if in deselect state
        or a checkmark if in select state
        """
        self.canvas.delete(tk.ALL)
        self.canvas.create_image(0, 0, image = self.image_tk, anchor = tk.NW)
        if self.deselect:
            for index, state in self.image_selection_states.iteritems():
                if not state:
                    center = self.image.get_image_center_from_order(index)
                    self.draw_x(center[0], center[1])
        else:
            for index, state in self.image_selection_states.iteritems():
                if state:
                    center = self.image.get_image_center_from_order(index)
                    self.draw_checkmark(center[0], center[1])

    def draw_x(self, x, y):
        """
        draws an x with the center at x, y
        """
        x1 = x + 10
        y1 = y + 10
        x2 = x - 10
        y2 = y - 10
        self.canvas.create_line(x1, y1, x2, y2, fill = "Red", width = 3)
        x1 = x + 10
        y1 = y - 10
        x2 = x - 10
        y2 = y + 10
        self.canvas.create_line(x1, y1, x2, y2, fill = "Red", width = 3)

    def draw_checkmark(self, x, y):
        """
        draws a checkmark with the center at x, y
        """
        x1 = x + 5
        y1 = y + 5
        x2 = x - 5
        y2 = y - 5
        self.canvas.create_line(x1, y1, x2, y2, fill="Green", width=3)
        x1 = x + 5
        y1 = y + 5
        x2 = x + 15
        y2 = y - 15
        self.canvas.create_line(x1, y1, x2, y2, fill="Green", width=3)

    def montage_click(self, event):
        """
        callback function for the event of clicking inside the image
        displays the full sized image in another window, closes the window if
        you click anywhere inside the GUI
        """
        image_order = self.image.get_image_index(event.x, event.y)

        # this will create a pop-up window with the selected image
        if (image_order - 1) < len(self.filenames):
            self.pop_up_image = tk.Toplevel()
            image = Image.open(self.filenames[image_order - 1])
            image_tk = ImageTk.PhotoImage(image)
            groupimage = tk.Label(self.pop_up_image, image=image_tk)
            groupimage.image = image_tk
            groupimage.pack()
            groupimage.grab_set()
            groupimage.bind("<Button-1>", self.exit_pop_up)

    def process_tags(self):
        """
        appends tags to the last row in the csv
        returns False and runs a warning box if not all tags are filled
        """
        # if there are no groups, all values are set to empty
        # and no warning raised if tags are not filled
        if GROUPING:
            nr_groups = self.questions[0].get_answer()
            if (nr_groups == "0"):
                for question in self.questions[1:]:
                    question.set_answer('')
                return True

        for question in self.questions:
            if question.get_answer() == '':
                tkMessageBox.showwarning("ERROR", "enter all tags!")
                return False

        # opens the csv in write / binary mode
        csv_file = open(self.group_csv, 'ab')
        writer_obj = csv.writer(csv_file,
                                delimiter=',',
                                quotechar='',
                                quoting=csv.QUOTE_NONE)

        answers = [[question.get_answer()] for question in self.questions]
        row_to_write = ([self.image_list.get_current_group()] + answers)
        writer_obj.writerow(row_to_write)
        csv_file.close()
        return True

    #### helper functions ##############################################

    def run(self):
        """
        convenience function for running the first montage. Throws an error if
        the provided csv file already containts the last event
        """
        try:
            self.start_time = time.time()
            self.image_list.get_next_group()
            self.draw_montage()
        # if the group method throws an index error, that means you're
        # trying to pop from an empty list which means you're already done
        except IndexError:
            tkMessageBox.showwarning("you are already done!",
                                     'the csv dir provided contains a csv file'
                                     ' which suggests that you have completed '
                                     'all images')
            self.master.destroy()

    def exit_pop_up(self, event):
        self.pop_up_image.destroy()

    def create_csv_path(self, output_path, string, date):
        csv_path = os.path.abspath(output_path +
                                   "/" +
                                   date +
                                   "/" +
                                   string +
                                   date +
                                   ".csv")
        return csv_path
