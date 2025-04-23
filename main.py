import os
import pickle
import numpy as np
import cv2
import face_recognition
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import sys

class FaceAttendanceSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Facetendance")
        self.root.geometry("1200x700")
        
        # Initialize Firebase with error handling
        try:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {
                'databaseURL': "https://facetendance-default-rtdb.firebaseio.com/",
                'storageBucket': "gs://facetendance.appspot.com"
            })
            self.bucket = storage.bucket()
            print("Firebase initialized successfully")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            sys.exit(1)
            
        # Load the encoding file with error handling
        try:
            print("Loading Encode File ...")
            encode_file_path = 'EncodeFile.p'
            if not os.path.exists(encode_file_path):
                raise Exception(f"Encoding file not found: {encode_file_path}")
                
            file = open(encode_file_path, 'rb')
            encodeListKnownWithIds = pickle.load(file)
            file.close()
            self.encodeListKnown, self.studentIds = encodeListKnownWithIds
            if not self.encodeListKnown or not self.studentIds:
                raise Exception("Encoding file exists but contains no data")
            print("Encode File Loaded")
        except Exception as e:
            print(f"Error loading encode file: {e}")
            sys.exit(1)
            
        # Set up camera with error handling
        self.camera_index = 1  # Try 0 instead of 1 if camera is not found
        max_camera_attempts = 3
        camera_attempt = 0

        while camera_attempt < max_camera_attempts:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                self.cap.set(3, 640)
                self.cap.set(4, 480)
                print(f"Camera initialized successfully with index {self.camera_index}")
                break
            else:
                camera_attempt += 1
                self.camera_index = 0 if self.camera_index == 1 else 1  # Toggle between 0 and 1
                print(f"Failed to open camera with index {self.camera_index}, trying alternative...")

        if not self.cap.isOpened():
            print("Error: Could not open camera after multiple attempts")
            sys.exit(1)
            
        # Initialize variables
        self.mode_type = 0
        self.counter = 0
        self.id = -1
        self.img_student = None
        self.student_info = None
        self.recognition_state = "Scanning"  # Initial state
        
        # Create UI elements
        self.create_ui()
        
        # Start camera thread
        self.running = True
        self.thread = threading.Thread(target=self.update_camera)
        self.thread.daemon = True
        self.thread.start()
        
    def create_ui(self):
        """Create the main user interface elements with green background design"""
        # Set main background to green
        self.root.configure(bg="#8AEA92")  # Light green background
        
        # Title
        title_label = tk.Label(self.root, text="Facetendance", 
                            font=("Arial", 36, "bold"), bg="#8AEA92", fg="#3A1492")  # Purple text
        title_label.place(x=50, y=40)
        
        # Left frame for camera feed (white rounded rectangle)
        self.camera_frame = tk.Frame(self.root, bg="#FFFFFF", bd=0)
        self.camera_frame.place(x=50, y=120, width=500, height=500)
        
        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        # Right frame for status and student info (blue rounded rectangle)
        self.info_frame = tk.Frame(self.root, bg="#4258B5", bd=0)  # Dark blue
        self.info_frame.place(x=650, y=120, width=500, height=500)
        
        # Status display in info frame
        self.status_frame = tk.Frame(self.info_frame, bg="#4258B5")
        self.status_frame.place(x=0, y=0, width=500, height=500)
        
        # Scanning label (initially visible)
        self.scanning_label = tk.Label(self.status_frame, text="Scanning", 
                                    font=("Arial", 32, "bold"), bg="#4258B5", fg="white")
        self.scanning_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Student info frame (initially hidden)
        self.student_info_frame = tk.Frame(self.info_frame, bg="#4258B5")
        
        # Student details labels
        self.name_label = tk.Label(self.student_info_frame, text="Name:", 
                                font=("Arial", 18), bg="#4258B5", fg="white")
        self.name_label.place(x=40, y=100)
        
        self.name_value = tk.Label(self.student_info_frame, text="", 
                                font=("Arial", 18, "bold"), bg="#4258B5", fg="white")
        self.name_value.place(x=200, y=100)
        
        self.id_label = tk.Label(self.student_info_frame, text="Roll Number:", 
                              font=("Arial", 18), bg="#4258B5", fg="white")
        self.id_label.place(x=40, y=150)
        
        self.id_value = tk.Label(self.student_info_frame, text="", 
                              font=("Arial", 18, "bold"), bg="#4258B5", fg="white")
        self.id_value.place(x=200, y=150)
        
        self.time_label = tk.Label(self.student_info_frame, text="Time:", 
                                font=("Arial", 18), bg="#4258B5", fg="white")
        self.time_label.place(x=40, y=200)
        
        self.time_value = tk.Label(self.student_info_frame, text="", 
                                font=("Arial", 18, "bold"), bg="#4258B5", fg="white")
        self.time_value.place(x=200, y=200)
        
        self.attendance_label = tk.Label(self.student_info_frame, text="Total Attendance:", 
                                      font=("Arial", 18), bg="#4258B5", fg="white")
        self.attendance_label.place(x=40, y=250)
        
        self.attendance_value = tk.Label(self.student_info_frame, text="", 
                                      font=("Arial", 18, "bold"), bg="#4258B5", fg="white")
        self.attendance_value.place(x=200, y=250)
        
        # Status indicator
        self.status_indicator = tk.Label(self.student_info_frame, text="MARKED", 
                                      font=("Arial", 24, "bold"), bg="#4258B5", fg="#FFFFFF")
        self.status_indicator.place(x=180, y=350)
        
    def update_camera(self):
        """Update camera feed and process face recognition in a separate thread"""
        while self.running:
            success, img = self.cap.read()
            
            if not success:
                print("Warning: Unable to read frame from camera, retrying...")
                self.cap.release()
                self.cap = cv2.VideoCapture(self.camera_index)
                if not self.cap.isOpened():
                    print("Error: Camera disconnected and can't be reinitialized")
                    self.running = False
                    break
                continue
                
            # Resize image to match the target region dimensions
            try:
                img = cv2.resize(img, (500, 500))
            except Exception as e:
                print(f"Error resizing camera frame: {e}")
                continue
                
            # Process image for face recognition
            try:
                imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
                imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
                face_cur_frame = face_recognition.face_locations(imgS)
                encode_cur_frame = face_recognition.face_encodings(imgS, face_cur_frame)
            except Exception as e:
                print(f"Error processing face recognition: {e}")
                face_cur_frame = []
                encode_cur_frame = []
                
            # Draw faces on image
            img_display = img.copy()
            
            if face_cur_frame:
                for encodeFace, faceLoc in zip(encode_cur_frame, face_cur_frame):
                    try:
                        matches = face_recognition.compare_faces(self.encodeListKnown, encodeFace)
                        faceDis = face_recognition.face_distance(self.encodeListKnown, encodeFace)
                        
                        if len(faceDis) > 0:  # Check if any faces were compared
                            matchIndex = np.argmin(faceDis)
                            
                            if matchIndex < len(matches) and matches[matchIndex]:
                                y1, x2, y2, x1 = faceLoc
                                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                                
                                # Draw rectangle around face
                                cv2.rectangle(img_display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                
                                # Draw corner rectangles
                                thickness = 2
                                corner_len = 20
                                # Top left
                                cv2.line(img_display, (x1, y1), (x1 + corner_len, y1), (0, 255, 0), thickness)
                                cv2.line(img_display, (x1, y1), (x1, y1 + corner_len), (0, 255, 0), thickness)
                                # Top right
                                cv2.line(img_display, (x2, y1), (x2 - corner_len, y1), (0, 255, 0), thickness)
                                cv2.line(img_display, (x2, y1), (x2, y1 + corner_len), (0, 255, 0), thickness)
                                # Bottom left
                                cv2.line(img_display, (x1, y2), (x1 + corner_len, y2), (0, 255, 0), thickness)
                                cv2.line(img_display, (x1, y2), (x1, y2 - corner_len), (0, 255, 0), thickness)
                                # Bottom right
                                cv2.line(img_display, (x2, y2), (x2 - corner_len, y2), (0, 255, 0), thickness)
                                cv2.line(img_display, (x2, y2), (x2, y2 - corner_len), (0, 255, 0), thickness)
                                
                                if matchIndex < len(self.studentIds):
                                    self.id = self.studentIds[matchIndex]
                                    
                                    if self.counter == 0:
                                        # Show loading state
                                        cv2.putText(img_display, "Loading", (50, 50), 
                                                  cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)
                                        self.counter = 1
                                        self.mode_type = 1
                                        # Set recognition state
                                        self.recognition_state = "Processing"
                                        self.root.after(0, self.update_status_display)
                        
                    except Exception as e:
                        print(f"Error in face recognition matching: {e}")
                
                # Process face recognition results
                if self.counter != 0:
                    self.process_recognition()
            else:
                # If no faces detected and not in middle of processing
                if self.mode_type != 1 and self.mode_type != 2:
                    self.mode_type = 0
                    self.counter = 0
                    self.recognition_state = "Scanning"
                    self.root.after(0, self.update_status_display)
            
            # Convert to format suitable for tkinter
            img_display = cv2.cvtColor(img_display, cv2.COLOR_BGR2RGB)
            img_tk = ImageTk.PhotoImage(image=Image.fromarray(img_display))
            
            # Update the UI with the camera feed
            self.camera_label.config(image=img_tk)
            self.camera_label.image = img_tk  # Keep a reference
            
            # Process tkinter events to prevent freezing
            self.root.update_idletasks()
            self.root.after(10)  # Small delay to reduce CPU usage
            
    def process_recognition(self):
        """Process the recognized face and update UI accordingly"""
        if self.counter == 1:
            # Get the Student Data with error handling
            self.student_info = self.get_student_info(self.id)
            if self.student_info is None:
                # Handle missing student info
                print(f"No data for student ID {self.id}, resetting")
                self.counter = 0
                self.mode_type = 0
                self.recognition_state = "Scanning"
                self.root.after(0, self.update_status_display)
                return

            # Update attendance with error handling
            try:
                if 'last_attendance_time' not in self.student_info:
                    print(f"Warning: 'last_attendance_time' field missing for student ID {self.id}")
                    self.student_info['last_attendance_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                current_time = datetime.now()
                current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
                
                datetimeObject = datetime.strptime(self.student_info['last_attendance_time'], 
                                                 "%Y-%m-%d %H:%M:%S") if 'last_attendance_time' in self.student_info else None
                
                if datetimeObject is None or (current_time - datetimeObject).total_seconds() > 30:
                    if 'total_attendance' not in self.student_info:
                        print(f"Warning: 'total_attendance' field missing for student ID {self.id}")
                        self.student_info['total_attendance'] = 0
                        
                    update_success = self.update_attendance(self.id, self.student_info)
                    if not update_success:
                        # Continue showing the student info even if update fails
                        print("Continuing despite attendance update failure")
                    
                    # Show MARKED status
                    self.recognition_state = "Marked"
                    self.student_info['last_attendance_time'] = current_time_str
                else:
                    # Show ALREADY MARKED status
                    self.recognition_state = "Already Marked"
            except Exception as e:
                print(f"Error processing attendance time: {e}")
                # Reset to initial state when error occurs
                self.counter = 0
                self.mode_type = 0
                self.recognition_state = "Scanning"
                self.root.after(0, self.update_status_display)
                return
                
            # Update UI to show student info
            self.root.after(0, self.update_student_info)
            self.root.after(0, self.update_status_display)

        self.counter += 1

        # Reset after 5 seconds (150 frames at 30fps)
        if self.counter >= 150:
            self.counter = 0
            self.mode_type = 0
            self.student_info = None
            self.recognition_state = "Scanning"
            self.root.after(0, self.update_status_display)
    
    def update_status_display(self):
        """Update the display based on recognition state"""
        if self.recognition_state == "Scanning":
            # Show scanning state
            self.student_info_frame.place_forget()
            self.scanning_label.config(text="Scanning")
            self.scanning_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self.status_frame.place(x=0, y=0, width=500, height=500)
            
        elif self.recognition_state == "Processing":
            # Show processing state
            self.student_info_frame.place_forget()
            self.scanning_label.config(text="Processing")
            self.scanning_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self.status_frame.place(x=0, y=0, width=500, height=500)
            
        elif self.recognition_state == "Marked" or self.recognition_state == "Already Marked":
            # Show student info with status
            self.status_frame.place_forget()
            self.student_info_frame.place(x=0, y=0, width=500, height=500)
            
            status_text = "MARKED" if self.recognition_state == "Marked" else "ALREADY MARKED"
            status_color = "#4CAF50" if self.recognition_state == "Marked" else "#F44336"  # Green or Red
            
            self.status_indicator.config(text=status_text, fg=status_color)
    
    def update_student_info(self):
        """Update the student information display"""
        if self.student_info is not None:
            # Update student details safely
            name = self.student_info.get('name', 'Unknown')
            attendance = self.student_info.get('total_attendance', 'N/A')
            time_str = self.student_info.get('last_attendance_time', datetime.now().strftime("%H:%M:%S"))
            
            # For time, show only the time portion (not date)
            try:
                dt_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                time_display = dt_obj.strftime("%H:%M:%S")
            except:
                time_display = time_str
                
            self.name_value.config(text=str(name))
            self.id_value.config(text=str(self.id))
            self.time_value.config(text=time_display)
            self.attendance_value.config(text=str(attendance))
    
    def get_student_info(self, student_id):
        """Safely get student info from database"""
        try:
            student_info = db.reference(f'Students/{student_id}').get()
            if student_info is None:
                print(f"Warning: No data found for student ID: {student_id}")
                return None
            return student_info
        except Exception as e:
            print(f"Error retrieving student info from database: {e}")
            return None
    
    def update_attendance(self, student_id, student_info):
        """Safely update attendance in database"""
        try:
            ref = db.reference(f'Students/{student_id}')
            student_info['total_attendance'] += 1
            ref.child('total_attendance').set(student_info['total_attendance'])
            ref.child('last_attendance_time').set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            print(f"Successfully updated attendance for student ID: {student_id}")
            return True
        except Exception as e:
            print(f"Error updating attendance in database: {e}")
            return False
    
    def on_closing(self):
        """Clean up resources when closing the app"""
        self.running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        self.root.destroy()
        print("Application closed successfully")

def main():
    root = tk.Tk()
    app = FaceAttendanceSystem(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()