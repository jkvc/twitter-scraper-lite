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

TEXT_ELEM_CLASSNAME = 'css-901oao r-hkyrab r-1qd0xha r-a023e6 r-16dba41 r-ad9z0x r-bcqeeo r-bnwqim r-qvutc0'
STATS_ELEM_CLASSNAME = 'css-1dbjc4n r-18u37iz r-1wtj0ep r-156q2ks r-1mdbhws'
REPLY_TO_ELEM_CLASSNAME = 'css-901oao r-1re7ezh r-1qd0xha r-a023e6 r-16dba41 r-ad9z0x r-bcqeeo r-qvutc0'

NUM_WORKER = 1


def parse_one_tweet(tweet_id, raw_path):
    with open(os.path.join(raw_path, f'{tweet_id}.html')) as f:
        raw_html = '\n'.join(f.readlines())
    soup = BeautifulSoup(raw_html, 'html.parser')

    # the time
    time_elem = soup.find('time')
    time_str = time_elem['datetime']

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

    # reply to
    reply_to_elem = soup.find('div', {
        'class': REPLY_TO_ELEM_CLASSNAME
    })
    if not reply_to_elem:
        reply_to = None
    else:
        reply_to = reply_to_elem.div.a.span.text.replace('@', '')

    parsed = {
        'time': time_str,
        'text': text_str,
        'replies': replies,
        'retweets': retweets,
        'likes': likes,
        'reply_to': reply_to
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

    for tweet_id in tqdm(tweet_ids, desc=profile_name, disable=hide_progress_bar, leave=True):
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

    for i, id_filepath in enumerate(id_filepaths):
        parse_one_profile(id_filepath, raw_path, dst_path, False)
