import json
import boto3
from botocore.exceptions import ClientError
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import logging

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

def load_credentials():
    """Load credentials from AWS SSM Parameter Store"""
    try:
        logger.info("Attempting to load credentials from SSM")
        ssm = boto3.client('ssm')
        params = {
            'BOOKING_USERNAME': ssm.get_parameter(
                Name='/desk_booking/username',
                WithDecryption=True
            )['Parameter']['Value'],
            'BOOKING_PASSWORD': ssm.get_parameter(
                Name='/desk_booking/password',
                WithDecryption=True
            )['Parameter']['Value'],
            'BOOKING_URL': "https://engage.spaceiq.com/floor/1667/desks/16193"
        }
        logger.info("Successfully loaded credentials from SSM")
        return params
    except ClientError as e:
        logger.error(f"Failed to load credentials from SSM: {str(e)}")
        raise Exception(f"Failed to load credentials from SSM: {str(e)}")

# Load credentials at module level
try:
    credentials = load_credentials()
    USERNAME = credentials['BOOKING_USERNAME']
    PASSWORD = credentials['BOOKING_PASSWORD']
    BOOKING_URL = credentials['BOOKING_URL']

    if not all([USERNAME, PASSWORD, BOOKING_URL]):
        raise ValueError("Missing required credentials")
    logger.info("Successfully initialized credentials")
except Exception as e:
    logger.error(f"Credential initialization failed: {str(e)}")
    raise

def setup_driver(proxy=None):
    """Initialize and return a Chrome WebDriver"""
    def request_interceptor(request):
        logger.info(f"Outgoing request: {request.url}")

    def response_interceptor(request, response):
        logger.info(f"Response from {request.url}: Status {response.status_code}")

    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = "/opt/chrome/chrome"
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("window-size=2560x1440")
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data")
    chrome_options.add_argument("--remote-debugging-port=9222")
    # Additional options for stability
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # Set user agent to look more like a regular browser
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

    options = {
        'request_interceptor': request_interceptor,
        'response_interceptor': response_interceptor
    }

    if proxy is not None:
        options['proxy'] = {
            "http": proxy,
            "https": proxy,
            'no_proxy': 'localhost,127.0.0.1'
        }
        logger.info(f"Setting up proxy: {proxy}")

    try:
        logger.info("Setting up Chrome driver with options")
        service = Service(executable_path="/opt/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options, seleniumwire_options=options)
        logger.info("Chrome driver setup successful")
        return driver
    except Exception as e:
        logger.error(f"Driver setup failed: {str(e)}")
        raise

def login(driver):
    """Handle the login process"""
    try:
        logger.info("Starting login process")

        # Initial page load with increased timeout
        logger.info("Waiting for initial page load...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logger.info("Initial body element found")

        logger.info(f"Navigating to booking URL: {BOOKING_URL}")
        driver.get(BOOKING_URL)
        logger.info("Navigation to booking URL completed")

        # What's your workspace? - increased timeout
        logger.info("Waiting for workspace input field...")
        workspace_input = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='your-workspace-url']"))
        )
        logger.info("Found workspace input field")
        workspace_input.send_keys("unimelb")
        logger.info("Entered workspace URL")

        workspace_button = driver.find_element(By.CSS_SELECTOR, ".sc-17uyjaq-5")
        workspace_button.click()
        logger.info("Clicked workspace button")

        # Wait for login page with increased timeout
        logger.info("Waiting for Okta login container...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "okta-login-container"))
        )
        logger.info("Login page loaded successfully")

        # Enter Username with explicit wait and multiple possible selectors
        logger.info("Waiting for username field...")
        try:
            # Try multiple possible selectors for the username field
            username_field = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                "input[name='identifier'], input[name='username'], input[type='email'], #okta-signin-username"))
            )
            logger.info("Username field found")

            # Try multiple possible selectors for the next button
            next_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                                            "input[value='Next'], button[type='submit'], .button-primary, #okta-signin-submit"))
            )

            # Add a small delay before typing
            driver.implicitly_wait(2)
            username_field.clear()
            username_field.send_keys(USERNAME)
            logger.info("Username entered")

            next_button.click()
            logger.info("Next button clicked")
        except Exception as e:
            logger.error("Failed to interact with username form")
            logger.error(f"Available elements on page: {driver.page_source}")
            raise

        # Wait for password page with increased timeout
        logger.info("Waiting for password verification page...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//*[text()='Verify with your password']"))
        )
        logger.info("Password verification page loaded")

        # Enter Password
        logger.info("Entering password...")
        password_field = driver.find_element(By.CSS_SELECTOR, "input[name='credentials.passcode']")
        verify_button = driver.find_element(By.CSS_SELECTOR, "input[value='Verify']")
        password_field.send_keys(PASSWORD)
        verify_button.click()
        logger.info("Password entered and verify button clicked")

        # Wait for Okta with increased timeout
        logger.info("Waiting for Okta authenticator list...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".authenticator-verify-list"))
        )
        logger.info("Okta authenticator list loaded")

        # Okta push notification verify
        logger.info("Looking for push notification button...")
        push_notification_button = driver.find_element(By.CSS_SELECTOR, "[data-se='okta_verify-push']")
        push_notification_button.click()
        logger.info("Push notification sent successfully")

    except Exception as e:
        logger.error(f"Login failed with exception type: {type(e)}")
        logger.error(f"Login failed with message: {str(e)}")
        logger.error(f"Current URL: {driver.current_url}")
        try:
            logger.error(f"Page source at time of error: {driver.page_source[:1000]}...")  # Increased to 1000 chars
            logger.error("Current page title: %s", driver.title)
            # Log all cookies for debugging
            cookies = driver.get_cookies()
            logger.error(f"Current cookies: {json.dumps(cookies, indent=2)}")
        except Exception as inner_e:
            logger.error(f"Failed to get error details: {str(inner_e)}")
        raise

def book_desk(driver, desk_id="preferred-desk-id"):
    """Handle the desk booking process"""
    try:
        logger.info("Starting desk booking process...")
        # Await page with increased timeout
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".openseadragon-canvas"))
        )
        logger.info("Booking page loaded successfully")

        # Note: Commenting out actual booking for testing
        # desk_element = WebDriverWait(driver, 30).until(
        #     EC.element_to_be_clickable((By.ID, desk_id))
        # )
        # desk_element.click()
        # logger.info(f"Clicked desk {desk_id}")
        #
        # # Confirm booking
        # confirm_button = driver.find_element(By.ID, "confirm-booking")
        # confirm_button.click()
        # logger.info("Clicked confirm booking button")
        #
        # # Wait for confirmation
        # WebDriverWait(driver, 30).until(
        #     EC.presence_of_element_located((By.CLASS_NAME, "booking-confirmation"))
        # )
        # logger.info("Booking confirmation received")

        logger.info(f"Successfully reached booking stage for desk {desk_id}")

    except Exception as e:
        logger.error(f"Desk booking failed: {str(e)}")
        try:
            logger.error(f"Current URL at failure: {driver.current_url}")
            logger.error(f"Page source at failure: {driver.page_source[:1000]}...")
        except:
            logger.error("Could not get failure details")
        raise

def handler(event, context):
    """AWS Lambda handler function"""
    logger.info("Lambda handler started")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info(f"Context: RequestId: {context.aws_request_id}")

    proxy = event.get("proxy")
    driver = None

    try:
        driver = setup_driver(proxy)
        login(driver)
        book_desk(driver)

        logger.info("Booking sequence completed successfully")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Booking sequence completed successfully"
            })
        }

    except Exception as e:
        logger.error(f"Booking sequence failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }

    finally:
        if driver:
            logger.info("Cleaning up driver")
            try:
                driver.quit()
                logger.info("Driver cleanup successful")
            except Exception as e:
                logger.error(f"Driver cleanup failed: {str(e)}")