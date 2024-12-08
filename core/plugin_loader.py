# core/plugin_loader.py

import os
import importlib
import inspect
from .plugin_interface import OrthyPlugin

class PluginLoader:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = {}

    def load_plugins(self, app_instance):
        """Load all plugins from plugin directory"""
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f"plugins.{module_name}")
                    
                    # Find plugin classes in module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, OrthyPlugin) and 
                            obj is not OrthyPlugin):
                            plugin = obj()
                            plugin.initialize(app_instance)
                            self.plugins[plugin.get_name()] = plugin
                            
                except Exception as e:
                    print(f"Failed to load plugin {module_name}: {e}")

    def get_plugin(self, name):
        return self.plugins.get(name)

    def cleanup(self):
        for plugin in self.plugins.values():
            plugin.cleanup()