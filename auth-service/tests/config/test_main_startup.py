import unittest

from app.main import app
from app.config import config


class MainApplicationTestCase(unittest.TestCase):

    def test_configuration_loading(self) -> None:
        """Verify environment variables and configuration models load safely."""
        self.assertIsNotNone(config)
        self.assertIn(config.environment.lower(), ["development", "production", "staging"])
        self.assertEqual(config.app_name, "Auth Service Platform")


if __name__ == "__main__":
    unittest.main()
