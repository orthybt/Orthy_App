# plugins/maestro_controls.py

from core.plugin_interface import OrthyPlugin
from tkinter import messagebox, filedialog, Toplevel, Label, Frame, Button
from pynput import keyboard, mouse
import logging
import os
import ctypes

class MaestroControlsPlugin(OrthyPlugin):
    def __init__(self):
        self.app = None
        self.full_control_mode = False
        self.full_control_hotkey_listener = None
        self.maestro_version = None
        self.ghost_click_positions = {}

    def initialize(self, app_instance):
        self.app = app_instance

    def get_name(self):
        return "MaestroControls"

    def get_buttons(self):
        return [{
            'text': 'Maestro Controls',
            'command': self.toggle_full_control,
            'grid': {'row': 18, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
            'width': 10,
            'variable_name': 'btn_full_control',
            'bg': 'red',
            'fg': 'white'
        }]

    def toggle_full_control(self):
        if not self.full_control_mode:
            # Prompt the user to select Maestro version
            maestro_version = self.prompt_maestro_version()
            if maestro_version is None:
                return
            self.maestro_version = maestro_version

            # Simplified coordinate setup dialog
            response = messagebox.askyesno(
                "Coordinate Setup",
                "How would you like to set up coordinates?\n\n" +
                "Click 'Yes' to select coordinates manually\n" +
                "Click 'No' to load coordinates from a file"
            )
            
            if response:  # Manual selection
                self.select_control_coordinates()
            else:  # Load from file
                filepath = filedialog.askopenfilename(
                    title="Select coordinates file",
                    filetypes=[("Text files", "*.txt")],
                    initialdir=self.app.base_dir
                )
                if filepath:
                    self.load_coords_from_file(filepath)
                else:
                    return

            self.full_control_mode = True
            self.start_full_control_hotkeys()
            logging.info(f"Full Control Mode Enabled for Maestro {self.maestro_version}")
            
            self.app.btn_full_control.config(
                text="Full_Ctrl_ON",
                bg='green',
                fg='white'
            )
        else:
            self.full_control_mode = False
            self.stop_full_control_hotkeys()
            logging.info("Full Control Mode Disabled")
            
            self.app.btn_full_control.config(
                text="FullCtrl",
                bg='red',
                fg='white'
            )

    def select_control_coordinates(self):
        """
        Guides the user to select coordinates for each control by clicking on the screen.
        """
        controls = [
            'DistalTip', 'MesialTip', 
            'NegativeTorque', 'PositiveTorque', 
            'MesialRotation', 'DistalRotation',
            'Intrusion', 'Extrusion',
            'DistalLinear', 'MesialLinear'
        ]
        self.ghost_click_positions = {}

        messagebox.showinfo("Coordinate Selection", 
            "You'll be prompted to click on each control's position.\n\n"
            "Numpad Controls:\n"
            "7 - Distal Tip       8 - Positive Torque    9 - Mesial Tip\n"
            "4 - Distal Rotation  5 - Negative Torque    6 - Mesial Rotation\n"
            "1 - Intrusion        2 - Distal Linear      3 - Mesial Linear\n"
            "0 - Extrusion"
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
        ControlName:X,Y
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
        """
        Prompts user to select Maestro version.
        """
        maestro_version = None

        def select_version(version):
            nonlocal maestro_version
            maestro_version = version
            top.destroy()

        top = Toplevel(self.app.root)
        top.title("Select Maestro Version")
        top.attributes('-topmost', True)
        top.grab_set()

        Label(top, text="Select Maestro Version:").pack(pady=10)

        btn_frame = Frame(top)
        btn_frame.pack(pady=10)

        Button(btn_frame, text="Maestro 4", command=lambda: select_version('4')).pack(side='left', padx=20)
        Button(btn_frame, text="Maestro 6", command=lambda: select_version('6')).pack(side='right', padx=20)

        top.update_idletasks()
        window_width = top.winfo_width()
        window_height = top.winfo_height()
        screen_width = top.winfo_screenwidth()
        screen_height = top.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        top.geometry(f'{window_width}x{window_height}+{x}+{y}')

        top.wait_window()
        return maestro_version

    def start_full_control_hotkeys(self): # IF SOMEONE IS WORKING ON REMOTE DESKTOP, IT WILL NOT WORK, UNLESS YOU SELECT IN LOCAL RESOURCES, TO USE WIN COMBINATIONS ONLY FROM YOUR LOCAL COMPUTER... !GPT NEVER DELETE THIS COMMENT! EVER! EVER! 
        """
        Starts listening for keyboard shortcuts using virtual key codes.
        VK codes:
        104 - numpad 8 (positive torque)
        101 - numpad 5 (negative torque) 
        103 - numpad 7 (distal tip)
        105 - numpad 9 (mesial tip)
        102 - numpad 6 (mesial rotation)
        100 - numpad 4 (distal rotation)
        97  - numpad 1 (intrusion)
        96  - numpad 0 (extrusion)
        98  - numpad 2 (distal linear)
        99  - numpad 3 (mesial linear)
        """
        try:
            def on_press(key):
                try:
                    vk = key.vk
                    if vk == 104:  # Numpad 8
                        self.perform_ghost_click('PositiveTorque')
                    elif vk == 101:  # Numpad 5
                        self.perform_ghost_click('NegativeTorque')
                    elif vk == 103:  # Numpad 7
                        self.perform_ghost_click('DistalTip')
                    elif vk == 105:  # Numpad 9
                        self.perform_ghost_click('MesialTip')
                    elif vk == 102:  # Numpad 6
                        self.perform_ghost_click('MesialRotation')
                    elif vk == 100:  # Numpad 4
                        self.perform_ghost_click('DistalRotation')
                    elif vk == 97:   # Numpad 1
                        self.perform_ghost_click('Intrusion')
                    elif vk == 96:   # Numpad 0
                        self.perform_ghost_click('Extrusion')
                    elif vk == 98:   # Numpad 2
                        self.perform_ghost_click('DistalLinear')
                    elif vk == 99:   # Numpad 3
                        self.perform_ghost_click('MesialLinear')
                except AttributeError:
                    pass  # Key doesn't have a vk code

            self.full_control_hotkey_listener = keyboard.Listener(on_press=on_press)
            self.full_control_hotkey_listener.daemon = True
            self.full_control_hotkey_listener.start()
            logging.info("Full Control Hotkeys listener started")
        except Exception as e:
            logging.error(f"Failed to start Full Control Hotkeys: {e}")
            messagebox.showerror("Hotkey Error", f"Failed to start Full Control Hotkeys: {e}")

    def stop_full_control_hotkeys(self):
        """
        Stops listening for keyboard shortcuts.
        """
        if self.full_control_hotkey_listener:
            self.full_control_hotkey_listener.stop()
            self.full_control_hotkey_listener = None
            logging.info("Full Control Hotkeys listener stopped")

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
        Performs a ghost click for the given action.
        """
        position = self.ghost_click_positions.get(action_name)
        if position is None:
            logging.error(f"No position defined for action '{action_name}'")
            return

        logging.info(f"Performing ghost click for '{action_name}' at position {position}")
        self.ghost_click_at_position(position)

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
            dwFlags=0x0001 | 0x8000,
            time=0,
            dwExtraInfo=None
        )

        mouse_down_input = INPUT()
        mouse_down_input.type = INPUT_MOUSE
        mouse_down_input.mi = MOUSEINPUT(
            dx=0,
            dy=0,
            mouseData=0,
            dwFlags=0x0002,
            time=0,
            dwExtraInfo=None
        )

        mouse_up_input = INPUT()
        mouse_up_input.type = INPUT_MOUSE
        mouse_up_input.mi = MOUSEINPUT(
            dx=0,
            dy=0,
            mouseData=0,
            dwFlags=0x0004,
            time=0,
            dwExtraInfo=None
        )

        inputs = (mouse_move_input, mouse_down_input, mouse_up_input)
        nInputs = len(inputs)
        LPINPUT = ctypes.POINTER(INPUT)
        pInputs = (INPUT * nInputs)(*inputs)
        cbSize = ctypes.sizeof(INPUT)

        ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)

    def cleanup(self):
        """
        Cleanup plugin resources.
        """
        if self.full_control_mode:
            self.cleanup_listeners()
