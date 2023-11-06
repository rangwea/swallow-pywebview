from unittest import TestCase
from pathlib import Path
from src.globals import gbl

gbl.base_dir = Path(__file__)

from src.api import Api

class TestApi(TestCase):
    def setUp(self):
        app_name = 'swallow'
        home_path = Path.home() / f'.{app_name}'
        home_path.mkdir(exist_ok=True)
        self.api = Api(Path.cwd().parent, home_path)

    def test_site_preview(self):
        self.api.site_preview()

    def test_site_deploy(self):
        self.api.site_deploy()

    def test_conf_get(self):
        print(self.api.conf_get('cos'))

    def test_conf_save(self):
        self.api.conf_save('cos', {'appid': 'a'})

    def test_article_list(self):
        l = self.api.article_list()
        print(l)

    def test_article_save(self):
        self.api.article_save('''
```
title = "This is my first blog"
categories = [""]
date = "2012-04-06"
description = ""
tags = ["one","two"]
```

中文
'''
        )

    def test_article_get(self):
        print(self.api.article_get(1665660190468))

    def test_article_del(self):
        self.api.article_del(1)

    def test_site_conf_get(self):
        print(self.api.site_conf_get())

    def test_site_conf_save(self):
        self.api.site_conf_save({'title':'swallow', 'description': 'All those moments will be lost in time', 'theme': 'stack'})
