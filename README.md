# Basic Face Recognition System

## Overview
This project implements a Flask-based server with WebSocket support for real-time communication. It provides endpoints for face recognition, user registration, and attendance logging. The system integrates with a face recognition module and a PostgreSQL database to manage user data and attendance records.

## Features
- **WebSocket Integration**: Real-time operations for face enrollment and verification, including support for IoT devices (e.g., ESP32-based attendance trackers).
- **REST API Endpoints**: For face recognition, user registration, and attendance retrieval.
- **Dynamic Web Pages**: Templates for viewing attendance records and scheduled classes.
- **Database Integration**: PostgreSQL for storing user and attendance data, with support for vector similarity search using pgvector.
- **Error Handling**: Handles common issues like no face detected, multiple faces detected, and unregistered users.

## Prerequisites
- Python 3.8 or higher
- PostgreSQL database (version 13+ recommended)
- **pgvector** PostgreSQL extension (for vector similarity search)
- Required Python packages (see `requirements.txt`)
- Basic knowledge of environment variables and database setup

## Installation
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd basic-face-recognition
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the PostgreSQL database:**
   - Create a database named `face_db`.
   - Install the pgvector extension:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
   - Update the `.env` file with your database credentials.

4. **Configure environment variables:**
   - Create a `.env` file in the project root with the following content:
     ```env
     DB_NAME=face_db
     DB_USER=your_username
     DB_PASSWORD=your_password
     DB_HOST=localhost
     DB_PORT=5432
     FLASK_SECRET_KEY=your_secret_key
     ```

5. **Run the server:**
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

### IoT Device Integration
- The server supports WebSocket connections from IoT devices (e.g., ESP32) for real-time attendance logging and face enrollment. Ensure your device firmware is configured to connect to the `/command` WebSocket endpoint and send properly formatted data.

## Project Structure
```
.
├── server.py               # Main server file
├── face_app.py             # Face recognition module
├── templates/              # HTML templates
│   ├── home.html           # Home page
│   ├── index.html          # Attendance tracker
│   ├── student_page.html   # Student attendance records
│   ├── about.html          # About page
├── static/                 # Static files (e.g., images, favicon)
│   └── favicon.ico         # Website icon
├── db/                     # Pickle files for face data
├── log/                    # Logs
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables
```

## Security & Nuances
- Sensitive data (e.g., database credentials, secret keys) is stored in environment variables.
- Use HTTPS for secure communication in production.
- The pgvector extension is required for efficient face embedding similarity search. Make sure your database user has permission to install extensions.
- Images and face embeddings are stored securely; ensure proper file permissions on the server.
- For production deployments, use a WSGI server (e.g., Gunicorn) and a reverse proxy (e.g., Nginx).
- If using IoT devices, ensure they are securely configured and use encrypted connections.

## Troubleshooting
- If you encounter errors related to missing packages, re-run `pip install -r requirements.txt`.
- For database connection issues, verify your `.env` settings and PostgreSQL server status.
- If face recognition is slow, ensure your server has sufficient CPU resources and consider using GPU-accelerated libraries.
- For issues with pgvector, confirm the extension is installed and available in your database.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments
- Flask for the web framework.
- PostgreSQL and pgvector for the database and vector search.
- OpenCV and face_recognition for face detection and recognition.
- Bootstrap for responsive web design.
- ESP32 and related IoT hardware for device integration.
