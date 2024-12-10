from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
from secure_credentials import SecureCredentialHandler
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeskBookingBot:
    def __init__(self):
        self.chrome_options = Options()
        # self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')

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
        driver = webdriver.Chrome(options=self.chrome_options)
        driver.implicitly_wait(10)
        return driver

    def login(self, driver):
        """Handle the login process"""
        try:
            driver.get(self.booking_url)

            # What's your workspace?
            workspace_input = driver.find_element(By.CSS_SELECTOR, "[aria-label='your-workspace-url']")
            workspace_input.send_keys("unimelb")
            workspace_button = driver.find_element(By.CSS_SELECTOR, ".sc-17uyjaq-5")
            workspace_button.click()
            # Wait for procession to login page
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "okta-login-container"))
            )
            logger.info("Login page")

            # Enter Username
            username_field = driver.find_element(By.ID, "input28")
            next_button = driver.find_element(By.CSS_SELECTOR, "input[value='Next']")
            username_field.send_keys(self.username)
            next_button.click()
            # Wait for Next
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[text()='Verify with your password']"))
            )

            # Enter Password
            password_field = driver.find_element(By.ID, "input54")
            verify_button = driver.find_element(By.CSS_SELECTOR, "input[value='Verify']")
            password_field.send_keys(self.password)
            verify_button.click()
            # Wait for Okta
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".authenticator-verify-list"))
            )

            # Okta push notification verify
            push_notification_button = driver.find_element(By.CSS_SELECTOR, "[data-se='okta_verify-push']")
            push_notification_button.click()

            logger.info("Awaiting push notification")

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    def book_desk(self, driver, desk_id="preferred-desk-id"):
        """Handle the desk booking process"""
        try:
            # Navigate to booking page
            booking_page = driver.find_element(By.ID, "booking-section")
            booking_page.click()

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
            raise

    def run_booking_sequence(self):
        """Execute the complete booking sequence"""
        driver = None
        try:
            driver = self.setup_driver()
            self.login(driver)
            self.book_desk(driver)
            return True

        except Exception as e:
            logger.error(f"Booking sequence failed: {str(e)}")
            return False

        finally:
            if driver:
                driver.quit()

def main():
    bot = DeskBookingBot()
    success = bot.run_booking_sequence()
    # Exit with appropriate status code for AWS
    exit(0 if success else 1)

if __name__ == "__main__":
    main()