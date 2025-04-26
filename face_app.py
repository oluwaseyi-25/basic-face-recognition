import os
import face_recognition
import pickle
import csv
import datetime
from cv2 import Mat
from numpy import mat
import psycopg2
from psycopg.types import none


class No_Face_Detected(Exception):
    pass


class Multiple_Faces_Detected(Exception):
    pass


class User_Not_Registered(Exception):
    pass


class Invalid_Username(Exception):
    pass


DB_DIR = "./db"
if not os.path.exists(DB_DIR):
    os.mkdir(DB_DIR)

pg_db = psycopg2.connect("dbname=face_db user=postgres password=1234")
pg_cursor = pg_db.cursor()

LOG_DIR = "./log"
if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)

LOG_PATH = "log.csv"
LOG_SCHEMA = ["username", "timestamp"]
if not os.path.exists(os.path.join(LOG_DIR, LOG_PATH)):
    with open(os.path.join(LOG_DIR, LOG_PATH), "w") as f:
        _logger = csv.DictWriter(f, fieldnames=LOG_SCHEMA)
        _logger.writeheader()

# TODO: Error handling for database connection

current_class_id:int = 0

def get_department_id(department: str | None) -> int:
    if department is None:
        return 0
    pg_cursor.execute(
        "SELECT id FROM departments WHERE name LIKE %s", (department,))
    return pg_cursor.fetchall()[0][0]

def get_college_id(college: str | None) -> int:
    if college is None:
        return 0
    pg_cursor.execute("SELECT id FROM colleges WHERE name LIKE %s", (college,))
    return pg_cursor.fetchall()[0][0]

def get_student_id(matric_no: str) -> int:
    pg_cursor.execute(
        "SELECT id FROM students_biodata WHERE matric_no LIKE %s", (matric_no,)
    )
    return pg_cursor.fetchall()[0][0]

def get_location_id(location: str) -> int:
    pg_cursor.execute(
        "SELECT id FROM locations WHERE name LIKE %s", (location,))
    return pg_cursor.fetchall()[0][0]

def get_course_id(course: str) -> int:
    pg_cursor.execute(
        "SELECT id FROM courses WHERE course_code LIKE %s", (course,))
    return pg_cursor.fetchall()[0][0]

def get_current_class_id(course_code: str | None) -> int:
    if course_code is None:
        return 0
    pg_cursor.execute("SELECT MAX(id) FROM classes WHERE course_code = %s", (course_code,))
    return pg_cursor.fetchall()[0][0]

def log(**data) -> None:
    global current_class_id
    data["class_id"] = current_class_id
    data["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["image_url"] = data.get("image_url")
    print(data)
    try:
        pg_cursor.execute(
            """
            INSERT INTO attendance_log 
            (matric_no, class_id, level, department, verified, timestamp, image_url)
            VALUES 
            (%(matric_no)s, %(class_id)s, %(level)s, %(dept)s, %(verified)s, %(timestamp)s, %(image_url)s);
            """,
            data,
        )
        pg_db.commit()
    except psycopg2.Error as e:
        pg_db.rollback()
        raise Exception(f"Database error: {e}")

def login(most_recent_capture_arr: Mat, **data) -> str:
    login_user_capture = most_recent_capture_arr.copy()
    login_user_embed = face_recognition.face_encodings(login_user_capture)

    if login_user_embed == []:
        raise No_Face_Detected("No face detected")

    elif len(login_user_embed) > 1:
        raise Multiple_Faces_Detected("Multiple faces detected")

    else:
        login_user_embed = login_user_embed[0]

        try:
            # TODO: Constrain face search to < 0.6; Get a range of users and confirm if the user is in the range
            pg_cursor.execute(
                """
                SELECT id, matric_no, SQRT(face_embed <-> %s) AS l2_confidence FROM public.students_biodata 
	            ORDER BY l2_confidence
	            LIMIT 1;
                """,
                (repr(list(login_user_embed)),),
            )

            user_id, matric_no, l2_confidence = pg_cursor.fetchone()
            print(user_id, matric_no, l2_confidence)
            data["user_id"] = user_id
            data["first_name"] = matric_no
            data["l2_confidence"] = l2_confidence
            data["course"] = "MEE527"
            data["location"] = "LT1"
            log(**data)
            return matric_no
        except psycopg2.Error as e:
            pg_db.rollback()
            raise Exception(f"Database error: {e}")
        except Exception as e:
            print("Something went wrong", e)
            raise User_Not_Registered("User not registered")

def register_new_user(register_new_user_saved_capture: Mat = None, face_flag: bool = False, **biodata) -> None:
    biodata["department"] = get_department_id(biodata.get("department"))
    biodata["college"] = get_college_id(biodata.get("college"))

    if face_flag:
        new_user_embed = face_recognition.face_encodings(
            register_new_user_saved_capture)[0]

        if new_user_embed == []:
            raise No_Face_Detected("No face detected")

        elif len(new_user_embed) > 1:
            raise Multiple_Faces_Detected("Multiple faces detected")

        biodata["face_embed"] = repr(list(new_user_embed))

        pg_cursor.execute(
            """
            INSERT INTO public.students_biodata 
            ( level, matric_no, department_id, face_embed)
            VALUES 
            ( %(level)s, %(matric_no)s, %(department)s, %(face_embed)s);
            """,
            biodata,
        )
    else:
        if biodata.get("first_name") is None or biodata.get("name") is None:
            raise Invalid_Username("Username cannot be empty")

        if biodata.get("name"):
            split_names = str(biodata.get("name")).split(" ", 3)
            if len(split_names) == 1:
                biodata["first_name"] = split_names[0]
                biodata["middle_name"] = None
                biodata["last_name"] = None
            elif len(split_names) == 2:
                biodata["first_name"] = split_names[0]
                biodata["middle_name"] = None
                biodata["last_name"] = split_names[1]
            elif len(split_names) == 3:
                biodata["first_name"] = split_names[0]
                biodata["middle_name"] = split_names[1]
                biodata["last_name"] = split_names[2]
        pg_cursor.execute(
            """
            UPDATE public.students_biodata 
            SET
                first_name = %(first_name)s,
                middle_name = %(middle_name)s,
                last_name = %(last_name)s,
                college_id = %(college)s,
                fprint_id = %(fprint_id)s,
                card_uid = %(card_uid)s
            WHERE matric_no LIKE %(matric_no)s;
            """,
            biodata,
        )

    pg_cursor.execute("COMMIT;")

    with open(os.path.join(DB_DIR, f"{biodata.get("first_name")}.pickle"), "wb") as f:
        pickle.dump(new_user_embed, f)

def log_class_details(class_details: dict) -> None:
    class_details["location_id"] = get_location_id(class_details.get("venue"))
    class_details["start_time"] = class_details.get("start_time").replace(" ", ":00 ")
    pg_cursor.execute(
        """
        INSERT INTO classes (course_code, venue, start_time, dept, level, auth_mode, duration)
        VALUES (%(code)s, %(venue)s, %(start_time)s, %(dept)s, %(level)s, %(auth_mode)s, %(duration)s);
        """,
        class_details,
    )
    pg_cursor.execute("COMMIT;")
    global current_class_id
    current_class_id = get_current_class_id(class_details.get("code"))
    return current_class_id

    
