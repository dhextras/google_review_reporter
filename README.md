# GRR (Google Review Reporter) Setup Guide

Follow these steps to set up and run the Google Review Reporter project.

## Prerequisites

Make sure you have the following installed:

- **Python** (preferably version 3.6 or higher)
- **pip** (Python package installer)

If you don't have Python and pip installed, you can install them using the following command:

```bash
sudo apt update
sudo apt install python3 python3-pip
```


## Step 1: Create a `.env` File

1. **Create a file named `.env` or copy the `.env.example` in the root directory.**
2. **Add the following details:**

   ```plaintext
   DOLPHIN_BASE_URL= # Mostly http://localhost:3001 but change it if you customize
   DOLPHIN_API_KEY= # Dolphin Api key grab it in https://dolphin-anty.com/panel/#/api
   ```

**Note:** Fill in the values for each variable as needed.

## Step 2: Create a `cred/selected_profiles.json` file

> Create this file or copy the example file. if you wanna select the profiles you want the automation to use

- Example: 
   ```json
   ["Profile xxx", "Profile yyy", "Profile zzz", "Profile www"]
   ```
   
## Step 3: Install Google Chrome and ChromeDriver


1. **Install Google Chrome:**

   ```bash
   cd /tmp/
   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
   sudo dpkg -i google-chrome-stable_current_amd64.deb
   sudo apt-get install -f
   ```

2. **Install ChromeDriver:**

   Replace `VERSION` with the version of Chrome you installed (e.g., `130.0.6723.58`):

   ```bash
   cd /tmp/
   sudo wget https://storage.googleapis.com/chrome-for-testing-public/VERSION/linux64/chromedriver-linux64.zip
   sudo unzip chromedriver_linux64.zip
   cd chromedriver_linux64
   sudo mv chromedriver /usr/bin/chromedriver
   ```

   ### Verify Installation

   Check that ChromeDriver is installed correctly by running:

   ```bash
   chromedriver --version
   ```

## Step 4: Run the Scripts

Fetch all the reports of who ever user you wanna report then report them one by one


- To run the **Review fetcher**, use:

  ```bash
  python fetch_reviews.py
  ```

- To run the **Review reporter**, use:

  ```bash
  python report_reviews.py
  ```

Make sure your `.env` file if properly set up before running these scripts.

## File Structure Overview

```plaintext
google_review_reporter/
├── data/                    # Folder to save scraper reports to access later
├── log/                     # Folder for log files
├── .env                     # Environment variables
├── .env.example             # Environment variables
├── .gitignore               # Git ignore file
├── README.md                # Project documentation
├── fetch_reviews.py         # Fetch specific users Reviews
└── report_reviews.py        # Report all reviews on all dolphin browser profiles
```
