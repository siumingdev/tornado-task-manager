import time
from datetime import datetime, timedelta
from typing import Tuple, Optional
from threading import RLock
from sortedcontainers import SortedSet

from .db import DbContainer
from .logger import app_log

Task = Tuple[int, str, Optional[datetime]]
TIMEDELTA = timedelta(minutes=15)


class TaskCache:
    """
    Thread-safe object to provide functionality of a task queue with fast read, write and delete.

    Let n be the number of tasks.
    Space complexity: O(n)
    Time complexity:
        add_task: O(log n)
        get_next_task: O(log n)
        remove_task: O(log n)
    """
    def __init__(self):
        self.__lock = RLock()
        self.__tasks_schedules = SortedSet()  # {(expiry_dt, id)}
        self.__tasks_dict = dict()  # {[id: (title, expiry_dt)]}

    def add_task(self, task: Task):
        """
        Add Task to the task queue.
        If a Task with the same id already exists, an existing record will be replaced.
        Otherwise will add a new record with key id.

        :param task: Task
        :return:
        """
        id, title, expiry_dt = task
        self.__lock.acquire()
        try:
            if id in self.__tasks_dict:
                self.__tasks_schedules.remove((self.__tasks_dict[id][1], id))
            self.__tasks_dict[id] = (title, expiry_dt)
            self.__tasks_schedules.add((expiry_dt, id))
        finally:
            self.__lock.release()

    def get_next_task(self) -> Optional[Task]:
        """
        Return the most earliest Task in terms of expiry datetime.
        It will return a task if there is at least one task in self.__tasks_schedules

        :return: task: Task or None
        """
        self.__lock.acquire()
        try:
            if self.__tasks_schedules:
                expiry_dt, id = self.__tasks_schedules[0]
                task_content = self.__tasks_dict.get(id)
                task = id, task_content[0], task_content[1]
            else:
                task = None
        finally:
            self.__lock.release()
        return task

    def task_done(self, task: Task):
        """
        Remove task from self.__tasks_schedules and self.__tasks_dict.

        :param task: Task
        :return:
        """
        id, title, expiry_dt = task
        self.remove_task(id)

    def remove_task(self, id: int):
        """
        Remove task from both self.__tasks_schedules and self.__tasks_dict

        :param task: Task
        :return:
        """
        self.__lock.acquire()
        try:
            title, expiry_dt = self.__tasks_dict[id]
            self.__tasks_schedules.discard((expiry_dt, id))
            del self.__tasks_dict[id]
        except KeyError:
            pass
        finally:
            self.__lock.release()

    def clear_all_tasks(self):
        """
        Clear all tasks from both self.__tasks_schedules and self.__tasks_dict

        :param task: Task
        :return:
        """
        self.__lock.acquire()
        try:
            self.__tasks_schedules = SortedSet()
            self.__tasks_dict = dict()
        except KeyError:
            pass
        finally:
            self.__lock.release()


class TaskExpiryAlert:
    __stopped = False
    __task_cache = TaskCache()

    @classmethod
    async def initialize(cls, db_container: DbContainer):
        """
        Read to-be-expired tasks from DB and load into task_cache.

        :return:
        """
        database = db_container.database
        tasks = db_container.tasks
        query = tasks.select().where(tasks.c.expiry_dt > datetime.now())
        async for row in database.iterate(query=query):
            task = dict(row)
            await cls.add_task(task.get("id"), task.get("title"), task.get("expiry_dt"))
        print('TaskExpiryAlert.initialize end')

    @classmethod
    async def add_task(cls, id: int, title: str, expiry_dt: Optional[datetime]):
        """
        Add a new task to task_cache. Can be called from any thread.

        :param id: int, id of the task
        :param title: str, title of the task
        :param expiry_dt: datetime, expiry datetime of the task
        :return:
        """
        if expiry_dt is not None:
            cls.__task_cache.add_task((id, title, expiry_dt))

    @classmethod
    async def remove_task(cls, id: int):
        """
        Remove a task from task_cache. Can be called from any thread.

        :param id: int, id of the task
        :param title: str, title of the task
        :param expiry_dt: datetime, expiry datetime of the task
        :return:
        """
        cls.__task_cache.remove_task(id)

    @classmethod
    async def clear_all_tasks(cls):
        """
        Clear all tasks from task_cache. Can be called from any thread.

        :return:
        """
        cls.__task_cache.clear_all_tasks()

    @classmethod
    def scheduler(cls):
        """
        The main body of the schedule job of TaskExpiryAlert.
        It is long-living and should be called only when invoking a new thread.

        :return:
        """
        while True:
            if cls.__stopped:
                return
            try:
                task = cls.__task_cache.get_next_task()
                if (task is not None) and (task[2] - datetime.now() - TIMEDELTA).total_seconds() < 0:
                    cls.__notify_user(*task)
                    cls.__task_cache.task_done(task)
                else:
                    time.sleep(0.1)
            except Exception as e:
                app_log.error(e)

    @classmethod
    def stop_scheduler(cls):
        cls.__stopped = True

    @classmethod
    def __notify_user(cls, id: int, title: str, expiry_dt: datetime):
        """
        Demo function for notifying user about task expiration.
        In this demo, it will only print a message to the console.
        In real situation, it may send an email or push a message to a MQ.
        TODO: consider execute the task in ThreadPoolExecutor.

        :param id: int, id of the task
        :param title: str, title of the task
        :param expiry_dt: datetime, expiry datetime of the task
        :return:
        """
        if expiry_dt > datetime.now():
            app_log.info(f"Your task (id:{id},title:\"{title}\") will be expired at {expiry_dt}!")
        else:
            app_log.info(f"Your task (id:{id},title:\"{title}\") is expired already at {expiry_dt}!")
