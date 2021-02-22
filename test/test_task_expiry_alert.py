import threading
import time
from datetime import datetime

from task_man.scheduling import TaskExpiryAlert, TIMEDELTA
from tornado.testing import AsyncTestCase, gen_test


class TestTaskExpiryAlert(AsyncTestCase):
    @classmethod
    def setUpClass(cls):
        threading.Thread(target=TaskExpiryAlert.scheduler).start()

    @classmethod
    def tearDownClass(cls):
        TaskExpiryAlert.stop_scheduler()

    @gen_test
    def test_add_no_expiry_task(self):
        yield TaskExpiryAlert.clear_all_tasks()
        time.sleep(1)
        yield TaskExpiryAlert.add_task(0, "abc", None)
        time.sleep(1)
        self.assertIsNone(TaskExpiryAlert._TaskExpiryAlert__task_cache.get_next_task())

    @gen_test
    def test_add_expire_soon_task(self):
        yield TaskExpiryAlert.clear_all_tasks()
        time.sleep(1)
        yield TaskExpiryAlert.add_task(0, "abc", datetime.now() + TIMEDELTA / 2)
        time.sleep(1)
        self.assertIsNone(TaskExpiryAlert._TaskExpiryAlert__task_cache.get_next_task())

    @gen_test
    def test_add_expire_not_soon_task(self):
        task = (0, "abc", datetime.now() + TIMEDELTA * 2)

        yield TaskExpiryAlert.clear_all_tasks()
        time.sleep(1)
        yield TaskExpiryAlert.add_task(*task)
        time.sleep(1)
        self.assertEqual(task, TaskExpiryAlert._TaskExpiryAlert__task_cache.get_next_task())

    @gen_test
    def test_add_3_tasks_2_ids(self):
        tasks = [
            (1, "def", datetime.now() + TIMEDELTA * 3),
            (0, "abc", datetime.now() + TIMEDELTA * 2),
            (0, "abc", datetime.now() + TIMEDELTA * 4)
        ]

        yield TaskExpiryAlert.clear_all_tasks()
        time.sleep(1)
        for task in tasks:
            yield TaskExpiryAlert.add_task(*task)
        time.sleep(1)
        self.assertEqual(tasks[0], TaskExpiryAlert._TaskExpiryAlert__task_cache.get_next_task())
        yield TaskExpiryAlert._TaskExpiryAlert__task_cache.task_done(tasks[0])
        time.sleep(1)
        self.assertEqual(tasks[2], TaskExpiryAlert._TaskExpiryAlert__task_cache.get_next_task())
