import sys
import math
import io
import os
import threading
import tkinter as tk
from tkinter import filedialog, colorchooser, simpledialog, messagebox, font as tkfont
from PIL import Image, ImageTk, ImageFont, ImageDraw
import cairosvg  # For SVG support
from pynput import keyboard, mouse  # For global keyboard events
import logging   # For logging
from lxml import etree  # For SVG manipulation
import datetime  # For date handling
import ctypes
import importlib  # For dynamic imports
from ctypes import wintypes
from pynput.keyboard import Key
import logging
from logging import Handler
import tkinter as tk
from  core.plugin_loader import PluginLoader # Import the PluginLoader class from the core.plugin_loader module


# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle (PyInstaller)
        base_path = sys._MEIPASS
    else:
        # If the application is run as a normal Python script
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_base_dir():
    """Get the base directory where the executable or script resides."""
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # If the application is run as a normal Python script
        return os.path.dirname(os.path.abspath(__file__))

class ImageState:
    """
    Represents the state of an individual image, including its transformations
    and visibility settings.
    """

    def __init__(self, image_original, name, svg_content=None):
        self.image_original = image_original
        self.image_display = None
        self.name = name
        self.visible = True

        # Transformation properties
        self.angle = 0
        self.scale = 1.0
        self.scale_log = 0
        self.offset_x = 512
        self.offset_y = 512
        self.rotation_point = None

        # Flip properties
        self.is_flipped_horizontally = False
        self.is_flipped_vertically = False

        # Transparency
        self.image_transparency_level = 0.2  # Set to minimum transparency by default

        # SVG content
        self.svg_content = svg_content

class TextHandler(Handler):
    """
    This handler logs events into a Tkinter Text widget with reduced font size.
    """
    def __init__(self, text_widget):
        Handler.__init__(self)
        self.text_widget = text_widget
        # Set a smaller font
        self.text_font = tkfont.Font(family="Helvetica", size=8)
        self.text_widget.configure(font=self.text_font)

    def emit(self, record):
        msg = self.format(record)
        # Insert log message at the end of the text box
        self.text_widget.insert(tk.END, msg + '\n')
        # Autoscroll to the end
        self.text_widget.see(tk.END)

class ImageOverlayApp:
    """
    Main application class that handles image loading, transformations,
    and user interactions through the GUI.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Controls")
        self.image_window_visible = False
        # Add small_font initialization before plugin loading
        self.small_font = tk.font.Font(size=8)
        
        # Initialize plugin loader after font setup
        self.plugin_loader = PluginLoader()
        self.plugin_loader.load_plugins(self)

        # Set the default size and position of the root window
        self.set_root_window_geometry()

        # Determine the base directory (where the .py or .exe file is located)
        self.base_dir = get_base_dir()

        # Path to the Images directory
        self.images_dir = os.path.join(self.base_dir, 'Images', 'ArchSaves')

        # In ImageOverlayApp.__init__, add dictionary for button references
        self.predefined_buttons = {}

        # Dictionary to store ImageState objects
        self.images = {}
        self.active_image_name = None  # Name of the active image
        self.previous_active_image_name = None  # To keep track of the previous active image

        # Mouse event variable8s
        self.start_x = 0
        self.start_y = 0
        self.i6s_dragging = False
        self.is_rotation_point_mode = False  # Rotation point selection mode

        # Additional windows
        self.additional_windows = []

        # Control mode variables
        self.control_mode = False  # Flag to track if control mode is active
        self.keyboard_listener = None

        self.alt_pressed = False    # To track the Alt key state
        self.shift_pressed = False  # To track the Shift key state

        # Full Control mode variables
        self.full_control_mode = False
        self.full_control_hotkey_listener = None

        # Declare the positions for ghost clicks (x, y)
        self.ghost_click_positions = {}

        # Initialize the GUI
        self.setup_buttons_window()
        self.setup_image_window()
        self.update_transparency_button()

        # Hide the image window by default
        self.image_window.withdraw()
        self.btn_hide_show_image.config(text="Show")

        # Initialize visibility trackers for additional images
        self.additional_images_visibility = {
            "Ruler": False,
            "Normal": False,
            "Tapered": False,
            "Ovoide": False,
            "Narrow Tapered": False,
            "Narrow Ovoide": False,
            "Angulation": False
        }

        # Set up global hotkeys
        self.setup_global_hotkeys()

    ##########################################################################################################
    ###                          --- Initialization and Setup Methods ---                                   ###
    ##########################################################################################################

    def set_root_window_geometry(self):
        """
        Sets the default size and position of the root window.
        """
        # Desired size of the root window
        window_width = 120  # Width stays the same
        
        # Calculate height based on:
        # - Button height (~25px)
        # - Padding between buttons (2px)
        # - Number of rows (~20)
        # - Extra padding (10px top/bottom)
        button_height = 25
        padding = 2
        num_rows = 20
        extra_padding = 20
        
        window_height = (button_height + padding) * num_rows + extra_padding

        # Margins from the screen edges
        margin_right = 60
        margin_top = 150

        # Get screen dimensions and calculate position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_position = screen_width - window_width - margin_right
        y_position = margin_top

        # Set the geometry
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    def setup_global_hotkeys(self):
        """
        Sets up global keyboard shortcuts using pynput.
        """
        # Ctrl + Alt + 1 to start/stop Control Mode
        def toggle_control_mode_hotkey():
            self.root.after(0, lambda: self.toggle_control_mode())
        # Ctrl + Alt + 2 to show/hide the image window
        def toggle_image_window_hotkey():
            self.root.after(0, self.toggle_image_window)
        # Ctrl + Alt + 3 to toggle Full Control mode
        def toggle_full_control_hotkey():
            self.root.after(0, self.toggle_full_control)
        try:
            self.global_hotkey_listener = keyboard.GlobalHotKeys({
                '<ctrl>+<alt>+1': toggle_control_mode_hotkey,
                '<ctrl>+<alt>+2': toggle_image_window_hotkey,
            })
            self.global_hotkey_listener.start()
            logging.info("Global Hotkeys listener started.")
        except ValueError as ve:
            logging.error(f"Failed to start Global Hotkeys: {ve}")
            messagebox.showerror("Hotkey Error", f"Failed to start hotkeys: {ve}")

    ##########################################################################################################
    ###                          --- GUI Control Creation Methods ---                                       ###
    ##########################################################################################################

    def setup_buttons_window(self):
        """
        Sets up the main control window with all the buttons and controls.
        """
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.small_font = tk.font.Font(size=8)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(padx=5, pady=5, fill='both', expand=True)

        self.create_transparency_controls(btn_frame)
        self.create_image_controls(btn_frame)
        self.create_flip_controls(btn_frame)
        self.create_rotation_point_control(btn_frame)
        self.create_zoom_controls(btn_frame)
        self.create_active_image_control(btn_frame)
        self.create_predefined_image_buttons(btn_frame)

        # Plugin buttons section with enhanced logging
        plugin_button_count = 0
        logging.info(f"Starting plugin button setup")
        logging.info(f"Plugin loader exists: {hasattr(self, 'plugin_loader')}")
        logging.info(f"Total plugins loaded: {len(self.plugin_loader.plugins)}")
        
        for plugin in self.plugin_loader.plugins.values():
            plugin_name = plugin.get_name()
            buttons = plugin.get_buttons()
            logging.info(f"Processing plugin: {plugin_name}")
            logging.info(f"Found {len(buttons)} buttons for plugin {plugin_name}")
            
            current_row = 7  # Start after standard buttons
            for btn_cfg in buttons:
                # Add row to grid config if not present
                if 'grid' not in btn_cfg:
                    btn_cfg['grid'] = {'row': current_row, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'}
                    current_row += 1
                
                self.create_button(btn_frame, btn_cfg)
                plugin_button_count += 1
                logging.info(f"Created button: {btn_cfg.get('text')} for {plugin_name}")

        logging.info(f"Completed loading {plugin_button_count} plugin buttons")
               
        # Other buttons
        other_buttons = [
            {
                'text': 'Load',
                'command': self.load_user_image,
                'grid': {'row': 17, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
                'width': 10
            },
            {
                'text': 'Ctrl Mode',
                'command': self.toggle_control_mode,
                'grid': {'row': 19, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'}, # Adjusted row
                'width': 10,
                'variable_name': 'btn_toggle_control_mode',
                'bg': 'red', # Initial state is inactive
                'fg': 'white'
            }
        ]

        for btn_cfg in other_buttons:
            self.create_button(btn_frame, btn_cfg)

        for i in range(2):
            btn_frame.columnconfigure(i, weight=1)

        self.root.attributes('-alpha', 1.0)

    def create_transparency_controls(self, parent):
        """
        Creates transparency control buttons.
        """
        buttons = [
            {
                'text': 'Transp',
                'command': self.toggle_transparency,
                'grid': {'row': 0, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
                'width': 8,
                'variable_name': 'btn_toggle_transparency'
            }
        ]

        for btn_cfg in buttons:
            self.create_button(parent, btn_cfg)

    def create_image_controls(self, parent):
        """
        Creates image loading and window toggling buttons.
        """
        buttons = [
            {
                'text': 'Hide',
                'command': self.toggle_image_window,
                'grid': {'row': 1, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
                'width': 10,
                'variable_name': 'btn_hide_show_image'
            }
        ]

        for btn_cfg in buttons:
            self.create_button(parent, btn_cfg)

    def create_flip_controls(self, parent):
        """
        Creates flip control buttons.
        """
        buttons = [
            {
                'text': 'Flip H',
                'command': self.flip_image_horizontal,
                'grid': {'row': 2, 'column': 0, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': 'Flip V',
                'command': self.flip_image_vertical,
                'grid': {'row': 2, 'column': 1, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            }
        ]

        for btn_cfg in buttons:
            self.create_button(parent, btn_cfg)

    def create_rotation_point_control(self, parent):
        """
        Creates rotation point control button.
        """
        buttons = [
            {
                'text': 'Rot Pt',
                'command': self.toggle_rotation_point_mode,
                'grid': {'row': 3, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
                'width': 10,
                'variable_name': 'btn_set_rotation_point'
            }
        ]

        for btn_cfg in buttons:
            self.create_button(parent, btn_cfg)

    def create_zoom_controls(self, parent):
        """
        Creates zoom control buttons.
        """
        buttons = [
            {
                'text': '+',
                'command': self.zoom_in,
                'grid': {'row': 4, 'column': 0, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': '-',
                'command': self.zoom_out,
                'grid': {'row': 4, 'column': 1, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': '+ Fine',
                'command': self.fine_zoom_in,
                'grid': {'row': 5, 'column': 0, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': '- Fine',
                'command': self.fine_zoom_out,
                'grid': {'row': 5, 'column': 1, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': 'Rot +',
                'command': self.fine_rotate_clockwise,
                'grid': {'row': 6, 'column': 0, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': 'Rot -',
                'command': self.fine_rotate_counterclockwise,
                'grid': {'row': 6, 'column': 1, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            }
        ]

        for btn_cfg in buttons:
            self.create_button(parent, btn_cfg)

    # Keep the creation of active image controls but comment out the grid placement
    def create_active_image_control(self, parent):
        """
        Creates active image selection controls.
        """
        # Commented out the label and dropdown menu grid placement
        # tk.Label(parent, text="Act Img:", font=self.small_font).grid(row=8, column=0, pady=2, sticky='e')

        self.active_image_var = tk.StringVar(value="")
        self.active_image_menu = tk.OptionMenu(
            parent, self.active_image_var, "", command=self.change_active_image
        )
        self.active_image_menu.config(font=self.small_font, width=8)
        # self.active_image_menu.grid(row=8, column=1, pady=2, sticky='ew')

    def create_predefined_image_buttons(self, parent):
        """
        Creates buttons for predefined images.
        """
        image_buttons = [
            ("Angul", "angulation.svg", self.toggle_angulation),
            ("Ruler", "liniar_new_n2.svg", self.toggle_ruler),
            ("Normal", "Normal(medium).svg", self.toggle_normal),
            ("Tapered", "Tapered.svg", self.toggle_tapered),
            ("Ovoide", "Ovoide.svg", self.toggle_ovoide),
            ("Narrow T", "NarrowTapered.svg", self.toggle_narrow_tapered),
            ("Narrow O", "NarrowOvoide.svg", self.toggle_narrow_ovoide),
        ]
        start_row = 10  # Adjust as needed
        for idx, (label, filename, command) in enumerate(image_buttons):
            btn_cfg = {
                'text': label,
                'command': command,
                'grid': {'row': start_row + idx, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
                'width': 10,
                'variable_name': f'btn_{label.lower().replace(" ", "_")}'
            }
            self.create_button(parent, btn_cfg)

    def create_button(self, parent, btn_cfg):
        """
        Helper method to create a button.
        """
        button = tk.Button(
            parent,
            text=btn_cfg['text'],
            command=self.log_button_press(btn_cfg['command']),
            font=self.small_font,
            width=btn_cfg.get('width', 6),
            bg=btn_cfg.get('bg'),     # Add background color support
            fg=btn_cfg.get('fg')      # Add foreground (text) color support
        )
        button.grid(**btn_cfg['grid'])

        # Assign reference if specified
        if 'variable_name' in btn_cfg:
            setattr(self, btn_cfg['variable_name'], button)

    def log_button_press(self, func):
        """
        Decorator to log button presses.
        """
        def wrapper(*args, **kwargs):
            logging.info(f"Button pressed: {func.__name__}")
            return func(*args, **kwargs)
        return wrapper

    ##########################################################################################################
    ###                          --- Canvas Setup and Event Binding Methods ---                             ###
    ##########################################################################################################

    def setup_image_window(self):
        """
        Sets up the image display window where images are shown and manipulated.
        """
        self.image_window = tk.Toplevel(self.root)
        self.image_window.title("Image Window")

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Set the window to match screen size
        self.image_window.geometry(f"{screen_width}x{screen_height}+0+0")

        # Allow window resizing
        self.image_window.resizable(True, True)

        # Remove window decorations and make background transparent
        self.image_window.overrideredirect(True)
        self.image_window.attributes('-transparentcolor', 'grey')

        self.image_window.attributes('-topmost', True)
        self.image_window.protocol("WM_DELETE_WINDOW", self.on_close)

        # Create the canvas with grey background
        self.canvas = tk.Canvas(self.image_window, bg='grey', highlightthickness=0, borderwidth=0)
        self.canvas.pack(fill='both', expand=True)

        # Force update to get accurate canvas size
        self.image_window.update_idletasks()

        # Bind mouse events
        self.bind_canvas_events()

        # Update canvas size on window resize
        self.image_window.bind('<Configure>', self.on_image_window_resize)

    def bind_canvas_events(self):
        """
        Binds mouse and keyboard events to the canvas for user interaction.
        """
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

        # Mouse wheel support across platforms
        if sys.platform.startswith('win'):
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        elif sys.platform == 'darwin':
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        else:
            self.canvas.bind("<Button-4>", lambda event: self.on_mouse_wheel(event))
            self.canvas.bind("<Button-5>", lambda event: self.on_mouse_wheel(event))

    def on_image_window_resize(self, event):
        """
        Adjusts the canvas size when the image window is resized.
        """
        self.canvas.config(width=event.width, height=event.height)
        self.draw_images()

    ##########################################################################################################
    ###                          --- Transparency Control Methods ---                                       ###
    ##########################################################################################################

    def toggle_transparency(self):
        """
        Toggles the transparency level of the active image.
        """
        active_image = self.get_active_image()
        if not active_image:
            return

        if active_image.image_transparency_level > 0.2:
            active_image.image_transparency_level = 0.2
            self.btn_toggle_transparency.config(text="Max Transp")
            logging.info(f"Transparency of image '{active_image.name}' set to minimum.")
        else:
            active_image.image_transparency_level = 1.0
            self.btn_toggle_transparency.config(text="Min Transp")
            logging.info(f"Transparency of image '{active_image.name}' set to maximum.")
        self.draw_images()

    def update_transparency_button(self):
        """
        Updates the transparency toggle button text based on the current state.
        """
        active_image = self.get_active_image()
        if active_image and active_image.image_transparency_level <= 0.2:
            self.btn_toggle_transparency.config(text="Max Transp")
        else:
            self.btn_toggle_transparency.config(text="Min Transp")

    ##########################################################################################################
    ###                          --- Image Loading Methods ---                                              ###
    ##########################################################################################################

    def load_image(self, image_name):
        """
        Loads an image file and creates an ImageState object.
        """
        filepath = filedialog.askopenfilename(
            title=f"Select {image_name}",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.svg")]
        )
        if filepath:
            image_original, svg_content = self.open_image_file(filepath)
            if image_original:
                image_state = ImageState(image_original, image_name, svg_content=svg_content)
                self.images[image_name] = image_state
                self.active_image_name = image_name
                self.update_active_image_menu()
                self.active_image_var.set(image_name)
                self.draw_images()

                logging.info(f"Image '{image_name}' loaded from '{filepath}'.")

                if not self.image_window_visible:
                    self.toggle_image_window()

    def open_image_file(self, filepath):
        """
        Opens an image file, handling SVG files separately.
        """
        try:
            if filepath.lower().endswith('.svg'):
                # Read SVG content
                with open(filepath, 'r', encoding='utf-8') as svg_file:
                    svg_content = svg_file.read()
                # Convert SVG to PNG using cairosvg
                png_data = cairosvg.svg2png(url=filepath)
                image_original = Image.open(io.BytesIO(png_data)).convert("RGBA")
                return image_original, svg_content
            else:
                image_original = Image.open(filepath).convert("RGBA")
                return image_original, None
        except Exception as e:
            logging.error(f"Error loading image: {e}")
            return None, None

    def load_default_image(self, image_key, filename):
        """
        Loads a default image given the key and filename.
        """
        filepath = resource_path(os.path.join('Images', filename))
        if os.path.exists(filepath):
            image_original, svg_content = self.open_image_file(filepath)
            if image_original:
                image_state = ImageState(image_original, image_key, svg_content=svg_content)
                self.images[image_key] = image_state

                # Center the image
                self.center_image(image_key)

                # Do not change the active image when loading the default image
                self.update_active_image_menu()
                self.draw_images()

                logging.info(f"Default '{image_key}' image loaded.")

                if not self.image_window_visible:
                    self.toggle_image_window()
        else:
            logging.error(f"'{filename}' not found at {filepath}")

    ##########################################################################################################
    ###                          --- Predefined Image Management Methods ---                                ###

    def toggle_ruler(self):
        """
        Toggles the visibility of the Ruler image.
        """
        self.toggle_predefined_image("Ruler", 'liniar_new_n2.svg', "Ruler")

    def toggle_normal(self):
        """
        Toggles the visibility of the Normal image.
        """
        self.toggle_predefined_image("Normal", 'Normal(medium).svg', "Normal")

    def toggle_tapered(self):
        """
        Toggles the visibility of the Tapered image.
        """
        self.toggle_predefined_image("Tapered", 'Tapered.svg', "Tapered")

    def toggle_ovoide(self):
        """
        Toggles the visibility of the Ovoide image.
        """
        self.toggle_predefined_image("Ovoide", 'Ovoide.svg', "Ovoide")

    def toggle_narrow_tapered(self):
        """
        Toggles the visibility of the Narrow Tapered image.
        """
        self.toggle_predefined_image("Narrow Tapered", 'NarrowTapered.svg', "Narrow Tapered")

    def toggle_narrow_ovoide(self):
        """
        Toggles the visibility of the Narrow Ovoide image.
        """
        self.toggle_predefined_image("Narrow Ovoide", 'NarrowOvoide.svg', "Narrow Ovoide")

    def toggle_angulation(self):
        """
        Toggles the visibility of the Angulation image.
        """
        self.toggle_predefined_image("Angulation", 'angulation.svg', "Angulation")

    def toggle_predefined_image(self, image_key, filename, button_label):
        """
        General method to toggle predefined images.
        """
        if not self.additional_images_visibility[image_key]:
            # Hide the previous active image
            if self.active_image_name and self.active_image_name in self.images:
                self.images[self.active_image_name].visible = False

            # Load the image if not already loaded
            if image_key not in self.images:
                self.load_default_image(image_key, filename)
            else:
                # If already loaded, make it visible without modifying its state
                self.images[image_key].visible = True
                self.draw_images()

            self.additional_images_visibility[image_key] = True
            logging.info(f"{image_key} image made visible.")

            # Store the previous active image and set the active image to the new one
            self.previous_active_image_name = self.active_image_name
            self.active_image_name = image_key
            self.update_active_image_menu()
            self.active_image_var.set(self.active_image_name)
            self.toggle_control_mode(True)  # Activate control mode

            if not self.image_window_visible:
                self.toggle_image_window()
        else:
            # Hide the image
            if image_key in self.images:
                self.images[image_key].visible = False
                self.draw_images()
            self.additional_images_visibility[image_key] = False
            logging.info(f"{image_key} image hidden.")

            # If the active image is the current one, revert to the previous active image
            if self.active_image_name == image_key:
                self.active_image_name = self.previous_active_image_name
                if self.active_image_name and self.active_image_name in self.images:
                    self.images[self.active_image_name].visible = True
                self.update_active_image_menu()
                self.active_image_var.set(self.active_image_name)
                self.previous_active_image_name = None
                self.toggle_control_mode(False)  # Deactivate control mode
                self.draw_images()

    def center_image(self, image_key):
        """
        Centers the specified image on the canvas, shifted 156 pixels to the right and 100 pixels down.
        """
        if image_key in self.images:
            self.image_window.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            image_state = self.images[image_key]
            image_state.offset_x = (canvas_width / 2) + 156  # Shift 156 pixels to the right
            image_state.offset_y = (canvas_height / 2) + 100  # Shift 100 pixels down

    ##########################################################################################################
    ###                           --- User Image Loading and Saving Methods ---                             ###

    def load_user_image(self):
        """
        Loads a user-selected image and adds it to the application.
        Prompts the user to enter a unique name for the image.
        """
        filepath = filedialog.askopenfilename(
            initialdir=self.images_dir,
            title="Select Image",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.svg")]
        )
        if filepath:
            image_original, svg_content = self.open_image_file(filepath)
            if image_original:
                # Prompt user for a unique name for the image
                default_name = os.path.splitext(os.path.basename(filepath))[0]
                image_name = simpledialog.askstring("Image Name", "Enter a unique name for the image:", initialvalue=default_name)
                if image_name:
                    # Ensure the name is unique
                    original_name = image_name
                    counter = 1
                    while image_name in self.images:
                        image_name = f"{original_name}_{counter}"
                        counter += 1

                    # Hide the previous active image
                    if self.active_image_name and self.active_image_name in self.images:
                        self.images[self.active_image_name].visible = False

                    # Create and store the image state
                    image_state = ImageState(image_original, image_name, svg_content=svg_content)
                    self.images[image_name] = image_state
                    self.active_image_name = image_name
                    self.images[self.active_image_name].visible = True  # Ensure the new image is visible
                    self.update_active_image_menu()
                    self.active_image_var.set(image_name)
                    self.draw_images()

                    logging.info(f"User-loaded image '{image_name}' loaded from '{filepath}'.")

                    self.toggle_control_mode(True)  # Activate control mode

                    if not self.image_window_visible:
                        self.toggle_image_window()
                else:
                    messagebox.showwarning("Name Required", "Image name is required to load the image.")
            else:
                messagebox.showerror("Load Failed", "Failed to load the selected image.")

    ##########################################################################################################
    ###                          --- Image Drawing Methods ---                                              ###
    ##########################################################################################################

    def draw_images(self):
        """
        Clears the canvas and redraws all visible images.
        """
        self.canvas.delete("all")
        for image_state in self.images.values():
            if image_state.visible:
                self.draw_image(image_state)
        self.image_window.update_idletasks()

    def draw_image(self, image_state):
        """
        Applies transformations to an image and draws it on the canvas.
        """
        # Apply transformations
        img = image_state.image_original.copy()

        # Apply transparency
        if image_state.image_transparency_level < 1.0:
            alpha = img.getchannel('A')
            alpha = alpha.point(lambda p: int(p * image_state.image_transparency_level))
            img.putalpha(alpha)

        # Resize
        img = img.resize(
            (int(img.width * image_state.scale), int(img.height * image_state.scale)),
            Image.LANCZOS
        )

        # Apply flips
        if image_state.is_flipped_horizontally:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if image_state.is_flipped_vertically:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        # Rotate around the rotation point if set
        if image_state.rotation_point:
            rotation_center = (
                image_state.rotation_point[0] - (image_state.offset_x - img.width / 2),
                image_state.rotation_point[1] - (image_state.offset_y - img.height / 2)
            )
            img = img.rotate(image_state.angle, expand=True, center=rotation_center)
        else:
            img = img.rotate(image_state.angle, expand=True)

        image_state.image_display = ImageTk.PhotoImage(img)

        # Draw the image at the offset position
        self.canvas.create_image(
            image_state.offset_x, image_state.offset_y, image=image_state.image_display
        )

        # Draw a marker at the rotation point if set
        if image_state.rotation_point:
            radius = 1.5  # Marker size
            self.canvas.create_oval(
                image_state.rotation_point[0] - radius, image_state.rotation_point[1] - radius,
                image_state.rotation_point[0] + radius, image_state.rotation_point[1] + radius,
                fill='red', outline=''
            )

    ##########################################################################################################
    ###                          --- Mouse and Keyboard Event Handlers ---                                  ###
    ##########################################################################################################

    def on_mouse_down(self, event):
        """
        Handles the event when the left mouse button is pressed.
        """
        if not self.is_rotation_point_mode:
            self.is_dragging = True
            self.start_x = event.x_root
            self.start_y = event.y_root
            logging.debug(f"Mouse down at ({self.start_x}, {self.start_y}).")

    def on_mouse_up(self, event):
        """
        Handles the event when the left mouse button is released.
        """
        self.is_dragging = False
        logging.debug(f"Mouse up at ({event.x_root}, {event.y_root}).")

    def on_mouse_move(self, event):
        """
        Handles the event when the mouse is moved while a button is pressed.
        """
        active_image = self.get_active_image()
        if self.is_dragging and active_image:
            dx = event.x_root - self.start_x
            dy = event.y_root - self.start_y

            if event.state & 0x0004:  # If Ctrl key is held down
                active_image.angle += dx * 0.1  # Reduced rotation sensitivity
                active_image.angle %= 360  # Keep angle within 0-360 degrees
                logging.debug(f"Rotating image '{active_image.name}' by {dx * 0.1} degrees.")
            else:
                active_image.offset_x += dx
                active_image.offset_y += dy
                logging.debug(f"Moving image '{active_image.name}' by ({dx}, {dy}).")

            self.start_x = event.x_root
            self.start_y = event.y_root
            self.draw_images()

    def on_canvas_click(self, event):
        """
        Handles the event when the canvas is clicked.
        """
        active_image = self.get_active_image()
        if active_image and self.is_rotation_point_mode:
            # Set the rotation point
            active_image.rotation_point = (event.x, event.y)
            self.is_rotation_point_mode = False
            self.btn_set_rotation_point.config(text="Rot Pt")
            self.draw_images()
            logging.info(f"Rotation point set for image '{active_image.name}' at ({event.x}, {event.y}).")
        elif active_image:
            # Check if click is outside the active image bounds
            img = active_image.image_original.copy()

            # Apply current transformations to get the actual displayed image size
            img = img.resize(
                (int(img.width * active_image.scale), int(img.height * active_image.scale)),
                Image.LANCZOS
            )

            if active_image.is_flipped_horizontally:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if active_image.is_flipped_vertically:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

            # Calculate image position
            img_width, img_height = img.size
            x_min = active_image.offset_x - img_width / 2
            y_min = active_image.offset_y - img_height / 2
            x_max = active_image.offset_x + img_width / 2
            y_max = active_image.offset_y + img_height / 2

            # If rotation is applied, the bounding box might be larger
            # For simplicity, we'll use the axis-aligned bounding box
            if not (x_min <= event.x <= x_max and y_min <= event.y <= y_max):
                self.toggle_control_mode(False)
                logging.info("Clicked outside the active image. Control mode disabled.")

    def on_mouse_wheel(self, event):
        """
        Handles the mouse wheel event for zooming.
        """
        active_image = self.get_active_image()
        if not active_image:
            return

        delta = self.get_mouse_wheel_delta(event)
        old_scale = active_image.scale
        active_image.scale_log += delta * 0.05  # Reduce sensitivity
        active_image.scale = pow(2, active_image.scale_log)

        # Limit scale
        active_image.scale = max(0.1, min(active_image.scale, 10.0))
        active_image.scale_log = math.log2(active_image.scale)

        logging.debug(f"Zooming image '{active_image.name}' to scale {active_image.scale}.")

        self.draw_images()

    def get_mouse_wheel_delta(self, event):
        """
        Normalizes the mouse wheel delta across different platforms.
        """
        if sys.platform.startswith('win') or sys.platform == 'darwin':
            return event.delta / 120
        else:
            if event.num == 4:  # Scroll up
                return 1
            elif event.num == 5:  # Scroll down
                return -1
            else:
                return 0

    def on_right_click(self, event=None):
        """
        Handles the event when the right mouse button is clicked (resets transformations).
        """
        active_image = self.get_active_image()
        if not active_image:
            return

        # Reset transformations
        active_image.angle = 0
        active_image.scale = 1.0
        active_image.scale_log = 0
        active_image.offset_x = self.canvas.winfo_width() / 2
        active_image.offset_y = self.canvas.winfo_height() / 2

        # Reset transparency
        active_image.image_transparency_level = 1.0
        self.btn_toggle_transparency.config(text="Transp")

        # Reset flips
        active_image.is_flipped_horizontally = False
        active_image.is_flipped_vertically = False

        # Reset rotation point
        active_image.rotation_point = None
        self.is_rotation_point_mode = False
        self.btn_set_rotation_point.config(text="Rot Pt")

        self.draw_images()

        logging.info(f"Reset transformations for image '{active_image.name}'.")

    ##########################################################################################################
    ###                          --- Image Transformation Methods ---                                       ###
    ##########################################################################################################

    def zoom_in(self):
        """
        Zooms in the active image.
        """
        self.adjust_zoom(0.05)

    def zoom_out(self):
        """
        Zooms out the active image.
        """
        self.adjust_zoom(-0.05)

    def fine_zoom_in(self):
        """
        Fine zooms in the active image.
        """
        self.adjust_zoom(0.01)

    def fine_zoom_out(self):
        """
        Fine zooms out the active image.
        """
        self.adjust_zoom(-0.01)

    def adjust_zoom(self, amount):
        """
        Adjusts the zoom level of the active image.
        """
        active_image = self.get_active_image()
        if not active_image:
            return
        active_image.scale = max(0.1, min(active_image.scale + amount, 10.0))
        active_image.scale_log = math.log2(active_image.scale)
        logging.info(f"Adjusted zoom for image '{active_image.name}' to scale {active_image.scale}.")
        self.draw_images()

    def flip_image_horizontal(self):
        """
        Flips the active image horizontally.
        """
        active_image = self.get_active_image()
        if not active_image:
            return
        active_image.is_flipped_horizontally = not active_image.is_flipped_horizontally
        logging.info(f"Image '{active_image.name}' flipped horizontally.")
        self.draw_images()

    def flip_image_vertical(self):
        """
        Flips the active image vertically.
        """
        active_image = self.get_active_image()
        if not active_image:
            return
        active_image.is_flipped_vertically = not active_image.is_flipped_vertically
        logging.info(f"Image '{active_image.name}' flipped vertically.")
        self.draw_images()

    def toggle_rotation_point_mode(self):
        """
        Toggles the mode for setting the rotation point.
        """
        active_image = self.get_active_image()
        if not active_image:
            return
        if not self.is_rotation_point_mode:
            self.is_rotation_point_mode = True
            self.btn_set_rotation_point.config(text="Cancel Rot Pt")
            logging.info("Rotation point mode enabled.")
        else:
            self.is_rotation_point_mode = False
            self.btn_set_rotation_point.config(text="Rot Pt")
            active_image.rotation_point = None
            logging.info("Rotation point mode disabled and rotation point reset.")
            self.draw_images()

    def fine_rotate_clockwise(self):
        """
        Rotates the active image clockwise by 0.5 degrees.
        """
        self.adjust_rotation(0.5)

    def fine_rotate_counterclockwise(self):
        """
        Rotates the active image counterclockwise by 0.5 degrees.
        """
        self.adjust_rotation(-0.5)

    def adjust_rotation(self, angle_increment):
        """
        Adjusts the rotation of the active image.
        """
        active_image = self.get_active_image()
        if not active_image:
            return
        active_image.angle = (active_image.angle + angle_increment) % 360
        logging.info(f"Rotated image '{active_image.name}' by {angle_increment} degrees.")
        self.draw_images()

    ##########################################################################################################
    ###                          --- Control Mode Management ---                                            ###
    ##########################################################################################################

    def toggle_control_mode(self, mode=None):
        """
        Toggles or sets the control mode with visual feedback.
        """
        if mode is True:
            if not self.control_mode and self.get_active_image():
                self.control_mode = True
                self.start_global_key_capture()
                logging.info("Control Mode Enabled.")
                # Update button appearance for active state
                self.btn_toggle_control_mode.config(
                    text="Disable Ctrl",
                    bg='green',
                    fg='white'
                )
        elif mode is False:
            if self.control_mode:
                self.control_mode = False
                self.stop_global_key_capture()
                logging.info("Control Mode Disabled.")
                # Update button appearance for inactive state
                self.btn_toggle_control_mode.config(
                    text="Ctrl Mode",
                    bg='red',
                    fg='white'
                )
        else:
            # Toggle mode
            if self.control_mode:
                self.control_mode = False
                self.stop_global_key_capture()
                logging.info("Control Mode Disabled.")
                # Update button appearance for inactive state
                self.btn_toggle_control_mode.config(
                    text="Ctrl Mode",
                    bg='red',
                    fg='white'
                )
            else:
                if self.get_active_image():
                    self.control_mode = True
                    self.start_global_key_capture()
                    logging.info("Control Mode Enabled.")
                    # Update button appearance for active state
                    self.btn_toggle_control_mode.config(
                        text="Disable Ctrl",
                        bg='green',
                        fg='white'
                    )

    def start_global_key_capture(self):
        """
        Starts capturing global keyboard inputs to control the active image.
        """
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_global_key_press,
            on_release=self.on_global_key_release
        )
        self.keyboard_listener.start()
        logging.info("Global key capture started without suppression.")

    def stop_global_key_capture(self):
        """
        Stops capturing global keyboard events.
        """
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener is not None:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
            logging.info("Global key capture stopped.")

    def on_global_key_press(self, key):
        """
        Handles global key press events.
        """
        try:
            if key == keyboard.Key.shift:
                self.shift_pressed = True
            if key.char == 'w':
                self.move_image('up')
            elif key.char == 's':
                self.move_image('down')
            elif key.char == 'a':
                self.move_image('left')
            elif key.char == 'd':
                self.move_image('right')
            elif key.char == 'c':
                self.rotate_image(-0.5)
            elif key.char == 'z':
                self.rotate_image(0.5)
            elif key.char == 'x':
                self.toggle_rotation_point_mode_thread_safe()
            elif key.char == 'q':
                self.fine_zoom_out_thread_safe()
            elif key.char == 'e' and self.alt_pressed:
                self.fine_zoom_in_thread_safe()
        except AttributeError:
            # Handle special keys
            if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.alt_pressed = True
            elif key == keyboard.Key.shift:
                self.shift_pressed = True

    def on_global_key_release(self, key):
        """
        Handles global key release events.
        """
        if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            self.alt_pressed = False
        if key == keyboard.Key.shift:
            self.shift_pressed = False

    def rotate_image(self, angle_increment):
        """
        Rotates the active image by the given angle increment.
        """
        self.canvas.after(0, self.adjust_rotation, angle_increment)

    def fine_zoom_in_thread_safe(self):
        self.canvas.after(0, self.fine_zoom_in)

    def fine_zoom_out_thread_safe(self):
        self.canvas.after(0, self.fine_zoom_out)

    def toggle_rotation_point_mode_thread_safe(self):
        self.canvas.after(0, self.toggle_rotation_point_mode)

    def move_image(self, direction):
        """
        Moves the active image in the specified direction.
        """
        self.canvas.after(0, self._move_image_main_thread, direction)

    def _move_image_main_thread(self, direction):
        active_image = self.get_active_image()
        if not active_image:
            return

        if self.shift_pressed:
            move_amount = 1  # Ultra-fine movement when shift is held
        else:
            move_amount = 3  # Pixels to move per key press

        if direction == 'up':
            active_image.offset_y -= move_amount
        elif direction == 'down':
            active_image.offset_y += move_amount
        elif direction == 'left':
            active_image.offset_x -= move_amount
        elif direction == 'right':
            active_image.offset_x += move_amount

        logging.info(f"Moved image '{active_image.name}' {direction} by {move_amount} pixels.")

        self.draw_images()

    ##########################################################################################################
    ###                          --- Application Exit Method ---                                            ###
    ##########################################################################################################

    def on_close(self):
        """
        Handles the closing of the application and ensures proper cleanup.
        """
        try:
            # Clean up plugins
            if hasattr(self, 'plugin_loader'):
                self.plugin_loader.cleanup()

            # Clean up windows
            if hasattr(self, 'image_window'):
                self.image_window.destroy()
            for window in self.additional_windows:
                if window.winfo_exists():
                    window.destroy()

            # Stop listeners
            if self.control_mode:
                self.stop_global_key_capture()
            if hasattr(self, 'full_control_mode') and self.full_control_mode:
                self.stop_full_control_hotkeys()
            if hasattr(self, 'global_hotkey_listener'):
                self.global_hotkey_listener.stop()

            # Clear image references
            if hasattr(self, 'images'):
                self.images.clear()

            # Destroy main window
            if self.root.winfo_exists():
                self.root.destroy()
        except Exception as e:
            logging.error(f"Error during application cleanup: {e}")
        finally:
            sys.exit(0)

    ##########################################################################################################
    ###                                             --- Helper Methods ---                                  ###
    ##########################################################################################################

    def update_active_image_menu(self):
        """
        Updates the dropdown menu for selecting the active image.
        """
        menu = self.active_image_menu['menu']
        menu.delete(0, 'end')
        for image_name in self.images.keys():
            menu.add_command(
                label=image_name,
                command=tk._setit(self.active_image_var, image_name, self.change_active_image)
            )
        if not self.images:
            self.active_image_var.set("")
        else:
            if self.active_image_name not in self.images:
                self.active_image_name = list(self.images.keys())[0]
                self.active_image_var.set(self.active_image_name)

    def get_active_image(self):
        """
        Retrieves the currently active image.
        """
        return self.images.get(self.active_image_name)

    def change_active_image(self, value):
        """
        Changes the active image based on user selection, hides the previous image,
        and activates control mode.
        """
        # Hide the previous active image
        if self.active_image_name and self.active_image_name in self.images:
            self.images[self.active_image_name].visible = False

        # Set the new active image
        self.active_image_name = value
        self.images[self.active_image_name].visible = True  # Ensure the new active image is visible

        self.update_transparency_button()
        logging.info(f"Active image changed to '{value}'.")

        self.draw_images()  # Redraw images to reflect visibility changes
        self.toggle_control_mode(True)  # Activate control mode

    def apply_transformations_to_svg(self, image_state):
        """
        Applies transformations to the SVG content and returns the transformed SVG.
        """
        try:
            svg_content = image_state.svg_content
            parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
            svg_root = etree.fromstring(svg_content.encode('utf-8'), parser=parser)

            # Build the transformation string
            transforms = []

            # Flips
            if image_state.is_flipped_horizontally or image_state.is_flipped_vertically:
                scale_x = -1 if image_state.is_flipped_horizontally else 1
                scale_y = -1 if image_state.is_flipped_vertically else 1
                transforms.append(f"scale({scale_x},{scale_y})")

            # Scaling
            if image_state.scale != 1.0:
                transforms.append(f"scale({image_state.scale})")

            # Rotation
            if image_state.angle != 0:
                if image_state.rotation_point:
                    cx, cy = image_state.rotation_point
                else:
                    # Use center of image
                    cx = image_state.offset_x
                    cy = image_state.offset_y
                transforms.append(f"rotate({image_state.angle},{cx},{cy})")

            # Translation
            transforms.append(f"translate({image_state.offset_x},{image_state.offset_y})")

            # Combine all transformations
            transform_str = ' '.join(transforms)

            # Create a new group element
            g = etree.Element("g")
            g.set("transform", transform_str)

            # Move all children of svg_root to the new group
            for child in list(svg_root):
                svg_root.remove(child)
                g.append(child)

            # Add the group to the svg_root
            svg_root.append(g)

            # Adjust transparency
            if image_state.image_transparency_level != 1.0:
                # Set opacity on the group
                g.set("opacity", str(image_state.image_transparency_level))

            # Convert back to string
            transformed_svg = etree.tostring(svg_root, encoding='utf-8', method='xml', pretty_print=True).decode('utf-8')

            return transformed_svg

        except Exception as e:
            logging.error(f"Error applying transformations to SVG: {e}")
            return None

    def get_transformed_image(self, image_state):
        """
        Applies transformations to the image and returns the transformed image.
        """
        try:
            img = image_state.image_original.copy()

            # Apply flips
            if image_state.is_flipped_horizontally:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if image_state.is_flipped_vertically:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

            # Resize
            img = img.resize(
                (int(img.width * image_state.scale), int(img.height * image_state.scale)),
                Image.LANCZOS
            )

            # Rotate
            img = img.rotate(-image_state.angle, expand=True)

            # Adjust transparency
            if image_state.image_transparency_level < 1.0:
                alpha = img.getchannel('A')
                alpha = alpha.point(lambda p: int(p * image_state.image_transparency_level))
                img.putalpha(alpha)

            return img

        except Exception as e:
            logging.error(f"Error getting transformed image: {e}")
            return None



    ##########################################################################################################
    ###                          --- Image Window Toggle Method ---                                         ###
    ##########################################################################################################

    def toggle_image_window(self):
        """
        Shows or hides the image window.
        """
        if self.image_window_visible:
            self.image_window.withdraw()
            self.image_window_visible = False
            self.btn_hide_show_image.config(text="Show")
            logging.info("Image window hidden.")
        else:
            self.image_window.deiconify()
            self.image_window_visible = True
            self.btn_hide_show_image.config(text="Hide")
            logging.info("Image window shown.")
            self.image_window.update_idletasks()
            self.draw_images()

##########################################################################################################
###                                             --- Run ---                                            ###
##########################################################################################################

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageOverlayApp(root)
    root.mainloop()

