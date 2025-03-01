import tkinter as tk
import cv2
from PIL import Image, ImageTk
import face_app
import util

scale = 1
MAIN_WINDOW_GEOMETRY = f'{int(1200*scale)}x{int(520*scale)}+1+10'
REGISTER_WINDOW_GEOMETRY = f'{int(1200*scale)}x{int(520*scale)}+10+20'
CAMERA_ID = 0


class App():
    def __init__(self) -> None:
        self.main_window = tk.Tk()
        self.main_window.geometry(MAIN_WINDOW_GEOMETRY)
        self.main_window.title('face_attendance v0.1')

        self.login_button_main_window = util.get_button(self.main_window, 'login', 'green', self.login)
        self.login_button_main_window.place(x=int(750*scale), y=int(300*scale))

        self.register_new_user_button_main_window = util.get_button(self.main_window, 'register new user', 'gray',
                                                                    self.register_new_user, fg='black')
        self.register_new_user_button_main_window.place(x=int(750*scale), y=int(400*scale))

        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(x=10, y=0, width=int(700*scale), height=int(500*scale))

        self.add_webcam(self.webcam_label)

    def run(self) -> None:
        self.main_window.mainloop()


    def add_webcam(self, label:tk.Label) -> None:
        if 'cap' not in self.__dict__:
            self.cap = cv2.VideoCapture(CAMERA_ID)

        self._label = label
        self.process_webcam()


    def process_webcam(self) -> None:
        """
        Continuously captures frames from the webcam and updates the GUI with the latest frame.
        This method reads a frame from the webcam, converts it to an RGB image, and updates the 
        label in the GUI with the latest captured image. If the frame capture fails, it displays 
        an error message and closes the main window.
        Returns:
            None
        """
      
        ret, frame = self.cap.read()

        self.most_recent_capture_arr = frame
        img_ = cv2.cvtColor(self.most_recent_capture_arr, cv2.COLOR_BGR2RGB)
        self.most_recent_capture_pil = Image.fromarray(img_)
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        self._label.imgtk = imgtk
        self._label.configure(image=imgtk)

        self._label.after(20, self.process_webcam)

    def login(self) -> None:
        try:
            username = face_app.login(self.most_recent_capture_arr)

        except face_app.No_Face_Detected:
            util.msg_box('Error', 'No face detected')
            return
        
        except face_app.Multiple_Faces_Detected:
            util.msg_box('Error', 'Multiple faces detected')
            return
        
        except face_app.User_Not_Registered:
            util.msg_box('Error', 'User not registered')
            return
        
        else:
            util.msg_box('Success', f'User {username} was logged in successfully')
            return
        
   
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
        try:
            face_app.register_new_user(self.register_new_user_saved_capture,  first_name=username)

        except face_app.Invalid_Username:
            util.msg_box('Error', 'Please enter a valid username')
            self.register_new_user_window.destroy()
            return
        
        else:
            util.msg_box('Success', 'User was registered successfully')
            self.register_new_user_window.destroy()
            return


    def try_again_button_register_new_user(self) -> None:
        self.register_new_user_window.destroy()



if __name__ == '__main__':
    app = App()
    app.run()
