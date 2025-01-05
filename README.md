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

   GEELARK_APP_ID= # You can find this Geelark Application > Discover > Api > Connection
   GEELARK_APP_KEY= # Discover > Api > API key ( need to generate )
   ```

**Note:** Fill in the values for each variable as needed.

## Step 2: Create a `cred/selected_XXXXX.json` file

`cred/selected_profiles.json` - for browser automation
`cred/selected_phones.json` - for mobile automation

> Create this file or copy the example file. if you wanna select the profiles you want the automation to use - Skip this if you wanna use all of em

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

- To run the **Profile reporter** with mobile, use:

  ```bash
  python report_profile.py
  ```

> This isn't fully finished so you have to run the RPA task manually until they finis new api for custom rpa tasks

      - **Small note: If you want to see task being ran on live ( make sure to start the phone before running these)**
      - Open Geelark Application. Go to Discover > Automation > custom tasks
      - In Google profile report click on the `>` play lie button
      - Create Common Tas > Add phone
      - Select All the phones you wanted to run this for and click ok
      - For each phones pubDate choose now
      - For each phones 
         - If reporting entire profile - profileUrl Enter the profile link you wanted to report ( must be a short link other wise wont work in some situations )
         - If reporting each reviews seperately - Enter the list of urls you got from running 'fetch_reviews.py' script
      - Click on Execution History to see the execution details

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
├── report_profile.py        # Report the user profile from all the mobiles in geelark
└── report_reviews.py        # Report all reviews on all dolphin browser profiles
```
