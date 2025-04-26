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

from flask import Flask, request, jsonify
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

current_class_id:int = 0

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
            biodata["image_filename"] = f"./static/enrolled/{biodata.get('matric_no', 'face_to_verify')}_{datetime.now()}.jpg"
            image.show()
            face_app.register_new_user(image_arr_bgr, face_flag=True, **biodata)

        except face_app.No_Face_Detected:
            logging.error("No face detected")
            ws.send({"ERR": "No face detected"})

        except face_app.Multiple_Faces_Detected:
            logging.error("Multiple faces detected")
            ws.send({"ERR": "Multiple faces detected"})

        except Exception as e:
            logging.error(f"Error processing user: {e}")
            ws.send(json.dumps({"status":"ERR",
                                "body": f"{e}"}))

        else:
            logging.info("Face enrollment successful")
            Image.open(BytesIO(data)).save(biodata["image_filename"])  # Save the image as a JPEG file
            ws.send(json.dumps(
                {"status":"OK", 
                 "body": f"{biodata.get("matric_no")} enrolled successfully"}))

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
    if not isinstance(data, bytes):
        logging.error("Invalid data type received")
        ws.send(json.dumps({"status":"error", 
                            "body": "Invalid data type."}))
        return

    try:
        image = Image.open(BytesIO(data))
        image.show()
        biodata["image_filename"] = f"./static/cache/{biodata.get('matric_no', 'face_to_verify')}_{datetime.strftime(datetime.now(), format="%Y%m%d_%H%M%S")}.jpg"
        image.save(biodata["image_filename"])  # Save the image as a JPEG file
        # Convert the image to a NumPy array and then to BGR format for OpenCV
        image_arr = np.array(image)
        image_arr_bgr = cv2.cvtColor(image_arr, cv2.COLOR_RGB2BGR)
        # TODO: Use matric number
        matric_no = face_app.login(image_arr_bgr, **biodata)

    except face_app.No_Face_Detected:
        logging.error("No face detected")
        ws.send({"ERR": "No face detected"})

    except face_app.Multiple_Faces_Detected:
        logging.error("Multiple faces detected")
        ws.send({"ERR": "Multiple faces detected"})

    except face_app.User_Not_Registered:
        logging.error("User not registered")
        ws.send({"ERR": "User not registered"})

    except Exception as e:
        logging.error(f"Error processing image: {e}")
        # Placeholder for face verification logic
        ws.send(json.dumps({"status":"ERR", 
                            "body": "Invalid image data."}))

    else:
        ws.send(json.dumps({"status":"OK", 
                            "body": f"{matric_no} recognized successfully"}))
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
    logging.info(f"Enrolling user {biodata.get("matric_no")}...")
    try:
        face_app.register_new_user(face_flag=False, **biodata)
    except face_app.Invalid_Username:
        logging.error("Invalid username")
        ws.send(json.dumps({"status":"ERR", 
                            "body": "Invalid username"}))
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        ws.send(json.dumps({"status":"ERR", 
                            "body": "Invalid image data."}))
    else:
        ws.send(json.dumps({"status":"OK", 
                            "body": f"{biodata.get("matric_no")} enrolled successfully"}))
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
        ws.send(json.dumps({"status":"ERR", 
                            "body": f"Error starting class: {e}"}))
    else:
        current_class_id = face_app.get_current_class_id(class_data.get("code"))
        ws.send(json.dumps({"status":"OK", 
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
        ws.send(json.dumps({"status":"ERR", 
                            "body": f"Error logging attendance: {e}"}))
    else:
        logging.info("Attendance logged successfully")
        ws.send(json.dumps({"status":"OK", 
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
app.config['SECRET_KEY'] = 'secret!'
app.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': 15}
socket = Sock(app)


@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Server Error: {error}")
    return "Internal Server Error", 500


@app.errorhandler(404)
def not_found_error(error):
    logging.warning(f"Not Found: {error}")
    return "Not Found", 404


@app.route("/")
def home():
    return "Welcome to the Basic Face Recognition Server!"


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
                "message": f"{data['first_name']+" "+data['last_name']} registered successfully"
            }
        )


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
                    ws.send(json.dumps({"status":"ERR", 
                                        "body": "Invalid command."}))
            elif isinstance(data, bytes):
                # Handle binary data (e.g., image)
                try:
                    image = Image.open(BytesIO(data))
                    # image.save("received_image.jpg")  # Save the image as a JPEG file
                    image.show()
                    ws.send(json.dumps(
                        {"status":"OK", 
                         "body": "Image received and saved."}))
                except Exception as e:
                    logging.error(f"Error processing image: {e}")
                    ws.send(json.dumps({"status":"ERR", 
                                        "body": "Invalid image data."}))
            else:
                ws.send(json.dumps({"status":"ERR", 
                                    "body": "Unsupported data type."}))
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            ws.send(json.dumps({"status":"ERR", 
                                "body": "Invalid JSON data."}))
        except Exception as e:
            logging.error(f"Error processing data: {e}")
            ws.send(json.dumps({"status":"ERR", 
                                "body": str(e)}))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
