"""
Google Drive Client for StockMate
Handles all Google Drive API interactions using Service Account authentication.
"""

import json
import os
import requests
from typing import Dict


class GoogleDriveClient:
    """Client for Google Drive file operations using Google Drive API v3.
    
    Uses Service Account authentication for serverless automation.
    Service account tokens never expire - perfect for Lambda functions.
    """
    
    def __init__(self, service_account_json: str, file_id: str):
        """Initialize Google Drive client with service account credentials.
        
        Args:
            service_account_json: JSON string containing service account credentials
            file_id: Google Drive file ID to read/write
        """
        self.file_id = file_id
        self.access_token = None
        
        if not service_account_json:
            raise ValueError("Service account JSON is required")
        
        if not file_id:
            raise ValueError("Google Drive file ID is required")
        
        print("🔐 Using Service Account authentication")
        self.service_account_data = json.loads(service_account_json)
    
    def get_access_token(self) -> str:
        """Get access token using Service Account credentials (JWT-based)."""
        import time
        import base64
        
        try:
            # Extract required fields from service account JSON
            private_key = self.service_account_data['private_key']
            client_email = self.service_account_data['client_email']
            
            # Create JWT header
            header = {
                "alg": "RS256",
                "typ": "JWT"
            }
            
            # Create JWT claims
            now = int(time.time())
            claims = {
                "iss": client_email,
                "scope": "https://www.googleapis.com/auth/drive",
                "aud": "https://oauth2.googleapis.com/token",
                "exp": now + 3600,  # Token expires in 1 hour
                "iat": now
            }
            
            # Encode JWT
            def base64url_encode(data):
                return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
            
            header_encoded = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
            claims_encoded = base64url_encode(json.dumps(claims, separators=(',', ':')).encode())
            
            message = f"{header_encoded}.{claims_encoded}".encode()
            
            # Sign the JWT using the private key
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend
            
            # Load private key
            private_key_obj = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend()
            )
            
            # Sign the message
            signature = private_key_obj.sign(
                message,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            signature_encoded = base64url_encode(signature)
            jwt_token = f"{header_encoded}.{claims_encoded}.{signature_encoded}"
            
            # Exchange JWT for access token
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": jwt_token
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            print("✅ Service Account token obtained successfully")
            return self.access_token
            
        except Exception as e:
            print(f"❌ Error getting Service Account token: {e}")
            print("\n💡 SOLUTION: Check that:")
            print("   1. GOOGLE_SERVICE_ACCOUNT_JSON is valid JSON")
            print("   2. The service account has access to the Drive file")
            print("   3. Drive API is enabled in your Google Cloud project")
            print("   4. The cryptography package is installed")
            raise
    
    def read_file(self) -> Dict:
        """Read JSON file from Google Drive.
        
        Returns:
            Dictionary containing the file data
        """
        try:
            if not self.access_token:
                print("Getting access token...")
                self.get_access_token()
                print("Access token obtained successfully")
            
            # Download file content
            file_url = f"https://www.googleapis.com/drive/v3/files/{self.file_id}?alt=media"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            print(f"Attempting to read file from Google Drive (File ID: {self.file_id})")
            response = requests.get(file_url, headers=headers)
            
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 404:
                # File doesn't exist, return default structure
                print("⚠️ File not found (404). Will create it on first save.")
                return {
                    "status": "active",
                    "last_deposit_date": None,
                    "deposit_amount": 0.0,
                    "tracked_prices": {},
                    "last_action": "None",
                }
            
            if response.status_code == 401:
                print("❌ Authentication failed (401). Check your credentials.")
                print(f"Response body: {response.text[:200]}")
                raise Exception("Google Drive authentication failed")
            
            if response.status_code == 403:
                print("❌ Access forbidden (403). Check file permissions.")
                print(f"Response body: {response.text[:200]}")
                raise Exception("Google Drive access forbidden - check file sharing settings")
            
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            print(f"✅ Successfully loaded data from Google Drive")
            print(f"   Last deposit date: {data.get('last_deposit_date')}")
            print(f"   Tracked prices count: {len(data.get('tracked_prices', {}))}")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error reading from Google Drive: {e}")
            raise
        except Exception as e:
            print(f"❌ Error reading from Google Drive: {e}")
            raise
    
    def write_file(self, data: Dict) -> None:
        """Write JSON file to Google Drive.
        
        Args:
            data: Dictionary to write as JSON
        """
        try:
            if not self.access_token:
                self.get_access_token()
            
            json_content = json.dumps(data, indent=4)
            
            # First, check if file exists
            check_url = f"https://www.googleapis.com/drive/v3/files/{self.file_id}"
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            print(f"Checking if file exists (File ID: {self.file_id})...")
            check_response = requests.get(check_url, headers=headers)
            
            if check_response.status_code == 404:
                print("❌ File not found! Please create the file in Google Drive first.")
                print(f"   1. Create a new file in Google Drive")
                print(f"   2. Get its File ID from the URL")
                print(f"   3. Set GOOGLE_DRIVE_FILE_ID environment variable")
                raise Exception("Google Drive file not found - please create it first")
            
            if check_response.status_code == 403:
                print("❌ Access forbidden! Check file permissions.")
                raise Exception("Cannot access Google Drive file - check sharing settings")
            
            check_response.raise_for_status()
            
            # File exists, update it
            print("File exists, updating content...")
            file_url = f"https://www.googleapis.com/upload/drive/v3/files/{self.file_id}?uploadType=media"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.patch(file_url, headers=headers, data=json_content)
            
            if response.status_code != 200:
                print(f"❌ Update failed with status {response.status_code}")
                print(f"Response: {response.text[:200]}")
            
            response.raise_for_status()
            
            print(f"✅ File updated successfully in Google Drive")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error writing to Google Drive: {e}")
            raise
        except Exception as e:
            print(f"❌ Error writing to Google Drive: {e}")
            raise

