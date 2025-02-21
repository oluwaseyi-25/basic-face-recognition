from cProfile import label
import tkinter as tk
import util
from PIL import Image, ImageTk
import cv2

SCREEN_GEOMETRY = '1200x520+1+10'
CAMERA_ID = 0

class App():
    def __init__(self):
        self.main_window = tk.Tk(screenName='face_attendance v0.1')
        self.main_window.geometry(SCREEN_GEOMETRY)

        self.login_button_main_window = util.get_button(self.main_window, 'login', 'green', self.login)
        self.login_button_main_window.place(x=750, y=200)

        self.logout_button_main_window = util.get_button(self.main_window, 'logout', 'red', self.logout)
        self.logout_button_main_window.place(x=750, y=300)

        self.register_new_user_button_main_window = util.get_button(self.main_window, 'register new user', 'gray',
                                                                    self.register_new_user, fg='black')
        self.register_new_user_button_main_window.place(x=750, y=400)

        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(x=10, y=0, width=700, height=500)

        self.add_webcam(self.webcam_label)

    def run(self) -> None:
        self.main_window.mainloop()

    def login(self) -> None:
        pass

    def logout(self) -> None:
        pass

    def register_new_user(self) -> None:
        pass

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



if __name__ == '__main__':
    app = App()
    app.run()
