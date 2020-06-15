from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from time import sleep
from tqdm import tqdm, trange
from pprint import pprint
import json
import datetime
import os
import pickle
import sys

from driver_util import *


PROFILES = [
    'barackobama',
    'realdonaldtrump'
    'gavinnewsom',
    'joebiden'
]

BEGIN_DATE = '2010-01-01'
DAYS_PER_SEARCH = 30
IDS_DIR = 'ids'
RAW_DIR = 'raw'

PAGE_DELAY = 1.5  # seconds
RATE_LIMITED_DELAY = 30  # second
BASEURL = (
    'https://twitter.com/search?q=' +
    'from%3A{}%20' +
    'since%3A{}%20' +
    'until%3A{}%20' +
    'include%3Aretweets&src=typed_query&f=live'
)

NO_BROWSER = True
CHROMEDRIVER_PATH = './chromedriver'
CHROME_OPTIONS = Options()
# TWEET_SELECTOR css depends on window width
CHROME_OPTIONS.add_argument("--window-size=800,2000")
if NO_BROWSER:
    CHROME_OPTIONS.add_argument("--headless")

TWEET_SELECTOR = 'div.css-1dbjc4n.r-my5ep6.r-qklmqi.r-1adg3ll'
ID_SELECTOR = 'a.css-4rbku5.css-18t94o4.css-901oao.r-1re7ezh.r-1loqt21.r-1q142lx.r-1qd0xha.r-a023e6.r-16dba41.r-ad9z0x.r-bcqeeo.r-3s2u2q.r-qvutc0'
RATE_LIMITED_SELECTOR = 'css-901oao.r-1re7ezh.r-1qd0xha.r-a023e6.r-16dba41.r-ad9z0x.r-117bsoe.r-bcqeeo.r-q4m81j.r-qvutc0'


########################################################################


def build_date_ranges(begin_date, end_date):
    ranges = []
    l = begin_date
    while l < end_date:
        r = l + datetime.timedelta(days=DAYS_PER_SEARCH)
        if r > end_date:
            r = end_date
        ranges.append((l, r))
        l = r
    return ranges


def build_url(profile_name, begin_date, end_date):
    begin_str = begin_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    return BASEURL.format(profile_name, begin_str, end_str)


def load_data(profile_name):
    filepath = os.path.join(IDS_DIR, f'{profile_name}.json')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
    else:
        data = {
            'profile_name':  profile_name,
            'latest_date': BEGIN_DATE,
            'tweet_ids': []
        }
    return data


def save_data(profile_name, data):
    filepath = os.path.join(IDS_DIR, f'{profile_name}.json')
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def save_raw(tweet_id, raw_html_str):
    filepath = os.path.join(RAW_DIR, f'{tweet_id}.html')
    with open(filepath, 'w') as f:
        f.write(raw_html_str)
        f.write('\n')


def get_tweet_id(tweet_elem):
    tweet_id = tweet_elem.find_element_by_css_selector(
        ID_SELECTOR
    ).get_attribute('href').split('/')[-1]
    return tweet_id


def get_driver():
    driver = webdriver.Chrome(
        executable_path=CHROMEDRIVER_PATH,
        options=CHROME_OPTIONS,
    )
    return driver


def scrape_one_page(driver, url):
    driver.get(url)
    sleep(PAGE_DELAY)

    scroll_down_to_load_all(driver, PAGE_DELAY)

    tweet_ids = set()
    try:
        scroll_to_top(driver)
        sleep(0.1)
        prev_scroll_height = 0

        while True:
            tweet_elems = driver.find_elements_by_css_selector(TWEET_SELECTOR)
            try:
                for elem in reversed(tweet_elems):
                    tweet_id = get_tweet_id(elem)
                    if tweet_id not in tweet_ids:
                        tweet_ids.add(tweet_id)
                        raw_html_str = elem.get_attribute('outerHTML')
                        save_raw(tweet_id, raw_html_str)
            except StaleElementReferenceException:
                continue

            scroll_down_viewheight(driver)
            sleep(0.1)
            curr_scroll_height = get_curr_scroll_height(driver)

            if curr_scroll_height == prev_scroll_height:
                break
            prev_scroll_height = curr_scroll_height

    except NoSuchElementException:
        pass

    if is_rate_limited(driver):
        print('rate limited, sleep')
        driver.delete_all_cookies()
        sleep(RATE_LIMITED_DELAY)
        return None

    driver.delete_all_cookies()
    return tweet_ids


def scrape_one_profile(profile_name, begin_date_str):
    data = load_data(profile_name)
    print(
        f'start scraping [{profile_name}], already has [{len(data["tweet_ids"])}] tweets, latest at [{data["latest_date"]}]')
    tweet_ids = set(data['tweet_ids'])

    begin_date = datetime.datetime.strptime(begin_date_str, '%Y-%m-%d')
    if 'latest_date' in data:
        begin_date = max(
            datetime.datetime.strptime(data['latest_date'], '%Y-%m-%d'),
            begin_date
        )
    date_ranges = build_date_ranges(
        begin_date, datetime.datetime.now() + datetime.timedelta(days=1)
    )

    driver = get_driver()
    for begin_date, end_date in tqdm(date_ranges):
        url = build_url(profile_name, begin_date, end_date)

        # scrape one page and merge
        new_tweet_ids = None
        while new_tweet_ids is None:
            new_tweet_ids = scrape_one_page(driver, url)
        tweet_ids = tweet_ids.union(new_tweet_ids)
        data['tweet_ids'] = list(tweet_ids)

        # checkpoint the latest date
        latest_date = min(
            end_date,
            datetime.datetime.now() - datetime.timedelta(days=1)  # yesterday
        ).strftime('%Y-%m-%d')
        data['latest_date'] = latest_date

        save_data(profile_name, data)

    print('done', profile_name, 'with', len(data['tweet_ids']), 'tweets')
    driver.close()


if __name__ == "__main__":
    for profile_name in PROFILES:
        scrape_one_profile(profile_name, BEGIN_DATE)
