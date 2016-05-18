# introduction
A tool for cropping and tagging images. The most typical use-case is to prepare images for machine learning.

# setup

## installing
This project uses Python 2.7.12 and pip.

```bash
git clone https://github.com/mbokulic/tagger-cropper
cd tagger-cropper

# run "pip install virtualenv" if you do not have it
# create a new virtual environment in venv/ folder
virtualenv --python=python2.7 venv

# activate the virtual environment
# windows users have run "venv/Scripts/activate.bat"
source venv/bin/activate

# install the dependencies
pip install -r requirements.txt
```

## configuration
```python
# config.py

GROUPING = True  # 
QUESTIONS_PATH = 'questions_example.json'

# graphical parameters
MONTAGE_WIDTH = 1400
MONTAGE_HEIGHT = 700
QUESTION_WIDTH = 30

# setting for the questions
REQUIRED_QUESTION_SECTIONS = ['name', 'description', 'answers', 'open_ended']
GROUP_QUESTION = {
    'name': 'nr_groups',
    'description': 'number of groups of targets',
    'answers': [0, 1, 2, 3],
    'open_ended': True
}
```

## running the program
```bash
$ python main.py -h
usage: main.py [-h] [--image_path IMAGE_PATH] [--output_path OUTPUT_PATH]
               [--size_of_group SIZE_OF_GROUP]

optional arguments:
  -h, --help            show this help message and exit
  --image_path IMAGE_PATH, -i IMAGE_PATH
                        path to where the images you wish to crop are. If you
                        leave empty, the program will ask you to choose a dir
                        interactively
  --output_path OUTPUT_PATH, -o OUTPUT_PATH
                        path to where you want to store the cropped images. If
                        you leave empty, the program will ask you to choose a
                        dir interactively
  --size_of_group SIZE_OF_GROUP, -size SIZE_OF_GROUP
                        Number of images you want per group. If left empty,
                        each group will contain images from the whole folder
```

# how to use

## general idea
Images from the input directory will be divided into groups. The groups will reflect the folder structure of the input directory. There are two modes which you control with CLI arguments

 * folder-by-folder: all images from one folder make up a group
 * constant size: each group will contain N images from the same folder

## group-level tags
The program will display image groups by creating a montage out of individual images. You should then tag the image group by clicking on the tags below, then click "next group". The idea is that tags apply to the whole group.

This is useful e.g., if you want to extract more than one class of image (for example, male and female faces) and it is faster to tag them in bulk instead of one-by-one. The GROUPING parameter in config.py will activate the question asking how many such classes are there. If you set that to True it will also allow you to skip certain groups.

To enlarge an individual image just click on it and click once again anywhere to close.

## cropping and image-level tags
After you tag an event a new window will appear with the first individual image from the montage. You can then crop the part of the image you want and tag that particular crop with the tags below.

Cropped images will be saved in the output directory in the subfolder crop. If there are any subfolders in the input directory, this directory structure will be respected.

You crop by dragging a rectangle over the target area. You can move that rectangle by clicking anywhere on the image, and rotate it using the right mouse button.

You can scrap (remove) the crop by clicking on the appropriate button below or the hotkey "d". Clicking finish will skip cropping altogether.

### cropping the detail
After you crop all of the images you can also crop details from them. Before that, you need to level the image by drawing a line, then crop.

## deselecting images from the montage
If many images are irrelevant to you, you can deselect those. Do this by shift clicking on one image, then another: all images in between will be selected or deselected. You can switch between deselection or selection behavior by clicking on the button on the right. Ctrl-click also works.

## behavior when no images are left
When you click "next image" and it is the last image, a dialog box will appear asking you if you want to exit the program and the Cropper will open up if nr of shoppers is not zero. You should crop the images and only then click "yes" on the dialog box.

I employed a dialog box just to force you to think before clicking "yes". The button "no" doesn't do anything and will actually force you to re-save the last image which is bad behavior (but you can always delete it).

## saving where you left off
Your progress is saved in two csv files in the provided csv directory. If the program finds a valid csv file with the expected filename in the provided directory, it will always start where you left off and if you want to start over you should delete the csv file. 

But remember, if you are tagging a group of images with multiple classes and stop in between tagging, you will not be able to start where you left off. So always tag the whole group, only then stop.

### what if I am done?
If you are done, the event csv will contain the last event in the last row. The program will read this, detect that no images are left and throw a warning. After clicking ok, the program will exit.

## how the tags are stored
Group tags are stored in "group.csv" in the output directory. Each group is indexed by its (sub)folder and a counter if you used constant size mode.

Crop tags are stored in "crop.csv" in the output directory. Each crop is indexed by the image filename.
