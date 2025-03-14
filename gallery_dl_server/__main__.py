# -*- coding: utf-8 -*-

import multiprocessing

from gallery_dl_server import app

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app.main(is_main_module=True)
