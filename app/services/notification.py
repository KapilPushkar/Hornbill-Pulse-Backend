import requests
import google.auth
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = "fcm_credentials.json"

FCM_URL = "https://fcm.googleapis.com/v1/projects/my-first-project-7def0/messages:send"

def get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, 
        scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    access_token = credentials.with_scopes(
        ["https://www.googleapis.com/auth/firebase.messaging"]
    ).token
    return access_token

def send_fcm_notification(device_token, title, body):
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }

    payload = {
        "message": {
            "token": device_token,
            "notification": {
                "title": title,
                "body": body,
            }
        }
    }

    response = requests.post(FCM_URL, headers=headers, json=payload)
    print(response.json())

if __name__ == "__main__":
    device_token = "YOUR_DEVICE_FCM_TOKEN"
    send_fcm_notification(device_token, "Hello FCM v1", "This is a test notification")
