import unittest
from unittest.mock import MagicMock

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.expression_control.pitch_bend_processor import PitchBendProcessor
from src.config_manager import ConfigManager # For type hinting and mocking

class TestPitchBendProcessor(unittest.TestCase):

    def _create_mock_config_manager(self, pitch_bend_range_val=1.0):
        mock_cm = MagicMock(spec=ConfigManager)
        mock_cm.get_setting.return_value = pitch_bend_range_val # Only 'pitch_bend_range' is used
        return mock_cm

    def test_initialization(self):
        """Test PitchBendProcessor initialization."""
        mock_cm = self._create_mock_config_manager(pitch_bend_range_val=2.5)
        processor = PitchBendProcessor(config_manager=mock_cm)
        
        mock_cm.get_setting.assert_called_once_with('pitch_bend_range', 1.0)
        self.assertEqual(processor.pitch_bend_range_semitones, 2.5)
        self.assertEqual(processor.midi_bend_max_abs_value, 8191)

    def test_calculate_pitch_bend_center(self):
        """Test pitch bend when finger is at the center of the zone."""
        processor = PitchBendProcessor(config_manager=self._create_mock_config_manager())
        zone_rect = (100, 0, 200, 100) # x, y, width, height
        finger_x = 200 # Center (100 + 200/2)
        self.assertEqual(processor.calculate_pitch_bend(finger_x, zone_rect), 0)

    def test_calculate_pitch_bend_left_edge(self):
        """Test pitch bend when finger is at the left edge."""
        processor = PitchBendProcessor(config_manager=self._create_mock_config_manager())
        zone_rect = (100, 0, 200, 100)
        finger_x = 100 # Left edge
        self.assertEqual(processor.calculate_pitch_bend(finger_x, zone_rect), -8191)

    def test_calculate_pitch_bend_right_edge(self):
        """Test pitch bend when finger is at the right edge."""
        processor = PitchBendProcessor(config_manager=self._create_mock_config_manager())
        zone_rect = (100, 0, 200, 100)
        finger_x = 300 # Right edge (100 + 200)
        self.assertEqual(processor.calculate_pitch_bend(finger_x, zone_rect), 8191)

    def test_calculate_pitch_bend_quarter_positions(self):
        """Test pitch bend at 1/4 and 3/4 positions."""
        processor = PitchBendProcessor(config_manager=self._create_mock_config_manager())
        zone_rect = (100, 0, 200, 100)
        
        # 1/4 position (relative_pos_x = 0.25) -> maps to -8191 * 0.5 = -4095.5 -> -4096
        finger_x_q1 = 150 # 100 + 200 * 0.25
        self.assertEqual(processor.calculate_pitch_bend(finger_x_q1, zone_rect), -4096) # round(-4095.5)
        
        # 3/4 position (relative_pos_x = 0.75) -> maps to 8191 * 0.5 = 4095.5 -> 4096
        finger_x_q3 = 250 # 100 + 200 * 0.75
        self.assertEqual(processor.calculate_pitch_bend(finger_x_q3, zone_rect), 4096) # round(4095.5)

    def test_calculate_pitch_bend_clamping_outside_zone(self):
        """Test pitch bend clamping when finger is outside the zone."""
        processor = PitchBendProcessor(config_manager=self._create_mock_config_manager())
        zone_rect = (100, 0, 200, 100)
        
        # Finger far left
        finger_x_far_left = 50
        self.assertEqual(processor.calculate_pitch_bend(finger_x_far_left, zone_rect), -8191)
        
        # Finger far right
        finger_x_far_right = 350
        self.assertEqual(processor.calculate_pitch_bend(finger_x_far_right, zone_rect), 8191)

    def test_calculate_pitch_bend_zero_width_zone(self):
        """Test pitch bend calculation with a zero-width zone."""
        processor = PitchBendProcessor(config_manager=self._create_mock_config_manager())
        zone_rect = (100, 0, 0, 100) # Zero width
        finger_x = 100
        self.assertEqual(processor.calculate_pitch_bend(finger_x, zone_rect), 0)

    def test_calculate_pitch_bend_precision(self):
        """Test pitch bend calculation for precise intermediate values."""
        processor = PitchBendProcessor(config_manager=self._create_mock_config_manager())
        zone_rect = (100, 0, 200, 100) # width 200
        
        # relative_pos_x = (125 - 100) / 200 = 25 / 200 = 0.125
        # map(0.125, 0, 1, -8191, 8191) = -8191 + 0.125 * (8191 - (-8191))
        # = -8191 + 0.125 * 16382 = -8191 + 2047.75 = -6143.25 -> round to -6143
        finger_x_precise = 125.0
        expected_bend = -6143 
        self.assertEqual(processor.calculate_pitch_bend(finger_x_precise, zone_rect), expected_bend)

        # relative_pos_x = (280 - 100) / 200 = 180 / 200 = 0.9
        # map(0.9, 0, 1, -8191, 8191) = -8191 + 0.9 * 16382
        # = -8191 + 14743.8 = 6552.8 -> round to 6553
        finger_x_precise_2 = 280.0
        expected_bend_2 = 6553
        self.assertEqual(processor.calculate_pitch_bend(finger_x_precise_2, zone_rect), expected_bend_2)


    def test_map_value_helper(self):
        """Test the internal _map_value helper if necessary, though it's implicitly tested."""
        processor = PitchBendProcessor(config_manager=self._create_mock_config_manager())
        # map_value(value, from_low, from_high, to_low, to_high)
        self.assertAlmostEqual(processor._map_value(0.5, 0, 1, 0, 100), 50.0)
        self.assertAlmostEqual(processor._map_value(0, 0, 1, -10, 10), -10.0)
        self.assertAlmostEqual(processor._map_value(1, 0, 1, -10, 10), 10.0)
        self.assertAlmostEqual(processor._map_value(0.25, 0, 1, -8191, 8191), -4095.5)
        # Test collapsed input range
        self.assertAlmostEqual(processor._map_value(0.5, 0, 0, 0, 100), 0) # Returns to_low


if __name__ == '__main__':
    unittest.main(verbosity=2)
