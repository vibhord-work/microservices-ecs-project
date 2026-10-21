import os
import unittest
from app import app

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "healthy")

    def test_api_data(self):
        endpoint = os.environ["TEST_ENDPOINT"]
        response = self.client.get("/" + endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data[endpoint], list)
        self.assertGreater(len(data[endpoint]), 0)
        self.assertIn("id", data[endpoint][0])
        self.assertIn("name", data[endpoint][0])

if __name__ == "__main__":
    unittest.main()
