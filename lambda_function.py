import json
from desk_booking_bot import DeskBookingBot
from selenium.webdriver.chrome.options import Options
import os
import shutil

def lambda_handler(event, context):
    # Set up /tmp directory for Chrome
    chrome_path = '/tmp/chrome'
    if not os.path.exists(chrome_path):
        os.makedirs(chrome_path)

    # Configure Chrome options for Lambda environment
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-dev-tools')
    chrome_options.add_argument('--no-zygote')
    chrome_options.add_argument('--single-process')
    chrome_options.add_argument(f'--user-data-dir={chrome_path}')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.binary_location = '/opt/chrome/chrome'

    try:
        # Initialize and run the booking bot
        bot = DeskBookingBot(chrome_options)
        success = bot.run_booking_sequence()

        # Clean up /tmp
        shutil.rmtree(chrome_path, ignore_errors=True)

        return {
            'statusCode': 200 if success else 500,
            'body': json.dumps({
                'message': 'Desk booking successful' if success else 'Desk booking failed',
                'success': success
            })
        }

    except Exception as e:
        # Clean up /tmp even if there's an error
        shutil.rmtree(chrome_path, ignore_errors=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Error: {str(e)}',
                'success': False
            })
        }