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
from simple_websocket import Server


def base64_to_img(base64_str: str) -> np.matrix:
    try:
        img_data = base64.b64decode(base64_str)
        img_pil = Image.open(BytesIO(img_data))
        img_arr = np.array(img_pil)
        img_arr_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
    except Exception as e:
        logging.error(f"Error decoding base64 image: {e}")
        raise ValueError("Invalid base64 image data")
    return img_arr_bgr

def bytes_to_img(data: bytes) -> np.matrix:
    try:
        image = Image.open(BytesIO(data))
        image.show()
        image.save("received_image.jpg")  # Save the image as a JPEG file
        # Convert the image to a NumPy array and then to BGR format for OpenCV
        image_arr = np.array(image)
        image_arr_bgr = cv2.cvtColor(image_arr, cv2.COLOR_RGB2BGR)
    except Exception as e:
        logging.error(f"Error converting bytes to image: {e}")
        raise ValueError("Invalid image data")
    return image_arr_bgr

def enroll_face(ws:Server, **biodata):
    logging.info("Enrolling face...")
    data = ws.receive()
    if isinstance(data, bytes):
        try:
            image = Image.open(BytesIO(data))
            image.save("face_to_enroll.jpg")  # Save the image as a JPEG file
            image.show()
            ws.send(json.dumps({"message": "Image received and saved."}))
        except Exception as e:
            logging.error(f"Error processing image: {e}")
            ws.send(json.dumps({"error": "Invalid image data."}))

def verify_face(ws:Server, **biodata):
    logging.info("Verifying face...")
    data = ws.receive()
    if not isinstance(data, bytes):
        logging.error("Invalid data type received")
        ws.send(json.dumps({"error": "Invalid data type."}))
        return
    
    try:
        img_arr = bytes_to_img(data)
        username = face_app.login(img_arr, **biodata)

    except face_app.No_Face_Detected:
        logging.error("No face detected")
        ws.send({"message": "No face detected"})

    except face_app.Multiple_Faces_Detected:
        logging.error("Multiple faces detected")
        ws.send({"message": "Multiple faces detected"})

    except face_app.User_Not_Registered:
        logging.error("User not registered")
        ws.send({"message": "User not registered"})

    except Exception as e:
        logging.error(f"Error processing image: {e}")
        ws.send(json.dumps({"error": "Invalid image data."}))  # Placeholder for face verification logic 
    
    else:
        ws.send(json.dumps({"message": f"{username} recognized successfully"}))
    return

def enroll_user(ws:Server, **biodata):
    logging.info("Enrolling user...")
    pass  # Placeholder for user enrollment logic

def start_class(ws:Server, **class_data):
    logging.info("Starting class...")
    pass  # Placeholder for starting a class logic

def log_attendance(ws:Server, **attendance_data):
    logging.info("Logging attendance...")
    pass  # Placeholder for logging attendance logic

operations = {
    "enroll_face":enroll_face,
    "verify_face":verify_face,
    "enroll_user":enroll_user,
    "start_class":start_class,
    "log_attendance":log_attendance
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
    # Placeholder for face recognition logic
    data:dict = request.get_json()
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
def command(ws:Server):
    logging.info("WebSocket connection established.")
    while True:
        data = ws.receive()
        try:
            if isinstance(data, str):
                # Handle JSON data
                json_data:dict = json.loads(data)
                logging.info({"parsed_data":json_data})

                operation:str = json_data.get("cmd")
                json_data.pop("cmd")
                if operation in operations:
                    operations[operation](ws, **json_data)
                else:
                    ws.send(json.dumps({"error": "Invalid command."}))
            elif isinstance(data, bytes):
                # Handle binary data (e.g., image)
                try:
                    image = Image.open(BytesIO(data))
                    # image.save("received_image.jpg")  # Save the image as a JPEG file
                    image.show()
                    ws.send(json.dumps({"message": "Image received and saved."}))
                except Exception as e:
                    logging.error(f"Error processing image: {e}")
                    ws.send(json.dumps({"error": "Invalid image data."}))
            else:
                ws.send(json.dumps({"error": "Unsupported data type."}))
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            ws.send(json.dumps({"error": "Invalid JSON data."}))
        except Exception as e:
            logging.error(f"Error processing data: {e}")
            ws.send(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
