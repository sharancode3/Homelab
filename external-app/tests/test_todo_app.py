import pytest
from unittest.mock import Mock, MagicMock
from todo_app import TaskManager

def test_create_task():
    app = TaskManager("http://localhost", "p1", "key1")
    app.client = MagicMock()
    app.client.db.insert.return_value = {"id": "task_123"}

    task_id = app.create_task("Test", "Desc")
    assert task_id.startswith("task_")
    app.client.db.insert.assert_called_once()
    args, kwargs = app.client.db.insert.call_args
    assert args[0] == "p1"
    assert args[1] == "tasks"
    assert args[2]["title"] == "Test"

def test_list_tasks():
    app = TaskManager("http://localhost", "p1", "key1")
    app.client = MagicMock()
    app.client.db.list.return_value = [{"data": {"id": "t1", "title": "Test"}}]

    tasks = app.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["data"]["title"] == "Test"

def test_complete_task():
    app = TaskManager("http://localhost", "p1", "key1")
    app.client = MagicMock()
    app.client.db.get.return_value = {"data": {"id": "t1", "title": "Test", "status": "pending"}}

    app.complete_task("t1")
    app.client.db.update.assert_called_once()
    args, kwargs = app.client.db.update.call_args
    assert args[3]["status"] == "completed"

def test_attach_file():
    app = TaskManager("http://localhost", "p1", "key1")
    app.client = MagicMock()
    app.client.storage.upload.return_value = {"id": "file_1"}

    file_id = app.attach_file("t1", "img.png", b"data")
    assert file_id == "file_1"
    app.client.storage.upload.assert_called_once()
