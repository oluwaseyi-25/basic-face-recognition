# Basic Face Recognition System

## Overview
This project implements a Flask-based server with WebSocket support for real-time communication. It provides endpoints for face recognition, user registration, and attendance logging. The system integrates with a face recognition module and a PostgreSQL database to manage user data and attendance records.

## Features
- **WebSocket Integration**: Real-time operations for face enrollment and verification.
- **REST API Endpoints**: For face recognition, user registration, and attendance retrieval.
- **Dynamic Web Pages**: Templates for viewing attendance records and scheduled classes.
- **Database Integration**: PostgreSQL for storing user and attendance data.
- **Error Handling**: Handles common issues like no face detected, multiple faces detected, and unregistered users.

## Prerequisites
- Python 3.8 or higher
- PostgreSQL database
- Required Python packages (see `requirements.txt`)

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd basic-face-recognition
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the PostgreSQL database:
   - Create a database named `face_db`.
   - Update the `.env` file with your database credentials.

4. Configure environment variables:
   - Create a `.env` file in the project root with the following content:
     ```env
     DB_NAME=face_db
     DB_USER=your_username
     DB_PASSWORD=your_password
     DB_HOST=localhost
     DB_PORT=5432
     FLASK_SECRET_KEY=your_secret_key
     ```

5. Run the server:
   ```bash
   python server.py
   ```

## Usage
### Web Pages
- **Home Page**: View scheduled and all classes.
- **Attendance Tracker**: View attendance records for a specific date and course.
- **Student Page**: View attendance records for a specific student.

### REST API Endpoints
- **POST `/recognize`**: Recognize a user's face.
- **POST `/register`**: Register a new user.

### WebSocket Commands
- **`enroll_face`**: Enroll a user's face.
- **`verify_face`**: Verify a user's face.
- **`log_attendance`**: Log attendance for a class session.

## Project Structure
```
.
├── server.py               # Main server file
├── face_app.py             # Face recognition module
├── templates/              # HTML templates
│   ├── home.html           # Home page
│   ├── index.html          # Attendance tracker
│   ├── student_page.html   # Student attendance records
├── static/                 # Static files (e.g., images)
├── db/                     # Pickle files for face data
├── log/                    # Logs
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables
```

## Security
- Sensitive data (e.g., database credentials, secret keys) is stored in environment variables.
- Use HTTPS for secure communication in production.

## Deployment
1. Use a production-ready server like Gunicorn or uWSGI.
2. Set up a reverse proxy with Nginx or Apache.
3. Use a task queue (e.g., Celery) for heavy operations like face recognition.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments
- Flask for the web framework.
- PostgreSQL for the database.
- OpenCV and face_recognition for face detection and recognition.
- Bootstrap for responsive web design.
