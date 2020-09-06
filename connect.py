import argparse
import logging
from logging.handlers import RotatingFileHandler
import re
import requests
import sys
import time

# Configuration
# -------------

# Your credentials
USERNAME = "PUT_YOUR_USERNAME_HERE"
PASSWORD = "PUT_YOUR_PASSWORD_HERE"
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
        web_page = requests.get("http://www.google.com", allow_redirects=False)
    except:
        logger.error("Unable to access the network.")
        return False

    if web_page.status_code == 200:
        logger.info("Already logged in.")
        return True

    elif web_page.status_code == 302:

        # Redirected to the Wifirst login site
        try:
            wifirst_page = requests.get("https://selfcare.wifirst.net/sessions/new")
        except:
            logger.error("Unable to reach Wifirst selfcare site.")
            return False

        if wifirst_page.status_code == 200:

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
                wifirst_page = session.post(
                    "https://selfcare.wifirst.net/sessions", data=post_data, allow_redirects=False
                )
            except:
                logger.error("Unable to reach Wifirst selfcare site with a POST request.")
                return False

            # If the authenticatino is ok, a redirection will take place
            if wifirst_page.status_code == 302:

                try:
                    wifirst_page = session.get("https://connect.wifirst.net/?perform=true")
                except:
                    logger.error("Unable to reach Wifirst redirected site.")
                    return False

                # The returned page content has an automatically filled form, that will submit on loading
                # On a Browser, as the content has an 'onLoad' function, it will automatically send the
                # form with the credentials

                # Wifirst login form
                try:
                    form_regex = re.compile('action="(https://[a-zA-Z0-9:\./]+)"')
                    username_regex = re.compile('name="username"\s+type="hidden"\s+value="(w/[0-9]+@wifirst.net)"')
                    password_regex = re.compile('name="password"\s+type="hidden"\s+value="([a-zA-Z0-9]+)"')

                    form_val = form_regex.search(str(wifirst_page.content)).group(1)
                    username_val = username_regex.search(str(wifirst_page.content)).group(1)
                    password_val = password_regex.search(str(wifirst_page.content)).group(1)
                except:
                    logger.error("Unable to retrieve the Wifirst Credentials.")
                    return False

                logger.info(f"Wifirst Usename='{username_val}' LoginPage = '{form_val}'.")

                # Now send the second authentication form and credentials
                post_data = {
                    "username": username_val,
                    "password": password_val,
                    "qos_class": "",
                    "success_url": "http://www.google.com",
                    "error_url": "https://connect.wifirst.net/login_error",
                }

                try:
                    wifirst_page = session.post(form_val, data=post_data, allow_redirects=True)
                except:
                    logger.error("Unable to reach Wifirst login form.")
                    return False

                if wifirst_page.status_code == 200:
                    if wifirst_page.url == "http://www.google.com":
                        logger.info("Authentication sucessfull.")
                        return True
                    else:
                        logger.error(f"Authentication failed, redirected to {wifirst_page.url}.")
                else:
                    logger.error("Final authentication failed with error {str(wifirst_page.status_code)}.")
                    return False

            # If the self care POST returns 200, it means that the Wifirst authentiation failed
            elif wifirst_page.status_code == 200:
                logger.error("Wrong credentials.")
                return False
            else:
                logger.error(f"Wifirst loging form returned {str(wifirst_page.status_code)}")
                return False
        else:
            logger.error("Unable to reach Wifirst redirected site.")
            return False
    else:
        logger.error("Unexpected HTTP result for http://www.google.com.")
        return False


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


def parse_command_line(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Set logging level to DEBUG.")
    parser.add_argument("-s", "--silent", action="store_true", help="Do not log to stdout.")
    parser.add_argument("-o", "--output", metavar="FILE", help="Log to file.")
    return parser.parse_args(argv[1:])


if __name__ == "__main__":
    args = parse_command_line(sys.argv)
    main(args)