from Group_tagger import *
import argparse
import os
import json
from config import *


argparser = argparse.ArgumentParser()

argparser.add_argument(
    '--image_path', '-i',
    help='path to where the images you wish to crop are. If '
    'you leave empty, the program will ask you to choose a '
    'dir interactively',
    default=None
)

argparser.add_argument(
    '--output_path', '-o',
    help='path to where you want to store the cropped images. '
    'If you leave empty, the program will ask you to choose a '
    'dir interactively',
    default=None
)

argparser.add_argument(
    '--size_of_group', '-size', type=int,
    help='Number of images you want per group. If left empty, '
    'each group will contain images from the whole folder'
)

args = argparser.parse_args()

if args.image_path:
    if not os.path.isdir(args.image_path):
        raise FileNotFoundError(
            'Error: image path you provided does not exist!')


def test_question_dictionary(qdict):
    if not set(REQUIRED_QUESTION_SECTIONS).issubset(qdict):
        raise Exception('every question provided should have the following '
                        'sections: ' + ', '.join(REQUIRED_QUESTION_SECTIONS))


# going through other questions
loaded_questions = json.load(open(QUESTIONS_PATH, 'r'))
group_questions = loaded_questions['group_level']
image_questions = loaded_questions['image_level']

for question in group_questions + image_questions:
    test_question_dictionary(question)

if GROUPING:
    group_questions.insert(0, GROUP_QUESTION)

root = tk.Tk()  # this is the Tkinter window
group_tagger = Group_tagger(
    master=root,
    group_question_definitions=group_questions,
    image_question_definitions=image_questions,
    image_dir=args.image_path,
    size_of_group=args.size_of_group,
    output_path=args.output_path)

group_tagger.run()

root.mainloop()
