<img src="twitter-scraper-lite.svg" alt="twitter-scraper-lite logo" width="100px">

# twitter-scraper-lite

A selenium-based Twitter scraper that scrapes the web frontend for a user timeline to get around the QPS and number of recent tweet limit imposed by the API.

## prerequisites

to use this, you need to be able to:

- write some python
- inspect a webpage

## install

`git clone` this repo directly, or `git submodule add` it to your existing repo

use python 3.7+

install some dependencies:

```bash
pip install tqdm termcolor selenium
```

the machine needs to have a version of chrome or chromium installed, ubuntu installation example:

```bash
sudo curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add
echo "deb http://dl.google.com/linux/chrome/deb/ stable main"  | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt-get -y update
sudo apt-get -y install google-chrome-stable
```

download the correct version of chromedriver from [here](https://chromedriver.chromium.org/downloads), unzip and put it in the same directory as `scrape.py`

## usage

both scripts auto-continues from where it previously left off, as long as the contents on the disk are unchanged since then.

to run from the command line, see:

```
python scrape.py -h
python parse.py -h
```

when scraping, respect twitter's rate limiting detection, dont use above 4 workers (processes) or we risk a higher chance of being limited and result in wait time. when using more than 1 worker (i.e. multiprocessing), use `pkill python; pkill chromedriver; pkill Chrome` in a separate session to terminate since `ctrl+c` is not reliable.

to use in another python script, call `scrape_one_profile` in `scrape.py`.

`parse.py` needs some configuring as well, and provide limited information. a better alternative is to use [twarc](https://github.com/DocNow/twarc) to hydrate the scraped ids 

## overview

twitter's official API has the following drawbacks:

- can only get 3200 most recent tweets
- require dev login
- rate limited

this solution uses selenium to scrape and parse the front end webpage of twitter, specifically the search, to get around the qps limit. 

at the time of writing, at this config, it runs at around 2 tweets per second per process.

for each profile, `scrape.py` performs the following:

1. search tweets from that profile within a date range
1. scroll down repeatedly to load all results
1. extract the tweet ids, save json to disk
2. extract raw htmls, save to disk
3. go to the next date range, repeat 

for each profile, `parse.py` performs the following:

1. pick one tweet id from the profile
2. load raw html from disk, parse to extract a dict of information
3. go to the next tweet id, repeat until there's no more unparsed tweets
4. save json to disk

on disk, the data is saved as:

```
/
    meta/   # mkdir'd by user and populated by scrape.py
        profile1.json
        profile2.json
    raw/    # mkdir'd by user and populated by scrape.py
        tweet_id1.html
        tweet_id2.html
    parsed/ # mkdir'd by user and populated by parse.py
        profile1.json
        profile2.json
```

side note: if you're running on osx, name the raw director hidden (e.g. `.raw/`) so the indexing service doesn't look at it, otherwise indexing breaks since there are many files (one per tweet).

## config

at the time of writing, the selectors are funcitonal out-of-the-box, but twitter might change their UI and therefore change the css names, so we might need to update the css selectors in the future

### `scrape.py`

configure `TWEET_SELECTOR` and `ID_SELECTOR` with the correct id selector, find this by inspecting the twitter's search page. [here's an example search page](https://twitter.com/search?q=from%3Abarackobama%20since%3A2020-06-14%20until%3A2020-07-01&src=typed_query&f=live). be sure to choose the one uniquely id each tweet box.

configure `NO_RESULT_SELECTOR` with the box that shows "no search result". [here's an example search page](https://twitter.com/search?q=from%3Abarackobama%20since%3A2029-01-01&src=typed_query&f=live). this is used such that when there's not tweet found, and there's not "no result" on the page, we know we're rate limited by twitter and should wait for a while.

### `parse.py`

inspect each element you would like to parse from the raw html, and modify `parse_one_tweet`.


