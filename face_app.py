"""
face_app.py

This module handles database operations, face recognition, and user management
for the face recognition system. It integrates with PostgreSQL for data storage
and uses the `face_recognition` library for face encoding and matching.

Features:
- Database integration for storing user and attendance data.
- Face recognition using the `face_recognition` library.
- Custom exceptions for specific error cases.
- Utility functions for retrieving IDs from the database.

Dependencies:
- face_recognition
- psycopg2
- OpenCV (cv2)
- NumPy
"""

import os
from dotenv import load_dotenv
import face_recognition
import datetime
from cv2 import Mat
import psycopg2

# Load environment variables from .env file
load_dotenv()

# Retrieve sensitive variables from environment
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# Update database connection
pg_db = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
pg_cursor = pg_db.cursor()


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

THRESHOLD = 0.65


current_class_id: int = 0


def get_department_id(department: str | None) -> int:
    """
    Get the department ID from the database.

    Args:
        department (str | None): The name of the department.

    Returns:
        int: The department ID.
    """
    if department is None:
        return 0
    pg_cursor.execute(
        "SELECT id FROM departments WHERE code = %s", (department,))
    return pg_cursor.fetchall()[0][0]


def get_college_id(college: str | None) -> int:
    """
    Get the college ID from the database.

    Args:
        college (str | None): The name of the college.

    Returns:
        int: The college ID.
    """
    if college is None:
        return 0
    pg_cursor.execute("SELECT id FROM colleges WHERE name = %s", (college,))
    return pg_cursor.fetchall()[0][0]


def get_student_id(matric_no: str) -> int:
    """
    Get the student ID from the database.

    Args:
        matric_no (str): The matriculation number of the student.

    Returns:
        int: The student ID.
    """
    pg_cursor.execute(
        "SELECT id FROM students_biodata WHERE matric_no = %s", (matric_no,)
    )
    return pg_cursor.fetchall()[0][0]


def get_location_id(location: str) -> int:
    pg_cursor.execute(
        "SELECT id FROM locations WHERE name = %s", (location,))
    return pg_cursor.fetchall()[0][0]


def get_course_id(course: str) -> int:
    pg_cursor.execute(
        "SELECT id FROM courses WHERE course_code = %s", (course,))
    return pg_cursor.fetchall()[0][0]


def get_current_class_id(course_code: str | None) -> int:
    if course_code is None:
        return 0
    pg_cursor.execute(
        "SELECT MAX(id) FROM classes WHERE course_code = %s", (course_code,))
    return pg_cursor.fetchall()[0][0]


def log(**data) -> None:
    """
    Log attendance data to the database.

    Args:
        data (dict): Attendance data to log.

    Raises:
        Exception: If a database error occurs.
    """
    global current_class_id
    data["class_id"] = current_class_id
    data["log_timestamp"] = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S.%f")
    data["image_url"] = data.get("image_filename")
    data["verified"] = data.get("verified", False)
    data["scan_timestamp"] = data.get(
        "scan_timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    data["l2_confidence"] = data.get("l2_confidence")
    print(data)
    try:
        pg_cursor.execute(
            """
            INSERT INTO attendance_log 
            (matric_no, class_id, level, department, verified, scan_timestamp, log_timestamp, image_url, confidence)
            VALUES 
            (%(matric_no)s, %(class_id)s, %(level)s, %(dept)s, %(verified)s, %(scan_timestamp)s, %(log_timestamp)s, %(image_url)s, %(l2_confidence)s);
            """,
            data,
        )
        pg_db.commit()
    except psycopg2.Error as e:
        pg_db.rollback()
        raise Exception(f"Database error: {e}")


def login(most_recent_capture_arr: Mat, **data) -> str:
    """
    Authenticate a user by matching their face encoding.

    Args:
        most_recent_capture_arr (Mat): The most recent face capture as a NumPy array.
        data (dict): Additional data for logging.

    Returns:
        str: The matriculation number of the authenticated user.

    Raises:
        No_Face_Detected: If no face is detected in the image.
        Multiple_Faces_Detected: If multiple faces are detected in the image.
        User_Not_Registered: If the user is not found in the database.
    """
    login_user_capture = most_recent_capture_arr.copy()
    login_user_embed = face_recognition.face_encodings(login_user_capture,
                                                       num_jitters=4)

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
                WHERE matric_no = '%s'
                ORDER BY l2_confidence ASC
                LIMIT 1;
                """,
                (repr(list(login_user_embed)), data.get("matric_no")),
            )

            user_id, matric_no, l2_confidence = pg_cursor.fetchone()
            if not any([user_id, matric_no, l2_confidence]):
                raise User_Not_Registered("User not registered")

            print(user_id, matric_no, l2_confidence)
            data["verified"] = l2_confidence < THRESHOLD
            data["user_id"] = user_id
            data["matric_no"] = matric_no
            data["l2_confidence"] = l2_confidence
            
            data["class_id"] = current_class_id
            log(**data)
            return data["verified"], matric_no, l2_confidence
        except psycopg2.Error as e:
            pg_db.rollback()
            raise Exception(f"Database error: {e}")
        except Exception as e:
            print("Something went wrong", e)
            raise User_Not_Registered("User not registered")


def register_new_user(register_new_user_saved_capture: Mat = None, face_flag: bool = False, **biodata) -> None:
    """
    Register a new user in the system.

    Args:
        register_new_user_saved_capture (Mat): The face capture as a NumPy array.
        face_flag (bool): Whether to register the face encoding.
        biodata (dict): User biodata.

    Raises:
        No_Face_Detected: If no face is detected in the image.
        Multiple_Faces_Detected: If multiple faces are detected in the image.
        Invalid_Username: If the username is invalid or empty.
    """
    biodata["department"] = get_department_id(biodata.get("dept"))
    biodata["college"] = get_college_id(biodata.get("college"))

    if face_flag:
        new_user_embed = face_recognition.face_encodings(
            register_new_user_saved_capture, num_jitters=4)

        if new_user_embed == []:
            raise No_Face_Detected("No face detected")

        elif len(new_user_embed) > 1:
            raise Multiple_Faces_Detected("Multiple faces detected")

        biodata["face_embed"] = str(list(new_user_embed[0]))

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
        if biodata.get("name") is None:
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

    pg_db.commit()


def log_class_details(class_details: dict) -> None:
    """
    Log class details to the database.

    Args:
        class_details (dict): Details of the class to log.

    Raises:
        Exception: If a database error occurs.
    """
    class_details["start_time"] = class_details.get(
        "start_time").replace(" ", ":00 ")
    class_details["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        pg_cursor.execute(
            """
            INSERT INTO classes (course_code, venue, start_time, dept, level, auth_mode, duration, date)
            VALUES (%(code)s, %(venue)s, %(start_time)s, %(dept)s, %(level)s, %(auth_mode)s, %(duration)s, %(date)s);
            """,
            class_details,
        )
        pg_db.commit()

    except psycopg2.Error as e:
        pg_db.rollback()
        raise Exception(f"Database error: {e}")
    global current_class_id
    current_class_id = get_current_class_id(class_details.get("code"))
    return current_class_id
