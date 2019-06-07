import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from threading import Thread
import re


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


def parse_afisha_movie(film_meta):
    def get_content(field):
        try:
            return field['content']
        except KeyError:
            return None

    def get_float(float_candidate):
        try:
            return float(float_candidate)
        except ValueError:
            return None

    return {
        'name': get_content(film_meta),
        'image': get_content(film_meta.findNext('meta', itemprop='image')),
        'director': get_content(
            film_meta.findNext('meta', itemprop='director')
        ),
        'description': get_content(
            film_meta.findNext('meta', itemprop='description')
        ),
        'afisha_link': film_meta.findNext('a')['href'],
        'genre': film_meta.findNext('span').string,
        'short_desc': film_meta.parent.findNext('p').string,
        'afisha_rating': get_float(
            film_meta.parent.parent.findNext('div', 'card__actions').div.string
        )
    }


def parse_afisha_list(raw_html):
    items_skip = 2
    items_limit = 10
#    try:
    film_tags = BeautifulSoup(raw_html, 'lxml').find_all(
        'meta',
        itemprop='name',
        limit=items_skip+items_limit   # find 12 tags
    )[items_skip:]                     # and skip 1st and 2nd
    print(film_tags)
    return [parse_afisha_movie(film_meta) for film_meta in film_tags]
#    except TypeError:
#        return None

        
def get_afisha_list(cache):
    afisha_list = cache.get('afisha-list')
    if afisha_list is None:
        afisha_list = parse_afisha_list(fetch_page(AFISHA))
        cache.set('afisha-list', afisha_list, timeout=3600)
    return afisha_list


def get_proxies_list(cache):
    proxies_list = cache.get('proxies-list')
    if proxies_list is None:
        proxies_list = fetch_page(
            FREEPROXY_API_URL,
            FREEPROXY_API_PARAMS
        ).decode('utf-8').split('\n')
        cache.set('proxies-list', proxies_list, timeout=3600)
    return proxies_list


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


def parse_kinopoisk_info(movie_title, proxies_pool, cache):
    movie_url = parse_kinopoisk_info_callback(
        parse_kinopoisk_movie_url,
        movie_title,
        proxies_pool,
    )
    movie_rates = parse_kinopoisk_info_callback(
        parse_kinopoisk_movie_rating,
        movie_url,
        proxies_pool,
    ) or (0, 0)
    cache.set(
        movie_title,
        {
            'kp_link': movie_url,
            'kp_rating': movie_rates[0],
            'kp_votes': movie_rates[1]
        },
        timeout=3600
    )


def start_kinopoisk_parser(cache, movies_list):
    for movie_name in movies_list:
        if cache.get(movie_name) is None:
            thread = Thread(target=parse_kinopoisk_info, args=(
                movie_name,
                get_proxies_list(cache),
                cache
            ))
            thread.daemon = True
            thread.start()
