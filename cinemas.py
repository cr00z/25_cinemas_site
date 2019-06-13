import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import re
import json


AFISHA = 'https://www.afisha.ru/msk/schedule_cinema/'
FREEPROXY_API_URL = 'http://www.freeproxy-list.ru/api/proxy'
FREEPROXY_API_PARAMS = {'anonymity': 'false', 'token': 'demo'}
KINOPOISK = 'https://www.kinopoisk.ru/'
KINOPOISK_SEARCH = '{}index.php'.format(KINOPOISK)


def fetch_page(url, params=None, proxy=None):
    proxy_timeout = 10
    try:
        response = requests.get(
            url,
            params=params,
            headers={'User-agent': str(UserAgent().random)},
            proxies={'https': 'https://{}'.format(proxy)} if proxy else None,
            timeout=proxy_timeout
        )
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException:
        return None


def parse_afisha_movie(film_info):
    return {
        'poster_url': film_info['Poster']['Url'],
        'year': film_info['ProductionYear'],
        'country': film_info['Country'],
        'genres': [genre['Name'] for genre in film_info['Genres']['Links']],
        'directors': [director['Name'] for director in film_info['Directors']['Links']],
        'orig_name': film_info['OriginalName'],
        'duration': film_info['Duration'],
        'age_restriction': film_info['AgeRestriction'],
        'afisha_rating': film_info['Rating'],
        'name': film_info['Name'],
        'afisha_url': film_info['Url'],
        'verdict': film_info['Verdict'],
        'description': film_info['Description']
    }


def parse_afisha_list(raw_html):
    if raw_html is None:
        return None
    html_str = raw_html.decode("utf-8")
    start_pos = html_str.find('JsonLogger,') + len('JsonLogger,')
    end_pos = html_str.find('),document.getElementById', start_pos)
    afisha_list = json.loads(html_str[start_pos:end_pos])
    afisha_list = afisha_list['ScheduleWidget']['Items']
    return [parse_afisha_movie(movie_info) for movie_info in afisha_list]


def get_proxies_list():
    return fetch_page(
        FREEPROXY_API_URL,
        FREEPROXY_API_PARAMS
    ).decode('utf-8').split('\n')


def get_soup(raw_html):
    try:
        return BeautifulSoup(raw_html, 'lxml')
    except TypeError:
        return None


def find_info_in_soup(soup, tag, tag_param, next_sibling=False):
    try:
        soup_tag = soup.find(tag, tag_param)
        if next_sibling:
            soup_tag = soup_tag.next_sibling
        return soup_tag.text
    except AttributeError:
        return None


def parse_kinopoisk_movie_url(movie_title, proxy):
    raw_html = fetch_page(
        KINOPOISK_SEARCH,
        params={'kp_query': movie_title},
        proxy=proxy
    )
    kp_soup = get_soup(raw_html)
    if kp_soup is None:
        return None
    try:
        data_url = kp_soup.find('a', {'class': 'js-serp-metrika'})['data-url']
        return re.search(r'film/\d*', data_url)[0]
    except (TypeError, AttributeError):
        return None


def parse_kinopoisk_movie_rating(movie_url, proxy):
    nbsp_char = '\xa0'
    raw_html = fetch_page('{}{}'.format(KINOPOISK, movie_url), proxy=proxy)
    kp_soup = get_soup(raw_html)
    if kp_soup is None:
        return None
    movie_votes_str = find_info_in_soup(kp_soup, 'span', {'class': 'ratingCount'})
    movie_rating_str = find_info_in_soup(kp_soup, 'span', {'class': 'rating_ball'})
    if not movie_rating_str:
        movie_votes_str = find_info_in_soup(
            kp_soup,
            'span',
            {'title': 'Рейтинг скрыт (недостаточно оценок)'},
            next_sibling=True
        )
        movie_rating_str = '0'
        if not movie_votes_str:
            return None
    return (
        float(movie_rating_str),
        int(movie_votes_str.replace(nbsp_char, ''))
    )


def parse_kinopoisk_info_callback(callback_func, url, proxies_pool):
    for proxy in proxies_pool:
        return_value = callback_func(url, proxy)
        if return_value:
            return return_value


if __name__ == "__main__":
    pass
