import cv2
import time

# Assuming relative imports work based on python path setup when running main.py
from .config_manager import ConfigManager
from .hand_tracking.detector import HandDetector
from .note_mapping.layout_generator import LayoutGenerator
from .expression_control.pitch_bend_processor import PitchBendProcessor
from .expression_control.velocity_intensity_processor import VelocityIntensityProcessor
from .audio_output.audio_engine import AudioEngine
from .note_mapping.interaction_logic import InteractionManager
from .ui.renderer import Renderer
import os # For adjusting config path if needed

class Application:
    """
    Main application class for the Hand-Tracked Musical Interface.
    Orchestrates all components and manages the main application loop.
    """

    def __init__(self, config_path='config/config.yaml'):
        """
        Initializes the application and all its core components.
        
        Args:
            config_path (str): Relative path to the main configuration file.
                               Assumes execution from the project root directory
                               (e.g., 'hand_tracked_musical_interface/').
                               If main.py is inside 'hand_tracked_musical_interface',
                               this path will be correct.
        """
        # If main.py is at the very root of the project (one level above hand_tracked_musical_interface directory)
        # then the config_path might need to be 'hand_tracked_musical_interface/config/config.yaml'
        # However, the prompt implies main.py is in 'hand_tracked_musical_interface/main.py'
        # in which case 'config/config.yaml' is correct relative to that.
        # ConfigManager itself resolves paths relative to its own location if a relative path is given,
        # specifically designed to find 'config/config.yaml' from 'src/'.
        # Let's stick to the ConfigManager's internal path resolution.
        
        # ConfigManager assumes config_path is relative to project root (hand_tracked_musical_interface/)
        # and it's called from src/. It then goes ../ to find the config folder.
        # So, if app.py is in src/, and main.py is in hand_tracked_musical_interface/,
        # when Application is created from main.py, ConfigManager will be instantiated with "config/config.yaml"
        # and it will correctly find hand_tracked_musical_interface/config/config.yaml.
        self.config_manager = ConfigManager(config_path=config_path) 

        # Initialize core components
        self.hand_detector = HandDetector(config_manager=self.config_manager)
        self.layout_generator = LayoutGenerator(config_manager=self.config_manager)
        self.pitch_bend_processor = PitchBendProcessor(config_manager=self.config_manager)
        self.velocity_intensity_processor = VelocityIntensityProcessor(config_manager=self.config_manager)
        self.audio_engine = AudioEngine(config_manager=self.config_manager)
        
        self.interaction_manager = InteractionManager(
            config_manager=self.config_manager,
            layout_generator=self.layout_generator, # Passed but zones are retrieved and passed in loop
            audio_engine=self.audio_engine,
            pitch_bend_processor=self.pitch_bend_processor,
            velocity_intensity_processor=self.velocity_intensity_processor
        )
        self.renderer = Renderer(config_manager=self.config_manager)

        self.cap = None
        self.running = False
        
        resolution = self.config_manager.get_setting('resolution', [1280, 720])
        self.screen_width = resolution[0]
        self.screen_height = resolution[1]
        
        self.fullscreen_mode = self.config_manager.get_setting('fullscreen', False)
        self.window_name = "Hand-Tracked Musical Interface"


    def initialize_camera(self):
        """
        Initializes the camera capture.
        """
        camera_index = self.config_manager.get_setting('camera.index', 0)
        self.cap = cv2.VideoCapture(camera_index)
        
        if not self.cap.isOpened():
            print(f"Error: Could not open camera with index {camera_index}.")
            self.running = False
            return

        # Set camera resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.screen_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.screen_height)
        
        # Verify resolution if possible (some cameras might not accept all settings)
        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"Camera initialized. Requested {self.screen_width}x{self.screen_height}, "
              f"Actual: {int(actual_width)}x{int(actual_height)}")
        
        self.running = True # Camera successfully initialized

    def run(self):
        """
        Starts and manages the main application loop.
        """
        self.initialize_camera()
        if not self.running: # If camera initialization failed
            print("Application cannot start due to camera initialization failure.")
            self.shutdown()
            return

        if self.fullscreen_mode:
            cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        prev_time = time.time()

        while self.running:
            success, frame = self.cap.read()
            if not success:
                print("Error: Could not read frame from camera. Exiting.")
                break
            
            # Flip the frame horizontally for a mirror effect
            frame = cv2.flip(frame, 1)

            # Ensure frame matches target processing resolution if camera didn't set it perfectly
            # This might be redundant if camera set it correctly, but good for consistency
            if frame.shape[1] != self.screen_width or frame.shape[0] != self.screen_height:
                 frame = cv2.resize(frame, (self.screen_width, self.screen_height))

            # --- Processing ---
            # HandDetector's process_frame can optionally draw landmarks on the frame it returns.
            # If Renderer is to be solely responsible for drawing, HandDetector.process_frame should be called with draw_landmarks_on_image=False.
            # Let's assume HandDetector returns a clean frame and hands_data.
            # The HandDetector.process_frame() implementation currently draws landmarks on the image passed to it
            # if draw_landmarks_on_image is True.
            # For the Renderer to take full control, we'd pass draw_landmarks_on_image=False.
            # However, the current Renderer code also has logic to draw landmarks.
            # To avoid double drawing:
            # Option A: HandDetector.process_frame(frame, draw_landmarks_on_image=False)
            # Option B: Renderer checks if landmarks are already on processed_frame (hard)
            # Option C: Modify HandDetector.process_frame to return raw frame + data, and a separate method/flag for drawing on its copy.
            # For now, let's assume HandDetector.process_frame returns frame that might have landmarks
            # and Renderer.draw_frame will draw zones on top, and then *also* draw landmarks if its config is set.
            # This is slightly inefficient if both draw.
            # The current Renderer._draw_landmarks_for_hand assumes it gets raw landmark data.
            # The current HandDetector.process_frame returns (image_with_landmarks, hands_data)
            
            # Let's make HandDetector NOT draw on the frame directly, so Renderer does it.
            # This requires passing `draw_landmarks_on_image=False` to `hand_detector.process_frame`.
            # The `HandDetector.find_hands` method has `draw_landmarks` argument.
            # `HandDetector.process_frame` calls `find_hands(image.copy(), draw_landmarks=draw_landmarks_on_image)`
            # So if `draw_landmarks_on_image` is False here, `find_hands` won't draw.
            
            # To be explicit:
            # 1. `detector.find_hands(frame_copy, draw_landmarks=False)` to get results without drawing
            # 2. `hands_data = detector.get_all_hands_data(frame.shape)` (hypothetical method restructuring)
            # 3. `renderer.draw_frame(frame, zones, hands_data)`
            
            # Given current structure of HandDetector.process_frame:
            # It processes and returns (image_with_potential_drawings, hands_data)
            # If we want Renderer to be the sole drawer of landmarks:
            # We need a frame *without* detector drawings.
            # Simplest for now: let HandDetector.process_frame do its thing,
            # and ensure Renderer.show_hand_landmarks is the master switch for landmarks visibility.
            # If Renderer.show_hand_landmarks is true, it will draw them.
            # If HandDetector also drew them, they might be drawn twice or one over the other.
            
            # Correct approach:
            # hand_detector.find_hands(frame, draw_landmarks=False) # This populates detector.results
            # hands_data_list = []
            # if hand_detector.results and hand_detector.results.multi_hand_landmarks:
            #    for i in range(len(hand_detector.results.multi_hand_landmarks)):
            #        lm_pos = hand_detector.get_landmark_positions(frame.shape, i)
            #        # ... and build up hands_data_list like in HandDetector.process_frame()
            # This is re-implementing parts of process_frame.
            # The simplest modification to HandDetector would be for its process_frame to take a
            # `draw_on_image` flag. It already does: `draw_landmarks_on_image`.
            
            # So, if Renderer is the authority for drawing landmarks:
            processed_frame_ignored, hands_data = self.hand_detector.process_frame(
                frame.copy(), 
                draw_landmarks_on_image=False # Renderer will handle drawing
            )
            render_target_frame = frame # Draw on the original (flipped, resized) frame

            zones = self.layout_generator.get_zones()
            self.interaction_manager.process_hands_data(hands_data, zones)

            # --- Rendering ---
            # Renderer draws zones and conditionally landmarks onto render_target_frame
            render_image = self.renderer.draw_frame(
                render_target_frame, 
                zones, 
                hands_data, 
                self.interaction_manager.active_notes # Pass active_notes for potential future use by renderer
            )
            
            # --- Display FPS ---
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
            prev_time = curr_time
            cv2.putText(render_image, f"FPS: {int(fps)}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # --- Display Image ---
            cv2.imshow(self.window_name, render_image)

            # --- Handle User Input ---
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27: # ESC key
                self.running = False
            elif key == ord('r'): # Example: Reload layout (useful for dev)
                print("Reloading note layout...")
                self.layout_generator.regenerate_layout()
                print("Layout reloaded.")


        self.shutdown()

    def shutdown(self):
        """
        Cleans up resources upon application exit.
        """
        print("Shutting down application...")
        if self.cap:
            self.cap.release()
            print("Camera released.")
        
        cv2.destroyAllWindows()
        print("OpenCV windows destroyed.")
        
        if self.audio_engine:
            self.audio_engine.shutdown() # This already prints messages
        
        if self.hand_detector:
            self.hand_detector.close() # MediaPipe Hands.close()
            print("HandDetector closed.")
        
        print("Application shutdown complete.")

```
