from flask import Flask, render_template, url_for
from werkzeug.contrib.cache import FileSystemCache
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, active_count
import time
import sys
import cinemas


SLEEP_DELAY = 25    # for 30 sec heroku limit


sys.setrecursionlimit(10000)
app = Flask(__name__)
cache = FileSystemCache('cinemas_cache')
thread_results = []


def start_kinopoisk_parser(movies_names):
    '''
    Не получается корректно реализовать ThreadPoolExecutor.
    Потоки блокируют основной поток до своего завершения и пользователь не получает вывод.
    Для Thread есть костыль thread.daemon, а тут не получается.
    + heroku накладывает ограничение на работу тредов в 30 секунд
    Что можно сделать?

    with ThreadPoolExecutor() as pool:
        for movie_name in movies_names:
            thread_results.append(pool.submit(
                cinemas.parse_kinopoisk_info,
                movie_name,
                proxies_list,
                cache
            ))
    '''
    proxies_list = cinemas.get_proxies_list(cache)
    if proxies_list is None:
        return None
    for movie_name in movies_names:
        thread = Thread(
            target=cinemas.parse_kinopoisk_info,
            args=(movie_name, proxies_list, cache)
        )
        thread.daemon = True
        thread.start()


def sleep_while_threads_works_or_timeout(seconds):
    for count in range(seconds):
        if active_count() == 0:
            break
        time.sleep(1)


def add_kinopoisk_info(movies_list):
    for movie_id, movie in enumerate(movies_list):
        movies_list[movie_id]['kp_url'] = cache.get('{}_url'.format(movie['name']))
        movies_list[movie_id]['kp_rates'] = cache.get('{}_rates'.format(movie['name']))


@app.route('/')
def films_stub():
    return render_template('redirect.html', sleep_delay=SLEEP_DELAY)


@app.route('/films')
def films_list():
    movies_list = cinemas.get_afisha_list(cache)
    if movies_list is None:
        return render_template('films_list.html', error=True)
    movies_names = [movie['name'] for movie in movies_list]
    start_kinopoisk_parser(movies_names)
    sleep_while_threads_works_or_timeout(SLEEP_DELAY)
    add_kinopoisk_info(movies_list)
    return render_template('films_list.html', movies_list=movies_list)


if __name__ == "__main__":
    app.run()
