import unittest

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.utils.datatypes import Point, Point3D, Rect, FINGER_NAME_TYPE

class TestDataTypes(unittest.TestCase):

    def test_point_creation_and_access(self):
        """Test creating a Point and accessing its attributes."""
        p = Point(x=10.5, y=20.25)
        self.assertEqual(p.x, 10.5)
        self.assertEqual(p.y, 20.25)
        self.assertIsInstance(p.x, float)
        self.assertIsInstance(p.y, float)

    def test_point3d_creation_and_access(self):
        """Test creating a Point3D and accessing its attributes."""
        p3d = Point3D(x=5.0, y=15.5, z=25.75)
        self.assertEqual(p3d.x, 5.0)
        self.assertEqual(p3d.y, 15.5)
        self.assertEqual(p3d.z, 25.75)
        self.assertIsInstance(p3d.x, float)
        self.assertIsInstance(p3d.y, float)
        self.assertIsInstance(p3d.z, float)

    def test_rect_creation_and_access(self):
        """Test creating a Rect and accessing its attributes."""
        r = Rect(x=0.0, y=0.0, width=100.0, height=50.5)
        self.assertEqual(r.x, 0.0)
        self.assertEqual(r.y, 0.0)
        self.assertEqual(r.width, 100.0)
        self.assertEqual(r.height, 50.5)
        self.assertIsInstance(r.x, float)
        self.assertIsInstance(r.y, float)
        self.assertIsInstance(r.width, float)
        self.assertIsInstance(r.height, float)

    def test_finger_name_type_literal(self):
        """Test the FINGER_NAME_TYPE Literal definition (conceptual)."""
        # This test is more about ensuring the type alias is defined.
        # Actual enforcement is by static type checkers.
        # We can check that it's a Literal type.
        from typing import Literal
        self.assertEqual(FINGER_NAME_TYPE.__origin__, Literal)
        # Check some expected values
        expected_finger_names = {"THUMB", "INDEX", "MIDDLE", "RING", "PINKY"}
        self.assertEqual(set(FINGER_NAME_TYPE.__args__), expected_finger_names)

if __name__ == '__main__':
    unittest.main(verbosity=2)
```
