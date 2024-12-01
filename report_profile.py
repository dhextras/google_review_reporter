import hashlib
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime


# Color configurations for terminal output
class Config:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Config.BLUE,
        "INFO": Config.GREEN,
        "WARNING": Config.YELLOW,
        "ERROR": Config.RED,
        "CRITICAL": Config.MAGENTA,
        "RESET": Config.RESET,
    }

    def format(self, record):
        log_message = super().format(record)
        return f"{self.COLORS.get(record.levelname, self.COLORS['RESET'])}{log_message}{self.COLORS['RESET']}"


def install_requirements():
    """Install required Python libraries"""
    try:
        import dotenv as _
        import inquirer as _
        import requests as _
    except ImportError:
        print(
            f"{Config.YELLOW}Required libraries not found. Installing...{Config.RESET}"
        )

        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "requests",
                "python-dotenv",
                "inquirer",
            ]
        )
        print(
            f"{Config.GREEN}Required libraries installed successfully.{Config.RESET}\n"
        )


install_requirements()

import requests
from dotenv import load_dotenv

load_dotenv()

# Constants
BATCH_SIZE = 100
GEELARK_BASE_URL = "https://openapi.geelark.com/open/v1"
APP_ID = os.getenv("GEELARK_APP_ID")
APP_KEY = os.getenv("GEELARK_APP_KEY")

SELECTED_PHONES_FILE = "cred/selected_phones.json"
PROCESSED_DATA_FILE = "cred/processed_data.json"


# Utility Functions
def generate_headers():
    """Generate required headers for Geelark API requests"""
    traceId = str(uuid.uuid4())
    ts = int(time.time() * 1000)
    nonce = traceId[:6]

    # Generate signature
    sign_str = f"{APP_ID}{traceId}{ts}{nonce}{APP_KEY}"
    sign = hashlib.sha256(sign_str.encode()).hexdigest().upper()

    return {
        "appId": APP_ID,
        "traceId": traceId,
        "ts": str(ts),
        "nonce": nonce,
        "sign": sign,
        "Content-Type": "application/json",
    }


def setup_logger(log_file=None):
    """Set up logging with colored console output"""
    logger = logging.getLogger("GeelarkAutomation")
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    os.makedirs("log", exist_ok=True)

    # File handler
    date = datetime.now().strftime("%m_%d")
    log_file = log_file or os.path.join("log", f"report_profile_{date}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "[%(asctime)s] - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Console handler with color
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log_message(message, level="INFO"):
    logger = setup_logger()
    getattr(logger, level.lower())(message)


def get_phone_list():
    """Fetch list of all the available from Geelark"""
    all_phones = []
    page_id = 1

    def get_phone_page(page=1, page_size=100):
        url = f"{GEELARK_BASE_URL}/phone/list"
        payload = {"page": page, "pageSize": page_size}

        try:
            response = requests.post(url, headers=generate_headers(), json=payload)
            response.raise_for_status()

            items = response.json().get("data", {}).get("items", [])
            total = response.json().get("data", {}).get("total", 0)

            return items, total
        except Exception as e:
            log_message(f"Error fetching phone list: {e}", "ERROR")
            return [], 0

    while True:
        phones, total = get_phone_page(page=page_id)
        all_phones = all_phones + phones

        if total == 0:
            break
        elif total <= len(all_phones):
            break

        page_id += 1

    return all_phones


def get_selected_phones(all_phones):
    """Get selected phones from file or return all phones"""
    try:
        with open(SELECTED_PHONES_FILE, "r") as f:
            chosen_phones = json.load(f)

        if not chosen_phones:
            return all_phones

        selected_phones = [
            phone for phone in all_phones if phone["serialName"] in chosen_phones
        ]
        return selected_phones
    except FileNotFoundError:
        return all_phones


def start_phones(phone_ids):
    """Start a specific phone environment"""
    url = f"{GEELARK_BASE_URL}/phone/start"
    payload = {"ids": phone_ids}

    try:
        response = requests.post(url, headers=generate_headers(), json=payload)
        response.raise_for_status()

        data = response.json().get("data", {})
        return data.get("successDetails", []), data.get("failDetails", [])
    except Exception as e:
        log_message(f"Error starting phones: {e}", "ERROR")
        return [], []


def stop_phones(phone_ids):
    """Stop a specific phone environment"""
    url = f"{GEELARK_BASE_URL}/phone/stop"
    payload = {"ids": phone_ids}

    try:
        response = requests.post(url, headers=generate_headers(), json=payload)
        response.raise_for_status()
        data = response.json().get("data", {})
        return data.get("successAmount", 0), data.get("failDetails", [])
    except Exception as e:
        log_message(f"Error stopping all the phones: {e}", "ERROR")
        return [], []


def choose_actions():
    """
    Displays a graphical interface to for user to choose the script options
    """

    import inquirer

    actions = [
        "Start All Phones",
        "Stop All Phones",
        "Bulk - Install Application",
        "Bulk - Uninstall Application",
    ]

    questions = [
        inquirer.List(
            "action",
            message="Select a review report file to process ( Use arrow keys to choose )",
            choices=actions,
        ),
    ]

    answers = inquirer.prompt(questions)

    if not answers:
        return None
    selected_action = answers["action"]
    return selected_action


def log_failed_devices(failed_devices, available_devices):
    device_name_map = {
        device["id"]: device.get("serialName", "unknown")
        for device in available_devices
    }

    print(f"{Config.YELLOW}Details:{Config.RESET}")
    for failed_device in failed_devices:
        device_name = device_name_map.get(failed_device["id"], "Unknown")
        print(
            f"{Config.YELLOW}       [FAILED] - Id: {failed_device['id']}, Name: {device_name}{Config.RESET} - Reason: {failed_device['msg']}"
        )


def main():
    if not all([APP_ID, APP_KEY]):
        log_message("Missing Geelark environment variables", "CRITICAL")
        sys.exit(1)

    action = choose_actions()
    if not action:
        log_message("Unrecognized action to take", "ERROR")
        sys.exit(1)

    try:
        all_phones = get_phone_list()
        selected_phones = get_selected_phones(all_phones)

        log_message(f"Found {len(selected_phones)} phones to process", "INFO")

        batches = [
            selected_phones[i : i + BATCH_SIZE]
            for i in range(0, len(selected_phones), BATCH_SIZE)
        ]

        for batch in batches:
            phone_ids = [phone["id"] for phone in batch]

            if action == "Start All Phones":
                started_phones, failed_phones = start_phones(phone_ids)
                log_message(
                    f"Successfully started {len(started_phones)} phones, Failed to start {len(failed_phones)} phones"
                )

                if len(failed_phones) > 0:
                    log_failed_devices(failed_phones, selected_phones)

                print(started_phones)
            elif action == "Stop All Phones":
                stoped_phones_len, failed_phones = stop_phones(phone_ids)
                log_message(
                    f"Successfully stoped {stoped_phones_len} phones, Failed to stop {len(failed_phones)} phones"
                )

                if len(failed_phones) > 0:
                    log_failed_devices(failed_phones, selected_phones)
            elif action == "Bulk - Install Application":
                print("Not yet implemented")
            elif action == "Bulk - Uninstall Application":
                print("Not yet implemented")

    except KeyboardInterrupt:
        log_message("Shutting down gracefully...", "INFO")


if __name__ == "__main__":
    main()
