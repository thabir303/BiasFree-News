"""
Test email verification feature
NOTE: In production, verification token should be sent via email, not shown in API response.
For testing purposes, we'll extract the token from the database.
"""
import requests
import json
import sqlite3

BASE_URL = "http://localhost:8000"

def get_verification_token_from_db(email):
    """Get verification token directly from database for testing"""
    conn = sqlite3.connect('biasfree.db')
    cursor = conn.cursor()
    cursor.execute("SELECT verification_token FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def test_email_verification():
    print("=== Testing Email Verification ===\n")
    
    # Use timestamp for unique user
    import time
    timestamp = int(time.time())
    
    # 1. Signup new user
    print("1. Creating new user...")
    signup_data = {
        "username": f"testuser{timestamp}",
        "email": f"test{timestamp}@example.com",
        "password": "Test@1234"
    }
    
    response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
    print(f"Signup Response Status: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print(f"User created: {data['user']['username']}")
        print(f"Email: {data['user']['email']}")
        
        # Get message
        message = data.get('message', '')
        print(f"Message: {message}\n")
        
        # In production, token would be sent via email
        # For testing, we get it from database
        print("Getting verification token from database...")
        verification_token = get_verification_token_from_db(signup_data["email"])
        
        if verification_token:
            print(f"Verification Token (from DB): {verification_token}\n")
            
            # 2. Try to signin before verification
            print("2. Trying to signin before email verification...")
            signin_data = {
                "email": signup_data["email"],
                "password": signup_data["password"]
            }
            
            response = requests.post(f"{BASE_URL}/auth/signin", json=signin_data)
            print(f"Signin Response Status: {response.status_code}")
            
            if response.status_code == 403:
                print(f"Error (Expected): {response.json()['detail']}\n")
            
            # 3. Verify email
            print("3. Verifying email...")
            response = requests.post(f"{BASE_URL}/auth/verify-email/{verification_token}")
            print(f"Verification Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"Success: {response.json()['message']}\n")
                
                # 4. Try to signin after verification
                print("4. Trying to signin after email verification...")
                response = requests.post(f"{BASE_URL}/auth/signin", json=signin_data)
                print(f"Signin Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Signin Successful!")
                    print(f"User: {data['user']['username']}")
                    print(f"Email: {data['user']['email']}")
                    print(f"Token: {data['access_token'][:20]}...\n")
                    
                    # 5. Test resend verification (should fail as already verified)
                    print("5. Testing resend verification (should fail)...")
                    response = requests.post(f"{BASE_URL}/auth/resend-verification/{signup_data['email']}")
                    print(f"Resend Response Status: {response.status_code}")
                    
                    if response.status_code == 400:
                        print(f"Error (Expected): {response.json()['detail']}\n")
                    
                    print("✅ All tests passed!")
                else:
                    print(f"❌ Signin failed after verification: {response.json()}")
            else:
                print(f"❌ Email verification failed: {response.json()}")
        else:
            print("❌ Verification token not found in database")
    else:
        print(f"❌ Signup failed: {response.json()}")

if __name__ == "__main__":
    test_email_verification()
