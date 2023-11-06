# -*- coding: utf-8 -*-
from datetime import datetime
import json
import logging
import shutil
import sqlite3
import webbrowser
from pathlib import Path
from subprocess import Popen
from zipfile import ZipFile

import psutil
import tomli
import tomli_w
import webview
from flask import Flask, request, render_template, send_file
from psutil import NoSuchProcess

from src.cossync import COS
from src.initsql import init_sql

SITE_NAME = 'site'
CONF_FILE = 'conf.json'
DB_NAME = 'db'

site_static_path = Path()
site_images_path = Path()  # type Path
current_article_id = ''

get_site_image_url_prefix = '/get_site_image/'


def use_logging(func):
    def wrapper(*args):
        try:
            r = func(*args)
            logging.info(f'call {func.__name__}({args}), return: {r}')
            return r
        except Exception as e:
            logging.error(f'sever error:{e}', exc_info=True)
            raise

    return wrapper


def sqlite_dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def read_matter(article_path: Path):
    matter = ''
    with article_path.open(encoding='utf-8') as f:
        i = 0
        for line in f.readlines():
            if i > 1:
                break
            if line.startswith('+++'):
                i = i + 1
            else:
                matter = matter + line
    return tomli.loads(matter)


def gen_aid():
    return datetime.now().strftime('%Y%m%d%H%M%S')


class Hugos:
    def __init__(self, base_dir: Path, app_home_path: Path, site_name):
        logging.info(f'init hugos:{self}')
        self.hugo = str((base_dir / 'lib' / 'hugo').absolute())
        self.app_home_path = app_home_path
        self.site_name = site_name
        self.site_path = app_home_path / site_name
        self.articles_path = self.site_path / 'content' / 'post'
        self.pre_pid_path = self.site_path / 'pre.pid'
        self.public_path = self.site_path / 'public'
        self.static_path = self.site_path / 'static'
        self.images_path = self.static_path / 'images'
        self.themes_path = self.site_path / 'themes'
        self.images_base_url = '/images/'
        self.site_conf_path = self.site_path / 'config.toml'
        self.site_about_path = self.site_path / 'content' / 'about' / 'index.md'
        self.themes_zip_path = base_dir / 'lib' / 'themes.zip'
        self.lib_conf_path = base_dir / 'lib' / 'config.toml'

    def new_site(self):
        if self.site_path.exists():
            logging.info(f'Not will be new site, because site has be existed:{self.site_path}')
            return
        Popen([self.hugo, 'new', 'site', self.site_name], cwd=self.app_home_path).wait()
        self.articles_path.mkdir(parents=True, exist_ok=True)
        self.site_about_path.parent.mkdir(exist_ok=True)
        self.site_about_path.touch(exist_ok=True)

        self.site_conf_path.unlink(missing_ok=True)
        shutil.copyfile(self.lib_conf_path, self.site_conf_path)

        with ZipFile(self.themes_zip_path) as z:
            z.extractall(path=self.themes_path)

        logging.info(f'new a site: {self.site_name}')

    def preview(self):
        if self.pre_pid_path.exists():
            e_pid = self.pre_pid_path.read_text()
            if e_pid:
                try:
                    p = psutil.Process(int(e_pid))
                    if 'hugo' in p.name() and p.is_running():
                        return
                    else:
                        self.pre_pid_path.write_text('')
                except NoSuchProcess:
                    pass

        pid = Popen([self.hugo, 'server'], cwd=self.site_path).pid
        self.pre_pid_path.write_text(str(pid))
        logging.info('start preview')

    def close_pre(self):
        pid = self.pre_pid_path.read_text()
        if pid:
            psutil.Process(int(pid)).kill()
        self.pre_pid_path.write_text('')

    def generate(self):
        Popen([self.hugo], cwd=self.site_path).wait()
        logging.info('hugo generate')

    def article_path(self, aid):
        return self.articles_path / f'{aid}.md'

    def loads_site_conf(self):
        with self.site_conf_path.open('rb') as f:
            return tomli.load(f)


class Conf:
    def __init__(self, app_home_path):
        self.conf_path = app_home_path / CONF_FILE  # type: Path
        if not self.conf_path.exists():
            self.conf_path.write_text('{}')

    def get(self, key):
        with self.conf_path.open() as f:
            return json.load(f).get(key)

    def save(self, key, content):
        with self.conf_path.open('r') as f:
            conf = json.load(f)
            conf[key] = content
        with self.conf_path.open('w') as f:
            json.dump(conf, f, indent=4, ensure_ascii=False)
            logging.info(f'save conf:{key}={conf}')


class DB:
    def __init__(self, db_path: Path):
        self.db_path = db_path

        if not self.db_path.exists():
            conn = self._conn()
            cur = conn.cursor()
            cur.executescript(init_sql)
            conn.commit()
            cur.close()
            conn.close()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def fetchall(self, sql):
        with self._conn() as conn:
            conn.row_factory = sqlite_dict_factory
            cur = conn.execute(sql)
            d = cur.fetchall()
            cur.close()
            return d

    def fetchone(self, sql):
        with self._conn() as conn:
            conn.row_factory = sqlite_dict_factory
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchone()

    def save(self, table, m: dict):
        placeholders = ', '.join(['?'] * len(m))
        columns = ', '.join(m.keys())
        sql = f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})"
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(sql, list(m.values()))
        conn.commit()

    def execute(self, sql):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()


class Api:
    def __init__(self, base_dir, app_home_path):
        self.base_dir = base_dir
        self.hugos = Hugos(base_dir, app_home_path, SITE_NAME)
        self.conf = Conf(app_home_path)
        self.app_home_path = app_home_path
        self.db = DB(app_home_path / DB_NAME)

        # new a site
        self.hugos.new_site()
        global site_images_path
        site_images_path = self.hugos.images_path
        global site_static_path
        site_static_path = self.hugos.static_path
        self.window = None

    def front_log(self, msg):
        logging.info(msg)

    @use_logging
    def site_preview(self):
        self.hugos.preview()
        webbrowser.open('http://localhost:1313/', new=1, autoraise=True)

    @use_logging
    def site_deploy(self):
        # exec hugo to generate public
        self.hugos.generate()
        # sync public to cos
        cos = COS(**self.conf.get('cos'), root=str(self.hugos.public_path.absolute()))
        cos.sync()

    @use_logging
    def conf_get(self, key):
        return self.conf.get(key)

    @use_logging
    def conf_save(self, key, content):
        return self.conf.save(key, content)

    @use_logging
    def article_list(self, page, search):
        size = 200
        offset = size * 10 if page else 0
        sql = 'select * from t_article'
        if search:
            sql = sql + f" where title like '%{search}%' or tags like '%{search}%' or categories like '%{search}%'"
        sql = sql + f' limit {size} offset {offset}'
        return self.db.fetchall(sql)

    @use_logging
    def article_new(self):
        global current_article_id
        current_article_id = gen_aid()

    def article_save(self, article):
        if current_article_id == 'about':
            article_path = self.hugos.site_about_path
            article_path.write_text(article)
        else:
            aid = current_article_id if current_article_id else gen_aid()
            article_path = self.hugos.article_path(aid)

            # replace front matter and write file
            with article_path.open('w+', encoding='utf-8') as f:
                i = 0
                for line in article.splitlines():
                    if (i == 0 or i == 1) and line.startswith('```'):
                        f.write(line.replace('```', '+++\n'))
                        i = i + 1
                    else:
                        f.write(line + '\n')

            matter = read_matter(article_path)
            d = {
                'aid': aid,
                'title': matter.get('title'),
                'create_time': matter.get('date'),
                'update_time': datetime.now().strftime('%Y-%m-%d, %H:%M:%S'),
                'tags': ','.join(matter.get('tags')),
                'categories': ','.join(matter.get('categories')),
            }
            self.db.save('t_article', d)

    @use_logging
    def article_get(self, aid):
        article = ''
        if aid == 'about':
            article_path = self.hugos.site_about_path
        else:
            article_path = self.hugos.article_path(aid)

        with article_path.open(encoding='utf-8') as f:
            i = 0
            for line in f.readlines():
                if (i == 0 or i == 1) and line.startswith('+++'):
                    line = line.replace('+++', '```')
                    i = i + 1
                    article = article + line
                else:
                    article = article + line

        global current_article_id
        current_article_id = aid

        return article

    @use_logging
    def article_del(self, aid):
        self.db.execute(f'delete from t_article where aid={aid}')
        self.hugos.article_path(aid).unlink(missing_ok=True)
        if aid:
            shutil.rmtree(site_images_path / str(aid), ignore_errors=True)

    @use_logging
    def site_conf_get(self):
        site_config = self.hugos.loads_site_conf()
        keys = ('title', 'description', 'theme', 'copyright', 'author')
        return {i: site_config.get(i) for i in keys}

    @use_logging
    def site_conf_save(self, new_site_conf):
        site_config = self.hugos.loads_site_conf()
        site_config.update(new_site_conf)
        with self.hugos.site_conf_path.open('wb') as f:
            tomli_w.dump(site_config, f)

    @use_logging
    def upload_site_image(self, name):
        file_types = ('Image Files (*.bmp;*.jpg;*.gif;*.png)', 'All files (*.*)')
        src = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)[0]
        target = self.hugos.static_path / name
        shutil.copyfile(src, target)
        logging.info(f'copy [{src}] to {target}')
        return get_site_image_url_prefix + name

    @use_logging
    def get_site_image_config(self):
        return {
            'avatar': get_site_image_url_prefix + 'avatar.png' if (
                    self.hugos.static_path / 'avatar.png').exists() else '',
            'favicon': get_site_image_url_prefix + 'favicon.ico' if (
                    self.hugos.static_path / 'favicon.ico').exists() else '',
        }


from src.globals import gbl

static_dir = str(gbl.base_dir / 'static')
logging.info(f'flask static dir:{static_dir}')
server = Flask(__name__, template_folder=static_dir, static_folder=static_dir)


@server.route('/')
def landing():
    return render_template('index.html')


@server.route('/get_site_image/<name>')
def get_site_image(name):
    image = (site_static_path / name)
    return send_file(image, mimetype="image/jpeg")


@server.route('/static/images/<aid>/<name>')
def get_image(aid, name):
    image = (site_images_path / aid / name)
    return send_file(image, mimetype="image/jpeg")


@server.route('/images/upload', methods=['GET', 'POST'])
@use_logging
def upload_image():
    if not current_article_id:
        logging.error('upload images fail, aid is null')
        raise
    logging.info(request.files)
    file = request.files['image']
    article_file_path = site_images_path / current_article_id
    article_file_path.mkdir(parents=True, exist_ok=True)
    file.save(article_file_path / file.filename)
    return {'data': {'filePath': f'/static/images/{current_article_id}/{file.filename}'}}
