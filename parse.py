import os
import json
import sys
import datetime
from tqdm import tqdm, trange
from pprint import pprint
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor

# USAGE: python parse.py <ids_dir> <raw_dir> <dst_dir>
# this script writes json to <dst_dir> for each json profile in <ids_dir>

DATE_ELEM_CLASSNAME = 'css-4rbku5 css-18t94o4 css-901oao r-1re7ezh r-1loqt21 r-1q142lx r-1qd0xha r-a023e6 r-16dba41 r-ad9z0x r-bcqeeo r-3s2u2q r-qvutc0'
TEXT_ELEM_CLASSNAME = 'css-901oao r-hkyrab r-1qd0xha r-a023e6 r-16dba41 r-ad9z0x r-bcqeeo r-bnwqim r-qvutc0'
STATS_ELEM_CLASSNAME = 'css-1dbjc4n r-18u37iz r-1wtj0ep r-156q2ks r-1mdbhws'

NUM_WORKER = 4


def parse_one_tweet(tweet_id, raw_path):
    with open(os.path.join(raw_path, f'{tweet_id}.html')) as f:
        raw_html = '\n'.join(f.readlines())
    soup = BeautifulSoup(raw_html, 'html.parser')

    # the date
    date_str = soup.find('a', {
        'class': DATE_ELEM_CLASSNAME
    }).text
    # tweet from this year does not show year in string
    if ',' not in date_str:
        date_str += ', ' + str(datetime.datetime.now().year)
    try:
        date_obj = datetime.datetime.strptime(date_str, '%b %d, %Y')
    except ValueError:
        # less than one day
        date_obj = datetime.datetime.now()
    date_str = date_obj.strftime("%Y-%m-%d")

    # the text
    text_elem = soup.find('div', {
        'class': TEXT_ELEM_CLASSNAME
    })
    text_str = text_elem.text if text_elem else ''

    # the stats
    replies = retweets = likes = 0
    stats_elem = soup.find('div', {
        'class': STATS_ELEM_CLASSNAME
    })
    stats_elem_str = stats_elem['aria-label']
    if len(stats_elem_str) > 0:
        for stat_str in stats_elem_str.split(', '):
            stat_num, stat_name = stat_str.lower().split(' ')
            stat_num = int(stat_num)
            if stat_name in ['replies', 'reply']:
                replies = stat_num
            if stat_name in ['retweets', 'retweet']:
                retweets = stat_num
            if stat_name in ['likes', 'like']:
                likes = stat_num

    parsed = {
        'date': date_str,
        'text': text_str,
        'replies': replies,
        'retweets': retweets,
        'likes': likes,
    }
    return parsed


def parse_one_profile(id_filepath, raw_path, dst_path, hide_progress_bar=False):
    with open(id_filepath) as f:
        id_data = json.load(f)
    profile_name = id_data['profile_name']
    tweet_ids = set(id_data['tweet_ids'])
    print(f'begin parsing [{profile_name}]')

    parsed_data = load_parsed_data(profile_name, dst_path)
    parsed_tweets = parsed_data['tweets']

    for tweet_id in tqdm(tweet_ids, desc=profile_name, disable=hide_progress_bar, leave=False):
        if tweet_id not in parsed_tweets:
            parsed_tweets[tweet_id] = parse_one_tweet(tweet_id, raw_path)

    save_parsed_data(profile_name, dst_path, parsed_data)
    print(f'done parsing [{profile_name}]')


def load_parsed_data(profile_name, dst_path):
    try:
        with open(os.path.join(dst_path, f'{profile_name}.json')) as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'profile_name': profile_name,
            'tweets': {}
        }


def save_parsed_data(profile_name, dst_path, parsed_data):
    with open(os.path.join(dst_path, f'{profile_name}.json'), 'w') as f:
        json.dump(parsed_data, f, indent=2)


if __name__ == "__main__":
    id_path, raw_path, dst_path = sys.argv[1:4]

    id_filepaths = sorted(list(
        os.path.join(id_path, file)
        for file in os.listdir(id_path)
        if os.path.isfile(os.path.join(id_path, file))
    ))

    with ProcessPoolExecutor(max_workers=NUM_WORKER) as executor:
        for i, id_filepath in enumerate(id_filepaths):
            executor.submit(
                parse_one_profile,
                id_filepath, raw_path, dst_path, NUM_WORKER > 1
            )
