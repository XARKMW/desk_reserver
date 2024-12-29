from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import logging
from secure_credentials import SecureCredentialHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeskBookingBot:
    def __init__(self, chrome_options=None):
        # Set up Chrome options if not provided
        if chrome_options is None:
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')

        self.chrome_options = chrome_options

        # Load secure credentials
        credential_handler = SecureCredentialHandler()
        credentials = credential_handler.load_credentials()

        # Set credentials
        self.username = credentials['BOOKING_USERNAME']
        self.password = credentials['BOOKING_PASSWORD']
        self.booking_url = credentials['BOOKING_URL']

        if not all([self.username, self.password, self.booking_url]):
            raise ValueError("Missing required credentials")

    def setup_driver(self):
        """Initialize and return a Chrome WebDriver"""
        service = Service(executable_path='/opt/chrome/chromedriver')
        driver = webdriver.Chrome(service=service, options=self.chrome_options)
        driver.implicitly_wait(10)
        return driver

    def login(self, driver):
        """Handle the login process"""
        try:
            driver.get(self.booking_url)
            logger.info("Navigating to booking URL")

            # What's your workspace?
            workspace_input = driver.find_element(By.CSS_SELECTOR, "[aria-label='your-workspace-url']")
            workspace_input.send_keys("unimelb")
            workspace_button = driver.find_element(By.CSS_SELECTOR, ".sc-17uyjaq-5")
            workspace_button.click()
            # Wait for procession to login page
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "okta-login-container"))
            )
            logger.info("Login page loaded")

            # Enter Username
            username_field = driver.find_element(By.ID, "input28")
            next_button = driver.find_element(By.CSS_SELECTOR, "input[value='Next']")
            username_field.send_keys(self.username)
            next_button.click()
            # Wait for Next
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[text()='Verify with your password']"))
            )
            logger.info("Username entered")

            # Enter Password
            password_field = driver.find_element(By.ID, "input54")
            verify_button = driver.find_element(By.CSS_SELECTOR, "input[value='Verify']")
            password_field.send_keys(self.password)
            verify_button.click()
            # Wait for Okta
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".authenticator-verify-list"))
            )
            logger.info("Password entered")

            # Okta push notification verify
            push_notification_button = driver.find_element(By.CSS_SELECTOR, "[data-se='okta_verify-push']")
            push_notification_button.click()
            logger.info("Push notification sent")

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    def book_desk(self, driver, desk_id="preferred-desk-id"):
        """Handle the desk booking process"""
        try:
            # Await page
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".openseadragon-canvas"))
            )
            logger.info("Booking page loaded")

            # Note: Commenting out actual booking for testing
            # desk_element = WebDriverWait(driver, 10).until(
            #     EC.element_to_be_clickable((By.ID, desk_id))
            # )
            # desk_element.click()
            #
            # # Confirm booking
            # confirm_button = driver.find_element(By.ID, "confirm-booking")
            # confirm_button.click()
            #
            # # Wait for confirmation
            # WebDriverWait(driver, 10).until(
            #     EC.presence_of_element_located((By.CLASS_NAME, "booking-confirmation"))
            # )

            logger.info(f"Successfully reached booking stage for desk {desk_id}")

        except Exception as e:
            logger.error(f"Desk booking failed: {str(e)}")
            raise

    def run_booking_sequence(self):
        """Execute the complete booking sequence"""
        driver = None
        try:
            driver = self.setup_driver()
            logger.info("Driver setup complete")
            self.login(driver)
            self.book_desk(driver)
            return True

        except Exception as e:
            logger.error(f"Booking sequence failed: {str(e)}")
            return False

        finally:
            if driver:
                driver.quit()