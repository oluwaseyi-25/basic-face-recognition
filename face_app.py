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


def log(**data) -> None:

    data["course_id"] = get_course_id(data.get("course"))
    data["location_id"] = get_location_id(data.get("location"))
    data["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pg_cursor.execute(
        """
        INSERT INTO attendance_log (timestamp, user_id, location_id, course_id)
          VALUES 
        (%(timestamp)s, %(user_id)s, %(location_id)s, %(course_id)s);
        """,
        data,
    )
    pg_cursor.execute("COMMIT")


def login(most_recent_capture_arr: Mat, **data) -> str:
    login_user_capture = most_recent_capture_arr.copy()
    login_user_embed = face_recognition.face_encodings(login_user_capture)

    if login_user_embed == []:
        raise No_Face_Detected("No face detected")

    elif len(login_user_embed) > 1:
        raise Multiple_Faces_Detected("Multiple faces detected")

    else:
        login_user_embed = login_user_embed[0]
        print(repr(list(login_user_embed)))

        try:
            # TODO: Constrain face search to < 0.6; Get a range of users and confirm if the user is in the range
            pg_cursor.execute(
                """
                SELECT id, first_name, SQRT(face_embed <-> %s) AS l2_confidence FROM public.students_biodata 
	            ORDER BY l2_confidence
	            LIMIT 1;
                """,
                (repr(list(login_user_embed)),),
            )

            user_id, first_name, l2_confidence = pg_cursor.fetchone()
            print(user_id, first_name, l2_confidence)
            data["user_id"] = user_id
            data["first_name"] = first_name
            data["l2_confidence"] = l2_confidence
            data["course"] = "MEE527"
            data["location"] = "LT1"
            log(**data)
            print(f"User {first_name} logged in successfully")
            return first_name

        except Exception as e:
            print("Something went wrong", e)
            raise User_Not_Registered("User not registered")


def register_new_user(register_new_user_saved_capture: Mat, **biodata) -> None:
    if biodata.get("first_name") == "":
        raise Invalid_Username("Username cannot be empty")
    biodata["department"] = get_department_id(biodata.get("department"))
    biodata["college"] = get_college_id(biodata.get("college"))
    embeddings = face_recognition.face_encodings(
        register_new_user_saved_capture)[0]
    biodata["face_embed"] = repr(list(embeddings))
    pg_cursor.execute(
        """
        INSERT INTO public.students_biodata 
        (first_name, middle_name, last_name, level, matric_no, department_id, college_id, email, phone_number, face_embed)
          VALUES 
        (%(first_name)s, %(middle_name)s, %(last_name)s, %(level)s, %(matric_no)s, %(department)s, %(college)s, 
         %(email)s, %(phone_number)s, %(face_embed)s);
        """,
        biodata,
    )
    pg_cursor.execute("COMMIT;")
    # TODO: Use psycopg to insert the new user into the database
    with open(os.path.join(DB_DIR, f"{biodata.get("first_name")}.pickle"), "wb") as f:
        pickle.dump(embeddings, f)
