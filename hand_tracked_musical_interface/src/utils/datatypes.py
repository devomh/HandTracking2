from typing import NamedTuple, Literal

class Point(NamedTuple):
    """Represents a 2D point with x and y coordinates."""
    x: float
    y: float

class Point3D(NamedTuple):
    """Represents a 3D point with x, y, and z coordinates."""
    x: float
    y: float
    z: float

class Rect(NamedTuple):
    """Represents a rectangle with x, y, width, and height."""
    x: float
    y: float
    width: float
    height: float

# Example of how a Literal type for finger names could be defined for type hinting,
# though not strictly enforced as a data structure itself without further integration.
FINGER_NAME_TYPE = Literal["THUMB", "INDEX", "MIDDLE", "RING", "PINKY"]

# Example of an Enum for finger states, if a more structured type is preferred over strings.
# from enum import Enum
# class FingerState(Enum):
#     RETRACTED = "retracted"
#     EXTENDED = "extended"
#     UNKNOWN = "unknown"

# Note: The project currently uses strings for finger states and names in many places.
# Introducing these more structured types would require refactoring in other modules
# (e.g., HandDetector, InteractionManager) to use them consistently.
# For now, Point, Point3D, and Rect are the primary generic datatypes being introduced.

if __name__ == '__main__':
    # Example Usage
    p1 = Point(10, 20)
    p2 = Point3D(5, 15, 25)
    rect1 = Rect(0, 0, 100, 50)

    print(f"Point: {p1}, x={p1.x}, y={p1.y}")
    print(f"Point3D: {p2}, x={p2.x}, y={p2.y}, z={p2.z}")
    print(f"Rect: {rect1}, x={rect1.x}, width={rect1.width}")

    # Example of using the Literal type hint (for type checkers)
    def get_finger_tip_id(finger_name: FINGER_NAME_TYPE) -> int:
        mapping = {"THUMB": 4, "INDEX": 8, "MIDDLE": 12, "RING": 16, "PINKY": 20}
        return mapping.get(finger_name, -1)

    print(f"Index finger tip ID: {get_finger_tip_id('INDEX')}")
    # print(f"Invalid finger tip ID: {get_finger_tip_id('WRIST')}") # Type checker would warn
```
