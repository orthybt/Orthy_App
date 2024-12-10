import logging
from pynput import keyboard
from pynput.keyboard import Key, Controller
from core.plugin_interface import OrthyPlugin

class ImageControlPlugin(OrthyPlugin):
    def __init__(self):
        self.app = None
        self.image_control_enabled = False
        self.keyboard_listener = None
        self.shift_pressed = False
        self.alt_pressed = False

    def initialize(self, app_instance):
        self.app = app_instance

    def get_name(self):
        return "ImageControl"

    def get_buttons(self):
        return []

    def toggle_image_control(self, mode=None):
        mc_plugin = self.app.plugin_loader.get_plugin("MaestroControls")

        if mode is True:
            # If full control is active, disable it first
            if mc_plugin and mc_plugin.full_control_mode:
                mc_plugin.toggle_full_control()  # This turns off full control
            if not self.image_control_enabled and self.app.get_active_image():
                self.image_control_enabled = True
                self.start_global_key_capture()
                logging.info("Image Control Enabled.")
                if hasattr(self.app, 'btn_toggle_control_mode'):
                    self.app.btn_toggle_control_mode.config(
                        text="Disable ImgCtrl",
                        bg='green',
                        fg='white'
                    )
        elif mode is False:
            if self.image_control_enabled:
                self.image_control_enabled = False
                self.stop_global_key_capture()
                logging.info("Image Control Disabled.")
                if hasattr(self.app, 'btn_toggle_control_mode'):
                    self.app.btn_toggle_control_mode.config(
                        text="Img Ctrl",
                        bg='red',
                        fg='white'
                    )
        else:
            # Toggle mode
            if self.image_control_enabled:
                # Currently on, turn it off
                self.image_control_enabled = False
                self.stop_global_key_capture()
                logging.info("Image Control Disabled.")
                if hasattr(self.app, 'btn_toggle_control_mode'):
                    self.app.btn_toggle_control_mode.config(
                        text="Img Ctrl",
                        bg='red',
                        fg='white'
                    )
            else:
                # Currently off, turn it on
                # If full control is on, turn it off first
                if mc_plugin and mc_plugin.full_control_mode:
                    mc_plugin.toggle_full_control()
                if self.app.get_active_image():
                    self.image_control_enabled = True
                    self.start_global_key_capture()
                    logging.info("Image Control Enabled.")
                    if hasattr(self.app, 'btn_toggle_control_mode'):
                        self.app.btn_toggle_control_mode.config(
                            text="Disable ImgCtrl",
                            bg='green',
                            fg='white'
                        )

    def start_global_key_capture(self):
        if self.keyboard_listener:
            return
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_global_key_press,
            on_release=self.on_global_key_release
        )
        self.keyboard_listener.start()
        logging.info("Global key capture for Image Control started.")

    def stop_global_key_capture(self):
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
            logging.info("Global key capture for Image Control stopped.")

    def on_global_key_press(self, key):
        try:
            if key == keyboard.Key.shift:
                self.shift_pressed = True
            if hasattr(key, 'char') and key.char:
                c = key.char.lower()
                if c == 'w':
                    self.move_image('up')
                elif c == 's':
                    self.move_image('down')
                elif c == 'a':
                    self.move_image('left')
                elif c == 'd':
                    self.move_image('right')
                elif c == 'c':
                    self.rotate_image(-0.5)
                elif c == 'z':
                    self.rotate_image(0.5)
                elif c == 'x':
                    self.toggle_rotation_point_mode_thread_safe()
                elif c == 'q':
                    self.fine_zoom_out_thread_safe()
                elif c == 'e' and self.alt_pressed:
                    self.fine_zoom_in_thread_safe()
        except AttributeError:
            if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                self.alt_pressed = True
            elif key == keyboard.Key.shift:
                self.shift_pressed = True

    def on_global_key_release(self, key):
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
            self.alt_pressed = False
        if key == keyboard.Key.shift:
            self.shift_pressed = False

    def rotate_image(self, angle_increment):
        self.app.canvas.after(0, self.app.adjust_rotation, angle_increment)

    def fine_zoom_in_thread_safe(self):
        self.app.canvas.after(0, self.app.fine_zoom_in)

    def fine_zoom_out_thread_safe(self):
        self.app.canvas.after(0, self.app.fine_zoom_out)

    def toggle_rotation_point_mode_thread_safe(self):
        self.app.canvas.after(0, self.app.toggle_rotation_point_mode)

    def move_image(self, direction):
        self.app.canvas.after(0, self._move_image_main_thread, direction)

    def _move_image_main_thread(self, direction):
        active_image = self.app.get_active_image()
        if not active_image:
            return
        move_amount = 1 if self.shift_pressed else 3
        if direction == 'up':
            active_image.offset_y -= move_amount
        elif direction == 'down':
            active_image.offset_y += move_amount
        elif direction == 'left':
            active_image.offset_x -= move_amount
        elif direction == 'right':
            active_image.offset_x += move_amount

        logging.info(f"Moved image '{active_image.name}' {direction} by {move_amount} pixels.")
        self.app.draw_images()

    def cleanup(self):
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        logging.info("ImageControlPlugin cleaned up.")
