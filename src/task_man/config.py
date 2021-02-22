from typing import NamedTuple


class MysqlConfig(NamedTuple):
    host: str = "localhost:3306"
    user: str = "root"
    password: str = "root"
    db: str = "task_man"
    pool_min_size: int = 5
    pool_max_size: int = 20


class Config(NamedTuple):
    mysql: MysqlConfig = MysqlConfig()
    # processes: int = 1
    port: int = 8888
