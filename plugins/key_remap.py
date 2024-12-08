# File: plugins/key_remap.py

from core.plugin_interface import OrthyPlugin
from pynput import keyboard
from pynput.keyboard import Key, Controller
import logging

class KeyRemapPlugin(OrthyPlugin):
    _instance = None
    
    def __init__(self):
        if KeyRemapPlugin._instance:
            return
        KeyRemapPlugin._instance = self
        self.app = None
        self.keyboard_controller = Controller()
        self.remap_listener = None
        self.alt_pressed = False
        self.enabled = True  # Add enabled state
        logging.debug("KeyRemapPlugin instance created")

    def initialize(self, app_instance):
        if self.remap_listener and self.remap_listener.is_alive():
            logging.debug("KeyRemap listener already running")
            return
            
        self.app = app_instance
        self.start_remap_listener()
        
        # Remove button creation from initialize - let OrthyApp handle it
        logging.debug("KeyRemap plugin initialized")

    def get_name(self):
        return "KeyRemap"

    def get_buttons(self):
        logging.debug("KeyRemap get_buttons called")
        return [{
            'text': 'Remap: ON' if self.enabled else 'Remap: OFF',
            'command': self.toggle_remap,
            'grid': {'row': 7, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
            'width': 12,
            'variable_name': 'btn_key_remap',
            'relief': 'sunken' if self.enabled else 'raised',
            'bg': '#a0ffa0' if self.enabled else '#ffa0a0'
        }]

    def toggle_remap(self):
        self.enabled = not self.enabled
        state = "enabled" if self.enabled else "disabled"
        logging.debug(f"Key remapping {state}")
        
        if self.app and 'btn_key_remap' in self.app.predefined_buttons:
            btn = self.app.predefined_buttons['btn_key_remap']
            btn.config(
                text=f'Remap: {"ON" if self.enabled else "OFF"}',
                relief='sunken' if self.enabled else 'raised',
                bg='#a0ffa0' if self.enabled else '#ffa0a0'
            )

    def start_remap_listener(self):
        def on_press(key):
            if not self.enabled:  # Check if enabled
                return
            try:
                if key == Key.alt_l:
                    self.alt_pressed = True
                    logging.debug("Alt key pressed")
                elif hasattr(key, 'vk') and self.alt_pressed:
                    vk = key.vk
                    if vk == 104:  # Numpad 8
                        self.keyboard_controller.press(Key.up)
                        self.keyboard_controller.release(Key.up)
                        logging.debug("Numpad 8 pressed, remapped to Up arrow")
                    elif vk == 101:  # Numpad 5
                        self.keyboard_controller.press(Key.down)
                        self.keyboard_controller.release(Key.down)
                        logging.debug("Numpad 5 pressed, remapped to Down arrow")
                    elif vk == 102:  # Numpad 6
                        self.keyboard_controller.press(Key.right)
                        self.keyboard_controller.release(Key.right)
                        logging.debug("Numpad 6 pressed, remapped to Right arrow")
                    elif vk == 100:  # Numpad 4
                        self.keyboard_controller.press(Key.left)
                        self.keyboard_controller.release(Key.left)
                        logging.debug("Numpad 4 pressed, remapped to Left arrow")
            except AttributeError:
                logging.error("AttributeError encountered in on_press")
                pass

        def on_release(key):
            if key == Key.alt_l:
                self.alt_pressed = False
                logging.debug("Alt key released")

        if not self.remap_listener or not self.remap_listener.is_alive():
            self.remap_listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release
            )
            self.remap_listener.daemon = True
            self.remap_listener.start()
            logging.info("Key remap listener started")

    def cleanup(self):
        if self.remap_listener:
            self.remap_listener.stop()
            self.remap_listener = None
            logging.debug("KeyRemap listener stopped")