import inspect
import json
import logging
import os
import random
import subprocess
import sys
import time
from datetime import datetime


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
        import dotenv as _
        import inquirer as _
        import requests as _
        import selenium as _
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
                "inquirer",
                "python-dotenv",
                "requests",
                "selenium",
            ]
        )
        print(
            f"{Config.GREEN}Required libraries installed successfully.{Config.RESET}\n"
        )


install_requirements()

import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()

IS_HEADLESS = False
PROFILE_LIMIT = 100
API_URL = "https://dolphin-anty-api.com"
BASE_URL = os.getenv("DOLPHIN_BASE_URL")
API_KEY = os.getenv("DOLPHIN_API_KEY")
SELECTED_PROFILES_FILE = "cred/selected_profiles.json"
PROCESSED_DATA_FILE = "cred/processed_data.json"

# Create the cred Dir
os.makedirs("cred", exist_ok=True)


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
        "[%(asctime)s] - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        "[%(asctime)s] - %(name)s - %(levelname)s - %(message)s"
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
    logger = setup_logger()
    getattr(logger, level.lower())(message)


def load_last_processed_data():
    try:
        with open(PROCESSED_DATA_FILE, "r") as f:
            data = json.load(f)
        profile_id = data["profile_id"]
        input_file = data["input_file"]
        return profile_id, input_file
    except:
        return None, None


def save_last_processed_data(profile_id, input_file):
    try:
        with open(PROCESSED_DATA_FILE, "w") as f:
            json.dump({"profile_id": profile_id, "input_file": input_file}, f)
    except:
        pass


def get_browser_profiles():
    """Fetch all available browser profiles"""
    all_profiles = []

    def get_profile_page(url=None):
        try:
            url = url if url else f"{API_URL}/browser_profiles"
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            }
            params = {"limit": PROFILE_LIMIT}

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()["data"], response.json()["next_page_url"]
        except Exception as e:
            log_message(
                f"Error fetching browser profiles for url: {url}: {str(e)}", "ERROR"
            )
            return [], None

    next_url = None
    while True:
        profiles, next_url = get_profile_page(next_url)
        all_profiles = all_profiles + profiles

        if not next_url:
            break

    return all_profiles


def get_selected_profiles(all_profiles):
    try:
        with open(SELECTED_PROFILES_FILE, "r") as f:
            choosen_profiles = json.load(f)

        if choosen_profiles == []:
            return all_profiles

        selected_profiles = [
            profile for profile in all_profiles if profile["name"] in choosen_profiles
        ]
        return selected_profiles
    except:
        return all_profiles


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


def perform_automation(profile_id, reviews_to_report):
    """
    Main automation function for reporting reviews with human-like behavior
    and login handling
    """

    try:
        response = run_profile(profile_id, IS_HEADLESS)
        if not response:
            log_message(f"Failed to start profile {profile_id}", "ERROR")
            return
        port = response["automation"]["port"]

        log_message(f"Connecting to profile {profile_id} at port {port}", "INFO")
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        driver = webdriver.Chrome(options=options)

        # Won't work in headless mode
        def human_like_mouse_movement():
            actions = ActionChains(driver)

            # Get viewport size
            viewport_width = driver.execute_script("return window.innerWidth;")
            viewport_height = driver.execute_script("return window.innerHeight;")

            def generate_bezier_curve(start_point, end_point, num_points=10):
                # Create a random control point for the curve
                control_x = random.randint(
                    min(start_point[0], end_point[0]), max(start_point[0], end_point[0])
                )
                control_y = random.randint(
                    min(start_point[1], end_point[1]), max(start_point[1], end_point[1])
                )

                points = []
                for t in range(num_points + 1):
                    t = t / num_points
                    # Quadratic Bezier curve formula
                    x = (
                        (1 - t) ** 2 * start_point[0]
                        + 2 * (1 - t) * t * control_x
                        + t**2 * end_point[0]
                    )
                    y = (
                        (1 - t) ** 2 * start_point[1]
                        + 2 * (1 - t) * t * control_y
                        + t**2 * end_point[1]
                    )
                    points.append((int(x), int(y)))
                return points

            # Perform several random curved movements
            current_x = current_y = 0
            for _ in range(3):  # Number of major movements
                # Generate random end point
                end_x = random.randint(-viewport_width // 3, viewport_width // 3)
                end_y = random.randint(-viewport_height // 3, viewport_height // 3)

                # Generate curve points
                curve_points = generate_bezier_curve(
                    (current_x, current_y),
                    (end_x, end_y),
                    num_points=random.randint(
                        8, 15
                    ),  # Random number of points for varying speed
                )

                # Follow the curve with slight imperfections
                for point in curve_points:
                    # Add slight random deviation to simulate hand shakiness
                    deviation_x = random.gauss(
                        0, 2
                    )  # Random deviation with normal distribution
                    deviation_y = random.gauss(0, 2)

                    try:
                        actions.move_by_offset(
                            point[0] - current_x + deviation_x,
                            point[1] - current_y + deviation_y,
                        ).perform()
                    except:
                        # Reset if we move out of bounds
                        actions = ActionChains(driver)
                        current_x = current_y = 0
                        continue

                    current_x, current_y = point

                    # Random micro pause
                    time.sleep(random.uniform(0.01, 0.03))

                # Occasional pause between major movements
                time.sleep(random.uniform(0.1, 0.3))

                # Sometimes add a "hesitation" movement
                if random.random() < 0.3:  # 30% chance
                    small_x = random.randint(-20, 20)
                    small_y = random.randint(-20, 20)
                    actions.move_by_offset(small_x, small_y).perform()
                    time.sleep(random.uniform(0.1, 0.2))
                    actions.move_by_offset(-small_x, -small_y).perform()

        def ensure_browser_focused():
            try:
                _ = driver.get_window_rect()  # window_rect

                actions = ActionChains(driver)
                actions.move_to_element(driver.find_element(By.TAG_NAME, "body"))
                actions.perform()

                driver.execute_script("window.focus();")

                driver.maximize_window()

                return True
            except Exception as e:
                log_message(f"Error focusing browser: {str(e)}", "ERROR")
                return False

        def simulate_human_behavior():
            """Simulate human-like mouse movements and scrolling"""
            try:
                # Random scroll with variable speed
                scroll_amount = random.randint(100, 300)
                for _ in range(scroll_amount // 20):  # Smooth scrolling
                    driver.execute_script(
                        f"window.scrollBy(0, {20 + random.randint(-5, 5)});"
                    )
                    time.sleep(random.uniform(0.01, 0.03))
                time.sleep(random.uniform(0.5, 1))

                if not ensure_browser_focused():
                    log_message("Failed to focus browser window", "ERROR")
                    return

                # Human-like mouse movements
                human_like_mouse_movement()

            except Exception as e:
                log_message(f"Error in human behavior simulation: {str(e)}", "ERROR")

        def handle_login():
            """Handle the login process when redirected to login page"""
            try:
                # TODO: Handle recaptcha if possible.. wait for manual solve for now
                account_selector = "#yDmH0d > div.gfM9Zd > div.tTmh9.NQ5OL > div.SQNfcc.WbALBb > div > div > div.Anixxd > div > div > div > form > span > section > div > div > div > div > ul > li.aZvCDf.oqdnae.W7Aapd.zpCp3.SmR8 > div"
                loop_count = 0

                while loop_count <= 30:  # Wait for 5 Min ( 5 min * 60 / 10 = 30 )
                    try:
                        account = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, account_selector)
                            )
                        )
                        break
                    except:
                        if loop_count == 0:
                            log_message(
                                "reCAPTCHA required... waiting until recaptcha got solved...",
                                "WARNING",
                            )
                        loop_count += 1

                if loop_count >= 30:
                    log_message(
                        "Maximum wait time for reCAPTCHA exceeded",
                        "ERROR",
                    )

                    return False

                # Click first signed out account
                account_selector = "#yDmH0d > div.gfM9Zd > div.tTmh9.NQ5OL > div.SQNfcc.WbALBb > div > div > div.Anixxd > div > div > div > form > span > section > div > div > div > div > ul > li.aZvCDf.oqdnae.W7Aapd.zpCp3.SmR8 > div"
                account = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, account_selector))
                )
                simulate_human_behavior()
                account.click()

                # Handle password input
                try:
                    password_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                "#password > div.aCsJod.oJeWuf > div > div.Xb9hP > input",
                            )
                        )
                    )
                    # Let autofill handle the password
                    time.sleep(2)

                    manual_login_wait_count = 0
                    if password_field.get_attribute("data-initial-value") != "":
                        log_message(
                            "Couldn't find any saved password, waiting for manual Password entry. Make sure to submit the password after entering",
                            "INFO",
                        )
                        while True:
                            time.sleep(5)
                            manual_login_wait_count += 5

                            if password_field.get_attribute("data-initial-value") == "":
                                raise TimeoutException  # To make sure that password isn't submitted in the middle of entering the password
                            if manual_login_wait_count > 240:
                                log_message(
                                    "Maximum wait time for manual login Exceeded",
                                    "ERROR",
                                )
                                return False

                    password_field.send_keys(Keys.ENTER)
                except TimeoutException:
                    pass

                # Handle "Not now" button
                try:
                    not_now_button = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                "#yDmH0d > div.gfM9Zd > div.tTmh9.NQ5OL > div.SQNfcc.WbALBb > div > div > div.fby5Ed > div > div.SxkrO > div > div > button > span",
                            )
                        )
                    )
                    not_now_button.click()
                    time.sleep(2)
                except TimeoutException:
                    pass

                return True
            except Exception as e:
                log_message(f"Error in login process: {str(e)}", "ERROR")
                return False

        for review_url in reviews_to_report:
            try:
                log_message(f"Processing review URL: {review_url[:100]}.....", "INFO")
                driver.get(review_url)
                time.sleep(random.uniform(1, 2))
                review_report_failed = False

                # Check if redirected to login page
                if (
                    driver.current_url.startswith("https://accounts.google.com/")
                    or driver.current_url != review_url
                ):
                    log_message("Login required. Handling login process...", "INFO")
                    if not handle_login():
                        log_message("Login failed, skipping this review", "ERROR")
                        continue

                    # Reload the review URL after login
                    driver.get(review_url)
                    time.sleep(2)

                    # Check if redirected to login again
                    if driver.current_url.startswith("https://accounts.google.com/v3"):
                        log_message(
                            "Redirected to login again, closing session", "ERROR"
                        )
                        break

                simulate_human_behavior()

                try:
                    spam_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                "#yDmH0d > c-wiz > div > ul > li:nth-child(2) > a",
                            )
                        )
                    )
                    spam_button.click()
                except Exception as e:
                    log_message(f"Error clicking spam button: {str(e)}", "ERROR")
                    continue

                try:
                    submit_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                "#yDmH0d > c-wiz.zQTmif.SSPGKf.eejsDc.BE677d > div > div.mhBSmf > div > div > button > span",
                            )
                        )
                    )

                    time.sleep(0.5)
                    submit_button.click()

                    try:
                        # TODO: use the actual selector
                        _ = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable(
                                (
                                    By.CSS_SELECTOR,
                                    "selector..",
                                )
                            )
                        )
                        review_report_failed = True
                    except:
                        pass

                except Exception as e:
                    log_message(f"Error clicking submit button: {str(e)}", "ERROR")
                    continue

                # If failed try to report it as offtopic
                if review_report_failed:
                    simulate_human_behavior()

                    try:
                        offtopic_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (
                                    By.CSS_SELECTOR,
                                    "#yDmH0d > c-wiz > div > ul > li:nth-child(1) > a",
                                )
                            )
                        )
                        offtopic_button.click()
                    except Exception as e:
                        log_message(
                            f"Error clicking offtopic button: {str(e)}", "ERROR"
                        )
                        continue

                    try:
                        submit_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (
                                    By.CSS_SELECTOR,
                                    "#yDmH0d > c-wiz.zQTmif.SSPGKf.eejsDc.BE677d > div > div.mhBSmf > div > div > button > span",
                                )
                            )
                        )

                        time.sleep(0.5)
                        submit_button.click()

                        try:
                            # TODO: use the actual selector
                            _ = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable(
                                    (
                                        By.CSS_SELECTOR,
                                        "selector..",
                                    )
                                )
                            )
                            review_report_failed = True
                        except:
                            pass

                    except Exception as e:
                        log_message(
                            f"Error clicking submit button while trying again: {str(e)}",
                            "ERROR",
                        )
                        continue

                # If that also failed simply move on to the next review
                if review_report_failed:
                    log_message(
                        f"Failed to to report review: {review_url[:100]}.....",
                        "ERROR",
                    )
                else:
                    log_message(
                        f"Successfully reported review for {review_url[:100]}.....",
                        "INFO",
                    )

                # Wait random time between reviews
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                log_message(f"Error processing review URL: {str(e)}", "ERROR")
                continue

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
        resume = False
        reviews_to_report = []
        last_processed_profile_idx = 0
        last_processed_profile, input_file = load_last_processed_data()

        if last_processed_profile and input_file:
            print(
                f"{Config.YELLOW}Found unfinished review reports. Profile Id: `{last_processed_profile}`, Review File: `{input_file.split('/')[-1]}`. ( Press y to resume anything else to skip... ):{Config.RESET}",
                end=" ",
            )
            resume_inp = input()

            if resume_inp.lower().strip() == "y":
                log_message("Resuming review reporter....", "INFO")
                resume = True
            else:
                log_message("Starting the review process from scratch...", "INFO")
                input_file = None
                save_last_processed_data(None, None)

        if not input_file:
            input_file = choose_file()

        if input_file is None:
            sys.exit(1)

        with open(input_file, "r") as f:
            reviews_to_report = json.load(f)

        if len(reviews_to_report) <= 0:
            log_message(
                f"Review file `{input_file}` doesn't contain any reviews to report"
            )
            sys.exit(1)

        log_message(
            f"Starting review reporter for review file: `{input_file.split('/')[-1]}`, total reviews to report: {len(reviews_to_report)}",
            "INFO",
        )

        # Fetch & Process all profiles / the selected profiles
        all_profiles = get_browser_profiles()
        profiles = get_selected_profiles(all_profiles)

        if resume:
            last_processed_profile_idx = next(
                (
                    idx
                    for idx, profile in enumerate(profiles)
                    if profile.get("id", None) == last_processed_profile
                ),
                0,
            )

        log_message(
            f"Found {len(profiles[last_processed_profile_idx:])} profiles to process",
            "INFO",
        )

        for profile in profiles[last_processed_profile_idx:]:
            try:
                profile_id = profile["id"]
                profile_name = profile["name"]
                log_message(
                    f"Processing profile '{profile_name}' - {profile_id} ( CTRL + C to exit )",
                    "INFO",
                )
                perform_automation(profile_id, reviews_to_report)
                time.sleep(random.uniform(1, 3))
                save_last_processed_data(profile_id, input_file)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except Exception as e:
                log_message(f"Processing one of the profile: {str(e)}", "ERROR")
                # Try to save the profil_id
                try:
                    save_last_processed_data(profile["id"], input_file)
                except:
                    pass

    except KeyboardInterrupt:
        log_message("Shutting down gracefully...", "INFO")
    except Exception as e:
        log_message(f"Critical error in main: {e}", "CRITICAL")
        sys.exit(1)


if __name__ == "__main__":
    main()
