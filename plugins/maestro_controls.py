# plugins/maestro_controls.py

from core.plugin_interface import OrthyPlugin
from tkinter import messagebox, filedialog, Toplevel, Label, Frame, Button
from pynput import keyboard, mouse
import logging
import os
import ctypes
from ctypes import wintypes
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Key
import tkinter as tk

class MaestroControlsPlugin(OrthyPlugin):
    def __init__(self):
        self.full_control_mode = False
        self.full_control_hotkey_listener = None
        self.app = None
        self.current_coords = {}
        logging.debug("MaestroControlsPlugin initialized")
        self.maestro_version = None
        self.ghost_click_positions = {}

    def initialize(self, app_instance):
        self.app = app_instance
        logging.debug("MaestroControlsPlugin initialized with app instance")

    def get_name(self):
        return "MaestroControls"

    def get_buttons(self):
        return [{
            'text': 'Maestro Controls',
            'command': self.toggle_full_control,
            'variable_name': 'btn_maestro_controls',
            'bg': '#a0ffa0' if self.full_control_mode else '#ffa0a0',
            'relief': 'sunken' if self.full_control_mode else 'raised',
            'width': 12
        }]

    def toggle_full_control(self):
        self.full_control_mode = not self.full_control_mode
        state = "Enabled" if self.full_control_mode else "Disabled"
        logging.info(f"Full Control Mode {state} for Maestro 6")
        if self.full_control_mode:
            self.prompt_maestro_version_and_start()
        else:
            self.stop_full_control_hotkeys()
            # Update button appearance
            if self.app and 'btn_maestro_controls' in self.app.predefined_buttons:
                btn = self.app.predefined_buttons['btn_maestro_controls']
                btn.config(bg='#ffa0a0', relief='raised')

    def prompt_maestro_version_and_start(self):
        """Prompt user to select Maestro version and choose coordinate loading method."""
        version = self.prompt_maestro_version()
        if version:
            self.maestro_version = version
            # Ask user to reset coordinates manually or load defaults
            choice = messagebox.askyesno(
                "Coordinate Method",
                "Do you want to reset the coordinates manually?\n\n"
                "Yes: Reset coordinates manually\n"
                "No: Load default coordinates"
            )
            if choice:
                self.select_control_coordinates()
            else:
                if self.check_for_saved_coords():
                    self.load_saved_coords()
                else:
                    messagebox.showwarning(
                        "No Defaults Found",
                        "Default coordinates not found. Please reset coordinates manually."
                    )
                    self.select_control_coordinates()
            self.start_full_control_hotkeys()
            # Update button appearance
            if self.app and 'btn_maestro_controls' in self.app.predefined_buttons:
                btn = self.app.predefined_buttons['btn_maestro_controls']
                btn.config(bg='#a0ffa0', relief='sunken')
        else:
            logging.info("Maestro version selection canceled.")
            self.full_control_mode = False
            # Update button appearance
            if self.app and 'btn_maestro_controls' in self.app.predefined_buttons:
                btn = self.app.predefined_buttons['btn_maestro_controls']
                btn.config(bg='#ffa0a0', relief='raised')

    def load_coordinates(self):
        """Load coordinates from file with proper error handling"""
        try:
            coord_file = f'coords_maestro_{self.maestro_version}.txt'
            coord_path = os.path.join(self.app.base_dir, coord_file)
            self.current_coords.clear()
            
            with open(coord_path, 'r') as f:
                for line in f:
                    try:
                        # Strip whitespace and split by colon first
                        parts = line.strip().split(':')
                        if len(parts) != 2:
                            logging.warning(f"Invalid line format: {line}")
                            continue
                        
                        name, coords = parts
                        # Now split coords by comma
                        coord_parts = coords.split(',')
                        if len(coord_parts) != 2:
                            logging.warning(f"Invalid coordinate format for '{name}': {coords}")
                            continue
                        
                        x_str, y_str = coord_parts
                        x, y = int(x_str), int(y_str)
                        self.current_coords[name] = (x, y)
                    except ValueError as e:
                        logging.warning(f"Invalid coordinate values in line: {line} - {e}")
                        continue
                
            if not self.current_coords:
                raise ValueError("No valid coordinates loaded")
                
            logging.info(f"Loaded {len(self.current_coords)} coordinates from {coord_file}")
            
        except Exception as e:
            logging.error(f"Failed to load coordinates: {e}")
            self.full_control_mode = False
            if self.app and 'btn_maestro_controls' in self.app.predefined_buttons:
                self.app.predefined_buttons['btn_maestro_controls'].config(
                    bg='#ffa0a0',
                    relief='raised'
                )
            messagebox.showerror("Load Failed", f"Failed to load coordinates: {e}")

    def select_control_coordinates(self):
        """
        Guides the user to select coordinates for each control by clicking on the screen.
        """
        controls = [
            'DistalTip', 'MesialTip',
            'NegativeTorque', 'PositiveTorque',
            'MesialRotation', 'DistalRotation', 
            'BuccalLinear', 'LingualLinear',
            'MesialLinear', 'DistalLinear',
            'Intrusion'
        ]
        self.ghost_click_positions = {}

        messagebox.showinfo("Coordinate Selection",
            "You'll be prompted to click on each control's position.\n\n"
            "Numpad Controls:\n"
            "7 - Distal Tip       + - Positive Torque    9 - Mesial Tip\n"
            "Backspace - Mesial Rotation    * - Distal Rotation\n" 
            "/ - Buccal Linear    2 - Lingual Linear     3 - Mesial Linear\n"
            "1 - Distal Linear    - - Negative Torque    0 - Intrusion"
        )

        for control in controls:
            messagebox.showinfo("Select Control", f"Please click on the '{control}' control on the screen.")
            self.app.root.withdraw()
            self.app.image_window.withdraw()
            self.wait_for_click(control)
            self.app.root.deiconify()
            self.app.image_window.deiconify()

        save_coords = messagebox.askyesno("Save Coordinates",
            "Do you want to save these coordinates for future use?"
        )
        if save_coords:
            self.save_coords_to_file()

    def wait_for_click(self, control_name):
        """
        Waits for the user to click on the screen and records the cursor position.
        """
        messagebox.showinfo("Coordinate Selection", f"Move your mouse to the '{control_name}' control and click.")

        position = None

        def on_click(x, y, button, pressed):
            nonlocal position
            if pressed and button == mouse.Button.left:
                position = (x, y)
                return False

        with mouse.Listener(on_click=on_click) as listener:
            listener.join()

        if position:
            self.ghost_click_positions[control_name] = position
            logging.info(f"Recorded position for '{control_name}': {position}")

    def save_coords_to_file(self):
        """
        Saves the ghost click positions to a file.
        Format:
        ControlName:x,y
        """
        coords_file = os.path.join(self.app.base_dir, f'coords_maestro_{self.maestro_version}.txt')
        try:
            with open(coords_file, 'w') as f:
                # Save in a specific order for readability
                control_order = [
                    'DistalTip', 'MesialTip',
                    'NegativeTorque', 'PositiveTorque',
                    'MesialRotation', 'DistalRotation',
                    'Intrusion', 'Extrusion',
                    'DistalLinear', 'MesialLinear'
                ]
                for control in control_order:
                    if control in self.ghost_click_positions:
                        position = self.ghost_click_positions[control]
                        f.write(f"{control}:{position[0]},{position[1]}\n")
            logging.info(f"Coordinates saved to {coords_file}")
            messagebox.showinfo("Coordinates Saved", f"Coordinates saved to {coords_file}")
        except Exception as e:
            logging.error(f"Failed to save coordinates: {e}")
            messagebox.showerror("Save Failed", "Failed to save coordinates")

    def load_saved_coords(self):
        """
        Loads the ghost click positions from a file.
        """
        coords_file = os.path.join(self.app.base_dir, f'coords_maestro_{self.maestro_version}.txt')
        try:
            with open(coords_file, 'r') as f:
                for line in f:
                    control, pos = line.strip().split(':')
                    x_str, y_str = pos.split(',')
                    self.ghost_click_positions[control] = (int(x_str), int(y_str))
            logging.info(f"Coordinates loaded from {coords_file}")
        except Exception as e:
            logging.error(f"Failed to load coordinates: {e}")
            messagebox.showerror("Load Failed", "Failed to load coordinates")

    def load_coords_from_file(self, filepath):
        """
        Loads coordinates from a specified file.
        """
        try:
            with open(filepath, 'r') as f:
                self.ghost_click_positions.clear()
                for line in f:
                    control, pos = line.strip().split(':')
                    x_str, y_str = pos.split(',')
                    self.ghost_click_positions[control] = (int(x_str), int(y_str))
            logging.info(f"Coordinates loaded from {filepath}")
        except Exception as e:
            logging.error(f"Failed to load coordinates from file: {e}")
            messagebox.showerror("Load Failed", "Failed to load coordinates from the selected file")

    def check_for_saved_coords(self):
        """
        Checks if saved coordinates file exists.
        """
        coords_file = os.path.join(self.app.base_dir, f'coords_maestro_{self.maestro_version}.txt')
        return os.path.exists(coords_file)

    def prompt_maestro_version(self):
        """Prompt user to select Maestro version"""
        dialog = tk.Toplevel()
        dialog.title("Select Maestro Version")
        dialog.geometry("300x100")
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        def select_version(version):
            self.maestro_version = version
            dialog.destroy()
            
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(expand=True)
        
        tk.Button(btn_frame, text="Maestro 4", 
                 command=lambda: select_version('4')).pack(side='left', padx=20)
        tk.Button(btn_frame, text="Maestro 6",
                 command=lambda: select_version('6')).pack(side='left', padx=20)
                 
        dialog.wait_window()
        return self.maestro_version

    def start_full_control_hotkeys(self):
        """Initialize and start hotkey listeners for full control mode"""
        try:
            # Stop existing listener if any
            if self.full_control_hotkey_listener is not None:
                if self.full_control_hotkey_listener.is_alive():
                    self.full_control_hotkey_listener.stop()
            # Create new listener
            self.full_control_hotkey_listener = keyboard.Listener(
                on_press=self.on_key_press,
                on_release=self.on_key_release
            )
            self.full_control_hotkey_listener.daemon = True
            self.full_control_hotkey_listener.start()
            logging.info("Full control hotkeys started")
        except Exception as e:
            logging.error(f"Failed to start full control hotkeys: {e}")
            self.full_control_mode = False
            if self.app and 'btn_maestro_controls' in self.app.predefined_buttons:
                btn = self.app.predefined_buttons['btn_maestro_controls']
                btn.config(bg='#ffa0a0', relief='raised')
            messagebox.showerror("Hotkey Error", f"Failed to start hotkeys: {e}")

    def stop_full_control_hotkeys(self):
        """Stop and cleanup hotkey listeners"""
        if self.full_control_hotkey_listener is not None:
            self.full_control_hotkey_listener.stop()
            self.full_control_hotkey_listener = None
            logging.info("Full control hotkeys stopped")

    def cleanup_listeners(self):
        """
        Explicitly cleanup all keyboard listeners
        """
        # Stop full control hotkeys
        if hasattr(self, 'full_control_hotkey_listener'):
            self.full_control_hotkey_listener.stop()
            self.full_control_hotkey_listener = None
        
        # Stop global key capture
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    def perform_ghost_click(self, action_name):
        """
        Performs a ghost click and returns cursor to original position.
        """
        position = self.ghost_click_positions.get(action_name)
        if position is None:
            logging.error(f"No position defined for action '{action_name}'")
            return

        # Get current cursor position using GetCursorPos
        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        original_x, original_y = point.x, point.y

        logging.info(f"Performing ghost click for '{action_name}' at position {position}")
        self.ghost_click_at_position(position)

        # Return to original position using SetCursorPos
        ctypes.windll.user32.SetCursorPos(original_x, original_y)

    def ghost_click_at_position(self, position):
        """
        Simulates a mouse click at the specified position.
        """
        x, y = position
        
        INPUT_MOUSE = 0
        
        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_ulong),
                ("mi", MOUSEINPUT)
            ]

        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)

        absolute_x = int(x * 65536 / screen_width)
        absolute_y = int(y * 65536 / screen_height)

        mouse_move_input = INPUT()
        mouse_move_input.type = INPUT_MOUSE
        mouse_move_input.mi = MOUSEINPUT(
            dx=absolute_x,
            dy=absolute_y,
            mouseData=0,
            dwFlags=0x0001 | 0x8000,  # MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
            time=0,
            dwExtraInfo=None
        )

        mouse_down_input = INPUT()
        mouse_down_input.type = INPUT_MOUSE
        mouse_down_input.mi = MOUSEINPUT(
            dx=0,
            dy=0,
            mouseData=0,
            dwFlags=0x0002,  # MOUSEEVENTF_LEFTDOWN
            time=0,
            dwExtraInfo=None
        )

        mouse_up_input = INPUT()
        mouse_up_input.type = INPUT_MOUSE
        mouse_up_input.mi = MOUSEINPUT(
            dx=0,
            dy=0,
            mouseData=0,
            dwFlags=0x0004,  # MOUSEEVENTF_LEFTUP
            time=0,
            dwExtraInfo=None
        )

        inputs = (mouse_move_input, mouse_down_input, mouse_up_input)
        nInputs = len(inputs)
        pInputs = (INPUT * nInputs)(*inputs)
        cbSize = ctypes.sizeof(INPUT)

        ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)

    def cleanup(self):
        """
        Cleanup plugin resources.
        """
        if self.full_control_mode:
            self.cleanup_listeners()

    def on_key_press(self, key):
        """Handle key press events"""
        try:
            if key == keyboard.Key.f1:
                self.perform_ghost_click('DistalTip')
            elif key == keyboard.Key.f2:
                self.perform_ghost_click('MesialTip')
            # Add more key mappings as needed
            logging.debug(f"Key pressed: {key}")
        except Exception as e:
            logging.error(f"Error in on_key_press: {e}")

    def on_key_release(self, key):
        """Handle keyboard release events"""
        try:
            if key == Key.esc:
                self.full_control_mode = False
                if self.full_control_hotkey_listener:
                    self.full_control_hotkey_listener.stop()
                logging.info("Full control mode disabled")
                # Update button appearance
                if self.app and 'btn_maestro_controls' in self.app.predefined_buttons:
                    btn = self.app.predefined_buttons['btn_maestro_controls']
                    btn.config(bg='#ffa0a0', relief='raised')
                return False
        except Exception as e:
            logging.error(f"Error in key release handler: {e}")