from flask import Flask, render_template, url_for
from werkzeug.contrib.cache import FileSystemCache
import cinemas
import threading
import time
import sys


SLEEP_DELAY = 25    # 30 sec heroku limit


sys.setrecursionlimit(10000)
app = Flask(__name__)
cache = FileSystemCache('cinemas_cache')


def sleep_while_threads_works_or_timeout(seconds):
    for count in range(seconds):
        if threading.active_count() == 0:
            break
        time.sleep(1)


def add_kinopoisk_info(movies_list):
    for movie_id, movie in enumerate(movies_list):
        kinopoisk_info = cache.get(movie['name'])
        if kinopoisk_info is None:
            kinopoisk_info = dict.fromkeys(['kp_link', 'kp_rating', 'kp_votes'])
        movies_list[movie_id].update(kinopoisk_info)


@app.route('/')
def films_stub():
    return render_template('redirect.html', sleep_delay=SLEEP_DELAY)


@app.route('/films')
def films_list():
    movies_list = cinemas.get_afisha_list(cache)
    if movies_list is None:
        return render_template('films_list.html', error=True)
    movies_names = [movie['name'] for movie in movies_list]
    cinemas.start_kinopoisk_parser(cache, movies_names)
    sleep_while_threads_works_or_timeout(SLEEP_DELAY)
    add_kinopoisk_info(movies_list)
    return render_template('films_list.html', movies_list=movies_list)


if __name__ == "__main__":
    app.run()
