from time import sleep


def scroll_to_top(driver):
    driver.execute_script('window.scrollTo(0, 0);')


def scroll_to_bottom(driver):
    driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')


def scroll_down_viewheight(driver):
    driver.execute_script('window.scrollBy(0, window.innerHeight)')


def get_curr_scroll_height(driver):
    return driver.execute_script('return window.pageYOffset')


def scroll_down_to_load_all(driver, delay):
    scroll_height = 0
    while True:
        scroll_to_bottom(driver)
        sleep(delay)
        new_scroll_height = driver.execute_script(
            'return document.body.scrollHeight')
        if new_scroll_height == scroll_height:
            return
        scroll_height = new_scroll_height


def is_rate_limited(driver):
    try:
        driver.find_element_by_css_selector(RATE_LIMITED_SELECTOR)
    except NoSuchElementException:
        return False
    return True
