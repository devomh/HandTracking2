import cv2
import mediapipe as mp
import math

class HandDetector:
    """
    Detects hands in an image, extracts landmark positions, and determines finger states.
    """
    def __init__(self, config_manager=None, # Allow None for backward compatibility or direct param setting
                 static_image_mode=None,
                 max_num_hands=None,
                 min_detection_confidence=None,
                 min_tracking_confidence=None):
        """
        Initializes the HandDetector.

        Args:
            config_manager (ConfigManager, optional): Configuration manager instance.
                                                      If provided, settings are read from config.
            static_image_mode (bool, optional): Overrides config if provided.
            max_num_hands (int, optional): Overrides config if provided.
            min_detection_confidence (float, optional): Overrides config if provided.
            min_tracking_confidence (float, optional): Overrides config if provided.
        """
        if config_manager:
            default_static_mode = config_manager.get_setting('hand_detector.static_image_mode', False)
            default_max_hands = config_manager.get_setting('hand_detector.max_num_hands', 2)
            default_min_detect_conf = config_manager.get_setting('hand_detector.min_detection_confidence', 0.5)
            default_min_track_conf = config_manager.get_setting('hand_detector.min_tracking_confidence', 0.5)
        else: # Defaults if no config manager
            default_static_mode = False
            default_max_hands = 2
            default_min_detect_conf = 0.5
            default_min_track_conf = 0.5

        self.static_image_mode = static_image_mode if static_image_mode is not None else default_static_mode
        self.max_num_hands = max_num_hands if max_num_hands is not None else default_max_hands
        self.min_detection_confidence = min_detection_confidence if min_detection_confidence is not None else default_min_detect_conf
        self.min_tracking_confidence = min_tracking_confidence if min_tracking_confidence is not None else default_min_track_conf
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.static_image_mode,
            max_num_hands=self.max_num_hands,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.results = None # To store the results from MediaPipe processing

        # print(f"HandDetector initialized with: static_mode={self.static_image_mode}, max_hands={self.max_num_hands}, "
        #       f"min_detect_conf={self.min_detection_confidence}, min_track_conf={self.min_tracking_confidence}")

        # Landmark indices for fingertips and other key points for finger state detection
        self.landmark_indices = {
            'WRIST': 0,
            'THUMB_CMC': 1, 'THUMB_MCP': 2, 'THUMB_IP': 3, 'THUMB_TIP': 4,
            'INDEX_FINGER_MCP': 5, 'INDEX_FINGER_PIP': 6, 'INDEX_FINGER_DIP': 7, 'INDEX_FINGER_TIP': 8,
            'MIDDLE_FINGER_MCP': 9, 'MIDDLE_FINGER_PIP': 10, 'MIDDLE_FINGER_DIP': 11, 'MIDDLE_FINGER_TIP': 12,
            'RING_FINGER_MCP': 13, 'RING_FINGER_PIP': 14, 'RING_FINGER_DIP': 15, 'RING_FINGER_TIP': 16,
            'PINKY_MCP': 17, 'PINKY_PIP': 18, 'PINKY_DIP': 19, 'PINKY_TIP': 20
        }
        self.finger_names = ["THUMB", "INDEX", "MIDDLE", "RING", "PINKY"]


    def find_hands(self, image, draw_landmarks=True):
        """
        Finds hands in the input image and optionally draws landmarks.

        Args:
            image: The input image in BGR format (OpenCV).
            draw_landmarks (bool): If True, draws hand landmarks on the image.

        Returns:
            The image with or without drawn landmarks.
        """
        # Convert the BGR image to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False # To improve performance, optionally mark the image as not writeable.

        # Process the image and find hands
        self.results = self.hands.process(image_rgb)

        image.flags.writeable = True # Make the image writeable again for drawing
        # image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR) # Not needed if we draw on original 'image'

        if draw_landmarks and self.results.multi_hand_landmarks:
            for hand_landmarks in self.results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )
        return image

    def get_landmark_positions(self, image_shape, hand_index=0):
        """
        Retrieves the denormalized landmark positions for a specific detected hand.

        Args:
            image_shape (tuple): The shape of the image (height, width).
            hand_index (int): The index of the hand for which to get landmarks.

        Returns:
            list: A list of tuples (id, x, y) for each landmark of the specified hand.
                  Returns an empty list if the hand is not found or no hands detected.
        """
        landmarks_list = []
        if self.results and self.results.multi_hand_landmarks:
            if hand_index < len(self.results.multi_hand_landmarks):
                hand = self.results.multi_hand_landmarks[hand_index]
                height, width = image_shape[:2]
                for lm_id, landmark in enumerate(hand.landmark):
                    # Convert normalized coordinates to pixel coordinates
                    cx, cy = int(landmark.x * width), int(landmark.y * height)
                    landmarks_list.append((lm_id, cx, cy, landmark.z)) # Also store z for potential future use
                return landmarks_list
        return []

    def get_finger_states(self, hand_landmarks_list):
        """
        Determines if each finger is extended or retracted based on landmark positions.

        Args:
            hand_landmarks_list (list): A list of denormalized landmark positions
                                       (id, x, y, z) for a single hand.

        Returns:
            dict: A dictionary indicating the state of each finger
                  (e.g., {'THUMB': 'extended', 'INDEX': 'retracted', ...}).
                  Returns None if landmarks are insufficient.
        """
        if not hand_landmarks_list or len(hand_landmarks_list) != 21:
            return None # Not enough landmarks to determine finger states

        states = {}
        
        # Convert list to dict for easier access by landmark ID
        landmarks = {lm[0]: (lm[1], lm[2], lm[3]) for lm in hand_landmarks_list}

        # Helper to get a landmark coordinate by its symbolic name
        def get_lm_coord(name):
            return landmarks.get(self.landmark_indices[name])

        # Thumb: Compare tip y-coord with IP joint y-coord (and MCP for more robustness if needed)
        # For simplicity, let's use a more direct y-coordinate comparison.
        # Assumes hand is somewhat upright. A more robust method would use distances or angles.
        thumb_tip = get_lm_coord('THUMB_TIP')
        thumb_ip = get_lm_coord('THUMB_IP')
        thumb_mcp = get_lm_coord('THUMB_MCP') # MCP of thumb
        thumb_cmc = get_lm_coord('THUMB_CMC')

        if thumb_tip and thumb_ip and thumb_mcp and thumb_cmc:
            # For thumb, extended can mean it's "away" from the palm.
            # A simple check: if thumb tip is further from wrist than MCP joint, or if it's horizontally extended
            # This is a common heuristic: check if tip is further out than the joint below it.
            # For thumb, the "upright" logic is different. We check if the tip is further from the wrist than MCP or IP.
            # Or, simpler: compare x-coordinate of tip vs ip (for side-ways extension)
            # or y-coordinate of tip vs ip (for upward extension)
            # Let's use a simplified distance logic for thumb, comparing tip to a point near palm
            
            # Heuristic: Thumb is extended if its tip is further from the MCP joint in the direction perpendicular to the vector from CMC to MCP
            # Or a simpler heuristic for now:
            # If the hand is typically oriented with fingers up, thumb_tip[0] (x) vs thumb_ip[0] (x) for right hand
            # For left hand, it's reversed. Let's use distance from palm center or a fixed point.
            # For now, a basic y-coord check, similar to other fingers, might be misleading for thumb.
            # Let's use distance from wrist:
            wrist = get_lm_coord('WRIST')
            if wrist:
                # Compare distance from wrist to tip vs distance from wrist to IP
                # Or, more simply, if the thumb tip is "above" (smaller y) its IP joint, or "sideways extended"
                # This needs handedness to be really accurate with simple x/y.
                # Let's try this: if the thumb tip is further from the index finger MCP than the thumb IP is.
                index_mcp = get_lm_coord('INDEX_FINGER_MCP')
                if index_mcp:
                    dist_tip_to_index_mcp = math.hypot(thumb_tip[0] - index_mcp[0], thumb_tip[1] - index_mcp[1])
                    dist_ip_to_index_mcp = math.hypot(thumb_ip[0] - index_mcp[0], thumb_ip[1] - index_mcp[1])
                    if dist_tip_to_index_mcp > dist_ip_to_index_mcp + abs(thumb_tip[0] - thumb_ip[0])*0.3 : # Added some buffer
                         states['THUMB'] = 'extended'
                    else:
                         states['THUMB'] = 'retracted'
                else: # Fallback if index_mcp not found
                    states['THUMB'] = 'retracted' # Default or simple y-coord
            else:
                states['THUMB'] = 'retracted'

        else:
            states['THUMB'] = 'unknown'


        # Fingers: Index, Middle, Ring, Pinky
        # Compare y-coordinate of TIP vs PIP. If TIP is "above" PIP (smaller y), it's extended.
        # This assumes the hand is mostly upright in the camera frame.
        finger_tip_indices = [
            self.landmark_indices['INDEX_FINGER_TIP'], self.landmark_indices['MIDDLE_FINGER_TIP'],
            self.landmark_indices['RING_FINGER_TIP'], self.landmark_indices['PINKY_TIP']
        ]
        finger_pip_indices = [
            self.landmark_indices['INDEX_FINGER_PIP'], self.landmark_indices['MIDDLE_FINGER_PIP'],
            self.landmark_indices['RING_FINGER_PIP'], self.landmark_indices['PINKY_PIP']
        ]
        finger_mcp_indices = [ # MCP joints for reference
            self.landmark_indices['INDEX_FINGER_MCP'], self.landmark_indices['MIDDLE_FINGER_MCP'],
            self.landmark_indices['RING_FINGER_MCP'], self.landmark_indices['PINKY_MCP']
        ]

        for i in range(4): # For Index, Middle, Ring, Pinky
            finger_name = self.finger_names[i+1]
            tip_coord = landmarks.get(finger_tip_indices[i])
            pip_coord = landmarks.get(finger_pip_indices[i])
            mcp_coord = landmarks.get(finger_mcp_indices[i]) # MCP for this finger

            if tip_coord and pip_coord and mcp_coord:
                # Extended if tip is further from MCP than PIP is from MCP (using y-coordinates for vertical extension)
                # And also tip is "above" (smaller y) PIP
                if tip_coord[1] < pip_coord[1] and pip_coord[1] < mcp_coord[1]:
                    states[finger_name] = 'extended'
                # More robust: distance from MCP to TIP vs MCP to PIP
                # dist_mcp_tip = math.hypot(tip_coord[0] - mcp_coord[0], tip_coord[1] - mcp_coord[1])
                # dist_mcp_pip = math.hypot(pip_coord[0] - mcp_coord[0], pip_coord[1] - mcp_coord[1])
                # if dist_mcp_tip > dist_mcp_pip * 1.1: # Tip is significantly further than PIP
                #     states[finger_name] = 'extended'
                else:
                    states[finger_name] = 'retracted'
            else:
                states[finger_name] = 'unknown' # Landmark missing

        return states

    def get_handedness(self, hand_index=0):
        """
        Retrieves the handedness (Left/Right) for a specific detected hand.

        Args:
            hand_index (int): The index of the hand.

        Returns:
            str: 'Left', 'Right', or 'Unknown' if not available.
        """
        if self.results and self.results.multi_handedness:
            if hand_index < len(self.results.multi_handedness):
                handedness_info = self.results.multi_handedness[hand_index]
                return handedness_info.classification[0].label
        return "Unknown"

    def calculate_bounding_box(self, hand_landmarks_list):
        """
        Calculates the bounding box (min_x, min_y, max_x, max_y) for a hand.

        Args:
            hand_landmarks_list (list): List of (id, x, y, z) landmarks for a hand.

        Returns:
            tuple: (min_x, min_y, max_x, max_y) or None if no landmarks.
        """
        if not hand_landmarks_list:
            return None
        
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for _, x, y, _ in hand_landmarks_list:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
        
        # Add a small padding if desired
        padding = 10 # pixels
        min_x -= padding
        min_y -= padding
        max_x += padding
        max_y += padding

        return (int(min_x), int(min_y), int(max_x), int(max_y))


    def process_frame(self, image, draw_landmarks_on_image=True):
        """
        Processes a single camera frame to find hands, landmarks, and finger states.

        Args:
            image: The input image (BGR format from OpenCV).
            draw_landmarks_on_image (bool): Whether to draw landmarks on the returned image.

        Returns:
            tuple: (processed_image, hands_data)
                - processed_image: The image with landmarks drawn (if enabled).
                - hands_data (list): A list of dictionaries, where each dictionary
                                     contains info for one detected hand:
                                     {
                                         'landmarks': [(id, x, y, z), ...], # Denormalized
                                         'handedness': 'Left' / 'Right',
                                         'finger_states': {'THUMB': 'extended', ...},
                                         'bounding_box': (min_x, min_y, max_x, max_y) # Optional
                                     }
        """
        processed_image = self.find_hands(image.copy(), draw_landmarks=draw_landmarks_on_image)
        hands_data = []

        if self.results and self.results.multi_hand_landmarks:
            for i, hand_landmarks_mp in enumerate(self.results.multi_hand_landmarks):
                # Get denormalized landmark positions for the current hand
                landmark_positions = self.get_landmark_positions(image.shape, hand_index=i)
                
                if not landmark_positions:
                    continue

                # Get handedness
                handedness = self.get_handedness(hand_index=i)

                # Get finger states
                finger_states = self.get_finger_states(landmark_positions)
                
                # Calculate bounding box
                bounding_box = self.calculate_bounding_box(landmark_positions)

                current_hand_data = {
                    'landmarks': landmark_positions,
                    'handedness': handedness,
                    'finger_states': finger_states if finger_states else {},
                    'bounding_box': bounding_box,
                    'mp_landmarks': hand_landmarks_mp # Store raw mediapipe landmarks if needed later
                }
                hands_data.append(current_hand_data)
        
        return processed_image, hands_data

    def close(self):
        """
        Releases resources used by the MediaPipe Hands solution.
        """
        self.hands.close()


if __name__ == '__main__':
    # Example Usage (requires a webcam)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    # Example of direct parameter setting (old way)
    # detector = HandDetector(max_num_hands=2, min_detection_confidence=0.7)

    # Example of using a mock config_manager for testing HandDetector standalone
    class MockConfigManager:
        def __init__(self, data): self.data = data
        def get_setting(self, key, default=None):
            parts = key.split('.')
            val = self.data
            try:
                for p in parts: val = val[p]
                return val
            except KeyError: return default
    
    mock_hd_config = {
        'hand_detector': {
            'static_image_mode': False,
            'max_num_hands': 1,
            'min_detection_confidence': 0.6,
            'min_tracking_confidence': 0.6
        }
    }
    config_mgr_hd_test = MockConfigManager(mock_hd_config)
    detector = HandDetector(config_manager=config_mgr_hd_test)


    while True:
        success, frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        frame = cv2.flip(frame, 1) # Flip horizontally for a selfie-view display.
        
        # Process the frame
        processed_frame, hands_detected_data = detector.process_frame(frame, draw_landmarks_on_image=True)

        if hands_detected_data:
            for i, hand_data in enumerate(hands_detected_data):
                print(f"--- Hand {i+1} ({hand_data['handedness']}) ---")
                # print(f"  Bounding Box: {hand_data['bounding_box']}")
                # print(f"  Landmarks (first 5): {hand_data['landmarks'][:5]}")
                print(f"  Finger States: {hand_data['finger_states']}")
                
                # Example: Draw a circle on the index finger tip
                if hand_data['landmarks'] and len(hand_data['landmarks']) > detector.landmark_indices['INDEX_FINGER_TIP']:
                    index_tip_id = detector.landmark_indices['INDEX_FINGER_TIP']
                    # Find the landmark for index tip
                    lm = next((item for item in hand_data['landmarks'] if item[0] == index_tip_id), None)
                    if lm:
                        cv2.circle(processed_frame, (lm[1], lm[2]), 10, (0, 255, 0), -1)
                
                # Display finger states on the image
                y_offset = 30
                for finger, state in hand_data['finger_states'].items():
                    cv2.putText(processed_frame, f"{finger}: {state}", (10, y_offset), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    y_offset += 30


        cv2.imshow('Hand Tracking Example', processed_frame)

        if cv2.waitKey(5) & 0xFF == 27: # Press 'ESC' to exit
            break

    detector.close()
    cap.release()
    cv2.destroyAllWindows()
```
