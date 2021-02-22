# tornado-task-manager

## Overview

A Simple Task Management System which supports CRUD of tasks with RESTful API and a task expiry notification service.

Originally it is a take home assessment within the interview process of a company.  
The tech lead leave that company a few days after I submit the assessment, and later on the new tech lead decided to hire junior developers...
so I don't know if this actually passed the interview or not LOL.

## Design docs

### Assumptions on requirements:
* Single user, assumed to be deployed in private network
    * so there is no user authentication.
* Task volume is not too large (e.g. <10k)
    * so the task scheduler is self-implemented, running along with the API server.
* Request volume is also not too large
    * so that single process of API server is enough
* Development environment: MacOS, Deployment environment: Linux

### Choices of Frameworks
I have chosen the following Python frameworks / libraries:
* [Tornado](https://www.tornadoweb.org/)
    * It is chosen because it is used in that company. 
    * Alternative: [FastAPI](https://fastapi.tiangolo.com/), which also supports async with additional functionalities like auto-generated Swagger docs
* [encode/databases](https://github.com/encode/databases)
    * Provides async connection to relational DB with SQLAlchemy Core expression language
    * Remarks: SQLAlchemy ORM is not supported. 
    * If there are more DB tables and more endpoints, consider using [pydantic](https://github.com/samuelcolvin/pydantic) model to act as entity object and DTO.
* [Python Sorted Containers](http://www.grantjenks.com/docs/sortedcontainers/)
    * For the task scheduler (see "Task Expiry Notification" sub-section) 

### API

* Basically follows RESTful design principle.
* 3 endpoints:
    1. `v1/health` with `GET` method: basic health check
    1. `v1/tasks` with `GET`, `POST`, `PUT` and `DELETE` methods
    1. `v1/tasks/<task_id>` with `GET`, `PUT` and `DELETE` methods
* Originally wanted to build a swagger doc (like [this](https://fastapi.tiangolo.com/#interactive-api-docs-upgrade)), however I don't have enough time to figure out how to do it for Tornado.
* Now a very brief API docs is written in the doc string of the class `task_man.handlers.v1.tasks.TasksHandler` and `task_man.handlers.v1.tasks.TaskByIdHandler`.

### Task Expiry Notification Service

* Functionality:
    * notify user by console log if the task will be expired in 15 minutes. (or notify immediately after accepting expired task from API)

* Module:
    * `task_man.scheduling`

* Design on implementations:
    * a periodic background task running in a separate thread along with the API server
        * originally want it to be an long-living async function in the same thread as the API server, however cannot figure out how to run the function right after API server main IO loop started.
    * instead of periodically checking DB for next to-be-expired task, the service caches task after accepting API requests of adding new tasks / updating or deleting existing tasks.
        * The cache is implemented in `task_man.scheduling.TaskCache`. It is composed of 2 parts:
            1. A dictionary with `id` as key and `(title, expiry_dt)` as value, storing latest snapshots of to-be-expired tasks.
            1. A `SortedSet` (from sortedcontainers) storing `(expiry_dt, id)`, storing all snapshots of tasks with non-nul `expiry_dt`.
                * e.g. if `expiry_dt` of a task is updated once, there will be 2 records in the sorted set.
                * chosen `SortedSet` instead of a priority queue to avoid duplicated records.
        * The scheduler keeps checking if the next to-be-expired task (min entry in the sorted sort) will be expired in 15mins, and if yes then process the task.
        * During processing an entry `(expiry_dt, id)` from the sorted set, it will check if `expiry_dt` matches the latest snapshot from the dictionary.
            * if matches, notify user and remove the task from both the dict and the sorted set
            * if not matches or not found, just discard the entry (the task is updated by the user)
    * auto-load to-be-expired tasks from DB to task cache when app start.
    * **CAUTION**: multi-process of API server is not supported. If enabled multi-process, each process will maintain a cache and will have problem on cache invalidation. Consider remote shared cache like RQ scheduler.
    
## Development Setup

### Python environment:
1. create a new conda environment and activate it. (I am using Python 3.7)
1. run `cd src` and `python setup.py develop` in terminal to install `task_man` in development mode.

### Database:
I have chosen MySQL as the backed database.  
1. Please follow standard MySQL setup guide to install MySQL DB locally.
1. run `mysql/create_db.sql` and then `mysql/task.sql` using tools like DBeaver to create database and table for development.

### How to run (Pycharm):
1. Choose the conda env with `task_man` dev installed in `Settings/Project/Project Interpreter
1. Environment variables required to run the app: `MYSQL_HOST`, `MYSQL_USER` and `MYSQL_PASSWORD` (default values: `localhost:3306`, `root`, `root`)
    1. Click `Edit Configuration` in the upper right.  
    1. Choose `src/main.py` in `Script path`.
    1. Setup the environment variables.  
1. Run `src/main.py` with the configuration you have just created to start the app.

## Deployment Setup (brief)
1. git clone from the repo
1. build wheels and install `task_man` package
1. setup environment variables for DB connection
1. run with entry point: `src/main.py`

## Testing

### Environment setup:
1. The functional test connects to the DB synchronously, which requires `mysqlclient` to be installed.  
    * Setup guide of `mysqlclient`: https://pypi.org/project/mysqlclient/
1. Also requires `requests`.
1. On Mac: can do steps 1 and 2 by running `chmod 700 test_req_setup_mac.sh` and then `test_req_setup_mac.sh`.
1. On Ubuntu: can do steps 1 and 2 by running `test_req_setup_ubuntu.sh`.

### Remarks:
1. Test coverage is not enough. 
    * It only provides basic positive tests. Need to add negative test cases e.g. test with invalid inputs.
    * Interaction between API server and task expiry notification is not tested.