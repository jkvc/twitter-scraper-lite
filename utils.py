from time import sleep
import datetime
import os
import json


def build_date_ranges(begin_date, end_date, days_per_search):
    """build a list of datetime tuples of ranges to query 

    Args:
    - begin_date (datetime): begin date inclusive
    - end_date (datetime): end date inclusive
    - days_per_search (int): number of days per range

    Returns:
    - list of tuples of (datetime, datetime)
    """

    ranges = []
    l = begin_date
    while l < end_date:
        r = l + datetime.timedelta(days=days_per_search)
        if r > end_date:
            r = end_date
        ranges.append((l, r))
        l = r
    return ranges


def load_metadata(profile_name, begin_date_str, ids_dir):
    """load metadata object

    Args:
    - profile_name (str): name of profile
    - begin_date_str (str): if no existing data, use this date as default latest search date
    - ids_dir (str): dir containing the json iles

    Returns:
    - dict: with 'profile_name' 'latest_date' 'tweet_ids'
    """

    filepath = os.path.join(ids_dir, f'{profile_name}.json')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
    else:
        data = {
            'profile_name':  profile_name,
            'latest_date': begin_date_str,
            'tweet_ids': []
        }
    return data


def save_metadata(profile_name, data, ids_dir):
    """save metadata object

    Args:
    - profile_name (str): name of profile
    - data (dict): to save
    - ids_dir (str): dir containing the json files
    """

    filepath = os.path.join(ids_dir, f'{profile_name}.json')
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def save_raw(tweet_id, raw_html_str, raw_dir):
    """save raw html to <id>.html

    Args:
    - tweet_id (str): the tweet id
    - raw_html_str (str): content to save
    - raw_dir (str): dir containing all the html fiels
    """

    filepath = os.path.join(raw_dir, f'{tweet_id}.html')
    with open(filepath, 'w') as f:
        f.write(raw_html_str)
        f.write('\n')


def load_parsed_data(profile_name, parsed_dir):
    """load a parsed data json

    Args:
    - profile_name (str): name of profile
    - parsed_dir (str): dir to store parsed data json

    Returns:
    - dict: with 'profile_name' and 'tweets'
    """

    try:
        with open(os.path.join(parsed_dir, f'{profile_name}.json')) as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'profile_name': profile_name,
            'tweets': {}
        }


def save_parsed_data(profile_name, parsed_dir, parsed_data):
    """save a parsed data json

    Args:
    - profile_name (str): name of profile
    - parsed_dir (str): dir to store parsed data json
    - parsed_data (obj): object to serialize to json
    """

    with open(os.path.join(parsed_dir, f'{profile_name}.json'), 'w') as f:
        json.dump(parsed_data, f, indent=2)


def scroll_down_to_load_all(driver, delay):
    """repeatedly scroll to bottom of page to trigger auto load more

    Args:
    - driver (chromedriver): 
    - delay (int): number of second to wait after per scroll
    """

    scroll_height = 0
    while True:
        scroll_to_bottom(driver)
        sleep(delay)
        new_scroll_height = driver.execute_script(
            'return document.body.scrollHeight')
        if new_scroll_height == scroll_height:
            return
        scroll_height = new_scroll_height


def scroll_to_top(driver):
    driver.execute_script('window.scrollTo(0, 0);')


def scroll_to_bottom(driver):
    driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')


def scroll_down_viewheight(driver):
    driver.execute_script('window.scrollBy(0, window.innerHeight)')


def get_curr_scroll_height(driver):
    return driver.execute_script('return window.pageYOffset')
