import logging
from pynput import keyboard
from pynput.keyboard import Key, Controller
from core.plugin_interface import OrthyPlugin

class KeyboardRemapperPlugin(OrthyPlugin):
    def __init__(self):
        self.app = None
        self.active = False
        self.keyboard_listener = None
        self.keyboard_controller = Controller()
        self.pressed_keys = set()

        self.wsad_to_arrows = {'w': Key.up, 's': Key.down, 'a': Key.left, 'd': Key.right}
        self.arrows_to_wsad = {v: k for k, v in self.wsad_to_arrows.items()}

    def initialize(self, app_instance):
        self.app = app_instance
        self.start_listener()

    def get_name(self):
        return "KeyboardRemapper"

    def get_buttons(self):
        return []

    def activate(self):
        self.active = True
        logging.info("[Remapper] Activated.")

    def deactivate(self):
        self.active = False
        logging.info("[Remapper] Deactivated.")
        self.release_all_mapped_keys()

    def start_listener(self):
        if self.keyboard_listener:
            return

        def on_press(key):
            if not self.active:
                return True

            logging.debug(f"[Remapper] on_press: {key}")

            is_char = hasattr(key, 'char') and key.char
            original = key.char.lower() if is_char and key.char else key

            # If already pressed, ignore
            if original in self.pressed_keys:
                logging.debug("[Remapper] Key already pressed, ignoring.")
                return True

            # Remap w/s/a/d -> Arrows
            if is_char:
                c = original
                if c in self.wsad_to_arrows:
                    arrow_key = self.wsad_to_arrows[c]
                    logging.debug(f"[Remapper] Press {arrow_key} for {c}")
                    self.keyboard_controller.press(arrow_key)
                    self.pressed_keys.add(c)
            else:
                # Remap arrows -> w/s/a/d
                if original in self.arrows_to_wsad:
                    wsad_char = self.arrows_to_wsad[original]
                    logging.debug(f"[Remapper] Press {wsad_char} for {original}")
                    self.keyboard_controller.press(wsad_char)
                    self.pressed_keys.add(original)

            return True

        def on_release(key):
            if not self.active:
                return True

            logging.debug(f"[Remapper] on_release: {key}")

            is_char = hasattr(key, 'char') and key.char
            original = key.char.lower() if is_char and key.char else key

            # Release corresponding mapped keys if they are pressed
            if is_char:
                c = original
                if c in self.wsad_to_arrows and c in self.pressed_keys:
                    arrow_key = self.wsad_to_arrows[c]
                    logging.debug(f"[Remapper] Release {arrow_key} for {c}")
                    self.keyboard_controller.release(arrow_key)
                    self.pressed_keys.remove(c)
            else:
                if original in self.arrows_to_wsad and original in self.pressed_keys:
                    wsad_char = self.arrows_to_wsad[original]
                    logging.debug(f"[Remapper] Release {wsad_char} for {original}")
                    self.keyboard_controller.release(wsad_char)
                    self.pressed_keys.remove(original)

            return True

        self.keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.keyboard_listener.start()
        logging.info("[Remapper] Listener started.")

    def release_all_mapped_keys(self):
        logging.debug("[Remapper] Releasing all mapped keys due to deactivation.")
        for k in list(self.pressed_keys):
            if isinstance(k, str) and k in self.wsad_to_arrows:
                arrow_key = self.wsad_to_arrows[k]
                logging.debug(f"[Remapper] Releasing {arrow_key} after deactivation.")
                self.keyboard_controller.release(arrow_key)
            elif k in self.arrows_to_wsad:
                wsad_char = self.arrows_to_wsad[k]
                logging.debug(f"[Remapper] Releasing {wsad_char} after deactivation.")
                self.keyboard_controller.release(wsad_char)
        self.pressed_keys.clear()

    def cleanup(self):
        if self.keyboard_listener:
            logging.info("[Remapper] Stopping keyboard listener...")
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        self.release_all_mapped_keys()
