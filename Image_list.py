import os
import re
import random
import warnings
import copy

SUPPORTED_EXTENSIONS = (".jpg", ".JPG", ".PNG", ".png", ".tiff", ".TIFF",
                        ".jpeg", ".JPEG")

class Image_list:
    """
    Takes a folder and organizes the image files into groups. Enables you to
    get the groups out in a queue-like functionality (FIFO) and stores the 
    history: the groups you've passed are not erased.

    The input folder can have any subfolder structure and this structure will
    be preserved in the way the queue is set up.

    Groups are defined in one of two modes. Folder mode means one folder = 
    one group. Constant size mode means that you specify the size of the group.
    Constant size mode also preserves folder structure, meaning that groups can
    contain only images from the same subfolder.
    """

    def __init__(self, directory, size_of_group=None, seed=None):

        self.directory = directory

        if(size_of_group):
            self.mode = 'constant_size'
            self.init_constant_size_mode(directory, size_of_group)
        else:
            self.mode = 'folder'
            self.init_folder_mode(directory)

        if(len(self.groups) == 0):
            raise Exception('No images found in the provided directory! '
                            'Extensions supported: ' +
                            ', '.join(SUPPORTED_EXTENSIONS))

        if seed is not None:
            # randomizing the group and filename list
            random.seed(seed)
            random.shuffle(self.groups)

        # setting the current group order to 0 as no group is active
        self.current_id = 0
        self.current_group = None
        self.state_repeated = None

        # initializing the log
        self.finished = []

    def init_folder_mode(self, path):
        self.groups = []
        self.nr_images = 0
        for root, dirs, files in os.walk(path):
            images = [f for f in files if f.endswith(SUPPORTED_EXTENSIONS)]
            images = sorted(images)  # sort alphabetically
            if(len(images) > 0):
                self.groups.append({
                    'full_dir': root,
                    # avoid prefix '/'
                    'relative_dir': re.split(path, root)[1][1:],
                    'group_name': 'root' + re.split(path, root)[1],
                    'filenames': images,
                    'repeated': False,
                    'count': len(images)
                })
                self.nr_images += len(images)

    def init_constant_size_mode(self, path, size):
        self.groups = []
        self.nr_images = 0
        for root, dirs, files in os.walk(path):

            images = [f for f in files if f.endswith(SUPPORTED_EXTENSIONS)]
            images = sorted(images)  # sort alphabetically

            if(len(images) > 0):
                counter = 1
                while len(images) > 0:
                    image_subgroup = images[0:size]
                    self.groups.append({
                        'full_dir': root,
                        'relative_dir': re.split(path, root)[1],
                        'group_name': 'root' + re.split(path, root)[1] +
                                      '#' + str(counter),
                        'filenames': image_subgroup,
                        'repeated': False,
                        'count': len(image_subgroup)
                    })
                    images = images[size:]
                    counter += 1

                self.nr_images += len(images)

    def __str__(self):
        result = []
        if(len(self.groups) > 0):
            result.append('UNFINISHED IMAGES')
            for image_group in self.groups:
                result.append('----- ' + image_group['group_name'] + ' -----')
                for path in image_group['filenames']:
                    result.append(path)
        if(len(self.finished) > 0):
            result.append('FINISHED IMAGES')
            for image_group in self.finished:
                result.append('----- ' + image_group['group_name'] + ' -----')
                for path in image_group['filenames']:
                    result.append(path)

        return '\n'.join(result)

    def print_summary(self):
        result = []
        if(len(self.groups) > 0):
            result.append('UNFINISHED IMAGES')
            for image_group in self.groups:
                result.append(image_group['group_name'] +
                              ', N = ' + str(image_group['count']))
        if(len(self.finished) > 0):
            result.append('FINISHED IMAGES')
            for image_group in self.finished:
                result.append(image_group['group_name'] +
                              ' : ' + str(image_group['count']))

        return '\n'.join(result)

    def get_next_group(self):
        """
        returns a list with:
            - dictionary with the next group fnames {1:fname1, 2:fname2}
            - the group repeated state True/False
        housekeeping: sets active group as current, archives last group
        if no groups are left, raises Error
        """

        if len(self.groups) == 0:
            raise IndexError('ERROR: no groups left to process')
            return

        if self.current_group and not self.get_repeat_state():
            self.finished.append(self.current_group)

        # preparing the new group
        self.current_group = self.groups.pop(0)
        self.state_repeated = self.current_group['repeated']
        self.current_id += 1

        # resolving the filenames
        self.current_filenames = dict(zip(
            range(1, len(self.current_group['filenames']) + 1),
            self.current_group['filenames']
        ))
        self.ignored_filenames = dict()

        return [self.get_current_filenames(), self.state_repeated]

    def get_previous_group(self):
        """
        returns a list with:
            - dictionary with the previous group fnames {1:fname1, 2:fname2}
            - the group repeated state True/False
        housekeeping: puts back the current active group in the queue,
                      sets previous group as current
        if there is no previous group, raises IndexError.
        Warning: not thoroughly tested with an application that uses repeated
        groups.
        """

        if len(self.finished) == 0:
            warnings.warn('WARNING: no groups before this one')
            return None

        # reinsert current group into the queue
        self.groups.insert(0, self.current_group)

        # set previous group as current
        self.current_group = self.finished.pop()
        self.current_filenames = dict(zip(
            range(1, len(self.current_group['filenames']) + 1),
            self.current_group['filenames']
        ))
        self.state_repeated = self.current_group['repeated']
        self.ignored_filenames = dict()
        self.current_id -= 1

        return [self.get_current_filenames(), self.state_repeated]

    def no_groups_left(self):
        """
        returns True if no groups are left
        """
        if len(self.groups) == 0:
            return True

    def repeat_group(self, times):
        """
        adds a copy of the current group to the list and sets it as repeated
        """
        for idx in reversed(range(times)):
            new_name = self.current_group['group_name'] + "_" + str(idx + 2)
            new_group = copy.deepcopy(self.current_group)
            new_group['group_name'] = new_name
            new_group['repeated'] = True
            self.groups.insert(0, new_group)

    def setup_list(self, last_group_name):
        """
        if you're done with some of the groups, this function will setup the
        to start with the group after the provided last_group
        it's assumed that the list is starting from the __init__ state. I don't
        need it to be more general for now
        """
        for idx in range(len(self.groups)):
            target = self.groups[idx]
            if re.match(target['group_name'], last_group_name):
                next_group_id = idx + 1
        if next_group_id >= len(self.groups):
            self.finished = self.groups[0:next_group_id]
            self.groups = []
        else:
            self.current_group = self.groups[next_group_id]
            self.current_filenames = dict(zip(
                range(1, len(self.current_group['filenames']) + 1),
                self.current_group['filenames']
            ))
            self.ignored_filenames = dict()
            self.state_repeated = self.current_group['repeated']
            self.finished = self.groups[0:next_group_id]
            self.groups = self.groups[next_group_id:]

    def add_remove_filenames(self, image_selection_states):
        """
        removes images indexed in the image_selection_states. The input
        should have this structure: {1: False, 2:True}, where False means that
        you should remove the filename and True means you should keep it.
        """
        for idx in image_selection_states.keys():
            state = image_selection_states[idx]
            if state:
                try:
                    self.current_filenames[idx] = \
                        self.ignored_filenames.pop(idx)
                except KeyError:
                    pass
            else:
                try:
                    self.ignored_filenames[idx] = \
                        self.current_filenames.pop(idx)
                except KeyError:
                    pass

    def get_log(self):
        """
        returns the list of finished group IDs
        """
        return [group['group_name'] for group in self.finished]

    def current_order(self):
        """
        returns the order of the current group, eg if you want to say how many
        are left
        """
        return self.current_id

    def get_current_group(self):
        """
        returns the current group ID
        """
        return self.current_group['group_name']

    def get_current_filenames(self):
        """
        returns fnames for the active group as a list, ordered from first to
        last img since fnames are stored in a dict, this returns fnames ordered
        by the key (i.e., in the way they were entered)
        """
        prefix = self.current_group['full_dir']
        return ['/'.join([prefix, self.current_filenames[idx]]) for idx
                in sorted(self.current_filenames.keys())]

    def get_ignored_filenames(self):
        """
        returns fnames for the active group as a list, ordered from first to
        last img since fnames are stored in a dict, this returns fnames ordered
        by the key (i.e., in the way they were entered)
        """
        return [self.ignored_filenames[idx] for idx
                in sorted(self.ignored_filenames.keys())]

    def get_repeat_state(self):
        """
        returns True if the current group is repeated
        """
        return self.state_repeated

    def get_next_repeat_state(self):
        """
        returns True if the next group is repeated
        """
        if len(self.groups) > 0:
            return self.groups[0]['repeated']
        else:
            return False

    def get_max_images_per_group(self):
        """
        finds the group that has the max nr of images, returns that nr
        """
        max_images = 0
        for group in self.groups:
            if group['count'] > max_images:
                max_images = group['count']
        return max_images

    def get_group_list(self):
        return [group['group_name'] for group in self.groups]

    def get_percent_complete(self):
        """
        returns a string representing percent complete
        """
        done = len(self.finished)
        remain = len(self.groups)
        proportion = float(done) / (done + remain + 1)
        percent = str(int(round(proportion, 2) * 100)) + "%"
        return percent

    def get_nr_groups_complete(self):
        """
        returns integer of number of groups completed
        """
        return len(self.finished)

    def get_nr_groups(self):
        """
        returns integer of number of groups
        """
        return len(self.finished) + len(self.groups)

    def get_timestamp(self):
        """
        hardcoded until I change the rest of the code
        """
        return "99:99"

    def get_relative_dir(self):
        relative_dir = self.current_group['relative_dir']
        if relative_dir == '':
            return relative_dir
        else:
            # starting slashes do not work well with os.path.join
            # should be a smarter way than this, but this works
            if relative_dir[0] == '/' or relative_dir[0] == '\\':
                relative_dir = relative_dir[1:]
            return relative_dir
