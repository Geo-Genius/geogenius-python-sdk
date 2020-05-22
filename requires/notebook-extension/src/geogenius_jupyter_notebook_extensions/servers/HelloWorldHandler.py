from notebook.base.handlers import IPythonHandler
import os


class HelloWorldHandler(IPythonHandler):
    def get(self):
        print("++++++", os.getenv('JUPYTER_TOKEN'))
        self.finish('Hello, this is Geogenius2!')
