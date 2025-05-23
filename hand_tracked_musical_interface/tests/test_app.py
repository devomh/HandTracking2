import unittest
from unittest.mock import patch, MagicMock, PropertyMock

# Ensure the 'src' directory is discoverable for imports if tests are run from project root
import sys
import os
# Add the parent directory of 'src' to sys.path to allow 'from src.app import Application'
# This assumes tests/test_app.py is in hand_tracked_musical_interface/tests/
# and src/ is hand_tracked_musical_interface/src/
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.app import Application
# Mocked versions of dependencies will be used via @patch

class TestApplication(unittest.TestCase):

    @patch('src.app.Renderer')
    @patch('src.app.InteractionManager')
    @patch('src.app.AudioEngine')
    @patch('src.app.VelocityIntensityProcessor')
    @patch('src.app.PitchBendProcessor')
    @patch('src.app.LayoutGenerator')
    @patch('src.app.HandDetector')
    @patch('src.app.ConfigManager')
    def setUp(self, MockConfigManager, MockHandDetector, MockLayoutGenerator,
              MockPitchBendProcessor, MockVelocityIntensityProcessor, MockAudioEngine,
              MockInteractionManager, MockRenderer):
        """
        Set up test environment for each test case.
        Mocks all major dependencies of the Application class.
        """
        # Configure the mock ConfigManager
        self.mock_config_manager_instance = MockConfigManager.return_value
        # Define a side_effect function for get_setting
        def config_get_setting_side_effect(key, default=None):
            config_values = {
                'resolution': [1280, 720],
                'fullscreen': False,
                'camera.index': 0,
                # Add other necessary config values here if Application directly uses them
                # e.g. hand_detector settings if HandDetector wasn't fully mocked
            }
            return config_values.get(key, default)
        self.mock_config_manager_instance.get_setting.side_effect = config_get_setting_side_effect
        
        # Store mock instances if needed for assertions on them
        self.mock_hand_detector_instance = MockHandDetector.return_value
        self.mock_audio_engine_instance = MockAudioEngine.return_value
        self.mock_layout_generator_instance = MockLayoutGenerator.return_value
        self.mock_interaction_manager_instance = MockInteractionManager.return_value
        self.mock_renderer_instance = MockRenderer.return_value


        # Initialize Application - this will use the mocked classes
        self.app = Application(config_path='dummy_config.yaml') # Path won't matter due to mock

    def test_application_initialization(self):
        """
        Test if all core components are initialized after Application instantiation.
        """
        self.mock_config_manager_instance.get_setting.assert_any_call('resolution', [1280, 720])
        self.assertIsNotNone(self.app.config_manager)
        self.assertIsNotNone(self.app.hand_detector)
        self.assertIsNotNone(self.app.layout_generator)
        self.assertIsNotNone(self.app.pitch_bend_processor)
        self.assertIsNotNone(self.app.velocity_intensity_processor)
        self.assertIsNotNone(self.app.audio_engine)
        self.assertIsNotNone(self.app.interaction_manager)
        self.assertIsNotNone(self.app.renderer)
        self.assertIsNone(self.app.cap) # Camera not initialized yet
        self.assertFalse(self.app.running)

    @patch('src.app.cv2.VideoCapture')
    def test_initialize_camera_success(self, MockVideoCapture):
        """
        Test successful camera initialization.
        """
        mock_cap_instance = MockVideoCapture.return_value
        mock_cap_instance.isOpened.return_value = True
        mock_cap_instance.get.side_effect = [1280.0, 720.0] # Mock return for width and height

        self.app.initialize_camera()

        MockVideoCapture.assert_called_once_with(0) # Assuming default camera index 0
        self.assertTrue(mock_cap_instance.isOpened.called)
        mock_cap_instance.set.assert_any_call(3, 1280) # CAP_PROP_FRAME_WIDTH = 3
        mock_cap_instance.set.assert_any_call(4, 720)  # CAP_PROP_FRAME_HEIGHT = 4
        self.assertIsNotNone(self.app.cap)
        self.assertTrue(self.app.running)

    @patch('src.app.cv2.VideoCapture')
    def test_initialize_camera_failure(self, MockVideoCapture):
        """
        Test camera initialization failure.
        """
        mock_cap_instance = MockVideoCapture.return_value
        mock_cap_instance.isOpened.return_value = False

        self.app.initialize_camera()

        MockVideoCapture.assert_called_once_with(0)
        self.assertTrue(mock_cap_instance.isOpened.called)
        self.assertFalse(self.app.running) # Should remain False or be set to False

    @patch('src.app.cv2') # Mock the entire cv2 module used by Application
    def test_shutdown_calls_dependencies(self, MockCv2):
        """
        Test if shutdown calls appropriate methods on its dependencies.
        """
        # Simulate an initialized camera for shutdown
        self.app.cap = MagicMock() 
        
        self.app.shutdown()

        self.app.cap.release.assert_called_once()
        MockCv2.destroyAllWindows.assert_called_once()
        self.mock_audio_engine_instance.shutdown.assert_called_once()
        self.mock_hand_detector_instance.close.assert_called_once()

    @patch('src.app.cv2')
    @patch('src.app.time.time') # Mock time.time for FPS calculation
    def test_run_loop_quits_on_q_key(self, MockTime, MockCv2):
        """
        Test if the main loop exits when 'q' key is pressed.
        This is a simplified test focusing on the exit condition.
        """
        # Mock camera initialization and successful opening
        mock_cap_instance = MagicMock()
        mock_cap_instance.isOpened.return_value = True
        mock_cap_instance.read.return_value = (True, MagicMock()) # Return a mock frame
        self.app.cap = mock_cap_instance # Manually set the cap for this test

        # Mock cv2.waitKey to return 'q' after a few 'other key' presses
        # ord('q') is 113. Any other key, e.g. 32 (space)
        MockCv2.waitKey.side_effect = [32, 32, ord('q')] 
        MockTime.side_effect = [1.0, 2.0, 3.0, 4.0] # Mock time progression for FPS

        # Mock other components within the loop to avoid errors
        self.mock_hand_detector_instance.process_frame.return_value = (MagicMock(), [])
        self.mock_layout_generator_instance.get_zones.return_value = []
        self.mock_renderer_instance.draw_frame.return_value = MagicMock()
        
        # Set app to running state as if initialize_camera was successful
        self.app.running = True 
        
        self.app.run() # This should now use the mocked loop components

        self.assertFalse(self.app.running) # Should be false after 'q' is pressed
        self.assertTrue(MockCv2.waitKey.call_count >= 3) # Ensure waitKey was called enough times
        # Ensure shutdown procedures are called
        self.assertTrue(self.mock_audio_engine_instance.shutdown.called)
        self.assertTrue(self.mock_hand_detector_instance.close.called)


if __name__ == '__main__':
    unittest.main()
