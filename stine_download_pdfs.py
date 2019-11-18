# -*- coding: utf-8 -*-
# !/usr/bin/env python
import re

import requests

from helpers import *  # noqa

browser = initiate_stine()

stine_version = (
    browser.page_source
    .split("-->")[0]
    .split("version:")[1]
    .split('\n')[0].replace('\t', '').strip())
if stine_version != '8.00.012':
    log.warn('Newer STiNE Version, could trigger errors')
else:
    log.warn('STiNE Version fine')

log.info("Navigating to lectures")
browser.find_element_by_link_text('Studium').click()
# navigate to events
browser.find_element_by_link_text("Veranstaltungsliste").click()

studies = browser.find_element_by_id(
    'semester').find_elements_by_tag_name('option')
el = choose_input_checklist(studies, 'your semester', override_env=True)
if len(el) != 1:
    print "select only one semester please"
    while len(el) != 1:
        el = choose_input_checklist(
            studies, 'your semester', override_env=True)
study_id = studies.index(el[0])
log.info("Selecting {}...".format(el[0].text))
el[0].click()
if (
    browser.find_element_by_id('semester')
    .find_elements_by_tag_name('option')[study_id]
    .get_property('selected')
):
    log.info("Done")
else:
    log.info('Something failed, not changed')


studies = browser.find_element_by_id(
    'semester').find_elements_by_tag_name('option')


def _mkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)

path = "/Users/nico.albers/Dropbox/00_Unikram/STiNE_DL/"
_mkdir(path)

path = (
    path + studies[study_id].text.split("/")[0].upper().replace(" ", "") + '/')
_mkdir(path)


re1 = '.*?'  # Non-greedy match on filler
re2 = '(".*?")'  # Double Quote String 1

rg = re.compile(re1 + re2, re.IGNORECASE | re.DOTALL)

browser.switch_to.window(browser.window_handles[0])

ASK_FOR_REDOWNLOAD = False
events = browser.find_elements_by_name('eventLink')
this_handle = browser.current_window_handle
if len(events) < 1:
    log.warn("to less events")
else:
    for event in range(len(events)):
        this_event = browser.find_elements_by_name('eventLink')[event]
        event_title = this_event.text
        event_title = event_title.replace("/", "")
        log.info(u'starting with {}'.format(event_title))
        this_handle = browser.current_window_handle
        this_event.click()
        links = filter(
            lambda a: a.get_attribute("text").endswith(".pdf"),
            browser.find_elements_by_css_selector("a")
        )
        if len(links) == 0:
            browser.back()
            continue
        _mkdir(os.path.join(path, event_title))
        for a in links:
            download = True
            fpath = os.path.join(
                path,
                event_title,
                a.get_attribute('text').replace(u'\xfc', 'ue')
            )
            if os.path.exists(fpath):
                if not ASK_FOR_REDOWNLOAD:
                    log.info(
                        u'not re-downloading due to global setting: {}'.format(
                            a.get_attribute('text')))
                    download = False
                    continue
                else:
                    log.info(u'\tstarted {}'.format(a.get_attribute('text')))

                foo = True
                while foo:
                    foo = raw_input('You want to re-download? (y/n): ')
                    if not ((foo.lower() == 'y') or (foo.lower() == 'n')):
                        foo = True
                    else:
                        if foo.lower() == 'y':
                            pass
                        elif foo.lower() == 'n':
                            download = False
                            foo = False
                            continue
                        foo = False
            if download:
                response = requests.get(a.get_attribute("href"), stream=True)
                with open(fpath, 'wb') as handle:
                    for chunk in response.iter_content(chunk_size=512):
                        if chunk:
                            handle.write(chunk)
                        else:
                            tmp = chunk
        browser.back()

print 'DONE'
