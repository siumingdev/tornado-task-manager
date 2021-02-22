import os

from task_man.app import main
from task_man.config import Config, MysqlConfig


if __name__ == "__main__":
    main(Config(
        port=8888,
        mysql=MysqlConfig(
            host=os.environ.get("MYSQL_HOST") or "localhost:3306",
            user=os.environ.get("MYSQL_USER") or "root",
            password=os.environ.get("MYSQL_PASSWORD") or "root",
        )
    ))
