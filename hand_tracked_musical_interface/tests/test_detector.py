import unittest
from unittest.mock import MagicMock, patch
import numpy as np # For creating mock image_shape

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.hand_tracking.detector import HandDetector
from src.config_manager import ConfigManager # For creating a mock config manager

# Mock the MediaPipe HandLandmark class structure for creating mock landmark objects
class MockHandLandmark:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class MockMultiHandLandmarks:
    def __init__(self, landmarks_list_of_lists):
        # landmarks_list_of_lists is a list, where each inner list contains MockHandLandmark objects for one hand
        self.landmark = [MockHandLandmark(lm.x, lm.y, lm.z) for lm in landmarks_list_of_lists]

class MockMediaPipeResults:
    def __init__(self, multi_hand_landmarks_data=None, multi_handedness_data=None):
        if multi_hand_landmarks_data:
            self.multi_hand_landmarks = [MockMultiHandLandmarks(hand_lms) for hand_lms in multi_hand_landmarks_data]
        else:
            self.multi_hand_landmarks = None
        
        if multi_handedness_data:
            self.multi_handedness = []
            for handedness_label in multi_handedness_data:
                mock_classification = MagicMock()
                mock_classification.label = handedness_label
                mock_handedness_item = MagicMock()
                mock_handedness_item.classification = [mock_classification]
                self.multi_handedness.append(mock_handedness_item)
        else:
            self.multi_handedness = None

class TestHandDetector(unittest.TestCase):

    def setUp(self):
        # Mock ConfigManager for HandDetector initialization
        self.mock_cm_data = {
            'hand_detector.static_image_mode': False,
            'hand_detector.max_num_hands': 2,
            'hand_detector.min_detection_confidence': 0.5,
            'hand_detector.min_tracking_confidence': 0.5,
        }
        # This mock ConfigManager is simpler than the one in test_config_manager
        # as we are not testing ConfigManager here, just its usage by HandDetector.
        self.mock_config_manager = MagicMock(spec=ConfigManager)
        def get_setting_side_effect(key, default=None):
            # Special handling for keys that might be split by '.'
            if key not in self.mock_cm_data and '.' in key:
                 # Fallback to direct key if dot-notation specific key not found
                 # (e.g. if 'hand_detector' itself is a dict in a larger config)
                 # This basic mock doesn't handle deep nesting for get_setting itself.
                 pass # Keep it simple, assume direct keys for this mock
            return self.mock_cm_data.get(key, default)
        self.mock_config_manager.get_setting.side_effect = get_setting_side_effect

        # Patch mediapipe.solutions.hands.Hands before HandDetector is instantiated
        self.mock_mp_hands_patcher = patch('mediapipe.solutions.hands.Hands')
        self.mock_mp_hands_class = self.mock_mp_hands_patcher.start()
        self.mock_mp_hands_instance = self.mock_mp_hands_class.return_value
        
        # Mock the process method of the Hands instance
        self.mock_mp_hands_instance.process.return_value = MockMediaPipeResults() # Default: no hands

        self.detector = HandDetector(config_manager=self.mock_config_manager)
        self.image_shape = (480, 640, 3) # Example image shape (height, width, channels)

    def tearDown(self):
        self.mock_mp_hands_patcher.stop()

    def test_initialization_with_config_manager(self):
        self.assertEqual(self.detector.static_image_mode, False)
        self.assertEqual(self.detector.max_num_hands, 2)
        self.assertEqual(self.detector.min_detection_confidence, 0.5)
        self.assertEqual(self.detector.min_tracking_confidence, 0.5)
        self.mock_mp_hands_class.assert_called_once_with(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def test_initialization_direct_params_override_config(self):
        # Reset the mock_mp_hands_class call count for this specific test
        self.mock_mp_hands_class.reset_mock()
        detector_override = HandDetector(
            config_manager=self.mock_config_manager, # Config manager is still passed
            static_image_mode=True,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.assertTrue(detector_override.static_image_mode)
        self.assertEqual(detector_override.max_num_hands, 1)
        self.assertEqual(detector_override.min_detection_confidence, 0.7)
        self.assertEqual(detector_override.min_tracking_confidence, 0.7)
        # Check that mp.solutions.hands.Hands was called with these overridden values
        self.mock_mp_hands_class.assert_called_once_with(
            static_image_mode=True,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )


    def test_get_landmark_positions_no_hands(self):
        self.detector.results = MockMediaPipeResults() # No hands
        positions = self.detector.get_landmark_positions(self.image_shape)
        self.assertEqual(positions, [])

    def test_get_landmark_positions_one_hand(self):
        # Create mock landmark data (normalized)
        mock_lm_list = [MockHandLandmark(x=0.1 * i, y=0.2 * i, z=0.05 * i) for i in range(21)]
        self.detector.results = MockMediaPipeResults(multi_hand_landmarks_data=[mock_lm_list])
        
        positions = self.detector.get_landmark_positions(self.image_shape) # hand_index=0 by default
        self.assertEqual(len(positions), 21)
        # Example check for denormalization (landmark 0)
        # x = 0.1*0 * 640 = 0, y = 0.2*0 * 480 = 0, z = 0.05*0 = 0
        self.assertEqual(positions[0], (0, 0, 0, 0.0))
        # Example check for landmark 1 (denormalized)
        # x = 0.1*1 * 640 = 64, y = 0.2*1 * 480 = 96, z = 0.05*1 = 0.05
        self.assertEqual(positions[1], (1, 64, 96, 0.05))


    def test_get_finger_states_insufficient_landmarks(self):
        landmarks_short = [(i, i*10, i*10, 0) for i in range(5)] # Only 5 landmarks
        states = self.detector.get_finger_states(landmarks_short)
        self.assertIsNone(states)

    def test_get_finger_states_extended_fingers(self):
        # Create a mock landmark list that would result in all fingers being extended
        mock_landmarks_raw = [(0,0,0,0)] * 21 # Placeholder
        
        # Index finger extended (TIP_Y < PIP_Y < MCP_Y)
        mock_landmarks_raw[self.detector.landmark_indices['INDEX_FINGER_MCP']] = (self.detector.landmark_indices['INDEX_FINGER_MCP'], 100, 200, 0)
        mock_landmarks_raw[self.detector.landmark_indices['INDEX_FINGER_PIP']] = (self.detector.landmark_indices['INDEX_FINGER_PIP'], 100, 180, 0)
        mock_landmarks_raw[self.detector.landmark_indices['INDEX_FINGER_DIP']] = (self.detector.landmark_indices['INDEX_FINGER_DIP'], 100, 160, 0)
        mock_landmarks_raw[self.detector.landmark_indices['INDEX_FINGER_TIP']] = (self.detector.landmark_indices['INDEX_FINGER_TIP'], 100, 140, 0)

        # Thumb extended (heuristic: tip further from index_mcp than ip is from index_mcp)
        mock_landmarks_raw[self.detector.landmark_indices['THUMB_TIP']] = (self.detector.landmark_indices['THUMB_TIP'], 50, 150, 0) 
        mock_landmarks_raw[self.detector.landmark_indices['THUMB_IP']]  = (self.detector.landmark_indices['THUMB_IP'], 70, 170, 0) 
        mock_landmarks_raw[self.detector.landmark_indices['THUMB_MCP']] = (self.detector.landmark_indices['THUMB_MCP'], 80, 190, 0)
        mock_landmarks_raw[self.detector.landmark_indices['THUMB_CMC']] = (self.detector.landmark_indices['THUMB_CMC'], 90, 210, 0)
        mock_landmarks_raw[self.detector.landmark_indices['WRIST']] = (self.detector.landmark_indices['WRIST'], 100, 250, 0) # Needed by some heuristics

        # For other fingers, set them to retracted for this specific test (TIP_Y > PIP_Y)
        for finger in ["MIDDLE", "RING", "PINKY"]:
            mcp_idx = self.detector.landmark_indices[f'{finger}_FINGER_MCP']
            pip_idx = self.detector.landmark_indices[f'{finger}_FINGER_PIP']
            tip_idx = self.detector.landmark_indices[f'{finger}_FINGER_TIP']
            mock_landmarks_raw[mcp_idx] = (mcp_idx, 150, 200, 0)
            mock_landmarks_raw[pip_idx] = (pip_idx, 150, 220, 0) 
            mock_landmarks_raw[tip_idx] = (tip_idx, 150, 240, 0) 

        states = self.detector.get_finger_states(mock_landmarks_raw)
        self.assertIsNotNone(states)
        self.assertEqual(states.get('INDEX'), 'extended')
        self.assertEqual(states.get('THUMB'), 'extended') 
        self.assertEqual(states.get('MIDDLE'), 'retracted')


    def test_get_handedness(self):
        self.detector.results = MockMediaPipeResults(multi_handedness_data=["Left", "Right"])
        self.assertEqual(self.detector.get_handedness(0), "Left")
        self.assertEqual(self.detector.get_handedness(1), "Right")
        self.assertEqual(self.detector.get_handedness(2), "Unknown") # Index out of bounds

    def test_calculate_bounding_box(self):
        landmarks = [(0, 10, 20, 0), (1, 30, 5, 0), (2, 15, 40, 0)] # (id, x, y, z)
        # Expected: min_x=10, max_x=30, min_y=5, max_y=40
        # With padding=10: (0, -5, 40, 50)
        bbox = self.detector.calculate_bounding_box(landmarks)
        self.assertEqual(bbox, (0, -5, 40, 50))

    @patch('cv2.cvtColor') # Mock cvtColor to avoid OpenCV dependency in this part
    def test_process_frame_structure(self, mock_cvt_color):
        mock_image = np.zeros(self.image_shape, dtype=np.uint8)
        
        mock_lm_list = [MockHandLandmark(x=0.1 * i, y=0.2 * i, z=0) for i in range(21)]
        mock_results = MockMediaPipeResults(
            multi_hand_landmarks_data=[mock_lm_list],
            multi_handedness_data=["Right"]
        )
        self.mock_mp_hands_instance.process.return_value = mock_results
        
        _processed_img, hands_data = self.detector.process_frame(mock_image, draw_landmarks_on_image=False)
        
        self.assertEqual(len(hands_data), 1)
        hand1_data = hands_data[0]
        
        self.assertIn('landmarks', hand1_data)
        self.assertIn('handedness', hand1_data)
        self.assertIn('finger_states', hand1_data)
        self.assertIn('bounding_box', hand1_data)
        self.assertIn('mp_landmarks', hand1_data)
        
        self.assertEqual(len(hand1_data['landmarks']), 21)
        self.assertEqual(hand1_data['handedness'], "Right")
        self.assertIsInstance(hand1_data['finger_states'], dict)
        self.assertIsInstance(hand1_data['bounding_box'], tuple)
        self.assertTrue(hasattr(hand1_data['mp_landmarks'], 'landmark'))


    def test_close_method(self):
        self.detector.close()
        self.mock_mp_hands_instance.close.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
