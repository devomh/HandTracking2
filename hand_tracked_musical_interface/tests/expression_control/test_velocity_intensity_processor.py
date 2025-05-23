import unittest
from unittest.mock import MagicMock

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.expression_control.velocity_intensity_processor import VelocityIntensityProcessor
from src.config_manager import ConfigManager # For type hinting and mocking

class TestVelocityIntensityProcessor(unittest.TestCase):

    def setUp(self):
        """Setup for test methods."""
        # This processor doesn't currently use any specific settings from ConfigManager,
        # but it expects an instance.
        mock_cm = MagicMock(spec=ConfigManager)
        self.processor = VelocityIntensityProcessor(config_manager=mock_cm)
        
        # Standard zone for testing: (x=50, y=100, width=100, height=200)
        # Zone top_y = 100, bottom_y = 300 (100+200)
        self.zone_rect = (50, 100, 100, 200)

    def test_initialization(self):
        """Test processor initialization."""
        self.assertIsNotNone(self.processor.config_manager)
        self.assertEqual(self.processor.midi_min_value, 0)
        self.assertEqual(self.processor.midi_max_value, 127)

    # Test cases for calculate_initial_velocity
    def test_velocity_at_top_edge(self):
        """Velocity should be min (0) at the top edge of the zone."""
        finger_y = self.zone_rect[1] # y = 100
        expected_velocity = 0 # Softer
        self.assertEqual(self.processor.calculate_initial_velocity(finger_y, self.zone_rect), expected_velocity)

    def test_velocity_at_bottom_edge(self):
        """Velocity should be max (127) at the bottom edge of the zone."""
        finger_y = self.zone_rect[1] + self.zone_rect[3] # y = 100 + 200 = 300
        expected_velocity = 127 # Louder
        self.assertEqual(self.processor.calculate_initial_velocity(finger_y, self.zone_rect), expected_velocity)

    def test_velocity_at_center(self):
        """Velocity at center should be around 63-64."""
        finger_y = self.zone_rect[1] + self.zone_rect[3] / 2 # y = 100 + 100 = 200
        # relative_y = (200-100)/200 = 0.5. map(0.5, 0,1, 0,127) = 63.5 -> round(63.5) = 64
        expected_velocity = 64
        self.assertEqual(self.processor.calculate_initial_velocity(finger_y, self.zone_rect), expected_velocity)

    def test_velocity_at_quarter_down(self):
        """Test velocity at 1/4 position from the top."""
        finger_y = self.zone_rect[1] + self.zone_rect[3] * 0.25 # y = 100 + 50 = 150
        # relative_y = (150-100)/200 = 0.25. map(0.25, 0,1, 0,127) = 31.75 -> round(31.75) = 32
        expected_velocity = 32
        self.assertEqual(self.processor.calculate_initial_velocity(finger_y, self.zone_rect), expected_velocity)

    def test_velocity_at_three_quarters_down(self):
        """Test velocity at 3/4 position from the top."""
        finger_y = self.zone_rect[1] + self.zone_rect[3] * 0.75 # y = 100 + 150 = 250
        # relative_y = (250-100)/200 = 0.75. map(0.75, 0,1, 0,127) = 95.25 -> round(95.25) = 95
        expected_velocity = 95
        self.assertEqual(self.processor.calculate_initial_velocity(finger_y, self.zone_rect), expected_velocity)

    def test_velocity_clamping_above_zone(self):
        """Velocity should be clamped to min (0) if finger is above the zone."""
        finger_y = self.zone_rect[1] - 50 # y = 50 (above top edge 100)
        expected_velocity = 0
        self.assertEqual(self.processor.calculate_initial_velocity(finger_y, self.zone_rect), expected_velocity)

    def test_velocity_clamping_below_zone(self):
        """Velocity should be clamped to max (127) if finger is below the zone."""
        finger_y = self.zone_rect[1] + self.zone_rect[3] + 50 # y = 350 (below bottom edge 300)
        expected_velocity = 127
        self.assertEqual(self.processor.calculate_initial_velocity(finger_y, self.zone_rect), expected_velocity)

    def test_velocity_zero_height_zone(self):
        """Velocity should be min_value (0) for a zero-height zone."""
        zero_height_zone = (50, 100, 100, 0)
        finger_y = 100
        self.assertEqual(self.processor.calculate_initial_velocity(finger_y, zero_height_zone), 0)

    # Test cases for calculate_continuous_intensity (logic is identical to velocity)
    def test_intensity_at_top_edge(self):
        finger_y = self.zone_rect[1]
        self.assertEqual(self.processor.calculate_continuous_intensity(finger_y, self.zone_rect), 0)

    def test_intensity_at_bottom_edge(self):
        finger_y = self.zone_rect[1] + self.zone_rect[3]
        self.assertEqual(self.processor.calculate_continuous_intensity(finger_y, self.zone_rect), 127)

    def test_intensity_at_center(self):
        finger_y = self.zone_rect[1] + self.zone_rect[3] / 2
        self.assertEqual(self.processor.calculate_continuous_intensity(finger_y, self.zone_rect), 64)

    def test_intensity_clamping_outside_zone(self):
        finger_y_above = self.zone_rect[1] - 20
        finger_y_below = self.zone_rect[1] + self.zone_rect[3] + 20
        self.assertEqual(self.processor.calculate_continuous_intensity(finger_y_above, self.zone_rect), 0)
        self.assertEqual(self.processor.calculate_continuous_intensity(finger_y_below, self.zone_rect), 127)

    def test_intensity_zero_height_zone(self):
        zero_height_zone = (50, 100, 100, 0)
        self.assertEqual(self.processor.calculate_continuous_intensity(100, zero_height_zone), 0)

    def test_map_value_helper_internal(self):
        """Test the _map_value helper for completeness, though implicitly tested."""
        # map_value(value, from_low, from_high, to_low, to_high)
        # Standard mapping
        self.assertEqual(self.processor._map_value(0.5, 0, 1, 0, 100), 50)
        # Clamping
        self.assertEqual(self.processor._map_value(1.5, 0, 1, 0, 100), 100) # Upper clamp
        self.assertEqual(self.processor._map_value(-0.5, 0, 1, 0, 100), 0)   # Lower clamp
        # Inverted target range
        self.assertEqual(self.processor._map_value(0.25, 0, 1, 100, 0), 75)
        # Inverted target range with clamping
        self.assertEqual(self.processor._map_value(1.5, 0, 1, 100, 0), 0)    # Clamp to min(100,0)
        self.assertEqual(self.processor._map_value(-0.5, 0, 1, 100, 0), 100)  # Clamp to max(100,0)
        # Collapsed input range
        self.assertEqual(self.processor._map_value(0.5, 0, 0, 0, 100), 0) # Returns to_low
        self.assertEqual(self.processor._map_value(0.5, 0, 0, 100, 0), 100) # Returns to_low (which is 100 here)


if __name__ == '__main__':
    unittest.main(verbosity=2)
```
