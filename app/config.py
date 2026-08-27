import json
import os
import sys

def get_config_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.join(os.path.dirname(sys.executable), "_internal")
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "config.json")

CONFIG_PATH = get_config_path()

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading config.json: {e}")
    # Default config
    return {
        "host": "0.0.0.0",
        "port": 8000,
        "max_file_size_mb": 10,
        "rate_limit_enabled": False,
        "enable_api_docs": False
    }

def save_config(config_data):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config.json: {e}")
        return False
