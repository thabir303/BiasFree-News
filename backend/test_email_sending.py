"""
Test email sending functionality
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_email_sending():
    print("=== Testing Email Sending ===\n")
    
    timestamp = int(time.time())
    
    print("1. Creating new user to test email sending...")
    signup_data = {
        "username": f"emailtest{timestamp}",
        "email": "tanvirhasanabir8@gmail.com",  # Your email
        "password": "Test@1234"
    }
    
    response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
    print(f"Signup Response Status: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print(f"✅ User created: {data['user']['username']}")
        print(f"✅ Email: {data['user']['email']}")
        print(f"✅ Message: {data.get('message', 'No message')}")
        print("\n🎉 Check your email inbox (tanvirhasanabir8@gmail.com) for verification email!")
        print("📧 Subject: Verify Your Email - BiasFree News")
        print("\nIf you don't see it, check spam folder.")
    else:
        print(f"❌ Signup failed: {response.json()}")

if __name__ == "__main__":
    test_email_sending()
