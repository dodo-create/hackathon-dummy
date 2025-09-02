import cv2
import pickle
import numpy as np

class ParkingSpacePicker:
    def __init__(self):
        self.width, self.height = 103, 43
        self.posList = []
        self.load_parking_positions()
        
        # Perspective transform variables
        self.perspective_matrix = None
        self.perspective_mode = False
        
        # Create control window
        self.create_control_window()
        
    def load_parking_positions(self):
        """Load existing parking positions"""
        try:
            with open('CarParkPos', 'rb') as f:
                self.posList = pickle.load(f)
            print(f"Loaded {len(self.posList)} existing parking positions")
        except:
            print("No existing parking positions found. Creating new ones.")
            self.posList = []
    
    def create_control_window(self):
        """Create control window with trackbars"""
        cv2.namedWindow("Controls")
        cv2.resizeWindow("Controls", 400, 200)
        
        # Perspective transform controls
        cv2.createTrackbar("Perspective Mode", "Controls", 0, 1, self.empty)
        cv2.createTrackbar("Top-Left X", "Controls", 10, 100, self.empty)
        cv2.createTrackbar("Top-Left Y", "Controls", 10, 100, self.empty)
        cv2.createTrackbar("Top-Right X", "Controls", 90, 100, self.empty)
        cv2.createTrackbar("Top-Right Y", "Controls", 10, 100, self.empty)
        cv2.createTrackbar("Bottom-Right X", "Controls", 90, 100, self.empty)
        cv2.createTrackbar("Bottom-Right Y", "Controls", 90, 100, self.empty)
        cv2.createTrackbar("Bottom-Left X", "Controls", 10, 100, self.empty)
        cv2.createTrackbar("Bottom-Left Y", "Controls", 90, 100, self.empty)
        
    def empty(self, a):
        pass
    
    def get_perspective_transform(self, img):
        """Get perspective transform matrix based on trackbar values"""
        h, w = img.shape[:2]
        
        # Get trackbar values (as percentages)
        tl_x = cv2.getTrackbarPos("Top-Left X", "Controls") / 100.0
        tl_y = cv2.getTrackbarPos("Top-Left Y", "Controls") / 100.0
        tr_x = cv2.getTrackbarPos("Top-Right X", "Controls") / 100.0
        tr_y = cv2.getTrackbarPos("Top-Right Y", "Controls") / 100.0
        br_x = cv2.getTrackbarPos("Bottom-Right X", "Controls") / 100.0
        br_y = cv2.getTrackbarPos("Bottom-Right Y", "Controls") / 100.0
        bl_x = cv2.getTrackbarPos("Bottom-Left X", "Controls") / 100.0
        bl_y = cv2.getTrackbarPos("Bottom-Left Y", "Controls") / 100.0
        
        # Define source points (original image corners)
        src_points = np.float32([
            [0, 0],           # Top-left
            [w, 0],           # Top-right
            [w, h],           # Bottom-right
            [0, h]            # Bottom-left
        ])
        
        # Define destination points (transformed corners)
        dst_points = np.float32([
            [w * tl_x, h * tl_y],      # Top-left
            [w * tr_x, h * tr_y],      # Top-right
            [w * br_x, h * br_y],      # Bottom-right
            [w * bl_x, h * bl_y]       # Bottom-left
        ])
        
        self.perspective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        return self.perspective_matrix
    
    def apply_perspective_transform(self, img):
        """Apply perspective transform to correct camera angle"""
        if self.perspective_matrix is None:
            self.get_perspective_transform(img)
        
        h, w = img.shape[:2]
        transformed = cv2.warpPerspective(img, self.perspective_matrix, (w, h))
        return transformed
    
    def mouseClick(self, events, x, y, flags, params):
        """Handle mouse clicks for adding/removing parking spaces"""
        if events == cv2.EVENT_LBUTTONDOWN:
            # Add new parking space
            self.posList.append((x, y))
            print(f"Added parking space at ({x}, {y})")
        elif events == cv2.EVENT_RBUTTONDOWN:
            # Remove parking space
            for i, pos in enumerate(self.posList):
                x1, y1 = pos
                if x1 < x < x1 + self.width and y1 < y < y1 + self.height:
                    removed = self.posList.pop(i)
                    print(f"Removed parking space at {removed}")
                    break
        
        # Save positions after any change
        self.save_parking_positions()
    
    def save_parking_positions(self):
        """Save parking positions to file"""
        with open('CarParkPos', 'wb') as f:
            pickle.dump(self.posList, f)
        print(f"Saved {len(self.posList)} parking positions")
    
    def draw_parking_spaces(self, img):
        """Draw all parking spaces on the image"""
        for i, pos in enumerate(self.posList):
            x, y = pos
            cv2.rectangle(img, pos, (x + self.width, y + self.height), (255, 0, 255), 2)
            cv2.putText(img, str(i+1), (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    
    def draw_perspective_guide(self, img):
        """Draw perspective transform guide lines"""
        if self.perspective_mode:
            h, w = img.shape[:2]
            
            # Get trackbar values
            tl_x = int(cv2.getTrackbarPos("Top-Left X", "Controls") / 100.0 * w)
            tl_y = int(cv2.getTrackbarPos("Top-Left Y", "Controls") / 100.0 * h)
            tr_x = int(cv2.getTrackbarPos("Top-Right X", "Controls") / 100.0 * w)
            tr_y = int(cv2.getTrackbarPos("Top-Right Y", "Controls") / 100.0 * h)
            br_x = int(cv2.getTrackbarPos("Bottom-Right X", "Controls") / 100.0 * w)
            br_y = int(cv2.getTrackbarPos("Bottom-Right Y", "Controls") / 100.0 * h)
            bl_x = int(cv2.getTrackbarPos("Bottom-Left X", "Controls") / 100.0 * w)
            bl_y = int(cv2.getTrackbarPos("Bottom-Left Y", "Controls") / 100.0 * h)
            
            # Draw perspective transform guide
            points = np.array([[tl_x, tl_y], [tr_x, tr_y], [br_x, br_y], [bl_x, bl_y]], np.int32)
            cv2.polylines(img, [points], True, (0, 255, 255), 2)
            
            # Draw corner points
            cv2.circle(img, (tl_x, tl_y), 5, (0, 255, 255), -1)
            cv2.circle(img, (tr_x, tr_y), 5, (0, 255, 255), -1)
            cv2.circle(img, (br_x, br_y), 5, (0, 255, 255), -1)
            cv2.circle(img, (bl_x, bl_y), 5, (0, 255, 255), -1)
    
    def run(self):
        """Main picker loop"""
        print("Parking Space Picker")
        print("Instructions:")
        print("- Left click to add parking space")
        print("- Right click on existing space to remove it")
        print("- Adjust perspective transform controls for different camera angles")
        print("- Press 'q' to quit")
        print("- Press 'c' to clear all spaces")
        print("- Press 's' to save current configuration")
        
        while True:
            # Load image
            img = cv2.imread('carParkImg.png')
            if img is None:
                print("Error: Could not load carParkImg.png")
                break
            
            # Check if perspective mode is enabled
            self.perspective_mode = cv2.getTrackbarPos("Perspective Mode", "Controls") == 1
            
            # Apply perspective transform if enabled
            if self.perspective_mode:
                img = self.apply_perspective_transform(img)
            
            # Draw parking spaces
            self.draw_parking_spaces(img)
            
            # Draw perspective guide
            self.draw_perspective_guide(img)
            
            # Display image
            cv2.imshow("Parking Space Picker", img)
            cv2.setMouseCallback("Parking Space Picker", self.mouseClick)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.posList.clear()
                self.save_parking_positions()
                print("Cleared all parking spaces")
            elif key == ord('s'):
                self.save_parking_positions()
                print("Configuration saved!")
        
        # Cleanup
        cv2.destroyAllWindows()

if __name__ == "__main__":
    picker = ParkingSpacePicker()
    picker.run()

