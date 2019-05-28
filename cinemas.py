import requests
from fake_useragent import UserAgent
import lxml
from bs4 import BeautifulSoup
import re


AFISHA = 'https://www.afisha.ru/msk/schedule_cinema/'


def fetch_page(url, params=None, proxy=None):
    proxy_timeout = 10
    try:
        return requests.get(
            url,
            params=params,
            headers={'User-agent': str(UserAgent().random)},
            proxies={'https': 'https://{}'.format(proxy)} if proxy else None,
            timeout=proxy_timeout
        ).content
    except requests.exceptions.RequestException:
        return None


def parse_afisha_list(raw_html):
    items_skip = 2
    items_limit = 10
    afisha_soup = BeautifulSoup(raw_html, 'lxml')
    film_tags = afisha_soup.find_all(
        'meta',
        itemprop='name',
        limit=items_skip+items_limit   # find 12 tags
    )[items_skip:]                     # and skip 1st and 2nd
    afisha_list = []
    for film_meta in film_tags:
        film_desc = film_meta.findNext('meta', itemprop='description')['content']
        sentence_delimiter_pos = film_desc.find('. ')
        if sentence_delimiter_pos == -1:
            sentence_delimiter_pos = len(film_desc)
        film_content = {
            'name': film_meta['content'],
            'image': film_meta.findNext('meta', itemprop='image')['content'],
            'director': film_meta.findNext('meta', itemprop='director')['content'],
            'desc_start': film_desc[:sentence_delimiter_pos+2],
            'desc_all': film_desc[sentence_delimiter_pos+2:],
            'afisha_link': film_meta.findNext('a')['href'],
            'genre': film_meta.findNext('span').string,
            'afisha_rating': film_meta.findNext('div', attrs={'class' : 'card__actions'}).contents[0] # TODO:
        }
        afisha_list.append(film_content)
    return afisha_list
