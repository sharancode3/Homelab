import unittest
import uuid
from datetime import datetime, timezone
from app.api.auth_models import UserRegisterRequest, UserLoginRequest
from app.api.auth_service import AuthServiceLayer, InvalidCredentialsException, UserAlreadyExistsException
from app.storage.providers.sqlite import SQLiteUserRepository
from app.auth import verify_password, create_access_token
from app.api.dependencies import get_current_user
from fastapi import HTTPException
from pydantic import ValidationError

class TestPlatformIdentity(unittest.TestCase):
    def setUp(self):
        self.repo = SQLiteUserRepository(db_path=":memory:")
        self.service = AuthServiceLayer(user_repo=self.repo)

    def test_successful_registration(self):
        req = UserRegisterRequest(username="testuser", email="test@example.com", password="SecurePassword123!")
        user = self.service.register(req)
        
        self.assertIsNotNone(user.user_id)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.is_active)
        self.assertNotEqual(user.hashed_password, "SecurePassword123!")
        self.assertTrue(verify_password("SecurePassword123!", user.hashed_password))

    def test_duplicate_registration_rejected(self):
        req = UserRegisterRequest(username="dupuser", email="dup@example.com", password="Password123!")
        self.service.register(req)
        
        with self.assertRaises(UserAlreadyExistsException):
            self.service.register(req)

    def test_successful_login(self):
        req = UserRegisterRequest(username="loginuser", email="login@example.com", password="Password123!")
        self.service.register(req)
        
        login_req = UserLoginRequest(email="login@example.com", password="Password123!")
        res = self.service.login(login_req)
        
        self.assertIsNotNone(res.access_token)
        self.assertIsNotNone(res.refresh_token)
        self.assertEqual(res.token_type, "bearer")

    def test_wrong_password_rejected(self):
        req = UserRegisterRequest(username="wrongpass", email="wrongpass@example.com", password="Password123!")
        self.service.register(req)
        
        login_req = UserLoginRequest(email="wrongpass@example.com", password="WrongPassword123!")
        with self.assertRaises(InvalidCredentialsException):
            self.service.login(login_req)

    def test_unknown_account_safely_rejected(self):
        login_req = UserLoginRequest(email="unknown@example.com", password="Password123!")
        with self.assertRaises(InvalidCredentialsException):
            self.service.login(login_req)

    def test_auth_dependency_resolves_user(self):
        req = UserRegisterRequest(username="depuser", email="dep@example.com", password="Password123!")
        user = self.service.register(req)
        
        token = create_access_token({"sub": user.user_id, "email": user.email})
        
        from app.storage.providers.sqlite import SQLiteRevocationRepository
        revocation_repo = SQLiteRevocationRepository(db_path=":memory:")
        resolved_user = get_current_user(token=token, user_repo=self.repo, revocation_repo=revocation_repo)
        self.assertEqual(resolved_user.user_id, user.user_id)
        self.assertEqual(resolved_user.email, user.email)

    def test_auth_dependency_invalid_token(self):
        from app.storage.providers.sqlite import SQLiteRevocationRepository
        revocation_repo = SQLiteRevocationRepository(db_path=":memory:")
        with self.assertRaises(HTTPException):
            get_current_user(token="invalid.token.here", user_repo=self.repo, revocation_repo=revocation_repo)

if __name__ == "__main__":
    unittest.main()
