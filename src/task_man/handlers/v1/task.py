import json
from typing import Union, Mapping
from datetime import datetime
from tornado.escape import json_decode
from tornado.web import RequestHandler
import sqlalchemy
from sqlalchemy import Table
from databases import Database

from task_man.scheduling import TaskExpiryAlert, Task
from task_man.logger import app_log
from . import URI_HEADER


def process_row(row: Union[Mapping, sqlalchemy.engine.RowProxy]) -> dict:
    row = dict(row)
    if ("expiry_dt" in row) and (row["expiry_dt"] is not None):
        row["expiry_dt"] = str(row["expiry_dt"])
    return row


def get_task_schedule(row: Union[Mapping, sqlalchemy.engine.RowProxy]) -> Task:
    return row.get("id"), row.get("title"), datetime.fromisoformat(row.get("expiry_dt")) if row.get("expiry_dt") else None


class TasksHandler(RequestHandler):
    endpoint = URI_HEADER + r"/tasks"

    def initialize(self, tasks: Table, database: Database, scheduler: TaskExpiryAlert):
        self.__tasks = tasks
        self.__database = database
        self.__scheduler = scheduler

    async def get(self):  # response all tasks
        """
        Get all tasks or pagination with offset and limit as query arguments

        parameters:
        -   limit: Optional, Number of records to fetch. Fetch from "offset" to last records if not inputted.
            offset: Optional, Position of the 1st record. Fetch from 1st record if not inputted.
        responses:
            200:
                description: list of tasks
        :return:
        """
        args = self.request.query_arguments
        query = self.__tasks.select()
        if "limit" in args:
            query = query.limit(int(args["limit"][0]))
        if "offset" in args:
            query = query.offset(int(args["offset"][0]))
        rows = await self.__database.fetch_all(query=query)
        self.write({"tasks": [process_row(row) for row in rows]})

    async def post(self):  # create one task, return the task with id
        """
        Create new task

        parameters: None
        request body:
        {
            "title": string,
            "description": string (optional),
            "expiry_dt": datetime string in isoformat with local timezone (optional)
        }
        responses:
            200:
                response body:
                {
                    "id": task_id of created task,
                    **request_body
                }
        :return:
        """
        try:
            new_task = json_decode(self.request.body)
        except json.JSONDecodeError:
            body_arguments = self.request.body_arguments
            new_task = {k: v[0].decode("utf-8") for k, v in body_arguments.items()}

        query = self.__tasks.insert().values(**new_task)
        new_id = await self.__database.execute(query=query)
        await self.__scheduler.add_task(*get_task_schedule({**new_task, "id": new_id}))
        self.write({"id": new_id, **new_task})

    async def put(self):  # bulk update of tasks
        """
        Bulk update of tasks.
        If some tasks in request body contains tasks with id(s) that do not exist, those tasks will be discarded.

        parameters: None
        request body:
        {
            "tasks": [
                {
                    "id": integer,
                    "title": string,
                    "description": string (optional),
                    "expiry_dt": datetime string in isoformat with local timezone (optional)
                },
                ...
            ]
        }
        responses:
            200:
        :return:
        """
        input_tasks = json_decode(self.request.body)
        async with self.__database.transaction():
            for input_task in input_tasks["tasks"]:
                id = input_task["id"]
                query = self.__tasks.update().where(self.__tasks.c.id == id).values(**input_task)
                await self.__database.execute(query=query)
                await self.__scheduler.add_task(*get_task_schedule(input_task))

    async def delete(self):  # delete all tasks
        """
        Delete all tasks

        responses:
            200:
                description: if id is found in DB
        :return:
        """
        query = self.__tasks.delete()
        await self.__database.execute(query=query)
        await self.__scheduler.clear_all_tasks()


class TaskByIdHandler(RequestHandler):
    endpoint = URI_HEADER + r"/tasks/([0-9]+)"

    def initialize(self, tasks: Table, database: Database, scheduler: TaskExpiryAlert):
        self.__tasks: Table = tasks
        self.__database = database
        self.__scheduler = scheduler

    async def get(self, id: int):  # response one task
        """
        Get one task by id.

        responses:
            200:
                description: if id is found in DB
                response body:
                {
                    "id": task_id of created task,
                    **request_body
                }
            404:
                description: if id is not found in DB
        :return:
        """
        query = self.__tasks.select().where(self.__tasks.c.id == id)
        row = await self.__database.fetch_one(query=query)
        if row is not None:
            self.write(process_row(row))
        else:
            app_log.error(f"No task with id {id}.")
            self.set_status(404, "Task not founded.")

    async def put(self, id: int):  # update specific task
        """
        Update existing task

        parameters: None
        request body:
        {
            "title": string,
            "description": string (optional),
            "expiry_dt": datetime string in isoformat with local timezone (optional)
        }
        responses:
            200:
                description: if id is found in DB
                response body:
                {
                    "id": task_id of created task,
                    **request_body
                }
            404:
                description: if id is not found in DB
        :return:
        """
        query = self.__tasks.select().where(self.__tasks.c.id == str(id))
        task_exist = await self.__database.fetch_one(query=query)
        if task_exist:
            input_task = {**json_decode(self.request.body), "id": id}
            query = self.__tasks.update().where(self.__tasks.c.id == str(id)).values(**input_task)
            await self.__database.execute(query=query)
            await self.__scheduler.add_task(*get_task_schedule(input_task))
            self.write(input_task)
        else:
            self.set_status(404, "Task not founded.")

    async def delete(self, id: int):  # delete one task
        """
        Delete existing task

        responses:
            200:
                description: if id is found in DB
            404:
                description: if id is not found in DB
        :return:
        """
        query = self.__tasks.delete().where(self.__tasks.c.id == id)
        is_deleted = await self.__database.execute(query=query)
        if not is_deleted:
            self.set_status(404, "Task not founded.")
        else:
            await self.__scheduler.remove_task(id)
