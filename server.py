from flask import Flask, render_template
from werkzeug.contrib.cache import FileSystemCache
import cinemas


app = Flask(__name__)
cache = FileSystemCache('cache', default_timeout=3600)


def get_afisha_list():
    afisha_list = cache.get('afisha-list')
    if afisha_list is None:
        afisha_list = cinemas.parse_afisha_list(
            cinemas.fetch_page(cinemas.AFISHA)
        )
        cache.set('afisha-list', afisha_list)
    return afisha_list


@app.route('/')
def films_list():
    afisha_list = get_afisha_list()
    return render_template('films_list.html', afisha_list=afisha_list)


if __name__ == "__main__":
    app.run()
