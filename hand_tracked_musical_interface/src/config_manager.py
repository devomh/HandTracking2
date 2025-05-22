import yaml
import os

class ConfigManager:
    """
    Manages loading and accessing configuration settings from a YAML file.
    """
    def __init__(self, config_path="config/config.yaml"):
        """
        Initializes the ConfigManager.

        Args:
            config_path (str, optional): The path to the configuration file.
                                         Defaults to "config/config.yaml" relative
                                         to the project's 'hand_tracked_musical_interface'
                                         directory.
        """
        # Construct the full path relative to this file's location
        # Assuming this script is in hand_tracked_musical_interface/src/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(base_dir, config_path)
        self.config = None
        self.load_config()
        if self.config: # Only validate if loading was successful
            self.validate_config()

    def load_config(self):
        """
        Loads the configuration from the YAML file.

        Handles FileNotFoundError and YAMLError, printing informative messages.
        """
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            if self.config is None: # Handle empty or invalid YAML content
                print(f"Warning: Configuration file '{self.config_path}' is empty or malformed.")
                self.config = {} # Set to empty dict to avoid errors in get_setting
        except FileNotFoundError:
            print(f"Error: Configuration file not found at '{self.config_path}'.")
            self.config = {} # Set to empty dict
        except yaml.YAMLError as e:
            print(f"Error: Could not parse configuration file '{self.config_path}'.")
            print(f"YAML Error: {e}")
            self.config = {} # Set to empty dict

    def get_setting(self, key, default=None):
        """
        Retrieves a configuration setting by its key.

        Args:
            key (str): The key of the setting to retrieve.
                       Supports dot notation for nested keys (e.g., "parent.child.key").
            default (any, optional): The default value to return if the key is not found.
                                     Defaults to None.

        Returns:
            any: The value of the setting, or the default value if not found.
        """
        if not self.config:
            return default

        # Handle nested keys
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else: # Path is invalid if an intermediate value is not a dict
                    return default
            return value
        except (KeyError, TypeError): # TypeError for trying to index a non-dict/list
            return default

    def validate_config(self):
        """
        Performs basic validation for critical configuration settings.
        Prints warnings for invalid settings.
        """
        if not self.config:
            print("Warning: No configuration loaded, skipping validation.")
            return

        # Resolution
        resolution = self.get_setting('resolution')
        if not (isinstance(resolution, list) and len(resolution) == 2 and
                isinstance(resolution[0], int) and resolution[0] > 0 and
                isinstance(resolution[1], int) and resolution[1] > 0):
            print(f"Warning: 'resolution' should be a list of two positive integers. Found: {resolution}")

        # Audio Mode
        audio_mode = self.get_setting('audio_mode')
        valid_audio_modes = ['midi', 'direct', 'both']
        if audio_mode not in valid_audio_modes:
            print(f"Warning: 'audio_mode' should be one of {valid_audio_modes}. Found: {audio_mode}")

        # MIDI Channel Range
        midi_channel_range = self.get_setting('midi_channel_range')
        if not (isinstance(midi_channel_range, list) and len(midi_channel_range) == 2 and
                isinstance(midi_channel_range[0], int) and isinstance(midi_channel_range[1], int) and
                midi_channel_range[1] >= midi_channel_range[0]):
            print(f"Warning: 'midi_channel_range' should be a list of two integers, with the second "
                  f"being greater than or equal to the first. Found: {midi_channel_range}")
        elif midi_channel_range and (midi_channel_range[0] < 1 or midi_channel_range[1] > 16):
             print(f"Warning: 'midi_channel_range' values should typically be between 1 and 16. Found: {midi_channel_range}")


        # Pitch Bend Range
        pitch_bend_range = self.get_setting('pitch_bend_range')
        if not (isinstance(pitch_bend_range, (int, float)) and pitch_bend_range > 0):
            print(f"Warning: 'pitch_bend_range' should be a positive number. Found: {pitch_bend_range}")

        # Starting Note
        starting_note = self.get_setting('starting_note')
        if not isinstance(starting_note, str):
            print(f"Warning: 'starting_note' should be a string. Found: {starting_note}")

        # Num Octaves
        num_octaves = self.get_setting('num_octaves')
        if not (isinstance(num_octaves, int) and num_octaves > 0):
            print(f"Warning: 'num_octaves' should be a positive integer. Found: {num_octaves}")

        # Preset Scales (basic check)
        preset_scales = self.get_setting('preset_scales')
        if not isinstance(preset_scales, list):
            print(f"Warning: 'preset_scales' should be a list. Found: {preset_scales}")
        else:
            for i, scale in enumerate(preset_scales):
                if not isinstance(scale, dict) or 'name' not in scale or 'notes' not in scale:
                    print(f"Warning: Preset scale at index {i} is malformed. Each scale needs 'name' and 'notes'. Found: {scale}")
                elif not isinstance(scale['name'], str) or not isinstance(scale['notes'], list):
                    print(f"Warning: Preset scale '{scale.get('name', 'Unnamed')}' has malformed 'name' (should be string) or 'notes' (should be list).")


if __name__ == "__main__":
    # To run this test, you need to be in the 'hand_tracked_musical_interface' directory
    # or ensure PYTHONPATH is set up so that 'config.config.yaml' can be found.
    # A more robust way is to specify the full path or relative path from this file.

    # Determine the path to config.yaml relative to this script
    # This script is in hand_tracked_musical_interface/src/
    # config.yaml is in hand_tracked_musical_interface/config/
    project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_file_path = os.path.join(project_root_dir, "config/config.yaml")
    
    # Check if the default config file exists, otherwise try the one at the root of the repo for testing
    # This is because the test runner might be in a different working directory
    # For the actual application, config_path will be relative to the project root.
    
    # The ConfigManager now correctly resolves paths from its own location.
    # The default config_path="config/config.yaml" should work if the CWD is hand_tracked_musical_interface/
    # or if this script is run directly from hand_tracked_musical_interface/src/
    
    print(f"Attempting to load configuration from: {config_file_path}")
    # We pass the relative path from the project root as intended for the class.
    # The class itself will join it with its base directory.
    manager = ConfigManager(config_path="config/config.yaml")

    if hasattr(manager, 'config') and manager.config: # Check if config loaded
        print("\n--- ConfigManager Test ---")
        print(f"Audio Mode: {manager.get_setting('audio_mode')}")
        print(f"Resolution: {manager.get_setting('resolution')}")
        print(f"MIDI Output Port: {manager.get_setting('midi_output_port')}")
        print(f"Fullscreen: {manager.get_setting('fullscreen')}")
        print(f"Unknown Setting (with default): {manager.get_setting('non_existent_key', 'default_value')}")
        print(f"Nested setting (preset_scales[0].name): {manager.get_setting('preset_scales.0.name')}") # Example of nested access

        print("\n--- Validating Configuration ---")
        # Validation is now called in __init__, but can be called again if needed.
        # manager.validate_config() # Already called in constructor
        print("Validation (should have occurred during initialization).")

        print("\n--- Testing with a non-existent file ---")
        non_existent_manager = ConfigManager(config_path="config/non_existent_config.yaml")
        print(f"Setting from non-existent config: {non_existent_manager.get_setting('audio_mode', 'default_for_non_existent')}")

        print("\n--- Testing with a malformed YAML file (manual test needed) ---")
        # To test this, manually create a malformed YAML file e.g., 'config/malformed.yaml'
        # malformed_manager = ConfigManager(config_path="config/malformed.yaml")
        # print(f"Setting from malformed config: {malformed_manager.get_setting('audio_mode', 'default_for_malformed')}")

        print("\n--- Test complete ---")
    else:
        print("ConfigManager Test: Failed to load configuration for testing.")
        print(f"Please ensure '{config_file_path}' exists and is valid.")

# Example of a malformed YAML file (save as config/malformed.yaml for testing):
"""
resolution: [1280, 720
fullscreen: true
  bad_indent: problem
audio_mode: midi
"""
