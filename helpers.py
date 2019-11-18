# -*- coding: utf-8 -*-
import locale
import logging
import os
import sys
import time

from dotenv import load_dotenv
import numpy as np
from recursive_dictionary import RecursiveDictionary
import selenium
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys

locale.setlocale(locale.LC_ALL, 'DE_DE')
load_dotenv(".env")

log = logging.getLogger("STiNE")
log.handlers = []  # bug when autoreloading, always adding new
hand = logging.StreamHandler(sys.stdout)
hand.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
hand.setLevel(5)
log.setLevel(5)
log.addHandler(hand)


def s_intersect(a, b):
    """Return first occurence of string b in string a."""
    lb = len(b)
    for i in reversed(range(1, lb + 1)):
        if a.find(b[:i]) >= 0:
            return b[:i]
    return ''


def pairwise_apply_on_series(series, f):
    """Apply function with two args pairwise on series."""
    assert len(series) > 1
    fval = f(series.iloc[0], series.iloc[1])
    for i in range(2, len(series)):
        fval = f(fval, series.iloc[i])
    return fval


def multi_checkbox_widget(descriptions):
    """Widget with a search field and lots of checkboxes. REMOVED / DEPRECATED.

    From: https://gist.github.com/pbugnion/5bb7878ff212a0116f0f1fbc9f431a5c
    """


def initiate_stine(
        headless=False,
        usr=os.environ.get("STINE_USER"),
        passwrd=os.environ.get("STINE_PASS"),
        chrome_path='/Users/nico.albers/Downloads/chromedriver 4'):
    """Initiate Browser with STiNE and log in."""
    log.info("Started Querying STiNE")
    if headless:
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        browser = webdriver.Chrome(
            executable_path=chrome_path, chrome_options=options)
    else:
        browser = webdriver.Chrome(executable_path=chrome_path)
    browser.get("https://www.stine.uni-hamburg.de/")
    time.sleep(2)
    # Login
    log.info("logging in...")
    username = browser.find_element_by_id("field_user")
    password = browser.find_element_by_id("field_pass")

    username.send_keys(usr)
    password.send_keys(passwrd)
    browser.find_element_by_id("logIn_btn").click()
    return browser


def choose_input_checklist(
        checklist,
        title='from List',
        override_env=False,
        selenium_elements=True,
        return_text=True
):
    """Show Select Dialog and let user choose one or multiple Inputs."""
    def _this_return(checklist, return_text):
        if return_text:
            return checklist
        else:
            return range(len(checklist))

    if ((os.environ.get('STINE_GET_ALL').lower() == 'true') and
            not override_env):
        return _this_return(checklist, return_text)
    if selenium_elements:
        options_strings = map(
            lambda (i, s): u'{}: \t{}'.format(i, s.text), enumerate(checklist))
    else:
        options_strings = map(
            lambda (i, s): u'{}: \t{}'.format(i, s), enumerate(checklist))
    print u"Choose {}[ENTER for all]:\n{}\r".format(
        title, "\n".join(options_strings))
    input_text = raw_input()
    if input_text:
        chosen_stuff = list(set(map(int, input_text.strip(",").split(","))))
        if return_text:
            return np.array(checklist)[chosen_stuff].tolist()
        else:
            return chosen_stuff
    return _this_return(checklist, return_text)


def navigate_to_study_overview(browser):
    log.info("Navigating to lectures")
    browser.find_element_by_link_text('Studium').click()
    # navigate to events
    browser.find_element_by_link_text("Anmeldung zu Veranstaltungen").click()
    studies = browser.find_element_by_id(
        'study').find_elements_by_tag_name('option')
    el = choose_input_checklist(studies, 'your study', override_env=True)
    if len(el) != 1:
        print "select only one study please"
        while len(el) != 1:
            el = choose_input_checklist(
                studies, 'your study', override_env=True)
    study_id = studies.index(el[0])
    log.info("Selecting {}...".format(el[0].text))
    el[0].click()
    if (browser.find_element_by_id('study')
            .find_elements_by_tag_name('option')[study_id]
            .get_property('selected')):
        log.info("Done")
    else:
        log.info('Something failed, not changed')


def _new_tab(ev, browser):
    """TEST."""
    ActionChains(browser).send_keys_to_element(
        ev, Keys.SHIFT + Keys.RETURN).release().perform()
    # https://superuser.com/a/1275100/865257
    # AND https://stackoverflow.com/a/35719148/6673446


def perform_path_rec(this_dict, browser):
    this_dict.rec_update({'table_data': {}})
    links = browser.find_elements_by_css_selector('div#pageContent ul li a')
    if len(links) > 0:
        escaped_links = map(
            lambda s: s.text.encode(
                'ascii', errors='xmlcharrefreplace').replace(u'&#228;', u'ä'),
            links)
        chosen_links = choose_input_checklist(
            escaped_links, selenium_elements=False, return_text=False)
        hrefs = {
            el.text: el.get_attribute('href')
            for el in np.array(links)[chosen_links].tolist()}
        for key in hrefs.keys():
            log.info(u'started getting {}'.format(key))
            browser.get(hrefs[key])
            this_dict.rec_update({key: {'table_data': {}}})
            this_dict[key] = perform_path_rec(
                RecursiveDictionary(this_dict[key]), browser)
    # END IF
    # store links for events in table and perform data analysis
    events = browser.find_elements_by_name('eventLink')
    this_handle = browser.current_window_handle
    if len(events) < 1:
        log.warn("to less events")
        return this_dict
    event_data = {}
    for event in range(len(events)):
        this_event = browser.find_elements_by_name('eventLink')[event]
        event_title = this_event.text
        if event_title in event_data.keys():
            log.info(u"{} bereits enthalten, continue".format(event_title))
            continue
        log.info(u'starting with {}'.format(event_title))
        this_handle = browser.current_window_handle
        _new_tab(this_event, browser)
        handles = browser.window_handles
        handles.remove(this_handle)
        assert len(handles) == 1
        browser.switch_to.window(handles[0])
        try:
            gruppen = browser.find_elements_by_link_text(
                'Kleingruppe anzeigen')
            if len(gruppen) == 0:
                raise selenium.common.exceptions.NoSuchElementException()
            detail_page_handle = browser.current_window_handle
            for i, group in enumerate(gruppen):
                _new_tab(group, browser)
                group_handles = browser.window_handles
                group_handles.remove(this_handle)
                group_handles.remove(detail_page_handle)
                browser.switch_to.window(group_handles[0])
                event_data.update({
                    u"{} - Kleingruppe {}".format(event_title, i + 1):
                    {'extracted_info': get_detail_page_information(browser)}})
                browser.close()
                browser.switch_to.window(detail_page_handle)
        except selenium.common.exceptions.NoSuchElementException as e:
            log.log(2, u'no exercise groups found for {}'.format(event_title))
            event_data.update({
                event_title:
                {'extracted_info': get_detail_page_information(browser)}})
        browser.close()
        browser.switch_to.window(this_handle)
    this_dict['table_data'] = RecursiveDictionary(event_data)
    # call links with some function
    return this_dict


def get_detail_page_information(browser):
    tabs = browser.find_elements_by_css_selector("div#contentlayoutleft table")
    detail_data = {}
    for tab in tabs:
        if 'Termine' in tab.get_property('caption').text:
            dates_list = []
            for tr in tab.find_elements_by_tag_name('tr'):
                if tr.get_attribute('class') == 'rw-hide':
                    continue
                else:
                    date_data = {
                        appointment: tr.find_element_by_name(appointment).text
                        for appointment in [
                            'appointmentDate',
                            'appointmentTimeFrom', 'appointmentDateTo',
                            'appointmentInstructors']
                    }
                    date_data.update({
                        'room': tr.find_element_by_xpath(
                            "//td[@class='tbdata rw rw-course-room']").text})
                    dates_list.append(date_data)
            detail_data.update({'termine': dates_list})

        if 'Veranstaltungsdetails' in tab.get_property('caption').text:
            detail_data.update({
                'coursetype': tab.find_element_by_name(
                    'coursetyp').find_element_by_xpath("..").text,
                'sws': tab.find_element_by_name('sws').get_attribute('value'),
                'credits': tab.find_element_by_name(
                    'credits').get_attribute('value').strip(),
                'dozent': tab.find_element_by_id('dozenten').text
            })
    return detail_data
