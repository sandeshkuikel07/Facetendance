
```markdown
# FaceAttendance System

A face recognition-based attendance management system using Firebase as the backend and OpenCV for camera integration. This system recognizes student faces and marks their attendance in real-time, displaying relevant information such as name, roll number, total attendance, and time of last attendance.

## Features
- Real-time face recognition using OpenCV and face_recognition libraries
- Firebase integration for storing student data and attendance records
- User-friendly UI built with Tkinter for displaying attendance status and student information
- Attendance marking with timestamp and automatic update of student records
- Error handling and system status updates during face recognition

## Requirements
- Python 3.x
- Libraries:
  - `firebase-admin` (for Firebase integration)
  - `opencv-python` (for camera and image processing)
  - `face_recognition` (for face detection and recognition)
  - `tkinter` (for GUI)
  - `PIL` (for image handling)
  - `numpy` (for array manipulation)

Install the required libraries using `pip`:

```bash
pip install firebase-admin opencv-python face_recognition tk pillow numpy
```

## Setup

1. Clone this repository:

   ```bash
   git clone https://github.com/sandeshkuikel07/FaceAttendance.git
   cd FaceAttendance
   ```

2. Download your Firebase service account key JSON file from the Firebase console:
   - Go to [Firebase Console](https://console.firebase.google.com/).
   - Select your project.
   - Navigate to **Project Settings** > **Service Accounts**.
   - Click **Generate New Private Key**, and the JSON file will be downloaded.

3. Rename the downloaded file to `serviceAccountKey.json` and place it in the project directory.

4. Modify the Firebase configuration in the `main.py` file:
   - Open `main.py` in a text editor.
   - Replace the `databaseURL` and `storageBucket` values in the following code snippet with your Firebase project details.

   ```python
   firebase_admin.initialize_app(cred, {
       'databaseURL': 'https://your-database-url.firebaseio.com/',
       'storageBucket': 'your-app-id.appspot.com'
   })
   ```

   - Replace `'https://your-database-url.firebaseio.com/'` with your Firebase Realtime Database URL.
   - Replace `'your-app-id.appspot.com'` with your Firebase Storage bucket.

5. Run the application:

   ```bash
   python main.py
   ```

## How It Works

1. The system initializes and connects to Firebase.
2. It loads face encodings from the `EncodeFile.p` file, which contains pre-encoded student faces and their IDs.
3. The camera captures live video, processes the frames, and performs face recognition.
4. When a student's face is recognized, their attendance is marked in Firebase, and their data (name, roll number, total attendance, and time) is displayed in the GUI.
5. If a student is recognized again within a short time frame, their attendance is marked as "Already Marked."

## Firebase Structure

The Firebase Realtime Database stores student data in the following format:

```
Students
  ├── student_id
       ├── name: "Student Name"
       ├── starting_year: "YYYY-MM"
       ├── total_attendance: number
       ├── year: number
```

## Screenshots

Include any relevant screenshots of the system in action here.

## Acknowledgments

- OpenCV and face_recognition for face recognition processing
- Firebase for real-time data management and storage
- Tkinter for GUI development
```

This README now includes everything needed to get the project set up, including Firebase configuration, service account key, and automatic modifications to the `main.py` file. You can simply copy and paste it into your GitHub repository without having to do any manual changes.
