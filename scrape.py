from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.chrome.options import Options
from time import sleep
from tqdm import tqdm
from pprint import pprint
import json
import datetime
import os
import argparse
import sys

from utils import *


DEFAULT_BEGIN_DATE = '2015-01-01'
DEFAULT_DAYS_PER_SEARCH = 30

PAGE_DELAY = 1  # seconds
RATE_LIMITED_DELAY = 45  # second
BASEURL = (
    'https://twitter.com/search?q=' +
    'from%3A{}%20' +
    'since%3A{}%20' +
    'until%3A{}%20' +
    'include%3Aretweets&src=typed_query&f=live'
)

CHROMEDRIVER_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'chromedriver'
)
CHROME_OPTIONS = Options()
# TWEET_SELECTOR css depends on window width
CHROME_OPTIONS.add_argument("--window-size=800,2000")
# dont show images
prefs = {"profile.managed_default_content_settings.images": 2}
CHROME_OPTIONS.add_experimental_option("prefs", prefs)

TWEET_SELECTOR = 'div.css-1dbjc4n.r-my5ep6.r-qklmqi.r-1adg3ll'
ID_SELECTOR = 'a.css-4rbku5.css-18t94o4.css-901oao.r-1re7ezh.r-1loqt21.r-1q142lx.r-1qd0xha.r-a023e6.r-16dba41.r-ad9z0x.r-bcqeeo.r-3s2u2q.r-qvutc0'
# RATE_LIMITED_SELECTOR = 'div.css-18t94o4.css-1dbjc4n.r-urgr8i.r-42olwf.r-sdzlij.r-1phboty.r-rs99b7.r-1w2pmg.r-1vuscfd.r-1dhvaqw.r-1ny4l3l.r-1fneopy.r-o7ynqc.r-6416eg.r-lrvibr'


########################################################################


def build_url(profile_name, begin_date, end_date):
    begin_str = begin_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    return BASEURL.format(profile_name, begin_str, end_str)


def get_tweet_id(tweet_elem):
    tweet_id = tweet_elem.find_element_by_css_selector(
        ID_SELECTOR
    ).get_attribute('href').split('/')[-1]
    return tweet_id


def is_rate_limited(driver):
    try:
        rle = driver.find_element_by_css_selector(RATE_LIMITED_SELECTOR)
        print('rle', rle.get_attribute('outerHTML'))
    except NoSuchElementException:
        return False
    return True


def get_driver(chromedriver_options=CHROME_OPTIONS):
    driver = webdriver.Chrome(
        executable_path=CHROMEDRIVER_PATH,
        options=chromedriver_options,
    )
    return driver


def scrape_one_page(driver, url, profile_name, raw_dir):
    driver.get(url)
    scroll_down_to_load_all(driver, PAGE_DELAY)

    tweet_ids = set()
    try:
        scroll_to_top(driver)
        prev_scroll_height = 0

        while True:
            tweet_elems = driver.find_elements_by_css_selector(TWEET_SELECTOR)
            try:
                for elem in reversed(tweet_elems):
                    tweet_id = get_tweet_id(elem)
                    if tweet_id not in tweet_ids:
                        raw_html_str = elem.get_attribute('outerHTML')
                        save_raw(tweet_id, raw_html_str, raw_dir, profile_name)
                        tweet_ids.add(tweet_id)
            except (StaleElementReferenceException, WebDriverException):
                continue

            scroll_down_viewheight(driver)
            curr_scroll_height = get_curr_scroll_height(driver)

            if curr_scroll_height == prev_scroll_height:
                break
            prev_scroll_height = curr_scroll_height

    except NoSuchElementException:
        pass

    # if is_rate_limited(driver):
    #     print('rate limited, sleep')
    #     driver.delete_all_cookies()
    #     sleep(RATE_LIMITED_DELAY)
    #     return None

    driver.delete_all_cookies()
    return tweet_ids


def scrape_one_profile(driver, profile_name, begin_date_str, days_per_search, meta_dir, raw_dir):

    data = load_metadata(profile_name, begin_date_str, meta_dir)
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
        begin_date,
        datetime.datetime.now() + datetime.timedelta(days=10),
        days_per_search
    )

    for begin_date, end_date in tqdm(date_ranges, desc=profile_name):
        url = build_url(profile_name, begin_date, end_date)

        # scrape one page and merge
        new_tweet_ids = None
        while new_tweet_ids is None:
            new_tweet_ids = scrape_one_page(driver, url, profile_name, raw_dir)
        tweet_ids = tweet_ids.union(new_tweet_ids)
        data['tweet_ids'] = list(tweet_ids)

        # checkpoint the latest date
        latest_date = min(
            end_date,
            datetime.datetime.now() - datetime.timedelta(days=1)  # yesterday
        ).strftime('%Y-%m-%d')
        data['latest_date'] = latest_date

        save_metadata(profile_name, data, meta_dir)

    print(
        f'done scraping [{profile_name}] with [{len(data["tweet_ids"])}] tweets')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'profiles', help='file containing profile strings, one per line')
    parser.add_argument(
        'meta_dir', help='dir to contain tweet ids json per profile')
    parser.add_argument(
        'raw_dir', help='dir to contain raw html files per tweet')
    parser.add_argument(
        '-q', '--quiet',
        help="don't show browser window",
        action='store_true',
    )
    args = parser.parse_args()

    with open(args.profiles) as f:
        profile_names = [
            s.rstrip()
            for s in f.readlines()
        ]

    if args.quiet:
        CHROME_OPTIONS.add_argument("--headless")
    driver = get_driver(CHROME_OPTIONS)

    for profile_name in profile_names:
        scrape_one_profile(
            driver=driver,
            profile_name=profile_name,
            begin_date_str=DEFAULT_BEGIN_DATE,
            days_per_search=DEFAULT_DAYS_PER_SEARCH,
            meta_dir=args.meta_dir,
            raw_dir=args.raw_dir,
        )
