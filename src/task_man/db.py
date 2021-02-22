from typing import NamedTuple

import sqlalchemy
from databases import Database, DatabaseURL

from .config import MysqlConfig


class DbContainer(NamedTuple):
    database: Database
    tasks: sqlalchemy.Table


def create_db_container(db_config: MysqlConfig):
    """
    Create namedtuple containing database object (from encode/databases) and sqlalchemy.Table object(s) from DB config.

    :param db_config: DB config
    :return:
    """
    DATABASE_URL = DatabaseURL(f"mysql://{db_config.user}:{db_config.password}@{db_config.host}/{db_config.db}")
    database = Database(DATABASE_URL, min_size=db_config.pool_min_size, max_size=db_config.pool_max_size)

    metadata = sqlalchemy.MetaData()
    tasks = sqlalchemy.Table(
        "task",
        metadata,
        sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
        sqlalchemy.Column("title", sqlalchemy.VARCHAR),
        sqlalchemy.Column("description", sqlalchemy.VARCHAR),
        sqlalchemy.Column("expiry_dt", sqlalchemy.DATETIME)
    )

    return DbContainer(database=database, tasks=tasks)
