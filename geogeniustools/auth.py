import logging

from geogeniustools.session import get_session

auth = None


def Auth(**kwargs):
    global auth
    if auth is None or len(kwargs) > 0:
        auth = _Auth(**kwargs)
    return auth


class _Auth(object):
    geogenius_connection = None

    def __init__(self, **kwargs):
        self.logger = logging.getLogger('geogeniustools')
        self.logger.setLevel(logging.ERROR)
        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(logging.ERROR)
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.console_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.console_handler)
        self.logger.info('Logger initialized')

        self.geogenius_connection = get_session()
