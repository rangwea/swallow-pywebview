# -*- coding: utf-8 -*-

import webview
import logging
from pathlib import Path

app_name = 'swallow'
home_path = Path.home() / f'.{app_name}'
home_path.mkdir(exist_ok=True)

log_file = home_path / 'out.log'
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%Y/%m/%d %H:%M:%S',
                    filename=log_file.absolute()
                    )

from src.globals import gbl

base_dir = Path(__file__).parent
logging.info(f'swallow base dir:{base_dir}')
gbl.base_dir = base_dir

from src.api import Api, server

api = Api(base_dir, home_path)


def on_closing():
    try:
        # close hugo preview process
        api.hugos.close_pre()
        logging.info('pywebview window is closing')
    except Exception as e:
        logging.warning(f'on closing fail:{e}')


if __name__ == '__main__':
    window = webview.create_window(app_name, server, js_api=api, min_size=(1000, 600), width=1200, height=800,
                                   confirm_close=True)
    window.events.closed += on_closing
    api.window = window
    webview.start(debug=True)
