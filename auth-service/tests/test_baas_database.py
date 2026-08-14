import unittest
from app.storage.providers.sqlite_tenant import TenantDatabaseValidator, TenantDatabaseError, SQLiteTenantConnectionFactory, TenantDatabaseManager
import shutil
from pathlib import Path

class TestTenantDatabase(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_data_dir")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        self.factory = SQLiteTenantConnectionFactory(storage_path=str(self.test_dir))
        self.manager = TenantDatabaseManager(self.factory)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_identifier_validation(self):
        TenantDatabaseValidator.validate_identifier("valid_name")
        TenantDatabaseValidator.validate_identifier("Valid_Name_123")
        
        with self.assertRaises(TenantDatabaseError):
            TenantDatabaseValidator.validate_identifier("1_invalid")
        with self.assertRaises(TenantDatabaseError):
            TenantDatabaseValidator.validate_identifier("invalid-name")
        with self.assertRaises(TenantDatabaseError):
            TenantDatabaseValidator.validate_identifier("sqlite_internal")
        with self.assertRaises(TenantDatabaseError):
            TenantDatabaseValidator.validate_identifier("_baas_tables")

    def test_create_and_list_tables(self):
        project_id = "proj_test1"
        self.manager.create_table(project_id, "users", {"name": "TEXT", "age": "INTEGER"})
        tables = self.manager.list_tables(project_id)
        self.assertIn("users", tables)
        
        schema = self.manager.get_table_schema(project_id, "users")
        col_names = [col["name"] for col in schema]
        self.assertIn("id", col_names)
        self.assertIn("name", col_names)
        self.assertIn("age", col_names)

        # Attempt to create duplicate
        with self.assertRaises(TenantDatabaseError):
            self.manager.create_table(project_id, "users", {"name": "TEXT"})

        # Attempt to create invalid type
        with self.assertRaises(TenantDatabaseError):
            self.manager.create_table(project_id, "bad_table", {"data": "VARCHAR(255)"})

    def test_row_crud(self):
        project_id = "proj_test2"
        self.manager.create_table(project_id, "products", {"name": "TEXT", "price": "REAL"})
        
        # Insert
        row_id = self.manager.insert_row(project_id, "products", {"id": "prod_1", "name": "Laptop", "price": 999.99})
        self.assertEqual(row_id, "prod_1")
        
        # Get
        row = self.manager.get_row(project_id, "products", "prod_1")
        self.assertEqual(row["name"], "Laptop")
        self.assertEqual(row["price"], 999.99)
        
        # List
        rows = self.manager.list_rows(project_id, "products")
        self.assertEqual(len(rows), 1)
        
        # Update
        updated = self.manager.update_row(project_id, "products", "prod_1", {"price": 899.99})
        self.assertTrue(updated)
        row = self.manager.get_row(project_id, "products", "prod_1")
        self.assertEqual(row["price"], 899.99)
        
        # Delete
        deleted = self.manager.delete_row(project_id, "products", "prod_1")
        self.assertTrue(deleted)
        
        row = self.manager.get_row(project_id, "products", "prod_1")
        self.assertIsNone(row)

    def test_tenant_isolation(self):
        # A file-system check to ensure databases are physically separate
        self.manager.create_table("proj_a", "data_a", {"val": "TEXT"})
        self.manager.create_table("proj_b", "data_b", {"val": "TEXT"})
        
        self.manager.insert_row("proj_a", "data_a", {"id": "1", "val": "A"})
        self.manager.insert_row("proj_b", "data_b", {"id": "1", "val": "B"})
        
        # Proj A should not see data_b
        with self.assertRaises(TenantDatabaseError):
            self.manager.list_rows("proj_a", "data_b")

if __name__ == "__main__":
    unittest.main()
