import os
import sys
import time
import random
import threading
from tkinter import Tk, Frame, Label, Button, StringVar, OptionMenu, Text, NORMAL, DISABLED, INSERT, LEFT, RIGHT, BOTTOM
from tkinter.filedialog import askopenfilename
from pygame import mixer
from scipy import stats
from pydub import AudioSegment
from pathlib import Path
from shutil import copy


def measure_time(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper


class AudioTestApp:
    def __init__(self, root):
        self.root = root
        self.tries, self.correct = 0, 0
        self.setup_ui()
        mixer.init()
        self.files_location = self.create_file_directory()
        self.filepath = None
        self.file_orig, self.file_orig_path, self.file_orig_name, self.file_orig_ext = None, None, None, None
        self.file_conv, self.file_conv_inv, self.file_mix = None, None, None
        

    def setup_ui(self):
        self.frame1 = Frame(self.root)
        self.frame2 = Frame(self.root)
        self.frame1.pack(padx=5, pady=5)
        self.frame2.pack(padx=5, pady=5)
        self.root.title("AudioTest")
        self.root.geometry("500x600")
        self.generate_random_file()
        self.label_file_name = Label(self.frame1, text="")
        self.label_file_name.pack(side=BOTTOM)
        self.label_quality = Label(self.frame2, text="Set Desired Quality (kbit/s):")
        self.label_quality.pack(side=LEFT)
        self.quality_list = ("65", "100", "165", "225", "320")
        self.quality_selected = StringVar(self.root)
        self.quality_menu = OptionMenu(self.frame2, self.quality_selected, *self.quality_list)
        self.quality_menu.pack(side=RIGHT)
        self.label_file = Label(self.frame1, text="Open File to Convert:")
        self.label_file.pack(side=LEFT)

        self.file_location = os.path.realpath(os.path.join(os.path.dirname(__file__), 'files'))

        self.button_choose = Button(self.frame1, command=self.button_choose_click, text="Choose File")
        self.button_choose.pack(side=RIGHT)
        self.button_convert = Button(self.root, command=self.button_convert_click, text="Convert File")
        self.button_convert.pack(padx=5, pady=5)
        self.button_convert["state"] = "disabled"
        self.button_open = Button(self.root, command=self.open_location, text="Open File Directory")
        self.button_open.pack(padx=5, pady=5)
        self.frame3 = Frame(self.root)
        self.frame3.pack()
        self.button_play_a = Button(self.frame3, command=lambda: self.play_sound('a'), text="Play A")
        self.button_play_a.pack(side=LEFT, padx=5, pady=5)
        self.button_play_b = Button(self.frame3, command=lambda: self.play_sound('b'), text="Play B")
        self.button_play_b.pack(side=RIGHT, padx=5, pady=5)
        self.frame4 = Frame(self.root)
        self.frame4.pack()
        self.button_play_x = Button(self.frame4, command=lambda: self.play_sound('x'), text="Play X")
        self.button_play_x.pack(side=LEFT, padx=5, pady=5)
        self.button_play_y = Button(self.frame4, command=lambda: self.play_sound('y'), text="Play Y")
        self.button_play_y.pack(side=RIGHT, padx=5, pady=5)
        self.frame5 = Frame(self.root)
        self.frame5.pack()
        self.button_a_x = Button(self.frame5, command=lambda: self.evaluate_guess('a_x'), text="A is X, B is Y")
        self.button_a_x.pack(side=LEFT, padx=5, pady=5)
        self.button_a_y = Button(self.frame5, command=lambda: self.evaluate_guess('a_y'), text="A is Y, B is X")
        self.button_a_y.pack(side=RIGHT, padx=5, pady=5)
        
        self.label_score = Label(self.root, text=f"{self.correct}/{self.tries}")
        self.label_score.pack()
        self.label_p = Label(self.root, text="p=1")
        self.label_p.pack()
        self.label_logs = Label(self.root, text="Logs:")
        self.label_logs.pack()
        self.logs = Text(self.root, height=15, width=52)
        self.logs.pack(padx=5, pady=5)
        sys.stdout.write = self.redirector

    def create_file_directory(self):
        self.file_location = os.path.realpath(os.path.join(os.getcwd(), 'files'))
        if not os.path.exists(self.file_location):
            os.makedirs(self.file_location)
        return self.file_location

    @measure_time
    def open_file(self):
        print("Opening...")
        filepath = askopenfilename()
        file = AudioSegment.from_file(filepath)
        self.p = 1
        self.tries = 0
        self.correct = 0
        self.label_score.config(text="0/0")
        self.label_p.config(text="p=1")
        self.buttons_change_state("disabled")
        copy(filepath, self.file_location)
        return file, filepath
    
    @measure_time
    def convert_file(self, file, filename):
        print("Converting...")
        quality = self.quality_selected.get()
        self.file_conv_path = f"{self.file_location}/{filename}_{quality}.mp3"
        file.export(self.file_conv_path,
                    format="mp3", bitrate=f"{quality}k")
        file_converted = AudioSegment.from_file(
            f"{self.file_location}/{filename}_{quality}.mp3", format="mp3")
        self.buttons_change_state("normal")
        return file_converted

    @measure_time
    def invert_file(self, file):
        print("Inverting...")
        file_inverted = file.invert_phase()
        return file_inverted
    
    @measure_time
    def mix_files(self, file1, file2, filename):
        print("Mixing...")
        file_mixed = file1.overlay(file2, position=0)
        file_mixed.export(f"{self.file_location}/{filename}_mix.mp3")
        return file_mixed
    
    def button_choose_click(self):
        threading.Thread(target=self.open_file_thread, daemon=True).start()

    def button_convert_click(self):
        threading.Thread(target=self.convert_file_thread, daemon=True).start()

    def open_file_thread(self):
        try:
            self.file_orig, self.file_orig_path = self.open_file()
            self.root.after(0, self.post_open_file)
        except OSError:
            print("Cancelled.")

    def convert_file_thread(self):
        self.file_conv = self.convert_file(self.file_orig, self.file_orig_name)
        self.file_conv_inv = self.invert_file(self.file_conv)
        self.file_mix = self.mix_files(self.file_orig, self.file_conv_inv, self.file_orig_name)
        print("Finished.")
        self.root.after(0, self.post_convert_file)

    def post_open_file(self):
        if self.file_orig_path:
            self.file_orig_name = Path(self.file_orig_path).stem
            self.file_orig_ext = Path(self.file_orig_path).suffix
            self.label_file_name.config(text=self.file_orig_name+self.file_orig_ext)
            self.button_convert["state"] = "normal"

    def post_convert_file(self):
        self.buttons_change_state("normal")
        
    def open_location(self):
        os.system("start "+str(self.file_location))
        
    def redirector(self, inputStr):
        self.logs.config(state=NORMAL)
        self.logs.insert(INSERT, inputStr)
        self.logs.config(state=DISABLED)
        self.logs.see("end")
    
    def play_sound(self, sound_type):
        if sound_type == 'a':
            file_to_play = self.file_orig_path if self.rand_file[0] == 0 else self.file_conv_path
        elif sound_type == 'b':
            file_to_play = self.file_orig_path if self.rand_file[0] == 1 else self.file_conv_path
        elif sound_type == 'x':
            file_to_play = self.file_orig_path if self.rand_file[1] == 0 else self.file_conv_path
        elif sound_type == 'y':
            file_to_play = self.file_orig_path if self.rand_file[1] == 1 else self.file_conv_path

        mixer.music.stop()
        mixer.music.load(file_to_play)
        mixer.music.play()
        
    def evaluate_guess(self, guess_type):
        self.tries += 1
        if guess_type == 'a_x':
            if self.rand_file[0] == self.rand_file[1]:
                self.correct += 1
        elif guess_type == 'a_y':
            if self.rand_file[0] != self.rand_file[1]:
                self.correct += 1

        score_text = f"{self.correct}/{self.tries}"
        self.label_score.config(text=score_text)

        p_value = stats.binomtest(self.correct, n=self.tries, p=0.5, alternative='greater').pvalue
        self.label_p.config(text=f"p={round(p_value, 3)}")

        self.generate_random_file()
        mixer.music.stop()
    
    def generate_random_file(self):
        self.rand_file = (random.randint(0, 1), random.randint(0, 1))
        
    def buttons_change_state(self, state):
        self.button_play_a["state"] = state
        self.button_play_b["state"] = state
        self.button_play_x["state"] = state
        self.button_play_y["state"] = state
        self.button_a_x["state"] = state
        self.button_a_y["state"] = state

def main():
    root = Tk()
    AudioTestApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
