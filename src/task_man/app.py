import threading
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application

from .handlers.v1.health import HealthHandler
from .handlers.v1.task import TasksHandler, TaskByIdHandler
from .db import create_db_container, DbContainer
from .logger import app_log
from .scheduling import TaskExpiryAlert
from .config import Config


def make_app(db_container: DbContainer):
    return Application([
        (HealthHandler.endpoint, HealthHandler),
        (TasksHandler.endpoint, TasksHandler, dict(tasks=db_container.tasks, database=db_container.database, scheduler=TaskExpiryAlert)),
        (TaskByIdHandler.endpoint, TaskByIdHandler, dict(tasks=db_container.tasks, database=db_container.database, scheduler=TaskExpiryAlert)),
    ])


def main(config: Config):
    db_container = create_db_container(config.mysql)

    async def connect_db():
        await db_container.database.connect()

    async def start_up_event():
        await TaskExpiryAlert.initialize(db_container)

    async def disconnect_db():
        await db_container.database.disconnect()

    IOLoop.current().run_sync(connect_db)
    IOLoop.current().run_sync(start_up_event)
    threading.Thread(target=TaskExpiryAlert.scheduler).start()
    try:
        app = make_app(db_container)
        app.listen(config.port)
        # if config.processes < 2:
        #     app.listen(config.port)
        # else:
        #     server = HTTPServer(app)
        #     server.bind(config.port)
        #     server.start(config.processes)
        IOLoop.current().start()
    except Exception as e:
        app_log.error(e)
    finally:
        IOLoop.current().run_sync(disconnect_db)
        TaskExpiryAlert.stop_scheduler()
