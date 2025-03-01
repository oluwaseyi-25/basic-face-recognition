from flask import Flask, request, jsonify
import base64
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
import face_app


def img_to_base64(img_path: str) -> str:
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


def base64_to_img(base64_str: str) -> np.matrix:
    img_data = base64.b64decode(base64_str)
    img_pil = Image.open(BytesIO(img_data))
    img_arr = np.array(img_pil)
    img_arr_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
    return img_arr_bgr


app = Flask(__name__)


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
    data = request.get_json()
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


if __name__ == "__main__":
    app.run(debug=True)
