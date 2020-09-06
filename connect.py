import argparse
import logging
import re
import requests
import sys
import time

from logging.handlers import RotatingFileHandler

# Configuration
# -------------
# Your credentials
USERNAME = "PUT_YOUR_USERNAME_HERE"
PASSWORD = "PUT_YOUR_PASSWORD_HERE"
# URL to be tested for checking internet access
TEST_URL = "http://www.google.com"
# Time in seconds between each login renewal
RENEW_INTERVAL = 3600
# Time in seconds between login retry when connection is lost
LOGIN_RETRY_INTERVAL = 10

# Get logger
# ----------
logger = logging.getLogger("wifirst_connect")


# Main function and its helpers
# -----------------------------
def connect(username, password):
    # Try to access internet
    try:
        web_page = requests.get(TEST_URL, allow_redirects=False)
    except:
        logger.error("Unable to access the network.")
        return False

    if web_page.status_code == 200:
        logger.info("Already logged in.")
        return True

    if web_page.status_code != 302:
        logger.error(f"Unexpected HTTP result for {TEST_URL}.")
        return False

    # Redirected to the Wifirst login page
    try:
        wifirst_page = requests.get("https://selfcare.wifirst.net/sessions/new")
    except:
        logger.error("Unable to reach Wifirst selfcare site.")
        return False

    if wifirst_page.status_code != 200:
        logger.error("Unable to reach Wifirst redirected site.")
        return False

    # Get the form token value
    # The token is the only value with 46 characters
    try:
        token_regex = re.compile('value="([^"]{30,})"')
        token = token_regex.search(str(wifirst_page.content)).group(1)
    except:
        logger.error("Unable to retrieve the login token.")
        return False

    logger.info(f"Login token: {token}.")

    # A session is used to keep the cookies through the process
    session = requests.Session()
    post_data = {
        "login": username,
        "password": password,
        "authenticity_token": token,
        "utf8": "&#x2713",
    }

    # Send the authentication form, with the credentials
    try:
        wifirst_page = session.post("https://selfcare.wifirst.net/sessions", data=post_data, allow_redirects=False)
    except:
        logger.error("Unable to send the credentials through the authentication form.")
        return False

    # If the self care POST returns 200, it means that the Wifirst authentiation failed
    if wifirst_page.status_code == 200:
        logger.error("Wrong credentials.")
        return False

    # If the authentication is ok, a redirection should take place
    if wifirst_page.status_code != 302:
        logger.error(f"Wifirst logging form returned {str(wifirst_page.status_code)}")
        return False

    try:
        wifirst_page = session.get("https://connect.wifirst.net/?perform=true")
    except:
        logger.error("Unable to reach Wifirst redirected site.")
        return False

    # The returned page content has an automatically filled form, that will submit on loading.
    # On a Browser, as the content has an 'onLoad' function, it will automatically send the
    # form with the credentials.
    # Here, we don't have a browser so the form will have to be sent manually.

    # Wifirst login form
    try:
        action_regex = re.compile('action="(https://[a-zA-Z0-9:\./]+)"')
        username_regex = re.compile('name="username"\s+type="hidden"\s+value="(w/[0-9]+@wifirst.net)"')
        password_regex = re.compile('name="password"\s+type="hidden"\s+value="([a-zA-Z0-9]+)"')

        action_val = action_regex.search(str(wifirst_page.content)).group(1)
        username_val = username_regex.search(str(wifirst_page.content)).group(1)
        password_val = password_regex.search(str(wifirst_page.content)).group(1)
    except:
        logger.error("Unable to retrieve the Wifirst credentials.")
        return False

    logger.info(f"Wifirst Usename='{username_val}' Password='******' LoginPage='{action_val}'.")

    # Now send the second authentication form and credentials
    post_data = {
        "username": username_val,
        "password": password_val,
        "qos_class": "",
        "success_url": TEST_URL,
        "error_url": "https://connect.wifirst.net/login_error",
    }

    try:
        wifirst_page = session.post(action_val, data=post_data, allow_redirects=True)
    except:
        logger.error("Unable to reach Wifirst login form.")
        return False

    if wifirst_page.status_code != 200:
        logger.error(f"Final authentication failed with error {str(wifirst_page.status_code)}.")
        return False

    if wifirst_page.url != TEST_URL:
        logger.error(f"Authentication failed, redirected to {wifirst_page.url}.")
        return False

    logger.info("Authentication successful.")
    return True


def setup_logging(verbose, silent, output):
    log_level = logging.DEBUG if verbose else logging.INFO

    # Setup format
    logger.setLevel(log_level)
    formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(message)s")

    # Setup file logging
    if output:
        file_handler = RotatingFileHandler(output, "a", 1000000, 1)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Setup stdout logging
    if not silent:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)
        logger.addHandler(stream_handler)


def main(args):
    setup_logging(args.verbose, args.silent, args.output)

    # Keep running no matter what
    while True:
        # On success: wait before checking status again
        # On failure: retry until it works
        if connect(USERNAME, PASSWORD):
            logger.info("Retry in 1 hour.")
            time.sleep(RENEW_INTERVAL)
        else:
            logger.info("Retry in 10 seconds.")
            time.sleep(LOGIN_RETRY_INTERVAL)


# File execution handling
# -----------------------
def parse_command_line(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Set logging level to DEBUG.")
    parser.add_argument("-s", "--silent", action="store_true", help="Do not log to stdout.")
    parser.add_argument("-o", "--output", metavar="FILE", help="Log to file.")
    return parser.parse_args(argv[1:])


if __name__ == "__main__":
    args = parse_command_line(sys.argv)
    main(args)
