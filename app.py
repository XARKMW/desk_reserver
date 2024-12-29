import json
import boto3
from botocore.exceptions import ClientError
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
import logging

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize global credentials
try:
    logger.info("Attempting to load credentials from SSM")
    ssm = boto3.client('ssm')
    USERNAME = ssm.get_parameter(
        Name='/desk_booking/username',
        WithDecryption=True
    )['Parameter']['Value']
    PASSWORD = ssm.get_parameter(
        Name='/desk_booking/password',
        WithDecryption=True
    )['Parameter']['Value']
    BOOKING_URL = "https://engage.spaceiq.com/floor/1667/desks/16193"

    if not all([USERNAME, PASSWORD, BOOKING_URL]):
        raise ValueError("Missing required credentials")
    logger.info("Successfully initialized credentials")
except Exception as e:
    logger.error(f"Credential initialization failed: {str(e)}")
    raise

def setup_driver(proxy=None):
    """Initialize and return a Chrome WebDriver with enhanced options"""
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

    # Additional stability options
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # New network and security options
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    chrome_options.add_argument("--dns-prefetch-disable")
    chrome_options.add_argument("--network-settings=native")

    # Enhanced user agent
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
        logger.info("Setting up Chrome driver with enhanced options")
        service = Service(executable_path="/opt/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options, seleniumwire_options=options)

        # Set network conditions
        driver.set_network_conditions(
            latency=100,  # Additional latency (ms)
            download_throughput=500 * 1024,  # Maximal throughput
            upload_throughput=500 * 1024  # Maximal throughput
        )

        logger.info("Chrome driver setup successful")
        return driver
    except Exception as e:
        logger.error(f"Driver setup failed: {str(e)}")
        raise

def login(driver):
    """Handle the login process with enhanced error handling and logging"""
    current_step = "initial"
    try:
        logger.info(f"Starting login process at URL: {BOOKING_URL}")

        # Initial page load with logging
        current_step = "page_load"
        driver.get(BOOKING_URL)

        # Wait for initial body load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logger.info("Initial page body loaded")

        # Workspace input step
        current_step = "workspace_input"
        workspace_input = WebDriverWait(driver, 30).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='your-workspace-url']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='workspace']"))
            )
        )
        workspace_input.send_keys("unimelb")
        logger.info("Entered workspace URL")

        # Find and click workspace button with multiple possible selectors
        workspace_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".sc-17uyjaq-5, button[type='submit']"))
        )
        workspace_button.click()
        logger.info("Clicked workspace button")

        # Wait for SSO login form
        current_step = "sso_form_wait"
        logger.info("Waiting for SSO login form...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "form[class*='o-form']"))
        )
        logger.info("SSO login form detected")

        # Username field detection
        current_step = "username_input"
        username_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='identifier']"))
        )

        # Add a small delay before typing
        driver.implicitly_wait(2)
        username_field.clear()
        username_field.send_keys(USERNAME)
        logger.info("Username entered")

        # Click next button
        next_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input.button.button-primary[type='submit'][value='Next']"))
        )
        next_button.click()
        logger.info("Next button clicked")

        # Wait for password page with enhanced error handling
        current_step = "password_page_wait"
        WebDriverWait(driver, 30).until(
            EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//*[text()='Verify with your password']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='credentials.passcode']"))
            )
        )
        logger.info("Password verification page loaded")

        # Enhanced password field handling
        current_step = "password_input"
        password_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='credentials.passcode'], input[type='password']"))
        )
        verify_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='Verify'], button[type='submit']"))
        )

        password_field.send_keys(PASSWORD)
        verify_button.click()
        logger.info("Password entered and verify button clicked")

        # Wait for Okta authenticator with enhanced timeout
        current_step = "okta_authenticator_wait"
        WebDriverWait(driver, 45).until(  # Increased timeout for authenticator
            EC.presence_of_element_located((By.CSS_SELECTOR, ".authenticator-verify-list"))
        )
        logger.info("Okta authenticator list loaded")

        # Enhanced push notification handling
        current_step = "push_notification"
        push_notification_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-se='okta_verify-push'], .push-authentication"))
        )
        push_notification_button.click()
        logger.info("Push notification sent successfully")

    except Exception as e:
        logger.error(f"Login failed at step: {current_step}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception message: {str(e)}")
        logger.error(f"Current URL: {driver.current_url}")
        try:
            logger.error(f"Page title: {driver.title}")
            logger.error(f"DOM snapshot: {driver.page_source[:1000]}")
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

        # Select desk
        desk_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, desk_id))
        )
        desk_element.click()

        # Confirm booking
        confirm_button = driver.find_element(By.ID, "confirm-booking")
        confirm_button.click()

        # Wait for confirmation
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "booking-confirmation"))
        )

        logger.info(f"Successfully booked desk {desk_id}")

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