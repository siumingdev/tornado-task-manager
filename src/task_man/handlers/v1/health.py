from tornado.web import RequestHandler

from . import URI_HEADER


class HealthHandler(RequestHandler):
    endpoint = URI_HEADER + r"/health"

    def get(self):
        self.write("Healthy")
