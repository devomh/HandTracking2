import unittest
import math

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.utils import math_utils
from src.utils.datatypes import Point

class TestMathUtils(unittest.TestCase):

    def test_map_value(self):
        """Test the map_value function."""
        # Basic mapping
        self.assertAlmostEqual(math_utils.map_value(0.5, 0, 1, 0, 100), 50.0)
        # Mapping with different ranges
        self.assertAlmostEqual(math_utils.map_value(5, 0, 10, 100, 200), 150.0)
        
        # Clamping (value below range)
        self.assertAlmostEqual(math_utils.map_value(-1, 0, 1, 0, 100, clamp_output=True), 0.0)
        self.assertAlmostEqual(math_utils.map_value(-1, 0, 1, 0, 100, clamp_output=False), -100.0)
        
        # Clamping (value above range)
        self.assertAlmostEqual(math_utils.map_value(2, 0, 1, 0, 100, clamp_output=True), 100.0)
        self.assertAlmostEqual(math_utils.map_value(2, 0, 1, 0, 100, clamp_output=False), 200.0)
        
        # Inverted target range with clamping
        self.assertAlmostEqual(math_utils.map_value(0.25, 0, 1, 100, 0, clamp_output=True), 75.0)
        self.assertAlmostEqual(math_utils.map_value(1.5, 0, 1, 100, 0, clamp_output=True), 0.0) # Clamps to min(100,0)
        self.assertAlmostEqual(math_utils.map_value(-0.5, 0, 1, 100, 0, clamp_output=True), 100.0) # Clamps to max(100,0)

        # Inverted target range without clamping
        self.assertAlmostEqual(math_utils.map_value(0.25, 0, 1, 100, 0, clamp_output=False), 75.0)
        self.assertAlmostEqual(math_utils.map_value(1.5, 0, 1, 100, 0, clamp_output=False), -50.0) # 100 + 1.5 * (0-100) = 100 - 150 = -50
        self.assertAlmostEqual(math_utils.map_value(-0.5, 0, 1, 100, 0, clamp_output=False), 150.0) # 100 + (-0.5) * (0-100) = 100 + 50 = 150

        # Collapsed input range (from_low == from_high)
        self.assertAlmostEqual(math_utils.map_value(0.5, 0, 0, 0, 100, clamp_output=True), 0.0) # Returns to_low
        self.assertAlmostEqual(math_utils.map_value(0.5, 1, 1, 50, 150, clamp_output=True), 50.0) # Returns to_low
        self.assertAlmostEqual(math_utils.map_value(0.5, 0, 0, 0, 100, clamp_output=False), 0.0) 
        
        # Collapsed input range, to_low > to_high, with clamping
        self.assertAlmostEqual(math_utils.map_value(0.5, 0, 0, 100, 0, clamp_output=True), 0.0) # Returns to_low (100), then clamps to min(100,0)=0


    def test_lerp(self):
        """Test the lerp function."""
        self.assertAlmostEqual(math_utils.lerp(0, 10, 0.5), 5.0)
        self.assertAlmostEqual(math_utils.lerp(10, 20, 0), 10.0)
        self.assertAlmostEqual(math_utils.lerp(10, 20, 1), 20.0)
        self.assertAlmostEqual(math_utils.lerp(10, 0, 0.2), 8.0)
        self.assertAlmostEqual(math_utils.lerp(0, 10, -0.5), -5.0) # Extrapolation
        self.assertAlmostEqual(math_utils.lerp(0, 10, 1.5), 15.0)  # Extrapolation

    def test_distance(self):
        """Test the distance function."""
        pA = Point(0, 0)
        pB = Point(3, 4)
        pC = Point(-1, -1)
        pD = Point(10, 0)

        self.assertAlmostEqual(math_utils.distance(pA, pB), 5.0)
        self.assertAlmostEqual(math_utils.distance(pA, pA), 0.0)
        self.assertAlmostEqual(math_utils.distance(pA, pC), math.sqrt(2))
        self.assertAlmostEqual(math_utils.distance(pB, pD), math.sqrt((10-3)**2 + (0-4)**2)) # sqrt(7^2 + (-4)^2) = sqrt(49+16) = sqrt(65)

    def test_clamp(self):
        """Test the clamp function."""
        self.assertEqual(math_utils.clamp(5, 0, 10), 5)
        self.assertEqual(math_utils.clamp(-5, 0, 10), 0)
        self.assertEqual(math_utils.clamp(15, 0, 10), 10)
        self.assertEqual(math_utils.clamp(0, 0, 10), 0)   # Value equals min_val
        self.assertEqual(math_utils.clamp(10, 0, 10), 10) # Value equals max_val
        
        # Test with float values
        self.assertAlmostEqual(math_utils.clamp(5.5, 0.0, 10.0), 5.5)
        self.assertAlmostEqual(math_utils.clamp(-1.0, 0.0, 10.0), 0.0)
        
        with self.assertRaisesRegex(ValueError, "min_val cannot be greater than max_val in clamp function."):
            math_utils.clamp(5, 10, 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
```
