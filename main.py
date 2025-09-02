import cv2
import pickle
import numpy as np
import os
import time

class CarParkingDetector:
    def __init__(self, video_path='carPark.mp4'):
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            print(f"Error: Could not open video file {video_path}")
            return
            
        self.width, self.height = 103, 43
        self.posList = []
        self.load_parking_positions()
        
        # Performance variables
        self.frame_count = 0
        self.warmup_frames = 30
        self.debounce_frames = 10  # Increased debounce for stability
        self.slot_state = [0] * len(self.posList)
        self.slot_debounce = [0] * len(self.posList)
        
        # Stability improvements
        self.slot_history = [[] for _ in range(len(self.posList))]  # Store last N measurements
        self.history_length = 5  # Number of frames to average
        self.stability_threshold = 0.7  # 70% of frames must agree
        
        # Terminal display control
        self.last_terminal_update = 0
        self.terminal_update_interval = 30  # Update terminal every 30 frames
        
        # UI controls
        self.show_stats = False
        self.show_list = False
        self.debug_mode = False  # Toggle debug info
        
        self.create_control_window()
        
    def load_parking_positions(self):
        try:
            with open('CarParkPos', 'rb') as f:
                self.posList = pickle.load(f)
            print(f"Loaded {len(self.posList)} parking positions")
        except:
            print("No existing parking positions found. Run ParkingSpacePicker.py first.")
            self.posList = []

    def create_control_window(self):
        cv2.namedWindow("Controls")
        cv2.resizeWindow("Controls", 640, 300)
        cv2.createTrackbar("Threshold", "Controls", 25, 100, self.empty)
        cv2.createTrackbar("Block Size", "Controls", 11, 50, self.empty)
        cv2.createTrackbar("C Value", "Controls", 2, 20, self.empty)
        cv2.createTrackbar("Blur", "Controls", 3, 20, self.empty)

    def empty(self, a): pass

    def preprocess_image(self, img):
        threshold = cv2.getTrackbarPos("Threshold", "Controls")
        block_size = cv2.getTrackbarPos("Block Size", "Controls")
        c_value = cv2.getTrackbarPos("C Value", "Controls")
        blur_size = cv2.getTrackbarPos("Blur", "Controls")

        if block_size % 2 == 0: block_size += 1
        if blur_size % 2 == 0: blur_size += 1

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if blur_size > 1:
            gray = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)

        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, block_size, c_value
        )

        return thresh

    def detect_parking_spaces_fast(self, img, img_thresh):
        self.frame_count += 1

        if self.frame_count <= self.warmup_frames:
            for pos in self.posList:
                x, y = pos
                w, h = self.width, self.height
                cv2.rectangle(img, pos, (x + w, y + h), (0, 0, 255), 2)
            return img, 0

        available_count = 0

        for i, pos in enumerate(self.posList):
            x, y = pos
            w, h = self.width, self.height

            space_crop = img_thresh[y:y+h, x:x+w]
            space_orig = img[y:y+h, x:x+w]

            # More stable occupancy metrics
            occupancy_ratio = np.mean(space_crop > 0)
            
            # Use grayscale variance instead of color variance (more stable)
            gray_space = cv2.cvtColor(space_orig, cv2.COLOR_BGR2GRAY)
            gray_variance = np.var(gray_space)
            
            # Simplified edge detection with lower sensitivity
            edges = cv2.Canny(gray_space, 30, 100)  # Lower thresholds
            edge_density = np.mean(edges > 0)

            # Store measurement in history
            if len(self.slot_history[i]) >= self.history_length:
                self.slot_history[i].pop(0)
            
            # Determine current state with more lenient thresholds
            if occupancy_ratio < 0.5 and edge_density < 0.1 and gray_variance < 800:
                current_state = 1  # Available
            else:
                current_state = 0  # Occupied
            
            self.slot_history[i].append(current_state)
            
            # Use majority voting from history for stability
            if len(self.slot_history[i]) >= 3:
                avg_state = np.mean(self.slot_history[i])
                if avg_state >= self.stability_threshold:
                    stable_state = 1  # Available
                elif avg_state <= (1 - self.stability_threshold):
                    stable_state = 0  # Occupied
                else:
                    stable_state = self.slot_state[i]  # Keep previous state
            else:
                stable_state = current_state

            # Debounce logic with stable state
            if stable_state != self.slot_state[i]:
                self.slot_debounce[i] += 1
                if self.slot_debounce[i] >= self.debounce_frames:
                    self.slot_state[i] = stable_state
                    self.slot_debounce[i] = 0
            else:
                self.slot_debounce[i] = 0

            if self.slot_state[i] == 1:
                available_count += 1

            color = (0, 255, 0) if self.slot_state[i] == 1 else (0, 0, 255)
            cv2.rectangle(img, pos, (x+w, y+h), color, 2)
            
            # Debug info overlay
            if self.debug_mode:
                debug_text = f"O:{occupancy_ratio:.2f} E:{edge_density:.2f} V:{gray_variance:.0f}"
                cv2.putText(img, debug_text, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        # Add count display on screen
        total_slots = len(self.posList)
        occupied_slots = total_slots - available_count
        
        # Large count display at top-left
        cv2.putText(img, f"AVAILABLE: {available_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
        cv2.putText(img, f"OCCUPIED: {occupied_slots}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        cv2.putText(img, f"TOTAL: {total_slots}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
        
        # Add percentage
        if total_slots > 0:
            utilization = (occupied_slots / total_slots) * 100
            cv2.putText(img, f"UTILIZATION: {utilization:.1f}%", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        return img, available_count

    def update_terminal_display(self, available_spaces):
        """Update terminal with real-time parking counts"""
        total_slots = len(self.posList)
        occupied_slots = total_slots - available_spaces
        utilization = (occupied_slots / total_slots * 100) if total_slots > 0 else 0
        
        # Clear terminal (works on most systems)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🚗 REAL-TIME PARKING MONITOR 🚗")
        print("=" * 40)
        print(f"📊 FRAME: {self.frame_count}")
        print(f"⏰ TIME: {time.strftime('%H:%M:%S')}")
        print("-" * 40)
        print(f"🅿️  TOTAL SLOTS:    {total_slots:>3}")
        print(f"✅ AVAILABLE:       {available_spaces:>3}")
        print(f"🚗 OCCUPIED:        {occupied_slots:>3}")
        print(f"📈 UTILIZATION:     {utilization:>6.1f}%")
        print("=" * 40)
        print("Controls: 'q'=quit, 'p'=stats, 'l'=list, 'd'=debug")
        print("Press 'q' to exit")

    def print_occupancy_demo(self, available_spaces):
        total = len(self.posList)
        occupied = total - available_spaces
        utilization = (occupied / total * 100) if total > 0 else 0

        print("\n📊 Parking Occupancy Report")
        print("-" * 30)
        print(f"🅿️  Total Slots: {total}")
        print(f"✅ Available:   {available_spaces}")
        print(f"🚗 Occupied:    {occupied}")
        print(f"📈 Utilization: {utilization:.1f}%")
        print("-" * 30)

        if self.show_list:
            print("\n📋 Slot Status:")
            for i, state in enumerate(self.slot_state):
                status = "Available ✅" if state == 1 else "Occupied 🚗"
                print(f"S{i:02d} → {status}")
            print("-" * 30)

    def run(self):
        print("Starting optimized car parking detection...")
        print("Press 'q' to quit, 'p' for stats, 'l' for slot list, 'd' for debug mode")
        
        while True:
            success, img = self.cap.read()
            if not success:
                print("Video ended or error reading frame. Press any key to exit...")
                cv2.waitKey(0)
                break

            img_thresh = self.preprocess_image(img)
            img, available_spaces = self.detect_parking_spaces_fast(img, img_thresh)

            # Update terminal display periodically
            if self.frame_count - self.last_terminal_update >= self.terminal_update_interval:
                self.update_terminal_display(available_spaces)
                self.last_terminal_update = self.frame_count

            if self.show_stats or self.show_list:
                self.print_occupancy_demo(available_spaces)

            cv2.imshow("Parking Detection", img)
            cv2.imshow("Threshold", img_thresh)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Quitting...")
                break
            elif key == ord('p'):
                self.show_stats = not self.show_stats
                print(f"Stats display {'ON' if self.show_stats else 'OFF'}")
            elif key == ord('l'):
                self.show_list = not self.show_list
                print(f"List view {'ON' if self.show_list else 'OFF'}")
            elif key == ord('d'):
                self.debug_mode = not self.debug_mode
                print(f"Debug mode {'ON' if self.debug_mode else 'OFF'}")

        self.cap.release()
        cv2.destroyAllWindows()
        print("Program ended.")

if __name__ == "__main__":
    if not os.path.exists("carPark.mp4"):
        print("Error: carPark.mp4 not found!")
    else:
        detector = CarParkingDetector(video_path="carPark.mp4")
        detector.run()
