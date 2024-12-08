# plugins/example_plugin.py

from core.plugin_interface import OrthyPlugin

class ExamplePlugin(OrthyPlugin):
    def __init__(self):
        self.app = None
        
    def initialize(self, app_instance):
        self.app = app_instance
        
    def get_name(self):
        return "Example"
        
    def get_buttons(self):
        return [{
            'text': 'Example',
            'command': self.example_action,
            'grid': {'row': 20, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
            'width': 10
        }]
        
    def example_action(self):
        print("Example plugin action")
        
    def cleanup(self):
        pass