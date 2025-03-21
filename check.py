import cv2
import pygame
import numpy as np
import sys
import time

def test_cameras_pygame():
    """
    Simple script to switch between two cameras (index 0 and 1) using PyGame for display
    Press 's' to switch cameras
    Press 'q' to quit
    """
    # Initialize pygame
    pygame.init()
    
    # Initialize variables
    current_camera = 0  # Start with camera index 0
    cap = cv2.VideoCapture(current_camera)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print(f"Error: Could not open camera {current_camera}")
        pygame.quit()
        return
    
    # Get initial frame to determine size
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab initial frame")
        pygame.quit()
        return
    
    height, width = frame.shape[0], frame.shape[1]
    
    # Set up display
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption(f"Camera {current_camera}")
    
    # Font for text overlay
    font = pygame.font.Font(None, 36)
    
    print("\nCamera Switcher (PyGame Version)")
    print("------------------------------")
    print("Currently showing camera index:", current_camera)
    print("Controls:")
    print("  's' - Switch between cameras")
    print("  'q' - Quit")
    
    running = True
    while running:
        # Check for PyGame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    # Switch camera index between 0 and 1
                    current_camera = 1 if current_camera == 0 else 0
                    
                    # Release current camera
                    cap.release()
                    
                    # Initialize new camera
                    cap = cv2.VideoCapture(current_camera)
                    
                    # Check if new camera opened successfully
                    if not cap.isOpened():
                        print(f"Error: Could not open camera {current_camera}, switching back")
                        current_camera = 1 if current_camera == 0 else 0
                        cap = cv2.VideoCapture(current_camera)
                    else:
                        print(f"Switched to camera index: {current_camera}")
                        pygame.display.set_caption(f"Camera {current_camera}")
                elif event.key == pygame.K_q:
                    running = False
        
        # Capture frame-by-frame
        ret, frame = cap.read()
        
        # If frame is read correctly ret is True
        if not ret:
            print(f"Error: Can't receive frame from camera {current_camera}. Retrying...")
            # Try to reinitialize the camera
            cap.release()
            time.sleep(0.5)
            cap = cv2.VideoCapture(current_camera)
            continue
        
        # Convert OpenCV BGR to RGB for PyGame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Rotate the image if needed (PyGame and OpenCV handle images differently)
        frame = np.rot90(frame)
        frame = np.flipud(frame)
        frame = np.rot90(frame, 3)
        
        # Convert to PyGame surface
        surface = pygame.surfarray.make_surface(frame)
        
        # Draw the surface to the screen
        screen.blit(surface, (0, 0))
        
        # Add text showing camera index
        text = font.render(f"Camera {current_camera}", True, (0, 255, 0))
        screen.blit(text, (10, 10))
        
        # Update the display
        pygame.display.flip()
    
    # When everything done, release the capture and close pygame
    cap.release()
    pygame.quit()

if __name__ == "__main__":
    test_cameras_pygame()