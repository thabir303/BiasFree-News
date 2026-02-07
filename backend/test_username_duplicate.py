"""
Test that username doesn't need to be unique (only email is unique)
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_duplicate_username():
    print("=== Testing Duplicate Username (Should Be Allowed) ===\n")
    
    timestamp = int(time.time())
    same_username = f"sameuser{timestamp}"
    
    # Create first user
    print("1. Creating first user with username:", same_username)
    user1_data = {
        "username": same_username,
        "email": f"user1_{timestamp}@example.com",
        "password": "Test@1234"
    }
    
    response1 = requests.post(f"{BASE_URL}/auth/signup", json=user1_data)
    print(f"Response Status: {response1.status_code}")
    
    if response1.status_code == 201:
        print(f"✅ First user created: {response1.json()['user']['email']}\n")
        
        # Create second user with SAME username but different email
        print("2. Creating second user with SAME username:", same_username)
        user2_data = {
            "username": same_username,  # Same username!
            "email": f"user2_{timestamp}@example.com",  # Different email
            "password": "Test@1234"
        }
        
        response2 = requests.post(f"{BASE_URL}/auth/signup", json=user2_data)
        print(f"Response Status: {response2.status_code}")
        
        if response2.status_code == 201:
            print(f"✅ Second user created with same username: {response2.json()['user']['email']}")
            print("✅ SUCCESS: Username uniqueness is NOT enforced!\n")
            
            # Try to create user with duplicate email (should fail)
            print("3. Testing duplicate email (should fail)...")
            user3_data = {
                "username": "differentuser",
                "email": f"user1_{timestamp}@example.com",  # Duplicate email!
                "password": "Test@1234"
            }
            
            response3 = requests.post(f"{BASE_URL}/auth/signup", json=user3_data)
            print(f"Response Status: {response3.status_code}")
            
            if response3.status_code == 400:
                print(f"✅ Error (Expected): {response3.json()['detail']}")
                print("✅ SUCCESS: Email uniqueness IS enforced!")
            else:
                print("❌ FAIL: Email uniqueness should have been enforced")
        else:
            print(f"❌ FAIL: Second user creation should have succeeded")
            print(f"Error: {response2.json()}")
    else:
        print(f"❌ FAIL: First user creation failed: {response1.json()}")

if __name__ == "__main__":
    test_duplicate_username()
