import inspect
import logging
import os
import random
import subprocess
import sys
import time
from datetime import datetime

IS_HEADLESS = False
PROFILE_LIMIT = 300
API_URL = "https://dolphin-anty-api.com"
BASE_URL = os.getenv("DOLPHIN_BASE_URL")
API_KEY = os.getenv("DOLPHIN_API_KEY")


# Color configurations for terminal output
class Config:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"


# Configure required libraries
def install_requirements():
    try:
        import inquirer as _
        import requests as _
        import selenium as _
    except ImportError:
        print(
            f"{Config.YELLOW}Required libraries not found. Installing...{Config.RESET}"
        )
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "inquirer", "requests", "selenium"]
        )
        print(
            f"{Config.GREEN}Required libraries installed successfully.{Config.RESET}\n"
        )


install_requirements()

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


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


def setup_logger(log_file=None):
    caller_script = inspect.stack()[2].filename
    script_name = os.path.splitext(os.path.basename(caller_script))[0]
    logger_name = script_name
    date = datetime.now().strftime("%m_%d")
    log_file = log_file or os.path.join("log", f"{script_name}_{date}.log")

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    log_directory = "log"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def choose_file():
    """
    Displays a graphical interface to select a report file.
    Returns the selected file path.
    """

    import inquirer

    choices = []
    file_paths = {}
    directory = os.getcwd()

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json") and file.startswith("review_report_"):
                choices.append(file)
                full_path = os.path.join(root, file)
                file_paths[file] = full_path

    questions = [
        inquirer.List(
            "file",
            message="Select a review report file to process ( Use arrow keys to choose )",
            choices=choices,
        ),
    ]

    answers = inquirer.prompt(questions)

    if not answers:
        return None
    selected_file = file_paths[answers["file"]]
    return selected_file


def log_message(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    logger = setup_logger()
    getattr(logger, level.lower())(f"[{timestamp}] {message}")


def get_browser_profiles():
    """Fetch all available browser profiles"""
    url = f"{API_URL}/browser_profiles"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    params = {"limit": PROFILE_LIMIT}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()["data"]
    except Exception as e:
        log_message(f"Error fetching browser profiles: {str(e)}", "ERROR")
        return []


def run_profile(profile_id, headless=False):
    """Start a browser profile"""
    try:
        is_headless_str = "&headless=true" if headless else ""
        url = f"{BASE_URL}/v1.0/browser_profiles/{profile_id}/start?automation=1{is_headless_str}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_message(f"Error starting profile {profile_id}: {str(e)}", "ERROR")
        return None


def close_profile(profile_id):
    """Stop a browser profile"""
    try:
        url = f"{BASE_URL}/v1.0/browser_profiles/{profile_id}/stop"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_message(f"Error closing profile {profile_id}: {str(e)}", "ERROR")
        return None


def perform_automation(profile_id):
    """
    Main automation function - customize this for your specific needs
    """
    try:
        log_message(f"Starting profile {profile_id}", "INFO")
        response = run_profile(profile_id, IS_HEADLESS)

        if not response:
            log_message(f"Failed to start profile {profile_id}", "ERROR")
            return

        port = response["automation"]["port"]

        # Connect to the opened browser via Selenium with debugAddress port
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        driver = webdriver.Chrome(options=options)

        # automation logic go here - for now just fetch the google title
        log_message("Starting automation sequence", "INFO")
        driver.get("https://google.com/")
        log_message(f"Page title: {driver.title}", "INFO")
        time.sleep(random.uniform(1, 2))

        # Clean up
        driver.quit()
        close_profile(profile_id)
        log_message(
            f"Successfully completed automation for profile {profile_id}", "INFO"
        )

    except Exception as e:
        log_message(f"Automation error for profile {profile_id}: {str(e)}", "ERROR")
        try:
            driver.quit()
        except:
            pass
        close_profile(profile_id)


def main():

    if not all([API_KEY, BASE_URL]):
        log_message("Missing required environment variables", "CRITICAL")
        sys.exit(1)

    try:
        input_file = choose_file()
        if input_file is None:
            sys.exit(1)

        log_message(
            f"Starting browser automation script for review file: {input_file}", "INFO"
        )

        # Fetch & Process all profiles
        profiles = get_browser_profiles()

        log_message(f"Found {len(profiles)} profiles", "INFO")

        for profile in profiles:
            profile_id = profile["id"]
            profile_name = profile["name"]
            log_message(f"Processing profile '{profile_name}' - {profile_id}", "INFO")
            perform_automation(profile_id)
            time.sleep(random.uniform(1, 3))

    except KeyboardInterrupt:
        log_message("Shutting down gracefully...", "INFO")
    except Exception as e:
        log_message(f"Critical error in main: {e}", "CRITICAL")
        sys.exit(1)


if __name__ == "__main__":
    main()
