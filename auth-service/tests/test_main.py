import unittest
import unittest.mock
import asyncio

from app.main import app, lifespan
from app.api.routes import get_api_service

class StartupWiringTestCase(unittest.TestCase):
    def test_app_startup_wiring(self) -> None:
        """
        Test that the app startup triggers the lifespan event and 
        correctly overrides the get_api_service dependency.
        """
        async def run_test():
            # If app is a mock, make dependency_overrides a real dict so it can be mutated
            if isinstance(app.dependency_overrides, type(unittest.mock.MagicMock())):
                app.dependency_overrides = {}
            elif not isinstance(app.dependency_overrides, dict):
                app.dependency_overrides = {}
                
            async with lifespan(app):
                self.assertIn(get_api_service, app.dependency_overrides)
                
                service = app.dependency_overrides[get_api_service]()
                self.assertIsNotNone(service)
                from app.api.service import APIServiceLayer
                self.assertIsInstance(service, APIServiceLayer)
                
                self.assertIsNotNone(service._coordinator)
                self.assertIsNotNone(service._coordinator._deployment_engine)
                self.assertIsNotNone(service._coordinator._deployment_engine._deployment_adapter)
        
        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
