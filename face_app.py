import os
import face_recognition
import pickle
import csv
import datetime
from cv2 import Mat
from numpy import mat

class No_Face_Detected(Exception):
    pass

class Multiple_Faces_Detected(Exception):    
    pass    

class User_Not_Registered(Exception):
    pass

class Invalid_Username(Exception):
    pass


DB_DIR = './db'
if not os.path.exists(DB_DIR):
    os.mkdir(DB_DIR)

LOG_DIR = './log'
if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)

LOG_PATH = 'log.csv'
LOG_SCHEMA = ['username', 'timestamp'
              ]
if not os.path.exists(os.path.join(LOG_DIR, LOG_PATH)):
    with open(os.path.join(LOG_DIR, LOG_PATH), 'w') as f:
        _logger = csv.DictWriter(f, fieldnames=LOG_SCHEMA)
        _logger.writeheader()

def log(username:str) -> None:
    log_dict = {}

    log_dict['username'] = username
    log_dict['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(os.path.join(LOG_DIR, LOG_PATH), 'a') as f:
        _logger = csv.DictWriter(f, fieldnames=LOG_SCHEMA)
        _logger.writerow(log_dict)


def login(most_recent_capture_arr:Mat) -> str:
    login_user_capture = most_recent_capture_arr.copy()
    login_user_embed = face_recognition.face_encodings(login_user_capture)

    if login_user_embed == []:
        raise No_Face_Detected('No face detected')
            
    elif len(login_user_embed) > 1:
        raise Multiple_Faces_Detected('Multiple faces detected')
    
    else:
        login_user_embed = login_user_embed[0]

        for user_profile in os.listdir(DB_DIR):
            with open(os.path.join(DB_DIR, user_profile), 'rb') as f:
                db_embed = pickle.load(f)
            
            distance = face_recognition.face_distance([db_embed], login_user_embed)
            if distance < 0.6:
                username = user_profile.split('.')[0]
                log(username)
                return username
        else:
            raise User_Not_Registered('User not registered')
        

def accept_button_register_new_user(name:str, register_new_user_saved_capture:Mat) -> None:
    if name == '':
        raise Invalid_Username('Username cannot be empty')
    
    embeddings = face_recognition.face_encodings(register_new_user_saved_capture)[0]
    with open(os.path.join(DB_DIR, f'{name}.pickle'), 'wb') as f:
        pickle.dump(embeddings, f)