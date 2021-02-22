import logging
from tornado.log import enable_pretty_logging


access_log = logging.getLogger("tornado.access")
app_log = logging.getLogger("tornado.application")
gen_log = logging.getLogger("tornado.general")

access_log.setLevel(logging.INFO)
app_log.setLevel(logging.INFO)
gen_log.setLevel(logging.INFO)

enable_pretty_logging()
