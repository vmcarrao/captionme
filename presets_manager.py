import json
import os
import streamlit as st

class PresetsManager:
    def __init__(self, filepath="presets.json"):
        self.filepath = filepath
        self.presets = self._load_presets_from_disk()

    def _load_presets_from_disk(self):
        """Loads presets from the JSON file."""
        if not os.path.exists(self.filepath):
            return {}
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading presets: {e}")
            return {}

    def save_to_disk(self):
        """Saves current presets memory to disk."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.presets, f, indent=4)
        except Exception as e:
            st.error(f"Error saving presets: {e}")

    def get_all_names(self):
        """Returns a list of all preset names."""
        return list(self.presets.keys())

    def get_preset(self, name):
        """Returns the configuration dict for a specific preset."""
        return self.presets.get(name)

    def save_preset(self, name, config):
        """Saves a new preset or updates an existing one."""
        self.presets[name] = config
        self.save_to_disk()

    def delete_preset(self, name):
        """Deletes a preset by name."""
        if name in self.presets:
            del self.presets[name]
            self.save_to_disk()
