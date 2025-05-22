class NoteZone:
    """
    Represents a clickable area on the screen that corresponds to a musical note.
    """
    def __init__(self, x, y, width, height, note_name, note_midi_value, label=None):
        """
        Initializes a NoteZone.

        Args:
            x (int): The x-coordinate of the top-left corner of the zone.
            y (int): The y-coordinate of the top-left corner of the zone.
            width (int): The width of the zone.
            height (int): The height of the zone.
            note_name (str): The musical note the zone represents (e.g., "C4", "F#5").
            note_midi_value (int): The MIDI number for the note.
            label (str, optional): A display label for the zone. Defaults to note_name.
        """
        self.rect = (x, y, width, height)  # (x, y, width, height)
        self.note_name = note_name
        self.note_midi_value = note_midi_value
        self.label = label if label is not None else note_name
        
        self.is_active = False  # True if a finger is currently activating this zone
        self.active_finger_id = None  # Identifier for the finger in the zone (e.g., (hand_id, finger_tip_id))
        
        # Optional: for visual feedback, can be set by UI or config
        self.base_color = (50, 50, 50) # Default dark grey
        self.highlight_color = (0, 255, 0) # Default green for active
        self.current_color = self.base_color # Color to be used for drawing

    def is_point_inside(self, point_x, point_y):
        """
        Checks if a given point (x, y) is within the zone's boundaries.

        Args:
            point_x (int): The x-coordinate of the point.
            point_y (int): The y-coordinate of the point.

        Returns:
            bool: True if the point is inside the zone, False otherwise.
        """
        zone_x, zone_y, zone_width, zone_height = self.rect
        if (zone_x <= point_x < zone_x + zone_width) and \
           (zone_y <= point_y < zone_y + zone_height):
            return True
        return False

    def activate(self, finger_id):
        """
        Activates the zone, typically when a finger enters it.

        Args:
            finger_id (any): An identifier for the finger activating the zone.
        """
        self.is_active = True
        self.active_finger_id = finger_id
        self.current_color = self.highlight_color
        # print(f"Zone {self.note_name} activated by {finger_id}") # For debugging

    def deactivate(self):
        """
        Deactivates the zone, typically when a finger leaves it.
        """
        self.is_active = False
        self.active_finger_id = None
        self.current_color = self.base_color
        # print(f"Zone {self.note_name} deactivated") # For debugging

    def update_highlight(self, intensity=1.0):
        """
        Optional: Updates the highlight color or style based on expression (e.g., intensity).
        For now, this might just switch between base and a fixed highlight.
        A more advanced version could change the shade of the highlight_color.

        Args:
            intensity (float): A value (e.g., 0.0 to 1.0) representing expression intensity.
        """
        if self.is_active:
            # Example: make highlight brighter or dimmer based on intensity
            # For now, we just ensure it's the highlight color if active.
            r, g, b = self.highlight_color
            # Simple intensity scaling (ensure color components stay 0-255)
            # This is a placeholder; actual color blending might be more complex
            scaled_r = min(255, int(r * intensity))
            scaled_g = min(255, int(g * intensity))
            scaled_b = min(255, int(b * intensity))
            self.current_color = (scaled_r, scaled_g, scaled_b)
        else:
            self.current_color = self.base_color

    def __repr__(self):
        return (f"NoteZone(note='{self.note_name}', midi={self.note_midi_value}, "
                f"rect={self.rect}, active={self.is_active})")

if __name__ == '__main__':
    # Example Usage
    zone1 = NoteZone(x=10, y=10, width=50, height=100, note_name="C4", note_midi_value=60)
    zone2 = NoteZone(x=70, y=10, width=50, height=100, note_name="D4", note_midi_value=62, label="Re")

    print("--- Initial State ---")
    print(zone1)
    print(zone2)

    print("\n--- Testing is_point_inside ---")
    print(f"Point (30, 60) in zone1: {zone1.is_point_inside(30, 60)}") # True
    print(f"Point (5, 50) in zone1: {zone1.is_point_inside(5, 50)}")   # False
    print(f"Point (60, 50) in zone1: {zone1.is_point_inside(60, 50)}")  # False (boundary)

    print("\n--- Testing Activation ---")
    zone1.activate(finger_id=("left_hand", "INDEX_TIP"))
    print(zone1)
    print(f"Zone1 current color: {zone1.current_color}")

    zone1.update_highlight(intensity=0.5) # Example of changing highlight
    print(f"Zone1 color after highlight update (intensity 0.5): {zone1.current_color}")


    zone1.deactivate()
    print(zone1)
    print(f"Zone1 current color after deactivation: {zone1.current_color}")

    print("\n--- Testing Zone with custom label ---")
    print(zone2)
    print(f"Zone2 Label: {zone2.label}")

    # Test boundary conditions for is_point_inside
    print("\n--- Boundary Checks for is_point_inside (zone1: x=10, y=10, w=50, h=100) ---")
    # Top-left corner (inside)
    print(f"Point (10, 10) in zone1: {zone1.is_point_inside(10, 10)}") # True
    # Point just outside top-left
    print(f"Point (9, 10) in zone1: {zone1.is_point_inside(9, 10)}")   # False
    print(f"Point (10, 9) in zone1: {zone1.is_point_inside(10, 9)}")   # False
    # Bottom-right edge (exclusive for x + width, y + height)
    # x goes from 10 to 59. y goes from 10 to 109.
    print(f"Point (59, 109) in zone1: {zone1.is_point_inside(59, 109)}")# True
    print(f"Point (60, 109) in zone1: {zone1.is_point_inside(60, 109)}")# False (x at x+width)
    print(f"Point (59, 110) in zone1: {zone1.is_point_inside(59, 110)}")# False (y at y+height)

```
