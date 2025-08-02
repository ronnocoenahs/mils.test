# tracker_manager.py
import configparser
import os

PROWLARR_CONFIG_FILE = "prowlarr.conf"
BTN_CONFIG_FILE = "btn.conf"
PTP_CONFIG_FILE = "ptp.conf"

def get_config(file_path):
    """Reads a .conf file."""
    if not os.path.exists(file_path):
        return None
    config = configparser.ConfigParser()
    config.read(file_path)
    return config

def save_config(config, file_path):
    """Saves a .conf file."""
    with open(file_path, 'w') as configfile:
        config.write(configfile)

def load_prowlarr_config():
    """Loads Prowlarr configuration."""
    return get_config(PROWLARR_CONFIG_FILE)

def load_btn_config():
    """Loads Broadcasthe.net configuration."""
    return get_config(BTN_CONFIG_FILE)

def load_ptp_config():
    """Loads PassThePopcorn.me configuration."""
    return get_config(PTP_CONFIG_FILE)

