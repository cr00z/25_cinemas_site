from flask import Flask, render_template
from werkzeug.contrib.cache import FileSystemCache
import cinemas
import threading
import time


SLEEP_DELAY = 3000


app = Flask(__name__)
cache = FileSystemCache('cache', default_timeout=3600)


@app.route('/')
def films_list():
    movies_list = cinemas.get_afisha_list(cache)
    cinemas.start_kinopoisk_parser(
        cache,
        [movie['name'] for movie in movies_list]
    )
    for count in range(SLEEP_DELAY):
        if threading.active_count() == 0:
            break
        time.sleep(1)
    for movie_id, movie in enumerate(movies_list):
        kinopoisk_info = cache.get(movie['name'])
        if kinopoisk_info is None:
            kinopoisk_info = dict.fromkeys(['kp_link', 'kp_rating', 'kp_votes'])
        movies_list[movie_id].update(kinopoisk_info)
    return render_template('films_list.html', movies_list=movies_list)


if __name__ == "__main__":
    app.run()
