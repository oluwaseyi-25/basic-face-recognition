import os
import tkinter as tk
import util
from PIL import Image, ImageTk
import cv2
import json
import datetime

import face_recognition
import pickle   

scale = 1
MAIN_WINDOW_GEOMETRY = f'{int(1200*scale)}x{int(520*scale)}+1+10'
REGISTER_WINDOW_GEOMETRY = f'{int(1200*scale)}x{int(520*scale)}+10+20'
CAMERA_ID = 0

DB_DIR = './db'

class App():
    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.geometry(MAIN_WINDOW_GEOMETRY)
        self.main_window.title('face_attendance v0.1')

        self.login_button_main_window = util.get_button(self.main_window, 'login', 'green', self.login)
        self.login_button_main_window.place(x=int(750*scale), y=int(200*scale))

        self.logout_button_main_window = util.get_button(self.main_window, 'logout', 'red', self.logout)
        self.logout_button_main_window.place(x=int(750*scale), y=int(300*scale))

        self.register_new_user_button_main_window = util.get_button(self.main_window, 'register new user', 'gray',
                                                                    self.register_new_user, fg='black')
        self.register_new_user_button_main_window.place(x=int(750*scale), y=int(400*scale))

        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(x=10, y=0, width=int(700*scale), height=int(500*scale))

        self.add_webcam(self.webcam_label)
        
        self.db_dir = DB_DIR
        if not os.path.exists(self.db_dir):
            os.mkdir(self.db_dir)

        self.log_dict = {}
        self.log_path = './log.txt'

    def run(self) -> None:
        self.main_window.mainloop()


    def add_webcam(self, label:tk.Label) -> None:
        if 'cap' not in self.__dict__:
            self.cap = cv2.VideoCapture(CAMERA_ID)

        self._label = label
        self.process_webcam()


    def process_webcam(self) -> None:
        ret, frame = self.cap.read()

        self.most_recent_capture_arr = frame
        img_ = cv2.cvtColor(self.most_recent_capture_arr, cv2.COLOR_BGR2RGB)
        self.most_recent_capture_pil = Image.fromarray(img_)
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        self._label.imgtk = imgtk
        self._label.configure(image=imgtk)

        self._label.after(20, self.process_webcam)

    def login(self) -> None:
        self.login_user_capture = self.most_recent_capture_arr.copy()
        self.login_user_embed = face_recognition.face_encodings(self.login_user_capture)

        if self.login_user_embed == []:
            util.msg_box('Error', 'No face detected')
            return
        
        elif len(self.login_user_embed) > 1:
            util.msg_box('Error', 'Multiple faces detected')
            return
        
        else:
            self.login_user_embed = self.login_user_embed[0]

            for user_profile in os.listdir(self.db_dir):
                with open(os.path.join(self.db_dir, user_profile), 'rb') as f:
                    db_embed = pickle.load(f)
                
                distance = face_recognition.face_distance([db_embed], self.login_user_embed)
                if distance < 0.6:
                    username = user_profile.split('.')[0]
                    # TODO: log the user better
                    self.log(username)
                    util.msg_box('Success', f'User {username} was logged in successfully')
                    break
            else:
                util.msg_box('Error', 'User not registered')
                return

    def logout(self) -> None:
        pass

    def log(self, username:str) -> None:
        # TODO: log the user better
        with open(self.log_path, 'a') as f:
            self.log_dict[username] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            json.dump(self.log_dict, f)


    def register_new_user(self) -> None:
        self.register_new_user_window = tk.Toplevel(self.main_window)
        self.register_new_user_window.geometry(REGISTER_WINDOW_GEOMETRY)
        self.register_new_user_window.title('Register New User')

        self.accept_button_register_new_user = util.get_button(self.register_new_user_window, 
                                                                      'Accept', 
                                                                      'green', 
                                                                      self.accept_button_register_new_user,
                                                                      )

        self.accept_button_register_new_user.place(x=int(scale*750), y=int(scale*300))

        self.try_again_button_register_new_user = util.get_button(self.register_new_user_window,
                                                                      'Try again',
                                                                      'red',
                                                                      self.try_again_button_register_new_user
                                                                      )
        self.try_again_button_register_new_user.place(x=int(scale*750), y=int(scale*400))

        self.capture_label_register_new_user = util.get_img_label(self.register_new_user_window)
        self.capture_label_register_new_user.place(x=10, y=0, width=int(700*scale), height=int(500*scale))

        self.add_img_to_label(self.capture_label_register_new_user)

        self.text_label_register_new_user = util.get_text_label(self.register_new_user_window, 'Enter your name:')
        self.text_label_register_new_user.place(x=int(750*scale), y=int(70*scale))

        self.entry_text_register_new_user = util.get_entry_text(self.register_new_user_window)
        self.entry_text_register_new_user.place(x=int(750*scale), y=int(150*scale))

    def add_img_to_label(self, label:tk.Label) -> None:
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        label.imgtk = imgtk
        label.configure(image=imgtk)

        self.register_new_user_saved_capture = self.most_recent_capture_arr.copy()

    def accept_button_register_new_user(self) -> None:
        username = self.entry_text_register_new_user.get(1.0, 'end-1c')
        if username == '':
            util.msg_box('Error', 'Please enter a valid username')
            self.register_new_user_window.destroy()
            return
        
        embeddings = face_recognition.face_encodings(self.register_new_user_saved_capture)[0]
        with open(os.path.join(self.db_dir, f'{username}.pickle'), 'wb') as f:
            pickle.dump(embeddings, f)

        util.msg_box('Success', 'User was registered successfully')
        self.register_new_user_window.destroy()

    def try_again_button_register_new_user(self) -> None:
        self.register_new_user_window.destroy()



if __name__ == '__main__':
    app = App()
    app.run()
