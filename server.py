import threading
from flask import Flask, render_template
import cinemas
import time


SLEEP_DELAY = 10
SLEEP_ONE_HOUR = 3600


app = Flask(__name__)
movies_list = []
error = False
mutex = threading.Lock()


def run_parser():
    global movies_list, error
    while True:
        raw_html = cinemas.fetch_page(cinemas.AFISHA)
        if raw_html is None:
            error = True
            time.sleep(SLEEP_DELAY)
            continue

        error = False
        movies_list_new = cinemas.parse_afisha_list(raw_html)
        if not movies_list_new:
            time.sleep(SLEEP_DELAY)
            continue
        with mutex:
            movies_list = movies_list_new.copy()

        proxies_list = cinemas.get_proxies_list() or proxies_list

        for movie_id, movie in enumerate(movies_list):
            movie_kp_url = cinemas.parse_kinopoisk_info_callback(
                cinemas.parse_kinopoisk_movie_url,
                movie['name'],
                proxies_list
            )
            with mutex:
                movies_list[movie_id]['kp_url'] = movie_kp_url

            movie_kp_rates = cinemas.parse_kinopoisk_info_callback(
                cinemas.parse_kinopoisk_movie_rating,
                movies_list[movie_id]['kp_url'],
                proxies_list
            )
            with mutex:
                movies_list[movie_id]['kp_rates'] = movie_kp_rates

        time.sleep(SLEEP_ONE_HOUR)


@app.before_first_request
def activate_movie_parser():
    thread = threading.Thread(target=run_parser)
    thread.start()


@app.route('/')
def films_list():
    if error:
        return render_template('films_list.html', error=True)
    if not movies_list:
        return render_template('redirect.html', sleep_delay=SLEEP_DELAY)
    with mutex:
        return render_template('films_list.html', movies_list=movies_list)


if __name__ == "__main__":
    app.run()
