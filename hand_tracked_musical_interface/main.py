import sys
import os

# This is to ensure that the 'src' directory is in the Python path
# when main.py is executed from the 'hand_tracked_musical_interface' directory.
# It allows imports like `from src.app import Application`.
# If main.py is moved or the project structure changes, this might need adjustment.
current_dir = os.path.dirname(os.path.abspath(__file__))
# If main.py is inside hand_tracked_musical_interface, then current_dir is .../hand_tracked_musical_interface
# We don't need to add src to sys.path if we use `from src.app import Application`
# and run python -m hand_tracked_musical_interface.main from the parent directory of hand_tracked_musical_interface
# OR if we run python main.py from within hand_tracked_musical_interface/ and the Python interpreter
# automatically adds the script's directory to sys.path (which it usually does).

# Let's assume standard execution: `python main.py` from within the `hand_tracked_musical_interface` directory.
# In this case, Python adds `hand_tracked_musical_interface/` to `sys.path`.
# So, `from src.app import Application` should work directly.

try:
    from src.app import Application
except ImportError as e:
    print("Error importing Application. Ensure main.py is run from the 'hand_tracked_musical_interface' directory,")
    print("or that the 'src' directory is correctly in your PYTHONPATH.")
    print(f"Original error: {e}")
    # Attempt to add 'src' to path if running from project root.
    # This assumes main.py is in hand_tracked_musical_interface/
    # and src/ is hand_tracked_musical_interface/src/
    # If running from one level above 'hand_tracked_musical_interface', adjust path.
    # For now, let's assume the standard case works. If not, the error message is informative.
    sys.exit(1)


if __name__ == "__main__":
    print("Starting Hand-Tracked Musical Interface...")
    # The Application class expects config_path relative to the project root
    # (i.e., relative to the hand_tracked_musical_interface directory).
    # ConfigManager then constructs the full path from its location in src/.
    # So, "config/config.yaml" is correct.
    app = Application(config_path='config/config.yaml')
    try:
        app.run()
    except KeyboardInterrupt:
        print("Application interrupted by user (KeyboardInterrupt). Shutting down.")
        app.shutdown()
    except Exception as e:
        print(f"An unexpected error occurred during application execution: {e}")
        import traceback
        traceback.print_exc()
        print("Attempting to shutdown gracefully...")
        app.shutdown()
        sys.exit(1)
    finally:
        print("Application has finished.")
```
