import gzip
import inspect
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime

# Constants
DATA_DIR = "data"


class Config:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"


def install_requirements():
    try:
        import brotli as _
        import inquirer as _
        import selenium as _
        import seleniumwire as _
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
                "selenium",
                "selenium-wire",
                "blinker==1.7.0",
                "brotli",
                "inquirer",
            ]
        )
        print(
            f"{Config.GREEN}Required libraries installed successfully.{Config.RESET}\n"
        )


install_requirements()

import brotli
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver as wire_webdriver


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",
        "INFO": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[95m",
        "RESET": "\033[0m",
    }

    def format(self, record):
        log_message = super().format(record)
        return f"{self.COLORS.get(record.levelname, self.COLORS['RESET'])}{log_message}{self.COLORS['RESET']}"


def setup_logger(log_file=None):
    caller_script = inspect.stack()[2].filename
    script_name = os.path.splitext(os.path.basename(caller_script))[0]
    logger_name = script_name
    date = datetime.now().strftime("%m_%d")

    # Create log directory if it doesn't exist
    log_directory = "log"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_file = log_file or os.path.join(log_directory, f"{script_name}_{date}.log")

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

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


def log_message(message, level="INFO"):
    logger = setup_logger()
    getattr(logger, level.lower())(message)


def choose_actions():
    """
    Displays a graphical interface to for user to choose the script options
    """

    import inquirer

    actions = [
        "Genearte Direct Report links - Dolphin",
        "Genearte Short links - Geelark",
    ]

    questions = [
        inquirer.List(
            "action",
            message="Select what you wanna fetch ( Use arrow keys to choose )",
            choices=actions,
        ),
    ]

    answers = inquirer.prompt(questions)

    if not answers:
        return None
    selected_action = answers["action"]
    return selected_action


def ensure_data_directory():
    """Create data directory if it doesn't exist"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        log_message(f"Created data directory at {DATA_DIR}", "INFO")


def decode_url(url):
    """Decode Google review URLs"""
    url = url.replace("\\\\u003d", "=")
    url = url.replace("\\\\u0026", "&")
    url = url.replace("\\u003d", "=")
    url = url.replace("\\u0026", "&")
    return url


def extract_short_urls_from_response(response_text):
    """Extract Google review URLs from response text using regex"""
    urls = set()
    pattern = re.compile(r'https://maps\.app\.goo\.gl/[^"\'}\s]*')
    matches = pattern.findall(response_text)
    urls.update(matches)
    return [decode_url(url) for url in urls]


def extract_report_urls_from_response(response_text):
    """Extract Google review URLs from response text using regex"""
    urls = set()
    pattern = re.compile(
        r'https://www\.google\.com/local/review/rap/report\?postId[^"\'}\s]*'
    )
    matches = pattern.findall(response_text)
    urls.update(matches)
    return [decode_url(url) for url in urls]


def scroll_through_available_reviews(driver, url):
    """Open user review and scroll until all the reviews have been loaded"""

    try:
        log_message(f"Navigating to user reviews: {url}", "INFO")
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        reviews_xpath = '//*[@aria-label="Reviews"]'
        total_reviews_element = wait.until(
            EC.presence_of_element_located((By.XPATH, reviews_xpath))
        )
        total_reviews_wait = WebDriverWait(total_reviews_element, 20)

        # Get total reviews count
        total_reviews_element = total_reviews_wait.until(
            lambda element: element.find_element(By.XPATH, "./div[1]/div[1]/span/span")
        )
        total_reviews_numbers = re.sub(r"[^0-9\s]", "", total_reviews_element.text)
        total_reviews_numbers = (
            re.sub(r"\s+", " ", total_reviews_numbers).strip().split(" ")
        )
        total_reviews = sum([int(i) for i in total_reviews_numbers])
        log_message(f"Found {total_reviews} total reviews to process", "INFO")

        expected_total_divs = total_reviews * 2 - 1
        reviews_container = total_reviews_wait.until(
            lambda element: element.find_element(By.XPATH, "./div[2]")
        )
        scrollable_div = wait.until(
            EC.presence_of_element_located((By.XPATH, reviews_xpath))
        )

        # Scroll through reviews
        last_current_div = 0
        max_scroll = 0
        while True:
            current_divs = len(reviews_container.find_elements(By.XPATH, "./div"))
            if last_current_div == current_divs:
                time.sleep(1)
                max_scroll += 1
            if current_divs >= expected_total_divs or max_scroll >= 10:
                break

            max_scroll = 0
            last_current_div = current_divs
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight",
                scrollable_div,
            )
            time.sleep(1)

    except Exception as e:
        log_message(f"Error during review extraction: {str(e)}", "ERROR")


def intercept_review_requests(user_id):
    """Process and extract direct review report URLs for a given user ID"""
    url = f"https://www.google.com/maps/contrib/{user_id}/reviews"
    all_review_urls = set()

    # Setup Chrome driver with selenium-wire
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    driver = wire_webdriver.Chrome(options=chrome_options)

    try:
        scroll_through_available_reviews(driver, url)

        # Process network requests
        for request in driver.requests:
            if request.response and "/locationhistory/preview/mas" in request.url:
                try:
                    response_data = brotli.decompress(request.response.body)
                    decoded_str = response_data.decode("utf-8")
                    urls = extract_report_urls_from_response(decoded_str)
                    all_review_urls.update(urls)
                except Exception as e:
                    log_message(f"Error processing response: {str(e)}", "ERROR")

        # Process initial state
        app_initial_state = driver.execute_script(
            "return window.APP_INITIALIZATION_STATE"
        )
        urls = extract_report_urls_from_response(str(app_initial_state))
        all_review_urls.update(urls)

        log_message(f"Found {len(all_review_urls)} unique review URLs", "INFO")
        return list(all_review_urls)

    except Exception as e:
        log_message(f"Error during review extraction: {str(e)}", "ERROR")
        return []

    finally:
        driver.quit()


def intercept_review_short_url_requests(user_id):
    """Process and extract short review URLs for a given user ID"""
    url = f"https://www.google.com/maps/contrib/{user_id}/reviews"
    short_review_urls = set()

    # Setup Chrome driver with selenium-wire
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    driver = wire_webdriver.Chrome(options=chrome_options)

    try:
        scroll_through_available_reviews(driver, url)

        # Extract available share buttons and click em
        share_buttons_selector = "#QA0Szd > div > div > div.w6VYqd > div:nth-child(2) > div > div.e07Vkf.kA9KIf > div > div > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde > div.m6QErb.XiKgde > * > div:nth-child(2) > div > div:nth-child(4) > div.Upo0Ec > button:nth-child(2)"
        share_buttons = driver.find_elements(By.CSS_SELECTOR, share_buttons_selector)

        wait = WebDriverWait(driver, 20)
        close_button_selector = "#modal-dialog > div > div.hoUMge > div > button"
        copy_link_selector = "#modal-dialog > div > div.hoUMge > div > div.yFnP6d > div > div > div > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde > div.NB4yxe > div.WVlZT > button"

        for button in share_buttons:
            try:
                button.click()
                time.sleep(0.1)

                # Wait for the link to get generated and close the dialog
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, copy_link_selector)
                    )
                )

                driver.find_element(By.CSS_SELECTOR, close_button_selector).click()
            except Exception as e:
                log_message(
                    f"Unabled to generate short link for the button id: '{button.id}', error: {str(e)}"
                )

        # Process network requests
        for request in driver.requests:
            if request.response and "shorturl" in request.url:
                try:
                    decoded_str = gzip.decompress(request.response.body).decode("utf-8")
                    urls = extract_short_urls_from_response(decoded_str)
                    short_review_urls.update(urls)
                except Exception as e:
                    log_message(f"Error processing response: {str(e)}", "ERROR")

        log_message(f"Found {len(short_review_urls)} unique review URLs", "INFO")
        return list(short_review_urls)

    except Exception as e:
        log_message(f"Error during review extraction: {str(e)}", "ERROR")
        return []

    finally:
        driver.quit()


def main():
    ensure_data_directory()

    action = choose_actions()
    if not action:
        log_message("Unrecognized action to take", "ERROR")
        sys.exit(1)

    user_id = input("User ID: ")
    log_message("Starting review scraping process", "INFO")

    if action == "Genearte Direct Report links - Dolphin":
        file_prefix = "review_report"
        review_urls = intercept_review_requests(user_id)
    elif action == "Genearte Short links - Geelark":
        file_prefix = "review_short_links"
        review_urls = intercept_review_short_url_requests(user_id)
    else:
        log_message("Unrecognized action to take", "ERROR")
        sys.exit(1)

    if review_urls:
        output_file = os.path.join(DATA_DIR, f"{file_prefix}_{user_id}.json")
        with open(output_file, "w") as f:
            json.dump(review_urls, f)
        log_message(
            f"Successfully saved {len(review_urls)} review URLs to {output_file}. for action: '{action}'",
            "INFO",
        )
    else:
        log_message("No review URLs were found", "WARNING")


if __name__ == "__main__":
    main()
