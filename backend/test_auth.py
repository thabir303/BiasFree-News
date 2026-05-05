#!/usr/bin/env python3
"""
Test script to verify authentication system setup.
"""
import sys
sys.path.insert(0, '/home/bs01127/Desktop/SPL-3/bias_free/backend')

from app.database.database import init_db, SessionLocal
from app.services.auth_service import AuthService
from app.database.models import User, UserRole

def test_auth_system():
    print("=" * 60)
    print("Testing Authentication System")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    print("✓ Database initialized")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create admin user
        print("\n2. Creating admin user...")
        admin = AuthService.create_admin_user(db)
        if admin:
            print(f"✓ Admin user created: {admin.username} ({admin.email})")
        else:
            print("✓ Admin user already exists")
        
        # Verify admin user
        print("\n3. Verifying admin user...")
        admin_user = db.query(User).filter(User.email == "adminuser@admin.com").first()
        if admin_user:
            print(f"✓ Admin found: {admin_user.username}")
            print(f"  - Email: {admin_user.email}")
            print(f"  - Role: {admin_user.role.value}")
            print(f"  - Active: {admin_user.is_active}")
        else:
            print("✗ Admin user not found!")
            return False
        
        # Test JWT token creation
        print("\n4. Testing JWT token creation...")
        token = AuthService.create_access_token(
            data={"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role.value}
        )
        print(f"✓ JWT token created: {token[:50]}...")
        
        # Test token decoding
        print("\n5. Testing JWT token decoding...")
        decoded = AuthService.decode_token(token)
        print(f"✓ Token decoded successfully")
        print(f"  - User ID: {decoded.get('sub')}")
        print(f"  - Email: {decoded.get('email')}")
        print(f"  - Role: {decoded.get('role')}")
        
        # Test password verification
        print("\n6. Testing password verification...")
        test_password = "platformadmin@123"
        is_valid = AuthService.verify_password(test_password, admin_user.hashed_password)
        if is_valid:
            print("✓ Password verification successful")
        else:
            print("✗ Password verification failed!")
            return False
        
        print("\n" + "=" * 60)
        print("✓ All authentication tests passed!")
        print("=" * 60)
        print("\nAdmin credentials:")
        print(f"  Email: adminuser@admin.com")
        print(f"  Password: platformadmin@123")
        print(f"  Username: admin")
        print(f"  Role: admin")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_auth_system()
    sys.exit(0 if success else 1)
