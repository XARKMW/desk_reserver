from cryptography.fernet import Fernet
import base64
import getpass
import os
import json
from datetime import datetime
import pytz

class SecureCredentialHandler:
    def __init__(self):
        self.key_file = 'encryption_key.key'
        self.cred_file = 'encrypted_credentials.json'

        # Generate or load encryption key
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as key_file:
                self.key = key_file.read()
        else:
            self.key = Fernet.generate_key()
            with open(self.key_file, 'wb') as key_file:
                key_file.write(self.key)

        self.cipher_suite = Fernet(self.key)

    def store_credentials(self):
        """Initial setup: Get and store encrypted credentials"""
        username = input("Enter username: ")
        password = getpass.getpass("Enter password: ")

        # Encrypt credentials
        encrypted_username = self.cipher_suite.encrypt(username.encode()).decode()
        encrypted_password = self.cipher_suite.encrypt(password.encode()).decode()

        # Store with timestamp
        creds_data = {
            'username': encrypted_username,
            'password': encrypted_password,
            'stored_date': datetime.now(pytz.UTC).isoformat()
        }

        with open(self.cred_file, 'w') as f:
            json.dump(creds_data, f)

        print("Credentials stored securely.")

        # Clear sensitive data from memory
        del password

    def load_credentials(self):
        """Load and decrypt stored credentials"""
        if not os.path.exists(self.cred_file):
            raise FileNotFoundError("No stored credentials found. Run store_credentials() first.")

        with open(self.cred_file, 'r') as f:
            creds_data = json.load(f)

        username = self.cipher_suite.decrypt(creds_data['username'].encode()).decode()
        password = self.cipher_suite.decrypt(creds_data['password'].encode()).decode()

        return username, password