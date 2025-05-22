import math
from .datatypes import Point # Assuming Point is defined in a local datatypes.py

def map_value(value: float, 
              from_low: float, from_high: float, 
              to_low: float, to_high: float, 
              clamp_output: bool = True) -> float:
    """
    Linearly maps a value from one range to another.

    Args:
        value: The input value to map.
        from_low: The lower bound of the input range.
        from_high: The upper bound of the input range.
        to_low: The lower bound of the output range.
        to_high: The upper bound of the output range.
        clamp_output: If True, the result is clamped to be within the target range
                      [min(to_low, to_high), max(to_low, to_high)].

    Returns:
        The mapped value.
    """
    # Avoid division by zero if from_low == from_high
    if from_low == from_high:
        # Options:
        # 1. Return the average of the target range if that makes sense.
        # 2. Return to_low or to_high.
        # 3. Raise an error.
        # Let's return to_low as a defined behavior for a "collapsed" input range.
        # If clamping, this will ensure it's within the target range.
        mapped_value = to_low 
    else:
        # Calculate the percentage of value in the from_range
        percentage = (value - from_low) / (from_high - from_low)
        # Apply that percentage to the to_range
        mapped_value = to_low + percentage * (to_high - to_low)

    if clamp_output:
        # Ensure correct clamping regardless of whether to_low < to_high or to_high < to_low
        min_target = min(to_low, to_high)
        max_target = max(to_low, to_high)
        # Clamp the mapped_value
        if mapped_value < min_target:
            mapped_value = min_target
        elif mapped_value > max_target:
            mapped_value = max_target
        
    return mapped_value


def lerp(a: float, b: float, t: float) -> float:
    """
    Performs linear interpolation between two values a and b.

    Args:
        a: The start value.
        b: The end value.
        t: The interpolation factor (typically between 0.0 and 1.0).
           If t=0, result is a. If t=1, result is b.
           Values of t outside [0,1] will extrapolate.

    Returns:
        The interpolated value.
    """
    return a + t * (b - a)


def distance(p1: Point, p2: Point) -> float:
    """
    Calculates the Euclidean distance between two 2D points.

    Args:
        p1: The first Point object.
        p2: The second Point object.

    Returns:
        The Euclidean distance.
    """
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamps a value to be within the range [min_val, max_val].

    Args:
        value: The value to clamp.
        min_val: The minimum allowed value.
        max_val: The maximum allowed value.

    Returns:
        The clamped value.
    """
    if min_val > max_val:
        # Or swap them: min_val, max_val = max_val, min_val
        raise ValueError("min_val cannot be greater than max_val in clamp function.")
    return max(min_val, min(value, max_val))


if __name__ == '__main__':
    print("--- Testing math_utils ---")

    # Test map_value
    print("\nTesting map_value:")
    # Basic mapping
    assert map_value(0.5, 0, 1, 0, 100) == 50.0, "Test 1 Failed"
    print(f"map_value(0.5, 0, 1, 0, 100) -> Expected 50.0, Got: {map_value(0.5, 0, 1, 0, 100)}")
    # Mapping with different ranges
    assert map_value(5, 0, 10, 100, 200) == 150.0, "Test 2 Failed"
    print(f"map_value(5, 0, 10, 100, 200) -> Expected 150.0, Got: {map_value(5, 0, 10, 100, 200)}")
    # Clamping (value below range)
    assert map_value(-1, 0, 1, 0, 100, clamp_output=True) == 0.0, "Test 3a Failed"
    print(f"map_value(-1, 0, 1, 0, 100, clamp_output=True) -> Expected 0.0, Got: {map_value(-1, 0, 1, 0, 100, True)}")
    assert map_value(-1, 0, 1, 0, 100, clamp_output=False) == -100.0, "Test 3b Failed"
    print(f"map_value(-1, 0, 1, 0, 100, clamp_output=False) -> Expected -100.0, Got: {map_value(-1, 0, 1, 0, 100, False)}")
    # Clamping (value above range)
    assert map_value(2, 0, 1, 0, 100, clamp_output=True) == 100.0, "Test 4 Failed"
    print(f"map_value(2, 0, 1, 0, 100, clamp_output=True) -> Expected 100.0, Got: {map_value(2, 0, 1, 0, 100, True)}")
    # Inverted target range with clamping
    assert map_value(0.25, 0, 1, 100, 0, clamp_output=True) == 75.0, "Test 5a Failed"
    print(f"map_value(0.25, 0, 1, 100, 0, clamp_output=True) -> Expected 75.0, Got: {map_value(0.25, 0, 1, 100, 0, True)}")
    # Inverted target range, value outside, with clamping
    assert map_value(1.5, 0, 1, 100, 0, clamp_output=True) == 0.0, "Test 5b Failed" # Should clamp to min(100,0) = 0
    print(f"map_value(1.5, 0, 1, 100, 0, clamp_output=True) -> Expected 0.0, Got: {map_value(1.5, 0, 1, 100, 0, True)}")
    assert map_value(-0.5, 0, 1, 100, 0, clamp_output=True) == 100.0, "Test 5c Failed" # Should clamp to max(100,0) = 100
    print(f"map_value(-0.5, 0, 1, 100, 0, clamp_output=True) -> Expected 100.0, Got: {map_value(-0.5, 0, 1, 100, 0, True)}")
    # Collapsed input range
    assert map_value(0.5, 0, 0, 0, 100, clamp_output=True) == 0.0, "Test 6a Failed"
    print(f"map_value(0.5, 0, 0, 0, 100, clamp_output=True) -> Expected 0.0, Got: {map_value(0.5, 0, 0, 0, 100, True)}")
    assert map_value(0.5, 1, 1, 50, 150, clamp_output=True) == 50.0, "Test 6b Failed"
    print(f"map_value(0.5, 1, 1, 50, 150, clamp_output=True) -> Expected 50.0, Got: {map_value(0.5, 1, 1, 50, 150, True)}")


    # Test lerp
    print("\nTesting lerp:")
    assert lerp(0, 10, 0.5) == 5.0, "Test 7 Failed"
    print(f"lerp(0, 10, 0.5) -> Expected 5.0, Got: {lerp(0, 10, 0.5)}")
    assert lerp(10, 20, 0) == 10.0, "Test 8 Failed"
    print(f"lerp(10, 20, 0) -> Expected 10.0, Got: {lerp(10, 20, 0)}")
    assert lerp(10, 20, 1) == 20.0, "Test 9 Failed"
    print(f"lerp(10, 20, 1) -> Expected 20.0, Got: {lerp(10, 20, 1)}")
    assert lerp(10, 0, 0.2) == 8.0, "Test 10 Failed"
    print(f"lerp(10, 0, 0.2) -> Expected 8.0, Got: {lerp(10, 0, 0.2)}")

    # Test distance
    print("\nTesting distance:")
    pA = Point(0, 0)
    pB = Point(3, 4)
    pC = Point(-1, -1)
    assert distance(pA, pB) == 5.0, "Test 11 Failed"
    print(f"distance(Point(0,0), Point(3,4)) -> Expected 5.0, Got: {distance(pA, pB)}")
    assert distance(pA, pA) == 0.0, "Test 12 Failed"
    print(f"distance(Point(0,0), Point(0,0)) -> Expected 0.0, Got: {distance(pA, pA)}")
    assert math.isclose(distance(pA, pC), math.sqrt(2)), "Test 13 Failed"
    print(f"distance(Point(0,0), Point(-1,-1)) -> Expected {math.sqrt(2):.4f}, Got: {distance(pA, pC):.4f}")

    # Test clamp
    print("\nTesting clamp:")
    assert clamp(5, 0, 10) == 5, "Test 14 Failed"
    print(f"clamp(5, 0, 10) -> Expected 5, Got: {clamp(5, 0, 10)}")
    assert clamp(-5, 0, 10) == 0, "Test 15 Failed"
    print(f"clamp(-5, 0, 10) -> Expected 0, Got: {clamp(-5, 0, 10)}")
    assert clamp(15, 0, 10) == 10, "Test 16 Failed"
    print(f"clamp(15, 0, 10) -> Expected 10, Got: {clamp(15, 0, 10)}")
    raised_error = False
    try:
        clamp(5, 10, 0)
    except ValueError:
        raised_error = True
    assert raised_error, "Test 17 Failed (ValueError not raised)"
    print(f"clamp(5, 10, 0) -> Correctly raised ValueError.")

    print("\n--- math_utils tests complete ---")
```
