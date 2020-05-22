import sys
import os
from notebook.extensions import (_get_config_dir)
from notebook.config_manager import BaseJSONConfigManager


def main():
    if len(sys.argv) is not 2:
        print('[error] please input target url, i,e : set_config "http://100.94.14.213:8080/extensions/notebook"')
        return
    iframe_src = sys.argv[1]
    sys_prefix = True
    user = False if sys_prefix else True
    config_dir = os.path.join(_get_config_dir(user=user, sys_prefix=sys_prefix), "nbconfig")
    cm = BaseJSONConfigManager(parent=None, config_dir=config_dir)
    section = "notebook"
    cm.update(section, {"side_data_searcher_iframe_src": iframe_src})


if __name__ == '__main__':
    main()
