import Tkinter as tk
from config import *


class Question:

    def __init__(self, name, answers, description, master,
                 use_open_ended=False):
        self.name = name
        self.answers = answers
        self.description = description
        self.master = master
        self.use_open_ended = use_open_ended
        self.value = tk.StringVar()
        self.draw()

    def draw(self):
        self.frame = tk.LabelFrame(self.master,
                                   text=self.description)
        self.frame.config(pady=10)
        self.buttons = []
        for answer in self.answers:
            button = tk.Radiobutton(self.frame,
                                    text=answer,
                                    variable=self.value,
                                    value=answer,
                                    indicatoron=0)
            button.config(width=QUESTION_WIDTH,
                          pady=4,
                          height=1)
            button.pack(anchor=tk.W)
            self.buttons.append(button)

        if(self.use_open_ended):
            self.open_ended_variable = tk.StringVar()
            self.open_ended_question = tk.Entry(
                self.frame,
                textvariable=self.open_ended_variable
            )
            self.open_ended_question.config(width=QUESTION_WIDTH)
            self.open_ended_question.pack(anchor=tk.W)

    def get_answer(self):
        if self.use_open_ended:
            open_answer = self.open_ended_question.get()
            if open_answer != '':
                return open_answer
        return self.value.get()

    def set_answer(self, new_value):
        self.value.set(new_value)

    def get_name(self):
        return self.name

    def deselect_buttons(self):
        for button in self.buttons:
            button.deselect()
        if self.use_open_ended:
            self.open_ended_question.delete(0, tk.END)

    def disable_buttons(self):
        for button in self.buttons:
            button.configure(state=tk.DISABLED)
        if self.use_open_ended:
            self.open_ended_question.configure(state=tk.DISABLED)

    def enable_buttons(self):
        for button in self.buttons:
            button.configure(state=tk.NORMAL)
        if self.use_open_ended:
            self.open_ended_question.configure(state=tk.NORMAL)
