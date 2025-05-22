import cv2
import numpy as np # For potential color manipulations or creating blank images
import mediapipe as mp # For HAND_CONNECTIONS if drawing landmarks manually

# Assuming ConfigManager is in src.config_manager
from ..config_manager import ConfigManager
# Assuming NoteZone is in src.note_mapping.zone
from ..note_mapping.zone import NoteZone # For type hinting if needed

class Renderer:
    """
    Handles drawing the UI elements, including note zones and hand landmarks,
    onto the camera frame.
    """

    # Standard MediaPipe Hand Connections
    MP_HAND_CONNECTIONS = mp.solutions.hands.HAND_CONNECTIONS

    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the Renderer.

        Args:
            config_manager (ConfigManager): An instance of the ConfigManager.
        """
        self.config_manager = config_manager

        # Load UI settings from config
        self.resolution = tuple(self.config_manager.get_setting('resolution', [1280, 720]))
        self.zone_labels_enabled = self.config_manager.get_setting('zone_labels', True)
        self.zone_style = self.config_manager.get_setting('zone_style', "block").lower() # "block" or "outline"
        self.show_hand_landmarks = self.config_manager.get_setting('show_hand_landmarks', True)
        self.highlight_active_zones = self.config_manager.get_setting('highlight_active_zones', True)
        # self.show_velocity_indicators = self.config_manager.get_setting('show_velocity_indicators', True) # For later

        # Define colors (BGR format for OpenCV)
        self.colors = {
            'zone_fill_default': self.config_manager.get_setting('colors.zone_fill_default', (50, 50, 50)),       # Dark Grey
            'zone_border_default': self.config_manager.get_setting('colors.zone_border_default', (200, 200, 200)), # Light Grey
            'zone_fill_active': self.config_manager.get_setting('colors.zone_fill_active', (0, 80, 0)),         # Darker Green
            'zone_border_active': self.config_manager.get_setting('colors.zone_border_active', (0, 255, 0)),     # Bright Green
            'zone_text': self.config_manager.get_setting('colors.zone_text', (255, 255, 255)),                 # White
            'landmark_point': self.config_manager.get_setting('colors.landmark_point', (0, 0, 255)),           # Red
            'landmark_connector': self.config_manager.get_setting('colors.landmark_connector', (0, 255, 0)),   # Green
            'velocity_indicator': self.config_manager.get_setting('colors.velocity_indicator', (255, 255, 0)) # Cyan/Aqua
        }
        
        # Font settings for labels
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale_base = 0.6 # Base scale, will be adjusted by zone height
        self.font_thickness = 1
        
        # Landmark drawing settings
        self.landmark_circle_radius = 5
        self.landmark_connector_thickness = 2


    def _draw_zone(self, image: np.ndarray, zone: NoteZone):
        """
        Helper method to draw a single note zone.
        """
        x, y, w, h = zone.rect
        
        fill_color = self.colors['zone_fill_default']
        border_color = self.colors['zone_border_default']

        # Use zone.current_color if NoteZone itself manages its active color based on interaction
        # This assumes zone.current_color is updated by InteractionManager or NoteZone.activate/deactivate
        if self.highlight_active_zones and zone.is_active:
            # If zone.current_color is the authority (e.g., from update_highlight in NoteZone)
            # fill_color = zone.current_color 
            # border_color = tuple(min(c + 50, 255) for c in zone.current_color) # Brighter border
            # For now, let's use explicit Renderer colors for active state
            fill_color = self.colors['zone_fill_active']
            border_color = self.colors['zone_border_active']


        if self.zone_style == "block":
            cv2.rectangle(image, (x, y), (x + w, y + h), fill_color, cv2.FILLED)
            cv2.rectangle(image, (x, y), (x + w, y + h), border_color, 2) # Border thickness 2
        elif self.zone_style == "outline":
            cv2.rectangle(image, (x, y), (x + w, y + h), border_color, 2) # Border thickness 2
        else: # Default to block if style is unknown
            cv2.rectangle(image, (x, y), (x + w, y + h), fill_color, cv2.FILLED)
            cv2.rectangle(image, (x, y), (x + w, y + h), border_color, 2)

        if self.zone_labels_enabled and zone.label:
            # Dynamically adjust font scale based on zone height, but cap it
            font_scale = min(self.font_scale_base * (h / 80.0), self.font_scale_base * 2.0) # Cap at 2x base
            font_scale = max(font_scale, 0.4) # Minimum scale

            text_size, _ = cv2.getTextSize(zone.label, self.font, font_scale, self.font_thickness)
            
            # Center text in the zone
            text_x = x + (w - text_size[0]) // 2
            text_y = y + (h + text_size[1]) // 2
            
            cv2.putText(image, zone.label, (text_x, text_y), self.font,
                        font_scale, self.colors['zone_text'], self.font_thickness, cv2.LINE_AA)

    def _draw_landmarks_for_hand(self, image: np.ndarray, hand_landmarks_list: list, connections=None):
        """
        Helper method to draw landmarks and connections for a single hand.
        hand_landmarks_list: List of (id, x, y, z) tuples for a single hand.
        connections: List of (start_lm_id, end_lm_id) tuples.
        """
        # Convert landmark list to a dictionary for easy lookup by ID
        landmarks_dict = {lm[0]: (lm[1], lm[2]) for lm in hand_landmarks_list} # (x,y)

        # Draw connections
        if connections:
            for connection in connections:
                start_id, end_id = connection
                if start_id in landmarks_dict and end_id in landmarks_dict:
                    start_point = landmarks_dict[start_id]
                    end_point = landmarks_dict[end_id]
                    cv2.line(image, start_point, end_point, self.colors['landmark_connector'],
                             self.landmark_connector_thickness)
        
        # Draw landmark points (circles)
        for lm_id, x, y, _ in hand_landmarks_list: # z is not used for 2D drawing
            cv2.circle(image, (x, y), self.landmark_circle_radius,
                       self.colors['landmark_point'], cv2.FILLED)


    def draw_frame(self, base_image: np.ndarray, zones: list[NoteZone], hands_data: list, active_notes_info=None):
        """
        Draws all UI elements onto the base image.

        Args:
            base_image: The camera feed (OpenCV BGR image). This will be modified.
            zones: A list of NoteZone objects.
            hands_data: List of hand info from HandDetector.
            active_notes_info: (Optional) Info about active notes from InteractionManager.
                               Currently not used directly, relies on zone.is_active.

        Returns:
            The modified base_image.
        """
        # Create a copy if you don't want to modify the original base_image outside this function
        # output_image = base_image.copy()
        # For efficiency, modify in place if base_image is already a frame copy from main loop.
        output_image = base_image 

        # 1. Draw Note Zones
        for zone in zones:
            self._draw_zone(output_image, zone)

        # 2. Draw Hand Landmarks
        if self.show_hand_landmarks:
            for hand in hands_data:
                # The HandDetector.process_frame() was defined to return 'landmarks' as denormalized (id,x,y,z)
                # and 'mp_landmarks' as the raw MediaPipe landmark objects.
                # If 'mp_landmarks' are available and we want MediaPipe's drawing style:
                # if 'mp_landmarks' in hand and hand['mp_landmarks']:
                #    mp.solutions.drawing_utils.draw_landmarks(
                #        output_image,
                #        hand['mp_landmarks'],
                #        self.MP_HAND_CONNECTIONS,
                #        mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                #        mp.solutions.drawing_styles.get_default_hand_connections_style())
                # else: # Fallback to manual drawing using denormalized landmarks
                #    self._draw_landmarks_for_hand(output_image, hand['landmarks'], self.MP_HAND_CONNECTIONS)
                
                # Current HandDetector.process_frame() returns the frame with landmarks *already drawn* by find_hands()
                # if its draw_landmarks=True.
                # If HandDetector.find_hands() has draw_landmarks=False, then Renderer must draw.
                # Let's assume HandDetector.find_hands() has draw_landmarks=False for now,
                # so Renderer is responsible.
                # The 'landmarks' field in hands_data is the list of (id, x, y, z).
                self._draw_landmarks_for_hand(output_image, hand['landmarks'], self.MP_HAND_CONNECTIONS)


        # 3. Draw Velocity/Intensity Indicators (Placeholder for now)
        # show_velocity_indicators = self.config_manager.get_setting('show_velocity_indicators', True)
        # if show_velocity_indicators and active_notes_info:
        #     for finger_id, note_info in active_notes_info.items():
        #         zone_rect = note_info['zone'].rect
        #         # This requires current intensity value, not just initial velocity.
        #         # Let's assume note_info contains 'current_intensity_0_1' (0.0 to 1.0)
        #         if 'current_intensity_0_1' in note_info:
        #             intensity_norm = note_info['current_intensity_0_1']
        #             indicator_x = zone_rect[0] + zone_rect[2] + 10 # 10px right of zone
        #             indicator_y_start = zone_rect[1]
        #             indicator_y_end = zone_rect[1] + zone_rect[3]
        #             current_y_pos = indicator_y_start + (1.0 - intensity_norm) * zone_rect[3] # Inverted: 0.0 at bottom, 1.0 at top
                          
        #             cv2.line(output_image, (indicator_x, indicator_y_start), (indicator_x, indicator_y_end), (100,100,100), 2)
        #             cv2.circle(output_image, (indicator_x, int(current_y_pos)), 5, self.colors['velocity_indicator'], -1)


        # Ensure the output image matches the configured resolution if it's different from base_image
        # Typically, base_image (camera frame) is already resized to self.resolution by the main loop.
        # If not, resizing here might be needed:
        # if output_image.shape[1::-1] != self.resolution: # shape is (h, w, c)
        #    output_image = cv2.resize(output_image, self.resolution)
            
        return output_image

if __name__ == '__main__':
    # --- Mock Classes for Testing Renderer ---
    class MockConfigManager:
        def __init__(self, config_data): self.config = config_data
        def get_setting(self, key, default=None): 
            # Basic dot notation access for testing
            if '.' in key:
                keys = key.split('.')
                val = self.config
                try:
                    for k_part in keys: val = val[k_part]
                    return val
                except (KeyError, TypeError): return default
            return self.config.get(key, default)

    class MockNoteZone: # Simplified version of actual NoteZone
        def __init__(self, x, y, w, h, label, is_active=False, current_color=(50,50,50), highlight_color=(0,255,0)):
            self.rect = (x, y, w, h)
            self.label = label
            self.is_active = is_active
            self.current_color = current_color # For testing if NoteZone manages its own color
            self.highlight_color = highlight_color

    # --- Test Setup ---
    config_data_render = {
        'resolution': [640, 480],
        'zone_labels': True,
        'zone_style': "block", # "block" or "outline"
        'show_hand_landmarks': True,
        'highlight_active_zones': True,
        'colors': { # Example of overriding default colors via config
            'zone_fill_default': (60, 60, 60),
            'zone_text': (240, 240, 240)
        }
    }
    mock_config_render = MockConfigManager(config_data_render)
    renderer = Renderer(mock_config_render)

    # Create a blank base image (BGR)
    test_resolution = tuple(mock_config_render.get_setting('resolution')) # (width, height)
    base_frame = np.zeros((test_resolution[1], test_resolution[0], 3), dtype=np.uint8) # OpenCV: height, width

    # Create mock zones
    zones_to_draw = [
        MockNoteZone(50, 50, 100, 150, "C4", is_active=False),
        MockNoteZone(200, 50, 100, 150, "D4", is_active=True),
        MockNoteZone(50, 250, 250, 100, "E4_LongLabel", is_active=False)
    ]
    
    # Create mock hand data
    # Example landmarks for one hand (ensure coordinates are within 640x480)
    mock_hand_landmarks = [
        (0, 300, 300, 0), (1, 320, 310, 0), (2, 340, 320, 0), (3, 360, 330, 0), (4, 380, 340, 0), # Thumb
        (5, 300, 250, 0), (6, 330, 240, 0), (7, 350, 230, 0), (8, 370, 220, 0), # Index
        # Add more landmarks if needed to test connections fully
    ]
    hands_data_to_draw = [{
        'landmarks': mock_hand_landmarks,
        'handedness': 'Right',
        'finger_states': {}, # Not directly used by Renderer currently
        'bounding_box': None, # Not used by Renderer
        'mp_landmarks': None # Not used if drawing manually
    }]

    print("--- Renderer Test ---")
    # Draw the frame
    output_frame = renderer.draw_frame(base_frame.copy(), zones_to_draw, hands_data_to_draw)

    # --- Display the output (requires an environment with a display) ---
    try:
        cv2.imshow("Renderer Test Output", output_frame)
        print("Displaying test output. Press any key in the window to continue...")
        cv2.waitKey(0) # Wait for a key press
        cv2.destroyAllWindows()
        print("Test display window closed.")
    except cv2.error as e:
        if "DISPLAY" in str(e) or "GTK" in str(e) or "Qt" in str(e): # Common errors on headless systems
            print(f"Skipping cv2.imshow due to display error (likely headless environment): {e}")
            # Optionally save the image to a file for verification
            cv2.imwrite("renderer_test_output.png", output_frame)
            print("Test output saved to renderer_test_output.png")
        else:
            raise # Re-raise if it's a different cv2 error

    print("\n--- Renderer Test Complete (check image or window) ---")

    # Test with zone_style = "outline"
    print("\n--- Testing Outline Style ---")
    config_data_render['zone_style'] = "outline"
    mock_config_outline = MockConfigManager(config_data_render)
    renderer_outline = Renderer(mock_config_outline)
    output_frame_outline = renderer_outline.draw_frame(base_frame.copy(), zones_to_draw, hands_data_to_draw)
    try:
        cv2.imshow("Renderer Test Outline", output_frame_outline)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except cv2.error as e:
        print(f"Skipping cv2.imshow for outline test: {e}")
        cv2.imwrite("renderer_test_output_outline.png", output_frame_outline)
        print("Outline test output saved to renderer_test_output_outline.png")

```
