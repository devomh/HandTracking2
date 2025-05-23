import unittest
from unittest.mock import patch, mock_open
import os
import yaml

# Ensure src is discoverable
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):

    def setUp(self):
        """
        Set up for test methods.
        Create a dummy valid config file and a malformed one for testing.
        """
        self.test_config_dir = os.path.join(project_root, "tests", "temp_config_data")
        os.makedirs(self.test_config_dir, exist_ok=True)

        self.valid_config_path = os.path.join(self.test_config_dir, "valid_config.yaml")
        self.valid_config_data = {
            'resolution': [1280, 720],
            'fullscreen': True,
            'audio_mode': 'midi',
            'midi_output_port': "Test MIDI Port",
            'pitch_bend_range': 2.0,
            'starting_note': "C4",
            'num_octaves': 2,
            'preset_scales': [{'name': "Major", 'notes': ["C", "D", "E"]}],
            'parent': {'child': {'key': 'nested_value'}}
        }
        with open(self.valid_config_path, 'w') as f:
            yaml.dump(self.valid_config_data, f)

        self.malformed_config_path = os.path.join(self.test_config_dir, "malformed_config.yaml")
        with open(self.malformed_config_path, 'w') as f:
            f.write("resolution: [1280, 720\n  fullscreen: true") # Malformed YAML

        self.empty_config_path = os.path.join(self.test_config_dir, "empty_config.yaml")
        with open(self.empty_config_path, 'w') as f:
            f.write("") # Empty file
            
        # Path for ConfigManager to use, relative to project root as it expects
        # ConfigManager will construct project_root/tests/temp_config_data/valid_config.yaml
        self.cm_valid_path_arg = os.path.join("tests", "temp_config_data", "valid_config.yaml")
        self.cm_malformed_path_arg = os.path.join("tests", "temp_config_data", "malformed_config.yaml")
        self.cm_empty_path_arg = os.path.join("tests", "temp_config_data", "empty_config.yaml")
        self.cm_non_existent_path_arg = os.path.join("tests", "temp_config_data", "non_existent_config.yaml")


    def tearDown(self):
        """
        Clean up after test methods.
        Remove the dummy config files and directory.
        """
        os.remove(self.valid_config_path)
        os.remove(self.malformed_config_path)
        os.remove(self.empty_config_path)
        os.rmdir(self.test_config_dir)

    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        cm = ConfigManager(config_path=self.cm_valid_path_arg)
        self.assertIsNotNone(cm.config)
        self.assertEqual(cm.get_setting('resolution'), [1280, 720])
        self.assertTrue(cm.get_setting('fullscreen'))
        self.assertEqual(cm.get_setting('parent.child.key'), 'nested_value')

    def test_get_setting_existing_key(self):
        """Test retrieving an existing setting."""
        cm = ConfigManager(config_path=self.cm_valid_path_arg)
        self.assertEqual(cm.get_setting('audio_mode'), 'midi')

    def test_get_setting_non_existent_key_with_default(self):
        """Test retrieving a non-existent key with a default value."""
        cm = ConfigManager(config_path=self.cm_valid_path_arg)
        self.assertEqual(cm.get_setting('unknown_key', 'default_val'), 'default_val')

    def test_get_setting_non_existent_key_no_default(self):
        """Test retrieving a non-existent key without a default value (should return None)."""
        cm = ConfigManager(config_path=self.cm_valid_path_arg)
        self.assertIsNone(cm.get_setting('unknown_key_no_default'))

    def test_get_setting_nested_key(self):
        """Test retrieving a nested key."""
        cm = ConfigManager(config_path=self.cm_valid_path_arg)
        self.assertEqual(cm.get_setting('parent.child.key'), 'nested_value')

    def test_get_setting_invalid_nested_key(self):
        """Test retrieving an invalid nested key."""
        cm = ConfigManager(config_path=self.cm_valid_path_arg)
        self.assertIsNone(cm.get_setting('parent.non_child.key'))
        self.assertEqual(cm.get_setting('parent.non_child.key', 'default_val'), 'default_val')

    def test_load_non_existent_config(self):
        """Test loading a non-existent configuration file."""
        # Suppress print output during this test for cleaner test logs
        with patch('builtins.print') as mock_print:
            cm = ConfigManager(config_path=self.cm_non_existent_path_arg)
            self.assertEqual(cm.config, {}) # Should default to empty dict
            mock_print.assert_any_call(f"Error: Configuration file not found at '{cm.config_path}'.")
        # Test get_setting behavior
        self.assertIsNone(cm.get_setting('any_key'))
        self.assertEqual(cm.get_setting('any_key', 'default'), 'default')


    def test_load_malformed_config(self):
        """Test loading a malformed YAML configuration file."""
        with patch('builtins.print') as mock_print:
            cm = ConfigManager(config_path=self.cm_malformed_path_arg)
            self.assertEqual(cm.config, {}) # Should default to empty dict on parse error
            mock_print.assert_any_call(f"Error: Could not parse configuration file '{cm.config_path}'.")
            # mock_print.assert_any_call(f"YAML Error: ...") # The specific error message might vary

    def test_load_empty_config(self):
        """Test loading an empty YAML configuration file."""
        with patch('builtins.print') as mock_print:
            cm = ConfigManager(config_path=self.cm_empty_path_arg)
            self.assertEqual(cm.config, {}) # Should be empty dict after loading an empty file
            mock_print.assert_any_call(f"Warning: Configuration file '{cm.config_path}' is empty or malformed.")


    @patch('builtins.print') # Suppress validation warnings during test
    def test_validation_logic_called(self, mock_print):
        """Test that validate_config is called during __init__ if config loads."""
        with patch.object(ConfigManager, 'validate_config', wraps=ConfigManager.validate_config) as mock_validate:
            cm = ConfigManager(config_path=self.cm_valid_path_arg)
            self.assertTrue(cm.config) # Ensure config was loaded
            mock_validate.assert_called_once()

    @patch('builtins.print')
    def test_validation_not_called_if_no_config(self, mock_print):
        """Test that validate_config is NOT called from __init__ if config loading fails and self.config is empty."""
        with patch.object(ConfigManager, 'validate_config') as mock_validate:
            # For this test to be meaningful, load_config must result in self.config being falsy (e.g. empty dict)
            # and ConfigManager.__init__ must check `if self.config:` before calling self.validate_config()
            cm = ConfigManager(config_path=self.cm_non_existent_path_arg) # This sets self.config to {}
            self.assertEqual(cm.config, {}) 
            # The current ConfigManager.__init__ structure is:
            # self.load_config()
            # if self.config: self.validate_config()
            # So, if self.config is {}, validate_config should not be called.
            mock_validate.assert_not_called()


    # Example of testing a specific validation rule (e.g., resolution)
    @patch('builtins.print') # Suppress print warnings
    def test_validate_invalid_resolution(self, mock_print_validate):
        invalid_res_data = self.valid_config_data.copy()
        invalid_res_data['resolution'] = [1280, -720] # Invalid height
        
        # Create a temporary config file with invalid resolution
        invalid_res_config_path = os.path.join(self.test_config_dir, "invalid_res_config.yaml")
        with open(invalid_res_config_path, 'w') as f:
            yaml.dump(invalid_res_data, f)
        
        cm_invalid_res_path_arg = os.path.join("tests", "temp_config_data", "invalid_res_config.yaml")
        cm = ConfigManager(config_path=cm_invalid_res_path_arg)
        
        # Check if the specific warning for resolution was printed by validate_config
        found_warning = False
        for call_arg in mock_print_validate.call_args_list:
            if "Warning: 'resolution' should be a list of two positive integers." in call_arg[0][0]:
                found_warning = True
                break
        self.assertTrue(found_warning, "Validation warning for invalid resolution was not printed.")
        
        os.remove(invalid_res_config_path) # Clean up temp file

if __name__ == '__main__':
    unittest.main(verbosity=2)
