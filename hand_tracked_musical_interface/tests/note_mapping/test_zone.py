import unittest

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.note_mapping.zone import NoteZone

class TestNoteZone(unittest.TestCase):

    def setUp(self):
        """Set up a default NoteZone instance for use in tests."""
        self.zone1 = NoteZone(x=10, y=20, width=50, height=100, 
                              note_name="C4", note_midi_value=60)
        self.zone_custom_label = NoteZone(x=70, y=20, width=50, height=100, 
                                          note_name="D4", note_midi_value=62, label="Re")

    def test_initialization_default_label(self):
        """Test NoteZone initialization with default label."""
        self.assertEqual(self.zone1.rect, (10, 20, 50, 100))
        self.assertEqual(self.zone1.note_name, "C4")
        self.assertEqual(self.zone1.note_midi_value, 60)
        self.assertEqual(self.zone1.label, "C4") # Default label is note_name
        self.assertFalse(self.zone1.is_active)
        self.assertIsNone(self.zone1.active_finger_id)
        self.assertEqual(self.zone1.current_color, self.zone1.base_color)

    def test_initialization_custom_label(self):
        """Test NoteZone initialization with a custom label."""
        self.assertEqual(self.zone_custom_label.label, "Re")

    def test_is_point_inside_true(self):
        """Test is_point_inside for a point that is inside."""
        self.assertTrue(self.zone1.is_point_inside(point_x=30, point_y=70)) # Center
        self.assertTrue(self.zone1.is_point_inside(point_x=10, point_y=20)) # Top-left corner

    def test_is_point_inside_false(self):
        """Test is_point_inside for points outside."""
        self.assertFalse(self.zone1.is_point_inside(point_x=5, point_y=70))  # Left
        self.assertFalse(self.zone1.is_point_inside(point_x=60, point_y=70)) # Right (x=10+50=60, exclusive)
        self.assertFalse(self.zone1.is_point_inside(point_x=30, point_y=15)) # Above
        self.assertFalse(self.zone1.is_point_inside(point_x=30, point_y=120))# Below (y=20+100=120, exclusive)

    def test_is_point_inside_boundary_conditions(self):
        """Test is_point_inside for points on the boundary."""
        # Points on the edge (inclusive for x, y; exclusive for x+width, y+height)
        self.assertTrue(self.zone1.is_point_inside(10, 20))      # Top-left corner
        self.assertTrue(self.zone1.is_point_inside(59, 20))      # Top-right x (10+50-1)
        self.assertTrue(self.zone1.is_point_inside(10, 119))     # Bottom-left y (20+100-1)
        self.assertTrue(self.zone1.is_point_inside(59, 119))     # Bottom-right corner (inner)

        self.assertFalse(self.zone1.is_point_inside(60, 119))    # x = zone_x + zone_width
        self.assertFalse(self.zone1.is_point_inside(59, 120))    # y = zone_y + zone_height

    def test_activate_zone(self):
        """Test activating a zone."""
        finger_id = ("right_hand", "INDEX_TIP")
        self.zone1.activate(finger_id)
        self.assertTrue(self.zone1.is_active)
        self.assertEqual(self.zone1.active_finger_id, finger_id)
        self.assertEqual(self.zone1.current_color, self.zone1.highlight_color)

    def test_deactivate_zone(self):
        """Test deactivating an active zone."""
        self.zone1.activate(("test_finger", 1)) # Activate first
        self.zone1.deactivate()
        self.assertFalse(self.zone1.is_active)
        self.assertIsNone(self.zone1.active_finger_id)
        self.assertEqual(self.zone1.current_color, self.zone1.base_color)

    def test_update_highlight_when_active(self):
        """Test update_highlight changes color when active."""
        self.zone1.activate(("test_finger", 1))
        original_highlight = self.zone1.highlight_color
        
        self.zone1.update_highlight(intensity=0.5)
        # Expect color to be a scaled version of highlight_color
        r, g, b = original_highlight
        expected_color = (min(255, int(r * 0.5)), 
                          min(255, int(g * 0.5)), 
                          min(255, int(b * 0.5)))
        self.assertEqual(self.zone1.current_color, expected_color)

    def test_update_highlight_when_inactive(self):
        """Test update_highlight does not change color from base when inactive."""
        self.assertFalse(self.zone1.is_active) # Ensure inactive
        base_c = self.zone1.base_color
        self.zone1.update_highlight(intensity=0.5)
        self.assertEqual(self.zone1.current_color, base_c)

    def test_representation_string(self):
        """Test the __repr__ string."""
        expected_repr = "NoteZone(note='C4', midi=60, rect=(10, 20, 50, 100), active=False)"
        self.assertEqual(repr(self.zone1), expected_repr)
        
        self.zone1.activate("fingerX")
        expected_repr_active = "NoteZone(note='C4', midi=60, rect=(10, 20, 50, 100), active=True)"
        self.assertEqual(repr(self.zone1), expected_repr_active)


if __name__ == '__main__':
    unittest.main(verbosity=2)
