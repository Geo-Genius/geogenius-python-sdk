# coding: utf-8
"""Provides magically-named functions for python-package installation."""

import os.path
from notebook.utils import url_path_join
from geogenius_jupyter_notebook_extensions.servers.HelloWorldHandler import HelloWorldHandler


def _jupyter_server_extension_paths():
    return [{
        "module": "geogenius_jupyter_notebook_extensions"
    }]


def _jupyter_nbextension_paths():
    # src & dest are os paths, and so must use os.path.sep to work correctly on
    # Windows.
    # In contrast, require is a requirejs path, and thus must use `/` as the
    # path separator.
    return [dict(
        section='notebook',
        # src is relative to current module
        src=os.path.join('static', 'toggle_iframe'),
        # dest directory is in the `nbextensions/` namespace
        dest='toggle_iframe',
        # require is also in the `nbextensions/` namespace
        # must use / as path.sep
        require='toggle_iframe/main',
    )]


def load_jupyter_server_extension(nb_server_app):
    """
    Called when the extension is loaded.
    Args:
        nb_server_app (NotebookWebApplication): handle to the Notebook webserver instance.
    """
    nb_server_app.log.info("server extension module enabled!")
    web_app = nb_server_app.web_app
    host_pattern = '.*$'
    route_pattern = url_path_join(web_app.settings['base_url'], '/hello')
    web_app.add_handlers(host_pattern, [(route_pattern, HelloWorldHandler)])
