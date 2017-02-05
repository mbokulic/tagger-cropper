# a JSON file for setting up tags. Each question
# group_level refers to tags you apply on all images in the group
# image_level are tags that show up only for individual images
QUESTIONS_PATH = 'questions_example.json'

# if True, a question asking "how many classes of targets" will appear
GROUPING = True

# graphical parameters
MONTAGE_WIDTH = 1400
MONTAGE_HEIGHT = 700
QUESTION_WIDTH = 30  # width of the question buttons
ZOOM_LEVEL = 0.5   # zoom level for images when cropping

# required sections for the questions definitions
REQUIRED_QUESTION_SECTIONS = ['name', 'description', 'answers', 'open_ended']

# definition of the question when GROUPING = True
GROUP_QUESTION = {
    'name': 'nr_groups',
    'description': 'number of classes of targets',
    'answers': [0, 1, 2, 3],
    'open_ended': True
}
