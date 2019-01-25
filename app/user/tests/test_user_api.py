from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
PROFILE_URL = reverse('user:profile')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserApiTest(TestCase):
    """Test the users API (public)"""

    def setUp(self):
        self.client = APIClient()

    def test_create_valid_user_success(self):
        """Test creating user with user valid payload is successful"""
        payload = {
            'email': 'test@test.pl',
            'password': 'Pass12345',
            'name': 'name name'
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(**res.data)
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_exists(self):
        """Test creating a user that already exists"""
        payload = {
            'email': 'test@test.pl',
            'password': 'Pass12345',
        }
        create_user(**payload)

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pass_too_short(self):
        """Test that the password must be more than 5 chars"""
        payload = payload = {
            'email': 'test@test.pl',
            'password': 'Pa',
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test that token is created for the user"""
        payload = payload = {
            'email': 'test@test.pl',
            'password': 'Password123',
        }

        create_user(**payload)
        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_invalid_credentials(self):
        """Test that token is not created if invalid credentials are given"""
        create_user(email='test@test.pl', password='pass1233')
        payload = {'email': 'test@test.pl', 'password': 'wrong'}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_no_user(self):
        """Test that token is not created if user doesnt exists"""
        payload = {
            'email': 'test@test.pl',
            'password': 'Password123',
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_missing_field(self):
        """Test that email password are required"""
        res = self.client.post(TOKEN_URL, {'email': 'one', 'password': ''})

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_anauthorized(self):
        """Test that authentication is required for users"""
        res = self.client.get(PROFILE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserAuthenticationTests(TestCase):
    """Test API request that require authentication"""

    def setUp(self):
        self.user = create_user(
            email='test@test.pl',
            password='testpass',
            name='test name'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_retrieve_success(self):
        """TEst retrieving profile for logged in user"""
        res = self.client.get(PROFILE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email
        })

    def test_post_in_profile_not_allowed(self):
        """Test that POST is not allowed on the profile url"""
        res = self.client.post(PROFILE_URL, {})

        self.assertEqual(
            res.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_user_profile(self):
        """Test updating the user profile for authenticated user"""
        payload = {'name': 'new name', 'password': 'newpass123'}
        res = self.client.patch(PROFILE_URL, payload)
        self.user.refresh_from_db()

        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
