"""
server.py

This module implements a Flask-based server with WebSocket support for real-time communication. It provides endpoints for face recognition, user registration, and attendance logging.

Features:
- WebSocket integration for real-time operations.
- REST API endpoints for face recognition and user registration.
- Integration with the face_app module for database and face recognition operations.
- Error handling for common issues like no face detected, multiple faces detected, and unregistered users.

Dependencies:
- Flask
- flask_sock
- face_recognition
- psycopg2
- OpenCV (cv2)
- PIL (Pillow)
"""

from flask import Flask, request, jsonify, render_template
from flask_sock import Sock

import base64
import json
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
import logging
import face_app
from datetime import datetime
from simple_websocket import Server
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve sensitive variables from environment
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
SOCK_PING_INTERVAL = int(os.getenv('SOCK_PING_INTERVAL', 15))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True') == 'True'
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))


def base64_to_img(base64_str: str) -> np.matrix:
    """
    Convert a base64-encoded string to an OpenCV-compatible image (NumPy array).

    Args:
        base64_str (str): The base64-encoded string representing the image.

    Returns:
        np.matrix: The decoded image in BGR format.

    Raises:
        ValueError: If the base64 string is invalid or cannot be decoded.
    """
    try:
        img_data = base64.b64decode(base64_str)
        img_pil = Image.open(BytesIO(img_data))
        img_arr = np.array(img_pil)
        img_arr_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
    except Exception as e:
        logging.error(f"Error decoding base64 image: {e}")
        raise ValueError("Invalid base64 image data")
    return img_arr_bgr


current_class_id: int = 0


def enroll_face(ws: Server, **biodata):
    """
    Enroll a user's face by receiving an image via WebSocket.

    Args:
        ws (Server): The WebSocket connection.
        biodata (dict): User biodata including matriculation number and other details.

    Sends:
        JSON response indicating success or error.
    """
    logging.info("Enrolling face...")
    data = ws.receive()


    if isinstance(data, bytes):
        try:
            image = Image.open(BytesIO(data))
            # Convert the image to a NumPy array and then to BGR format for OpenCV
            image_arr = np.array(image)
            image_arr_bgr = cv2.cvtColor(image_arr, cv2.COLOR_RGB2BGR)
            biodata["image_filename"] = f"./static/enrolled/{biodata.get('matric_no', 'face_to_verify')}_{datetime.strftime(datetime.now(), format='%Y%m%d_%H%M%S')}.jpg"
            image.show()
            face_app.register_new_user(
                image_arr_bgr, face_flag=True, **biodata)

        except face_app.No_Face_Detected:
            logging.error("No face detected")
            ws.send({"ERR": "No face detected"})

        except face_app.Multiple_Faces_Detected:
            logging.error("Multiple faces detected")
            ws.send({"ERR": "Multiple faces detected"})

        except Exception as e:
            logging.error(f"Error processing user: {e}")
            ws.send(json.dumps({"status": "ERR",
                                "body": f"{e}"}))

        else:
            logging.info("Face enrollment successful")
            # Save the image as a JPEG file
            Image.open(BytesIO(data)).save(biodata["image_filename"])
            ws.send(json.dumps({"status": "OK",
                                "body": f"{biodata.get('matric_no')} enrolled successfully"}))


def verify_face(ws: Server, **biodata):
    """
    Verify a user's face by matching it against the database.

    Args:
        ws (Server): The WebSocket connection.
        biodata (dict): User biodata including matriculation number and other details.

    Sends:
        JSON response indicating success or error.
    """
    logging.info("Verifying face...")
    data = ws.receive()
    biodata["scan_timestamp"] = biodata.get(
        "scan_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    if not isinstance(data, bytes):
        logging.error("Invalid data type received")
        ws.send(json.dumps({"status": "error",
                            "body": "Invalid data type."}))
        return

    try:
        image = Image.open(BytesIO(data))
        image.show()
        biodata["image_filename"] = f"./static/cache/{biodata.get('matric_no', 'face_to_verify')}_{datetime.strftime(datetime.now(), format='%Y%m%d_%H%M%S')}.jpg"
        image.save(biodata["image_filename"])  # Save the image as a JPEG file
        # Convert the image to a NumPy array and then to BGR format for OpenCV
        image_arr = np.array(image)
        image_arr_bgr = cv2.cvtColor(image_arr, cv2.COLOR_RGB2BGR)
        verified, matric_no, l2_confidence = face_app.login(image_arr_bgr, **biodata)

    except face_app.No_Face_Detected:
        logging.error("No face detected")
        ws.send({"status": "ERR", "body": "No face detected", "verified": False})

    except face_app.Multiple_Faces_Detected:
        logging.error("Multiple faces detected")
        ws.send(
            {"status": "ERR", "body": "Multiple faces detected", "verified": False})

    except face_app.User_Not_Registered:
        logging.error("User not registered")
        ws.send({"status": "ERR", "body": "User not registered", "verified": False})

    except Exception as e:
        logging.error(f"Error processing image: {e}")
        # Placeholder for face verification logic
        ws.send(json.dumps({"status": "ERR",
                            "body": "Invalid image data."}))

    else:
        THRESHOLD = 0.65
        ws.send(json.dumps({"status": "OK" if verified else "ERR",
                            "body": f"{matric_no}",
                            "verified": verified
                            }
                           )
                )
        logging.info(f"Face verification successful for {matric_no}")
    return


def enroll_user(ws: Server, **biodata):
    """
    Enroll a new user without face data.

    Args:
        ws (Server): The WebSocket connection.
        biodata (dict): User biodata including matriculation number and other details.

    Sends:
        JSON response indicating success or error.
    """
    logging.info(f"Enrolling user {biodata.get('matric_no')}...")
    try:
        face_app.register_new_user(face_flag=False, **biodata)
    except face_app.Invalid_Username:
        logging.error("Invalid username")
        ws.send(json.dumps({"status": "ERR",
                            "body": "Invalid username"}))
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        ws.send(json.dumps({"status": "ERR",
                            "body": "Invalid image data."}))
    else:
        ws.send(json.dumps({"status": "OK",
                            "body": f"{biodata.get('matric_no')} enrolled successfully"}))
    return


def start_class(ws: Server, **class_data) -> None:
    """
    Start a new class session and log its details in the database.

    Args:
        ws (Server): The WebSocket connection.
        class_data (dict): Details of the class including course code, venue, and start time.

    Sends:
        JSON response indicating success or error.
    """
    global current_class_id
    try:
        logging.info("Starting class...")
        face_app.log_class_details(class_data)
    except Exception as e:
        ws.send(json.dumps({"status": "ERR",
                            "body": f"Error starting class: {e}"}))
    else:
        current_class_id = face_app.get_current_class_id(
            class_data.get("code"))
        ws.send(json.dumps({"status": "OK",
                            "body": f"Class {current_class_id} started successfully"}))


def log_attendance(ws: Server, **attendance_data):
    """
    Log attendance for a class session.

    Args:
        ws (Server): The WebSocket connection.
        attendance_data (dict): Attendance details including matriculation number and verification status.

    Sends:
        JSON response indicating success or error.
    """
    logging.info("Logging attendance...")
    try:
        face_app.log(**attendance_data)
    except Exception as e:
        logging.error(f"Error logging attendance: {e}")
        ws.send(json.dumps({"status": "ERR",
                            "body": f"Error logging attendance: {e}"}))
    else:
        logging.info("Attendance logged successfully")
        ws.send(json.dumps({"status": "OK",
                            "body": f"Attendance logged successfully"}))


operations = {
    "enroll_face": enroll_face,
    "verify_face": verify_face,
    "enroll_user": enroll_user,
    "start_class": start_class,
    "log_attendance": log_attendance
}

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY
app.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': SOCK_PING_INTERVAL}

socket = Sock(app)


@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Server Error: {error}")
    return "Internal Server Error", 500


@app.errorhandler(404)
def not_found_error(error):
    logging.warning(f"Not Found: {error}")
    return "Not Found", 404

@app.route('/')
def home():
    """
    Render the home page.

    Returns:
        str: Rendered HTML template for the home page.
    """
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
                   SELECT course_code, dept, level, start_time, start_time + interval '1' hour * duration as end_time, duration,  auth_mode, venue, date 
                   FROM classes
                   WHERE date IS NOT NULL 
                   """)
    all_classes = cursor.fetchall()

    cursor.execute("""
                   SELECT course_code, dept, level, start_time, start_time + interval '1' hour * duration as end_time, duration,  auth_mode, venue, date 
                   FROM classes
                   WHERE date IS NOT NULL 
                   AND DATE(date) = CURRENT_DATE
                   """)
    scheduled_classes = cursor.fetchall()

    conn.close()
    return render_template('home.html', scheduled_classes=scheduled_classes, all_classes=all_classes)

@app.route('/attendance', methods=['POST', 'GET'])
def attendance():
    """
    Handle attendance data retrieval based on the selected date and course code.

    This endpoint processes a POST request containing a selected date and course code,
    queries the database for attendance records matching the criteria, and renders
    the results on the `index.html` template.

    Request Parameters:
        - selected_date (str): The date for which attendance data is requested (format: YYYY-MM-DD).
        - course_code (str): The course code for which attendance data is requested.

    Database Query:
        - Retrieves matriculation number, department, level, and log timestamp for
          attendance records matching the selected date and course code.

    Returns:
        - Renders `index.html` with the attendance data if records are found.
        - Renders `index.html` with a message indicating no data if no records are found.

    Raises:
        - psycopg2.DatabaseError: If there is an issue connecting to or querying the database.
    """
    selected_date = request.form.get('selected_date') or request.args.get('selected_date')
    course_code = request.form.get('course_code') or request.args.get('course_code')
    
    if selected_date == "None":
        return render_template('index.html', selected_date=selected_date, course_code=course_code, no_data=True)
    
    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    formatted_date = selected_date_obj.strftime('%Y-%m-%d')

    
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    if course_code == "None":
        cursor.execute("""
                       SELECT a.matric_no, a.department, a.level, cast(log_timestamp::timestamp as time), a.verified, a.image_url 
                       FROM attendance_log a
                       LEFT JOIN classes ON a.class_id = classes.id
                       WHERE DATE(log_timestamp) = %s
                       """, (formatted_date,))
    else:
        cursor.execute("""
                        SELECT a.matric_no, a.department, a.level, cast(log_timestamp::timestamp as time), a.verified, a.image_url 
                        FROM attendance_log a
                        INNER JOIN classes ON a.class_id = classes.id
                        WHERE DATE(log_timestamp) = %s
                            AND course_code = %s
                        """, (formatted_date, course_code))
        
    attendance_data = cursor.fetchall()
    conn.close()

    if not attendance_data:
        return render_template('index.html', selected_date=selected_date, course_code=course_code, no_data=True)

    return render_template('index.html', selected_date=selected_date, course_code=course_code, attendance_data=attendance_data)


@app.route("/recognize", methods=["POST"])
def recognize():
    """
    REST API endpoint to recognize a user's face.

    Expects:
        JSON payload with base64-encoded image data and user details.

    Returns:
        JSON response indicating success or error.
    """
    # Placeholder for face recognition logic
    data = request.get_json()
    image_data = data.pop("image_data")
    try:
        username = face_app.login(base64_to_img(image_data), **data)

    except face_app.No_Face_Detected:
        return jsonify({"message": "No face detected"})

    except face_app.Multiple_Faces_Detected:
        return jsonify({"message": "Multiple faces detected"})

    except face_app.User_Not_Registered:
        return jsonify({"message": "User not registered"})

    else:
        return jsonify({"message": f"{username} recognized successfully"})


@app.route("/register", methods=["POST"])
def register():
    """
    REST API endpoint to register a new user.

    Expects:
        JSON payload with base64-encoded image data and user details.

    Returns:
        JSON response indicating success or error.
    """
    # Placeholder for face recognition logic
    data: dict = request.get_json()
    image_data = data.pop("image_data")

    try:
        face_app.register_new_user(base64_to_img(image_data), **data)
    except face_app.No_Face_Detected:
        return jsonify({"message": "No face detected"})
    else:
        return jsonify(
            {
                "message": f"{data['first_name']+' '+data['last_name']} registered successfully"
            }
        )


@app.route('/student/<student_id>', methods=['GET'])
def student_page(student_id):
    """
    Render the student attendance records page.

    Args:
        student_id (str): The ID of the student whose attendance records are to be displayed.

    Returns:
        str: Rendered HTML template for the student's attendance records.

    Database Query:
        - Retrieves attendance records for the given student ID, including date, course code, course title, status, and time marked.

    Raises:
        - psycopg2.DatabaseError: If there is an issue connecting to or querying the database.
    """
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
                    SELECT * from students_biodata
                    WHERE matric_no = %s
                   """, (student_id,))
    
    student_info = cursor.fetchall()

    cursor.execute("""
                   SELECT c.date, c.course_code, 
                          CASE WHEN a.verified THEN 'Present' ELSE 'Absent' END AS status, 
                          cast(a.log_timestamp::timestamp as time) AS time
                   FROM attendance_log a
                   INNER JOIN classes c ON a.class_id = c.id
                   WHERE a.matric_no = %s
                   ORDER BY c.date DESC
                   """, (student_id,))

    student_records = cursor.fetchall()
    conn.close()

    if not student_records:
        student_name = "Unknown Student"
    else:
        # student_name = student_records[0].get('student_name', 'Student')
        student_name = student_info[0].get('first_name', 'Student') + " " + student_info[0].get('last_name', 'Student')

    return render_template('student_page.html', student_name=student_name, student_records=student_records)


@socket.route('/command')
def command(ws: Server):
    """
    WebSocket endpoint to handle various commands like enrolling faces, verifying faces, and logging attendance.

    Args:
        ws (Server): The WebSocket connection.

    Handles:
        - JSON commands for operations.
        - Binary data for image processing.

    Sends:
        JSON response indicating success or error.
    """
    logging.info("WebSocket connection established.")
    while True:
        data = ws.receive()
        try:
            if isinstance(data, str):
                # Handle JSON data
                json_data: dict = json.loads(data)
                logging.info({"parsed_data": json_data})

                operation: str = json_data.get("cmd")
                json_data.pop("cmd")
                if operation in operations:
                    operations[operation](ws, **json_data)
                else:
                    ws.send(json.dumps({"status": "ERR",
                                        "body": "Invalid command."}))
    
            else:
                ws.send(json.dumps({"status": "ERR",
                                    "body": "Unsupported data type."}))
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            ws.send(json.dumps({"status": "ERR",
                                "body": "Invalid JSON data."}))
        except Exception as e:
            logging.error(f"Error processing data: {e}")
            ws.send(json.dumps({"status": "ERR",
                                "body": str(e)}))


if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT)
