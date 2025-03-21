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
import pygame
from pygame.locals import *
import sys

# Initialize Pygame
pygame.init()

# Initialize Firebase with error handling
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': "https://facetendance-default-rtdb.firebaseio.com/",
        'storageBucket': "gs://facetendance.appspot.com"
    })
    bucket = storage.bucket()
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    sys.exit(1)

# Set up camera with error handling
camera_index = 1  # Try 0 instead of 1 if camera is not found
max_camera_attempts = 3
camera_attempt = 0

while camera_attempt < max_camera_attempts:
    cap = cv2.VideoCapture(camera_index)
    if cap.isOpened():
        cap.set(3, 640)
        cap.set(4, 480)
        print(f"Camera initialized successfully with index {camera_index}")
        break
    else:
        camera_attempt += 1
        camera_index = 0 if camera_index == 1 else 1  # Toggle between 0 and 1
        print(f"Failed to open camera with index {camera_index}, trying alternative...")

if not cap.isOpened():
    print("Error: Could not open camera after multiple attempts")
    sys.exit(1)

# Load background image with error handling
try:
    imgBackground_cv = cv2.imread('Resources/background.png')
    if imgBackground_cv is None:
        raise Exception("Background image not found")
    
    # Convert OpenCV image to Pygame surface
    imgBackground_cv = cv2.cvtColor(imgBackground_cv, cv2.COLOR_BGR2RGB)
    imgBackground = pygame.surfarray.make_surface(imgBackground_cv.swapaxes(0, 1))
    
    # Get background dimensions for creating the display
    bg_height, bg_width = imgBackground_cv.shape[:2]
    window_size = (bg_width, bg_height)
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Face Attendance")
except Exception as e:
    print(f"Error loading background image: {e}")
    sys.exit(1)

# Load mode images with error handling
try:
    folderModePath = 'Resources/Modes'
    if not os.path.exists(folderModePath):
        raise Exception(f"Mode images folder not found: {folderModePath}")
        
    modePathList = os.listdir(folderModePath)
    if not modePathList:
        raise Exception("No mode images found in folder")
        
    imgModeList_cv = []
    imgModeList = []
    for path in modePathList:
        img_path = os.path.join(folderModePath, path)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Warning: Could not load mode image: {img_path}")
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        imgModeList_cv.append(img)
        imgModeList.append(pygame.surfarray.make_surface(img.swapaxes(0, 1)))
    
    if not imgModeList:
        raise Exception("Failed to load any mode images")
except Exception as e:
    print(f"Error loading mode images: {e}")
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
    encodeListKnown, studentIds = encodeListKnownWithIds
    if not encodeListKnown or not studentIds:
        raise Exception("Encoding file exists but contains no data")
    print("Encode File Loaded")
except Exception as e:
    print(f"Error loading encoding file: {e}")
    sys.exit(1)

# Create fonts with error handling
try:
    pygame.font.init()
    font = pygame.font.SysFont('Arial', 20)
    font_large = pygame.font.SysFont('Arial', 30)
    font_small = pygame.font.SysFont('Arial', 15)
except Exception as e:
    print(f"Error initializing fonts: {e}")
    sys.exit(1)

# Function to display text on Pygame surface
def put_text(surface, text, position, font, color=(255, 255, 255)):
    if text is None:
        text = "N/A"
    if not isinstance(text, str):
        text = str(text)
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, position)

# Function to create corner rectangle (similar to cvzone.cornerRect)
def corner_rect(surface, rect, color=(0, 255, 0), thickness=2, corner_radius=20):
    x, y, w, h = rect
    pygame.draw.rect(surface, color, (x, y, w, h), thickness)
    # Draw corners
    pygame.draw.line(surface, color, (x, y), (x + corner_radius, y), thickness)
    pygame.draw.line(surface, color, (x, y), (x, y + corner_radius), thickness)
    pygame.draw.line(surface, color, (x + w, y), (x + w - corner_radius, y), thickness)
    pygame.draw.line(surface, color, (x + w, y), (x + w, y + corner_radius), thickness)
    pygame.draw.line(surface, color, (x, y + h), (x, y + h - corner_radius), thickness)
    pygame.draw.line(surface, color, (x, y + h), (x + corner_radius, y + h), thickness)
    pygame.draw.line(surface, color, (x + w, y + h), (x + w - corner_radius, y + h), thickness)
    pygame.draw.line(surface, color, (x + w, y + h), (x + w, y + h - corner_radius), thickness)
    return surface

# Create a default student image (blank with text)
def create_default_student_image(size=(216, 216)):
    img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 200  # Light gray background
    img = cv2.putText(img, "No Image", (30, 108), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
    return img

# Function to safely get student info from database
def get_student_info(student_id):
    try:
        student_info = db.reference(f'Students/{student_id}').get()
        if student_info is None:
            print(f"Warning: No data found for student ID: {student_id}")
            return None
        return student_info
    except Exception as e:
        print(f"Error retrieving student info from database: {e}")
        return None

# Function to safely update attendance in database
def update_attendance(student_id, student_info):
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

# Function to safely get student image from storage
def get_student_image(student_id, size=(216, 216)):
    try:
        blob = bucket.get_blob(f'Images/{student_id}.png')
        if blob is None:
            print(f"Warning: No image found for student ID: {student_id}")
            return create_default_student_image(size)
            
        array = np.frombuffer(blob.download_as_string(), np.uint8)
        img = cv2.imdecode(array, cv2.COLOR_BGRA2BGR)
        if img is None:
            print(f"Warning: Failed to decode image for student ID: {student_id}")
            return create_default_student_image(size)
            
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, size)
        return img
    except Exception as e:
        print(f"Error getting student image from storage: {e}")
        return create_default_student_image(size)

modeType = 0
counter = 0
id = -1
imgStudent_cv = None
imgStudent = None

clock = pygame.time.Clock()
running = True

while running:
    # Check for Pygame events
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                running = False

    # Capture camera frame with error handling
    success, img = cap.read()

    if not success:
        print("Warning: Unable to read frame from camera, retrying...")
        # Try to reinitialize camera if needed
        cap.release()
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("Error: Camera disconnected and can't be reinitialized")
            running = False
            continue

    # Resize image to match the target region dimensions (640x480)
    try:
        img = cv2.resize(img, (640, 480))
    except Exception as e:
        print(f"Error resizing camera frame: {e}")
        continue

    # Process image for face recognition
    try:
        imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        faceCurFrame = face_recognition.face_locations(imgS)
        encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)
    except Exception as e:
        print(f"Error processing face recognition: {e}")
        faceCurFrame = []
        encodeCurFrame = []

    # Convert camera image to Pygame surface
    try:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_surface = pygame.surfarray.make_surface(img.swapaxes(0, 1))
    except Exception as e:
        print(f"Error converting camera image to Pygame surface: {e}")
        continue

    # Create a copy of the background
    screen_surface = imgBackground.copy()
    
    # Place camera image on background
    screen_surface.blit(img_surface, (55, 162))
    
    # Make sure modeType is within valid range
    if modeType < 0 or modeType >= len(imgModeList):
        print(f"Warning: Invalid modeType {modeType}, resetting to 0")
        modeType = 0
    
    screen_surface.blit(imgModeList[modeType], (808, 44))

    if faceCurFrame:
        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            try:
                matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                
                if len(faceDis) > 0:  # Check if any faces were compared
                    matchIndex = np.argmin(faceDis)
                    
                    if matchIndex < len(matches) and matches[matchIndex]:
                        y1, x2, y2, x1 = faceLoc
                        y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                        bbox = (55 + x1, 162 + y1, x2 - x1, y2 - y1)
                        screen_surface = corner_rect(screen_surface, bbox)
                        
                        if matchIndex < len(studentIds):
                            id = studentIds[matchIndex]
                            
                            if counter == 0:
                                loading_text = font_large.render("Loading", True, (255, 255, 255))
                                text_rect = loading_text.get_rect(center=(275 + 55, 400))
                                screen_surface.blit(loading_text, text_rect)
                                pygame.display.flip()
                                counter = 1
                                modeType = 1
            except Exception as e:
                print(f"Error in face recognition matching: {e}")

        if counter != 0:
            if counter == 1:
                # Get the Student Data with error handling
                studentInfo = get_student_info(id)
                if studentInfo is None:
                    # Handle missing student info
                    print(f"No data for student ID {id}, resetting")
                    counter = 0
                    modeType = 0
                    continue

                # Get the Image from storage with error handling
                imgStudent_cv = get_student_image(id)
                imgStudent = pygame.surfarray.make_surface(imgStudent_cv.swapaxes(0, 1))
                
                # Update attendance with error handling
                try:
                    if 'last_attendance_time' not in studentInfo:
                        print(f"Warning: 'last_attendance_time' field missing for student ID {id}")
                        studentInfo['last_attendance_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    datetimeObject = datetime.strptime(studentInfo['last_attendance_time'], "%Y-%m-%d %H:%M:%S")
                    secondsElapsed = (datetime.now() - datetimeObject).total_seconds()
                    print(f"Seconds elapsed since last attendance: {secondsElapsed}")
                    
                    if secondsElapsed > 30:
                        if 'total_attendance' not in studentInfo:
                            print(f"Warning: 'total_attendance' field missing for student ID {id}")
                            studentInfo['total_attendance'] = 0
                            
                        update_success = update_attendance(id, studentInfo)
                        if not update_success:
                            # Continue showing the student info even if update fails
                            print("Continuing despite attendance update failure")
                    else:
                        modeType = 3
                        counter = 0
                        screen_surface.blit(imgModeList[modeType], (808, 44))
                except Exception as e:
                    print(f"Error processing attendance time: {e}")
                    # Reset to initial state when error occurs
                    counter = 0
                    modeType = 0
                    continue

            if modeType != 3:
                if 10 < counter < 20:
                    modeType = 2

                if modeType < len(imgModeList):
                    screen_surface.blit(imgModeList[modeType], (808, 44))

                if counter <= 10 and imgStudent is not None:
                    try:
                        # Display student information safely
                        attendance = studentInfo.get('total_attendance', 'N/A')
                        major = studentInfo.get('major', 'N/A')
                        standing = studentInfo.get('standing', 'N/A')
                        year = studentInfo.get('year', 'N/A')
                        starting_year = studentInfo.get('starting_year', 'N/A')
                        name = studentInfo.get('name', 'Unknown')
                        
                        put_text(screen_surface, str(attendance), (861, 125), font_large)
                        put_text(screen_surface, str(major), (1006, 550), font_small)
                        put_text(screen_surface, str(id), (1006, 493), font_small)
                        put_text(screen_surface, str(standing), (910, 625), font_small, (100, 100, 100))
                        put_text(screen_surface, str(year), (1025, 625), font_small, (100, 100, 100))
                        put_text(screen_surface, str(starting_year), (1125, 625), font_small, (100, 100, 100))
                        
                        # Center the name
                        name_text = font.render(str(name), True, (50, 50, 50))
                        text_rect = name_text.get_rect(center=(808 + 414//2, 445))
                        screen_surface.blit(name_text, text_rect)
                        
                        # Display student image
                        screen_surface.blit(imgStudent, (909, 175))
                    except Exception as e:
                        print(f"Error displaying student information: {e}")

                counter += 1

                if counter >= 20:
                    counter = 0
                    modeType = 0
                    studentInfo = None
                    imgStudent = None
                    if modeType < len(imgModeList):
                        screen_surface.blit(imgModeList[modeType], (808, 44))
    else:
        modeType = 0
        counter = 0

    # Update the display
    try:
        screen.blit(screen_surface, (0, 0))
        pygame.display.flip()
    except Exception as e:
        print(f"Error updating display: {e}")

    # Control frame rate
    try:
        clock.tick(30)
    except Exception as e:
        print(f"Error in clock.tick: {e}")

# Clean up resources
try:
    cap.release()
    pygame.quit()
    print("Application closed successfully")
except Exception as e:
    print(f"Error during cleanup: {e}")