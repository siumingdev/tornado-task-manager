import requests
import os
import unittest
import time

from sqlalchemy import create_engine
from sqlalchemy.sql import text

from task_man.config import MysqlConfig
from task_man.db import DbContainer, create_db_container


class TestTaskApi(unittest.TestCase):
    db_container: DbContainer = None
    db_config: MysqlConfig = MysqlConfig(
        host=os.environ.get("MYSQL_HOST") or "localhost:3306",
        user=os.environ.get("MYSQL_USER") or "root",
        password=os.environ.get("MYSQL_PASSWORD") or "root",
    )
    engine = None

    HOST_URL = "http://localhost:8888"

    @classmethod
    def setUpClass(cls) -> None:
        cls.db_container = create_db_container(cls.db_config)
        cls.engine = create_engine(str(cls.db_container.database.url))

    def __count(self) -> int:
        with self.engine.connect() as conn:
            return conn.execute(text("SELECT count(*) FROM task")).fetchall()[0][0]

    def __insert_sample_tasks(self):
        with self.engine.connect() as conn:
            conn.execute(self.db_container.tasks.insert(), [
                {"title": "abc1", "description": "def"},
                {"title": "abc2", "description": "def"},
                {"title": "abc3", "description": "def"},
                {"title": "abc4", "description": "def"}
            ])

    def setUp(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(self.db_container.tasks.delete())
        self.__insert_sample_tasks()

    def tearDown(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(self.db_container.tasks.delete())

    def test_get_all_tasks(self):
        response = requests.get(self.HOST_URL + "/v1/tasks")
        self.assertEqual(200, response.status_code)
        self.assertEqual(4, len(response.json()["tasks"]))

    def test_get_tasks_pagination(self):
        response = requests.get(self.HOST_URL + "/v1/tasks?offset=1&limit=2")
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(response.json()["tasks"]))
        self.assertEqual("abc2", response.json()["tasks"][0]["title"])
        self.assertEqual("abc3", response.json()["tasks"][1]["title"])

    def test_post_one_task(self):
        request_body = {"title": "abc4", "description": "def"}
        response = requests.post(self.HOST_URL + "/v1/tasks", json=request_body)
        self.assertEqual(200, response.status_code)
        self.assertIn("id", response.json())
        self.assertIn("title", response.json())
        self.assertIn("description", response.json())
        time.sleep(1)
        self.assertEqual(5, self.__count())

    def test_put_two_tasks(self):
        response = requests.get(self.HOST_URL + "/v1/tasks").json()
        id_1 = response["tasks"][0]["id"]
        id_2 = response["tasks"][1]["id"]

        request_body = {
            "tasks": [
                {"id": id_1, "title": "abc1_test_put_two_tasks", "description": "def"},
                {"id": id_2, "title": "abc2_test_put_two_tasks", "description": "def"}
            ]
        }
        response = requests.put(self.HOST_URL + "/v1/tasks", json=request_body)
        self.assertEqual(200, response.status_code)

        response = requests.get(self.HOST_URL + "/v1/tasks").json()
        self.assertEqual(request_body["tasks"][0]["title"], response["tasks"][0]["title"])
        self.assertEqual(request_body["tasks"][1]["title"], response["tasks"][1]["title"])

    def test_delete_all_task(self):
        requests.delete(self.HOST_URL + "/v1/tasks")
        time.sleep(1)
        self.assertEqual(0, self.__count())

    def test_get_one_task_by_id(self):
        id = requests.get(self.HOST_URL + "/v1/tasks").json()["tasks"][0]["id"]

        response = requests.get(self.HOST_URL + f"/v1/tasks/{id}")
        self.assertEqual(200, response.status_code)
        self.assertIn("id", response.json())
        self.assertIn("title", response.json())
        self.assertIn("description", response.json())
        self.assertEqual(id, response.json()["id"])

    def test_put_one_task(self):
        id = requests.get(self.HOST_URL + "/v1/tasks").json()["tasks"][0]["id"]

        request_body = {"title": "test_put_one_task", "description": "def"}
        response = requests.put(self.HOST_URL + f"/v1/tasks/{id}", json=request_body)
        self.assertEqual(200, response.status_code)
        self.assertIn("id", response.json())
        self.assertIn("title", response.json())
        self.assertIn("description", response.json())
        time.sleep(1)
        self.assertEqual(4, self.__count())

        response = requests.get(self.HOST_URL + f"/v1/tasks/{id}")
        self.assertEqual(request_body["title"], response.json()["title"])

    def test_delete_one_task(self):
        id = requests.get(self.HOST_URL + "/v1/tasks").json()["tasks"][0]["id"]

        response = requests.delete(self.HOST_URL + f"/v1/tasks/{id}")
        self.assertEqual(200, response.status_code)

        response = requests.get(self.HOST_URL + f"/v1/tasks/{id}")
        self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    unittest.main()
