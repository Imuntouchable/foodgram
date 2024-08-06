# backend/api/tests.py
from http import HTTPStatus

from django.test import Client, TestCase

from api import models


class APITestCase(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_users_list_exists(self):
        """Проверка доступности списка пользователей."""
        response = self.guest_client.get('/api/users/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_ingredients_list_exists(self):
        """Проверка доступности списка ингредиентов."""
        response = self.guest_client.get('/api/ingredients/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_recipes_list_exists(self):
        """Проверка доступности списка рецептов."""
        response = self.guest_client.get('/api/recipes/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

