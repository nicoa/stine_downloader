# -*- coding: utf-8 -*-
# !/usr/bin/env python
from collections import OrderedDict
import os
import textwrap
import warnings

import matplotlib as mpl
import matplotlib.pyplot as plt
from helpers import *  # noqa
import pandas as pd
warnings.simplefilter("ignore", category=mpl.mplDeprecation)


def replace_arrow_tags(s):
    foo = s.text
    for el in s.find_elements_by_class_name('arrow'):
        foo = foo.replace(el.text, "").strip()
    return foo


def find_short(el):
    try:
        link = el.find_element_by_class_name('link')
        return {'short': link.text, 'title': link.get_attribute('title')}
    except:
        link = el.find_element_by_css_selector('span[title]')
        return {'short': link.text, 'title': link.text}


def plot_timetable(table):

    days = OrderedDict({
        'Montag': 1, 'Dienstag': 2, 'Mittwoch': 3, 'Donnerstag': 4,
        'Freitag': 5, 'Samstag': 6, 'Sonntag': 7})
    if not table.find_elements_by_class_name('appointment'):
        return
    df = pd.DataFrame(map(lambda el: {
        'abbr': el.get_attribute('abbr').split(' Spalte ')[0],
        'timePeriod':
            replace_arrow_tags(el.find_element_by_class_name('timePeriod')),
        'short': find_short(el)['short'],
        'title': find_short(el)['title'],
    }, table.find_elements_by_class_name('appointment'))).sort_values(
        ['abbr', 'timePeriod'])

    fig = plt.figure(figsize=(20, 9))
    for i, data in df.iterrows():
        event = data['title']
        day = days[data['abbr']] - 0.48
        start, end = data.timePeriod.split(' - ')
        start = float(start.split(':')[0]) + float(start.split(':')[1]) / 60
        end = float(end.split(':')[0]) + float(end.split(':')[1][:2]) / 60
        plt.fill_between(
            [day, day + 0.96], [start, start], [end, end], color='#cccccc',
            edgecolor='k', linewidth=0.5, zorder=1)
        # plot beginning time
        plt.text(
            day + 0.02, start + 0.05, data.timePeriod, va='top', fontsize=9)
        # plot event name
        plt.text(
            day + 0.48, (start + end) * 0.5,
            '\n'.join(textwrap.wrap(
                event if len(event) <= 55 else event[:52] + u'…', width=30)),
            ha='center', va='center', fontsize=11)

    # Set Axis
    ax = fig.add_subplot(111)
    ax.yaxis.grid()
    ax.set_xlim(0.5, len(days) + 0.5)
    ax.set_ylim(ax.get_ylim()[::-1])
    ax.set_xticks(range(1, len(days) + 1))
    ax.set_xticklabels({v: k for k, v in days.iteritems()}.values())
    ax.set_title(table.find_element_by_tag_name('caption').text, y=1.07)
    fig.tight_layout()
    table.find_element_by_tag_name('caption').text
    f = table.find_element_by_tag_name('caption').text.replace(
        '.', ''
    ).replace("/", "_").replace(' ', '_').replace('_Woche_von_', '_von_')
    ff = f.split("_")  # correct ordering of month/day: not 31.01., rather 0131
    ff[-1] = ff[-1][2:] + ff[-1][:2]
    ff[-3] = ff[-3][2:] + ff[-3][:2]
    f = "_".join(ff)
    plt.savefig(path + '{}.png'.format(f), dpi=60)
    plt.close()


def _mkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)


browser = initiate_stine(
    usr=os.environ.get('STINE_FSR_USER'),
    passwrd=os.environ.get('STINE_FSR_PASS'))

stine_version = (
    browser.page_source
    .split("-->")[0]
    .split("version:")[1]
    .split('\n')[0]
    .replace('\t', '')
    .strip()
)
if stine_version != '8.00.012':
    log.warn('Newer STiNE Version, could trigger errors')
else:
    log.warn('STiNE Version fine')

log.info("Navigating to rooms")
browser.find_element_by_link_text('Verwaltung').click()
# navigate to events

browser.find_element_by_link_text("Raumanfrage").click()

studies = browser.find_element_by_id(
    'room_site').find_elements_by_tag_name('option')

el = filter(lambda el: el.get_attribute('text') == 'NATUR', studies)[0]

log.info("Selecting {}...".format(el.text))
el.click()

studies = browser.find_element_by_id(
    'room_building').find_elements_by_tag_name('option')
el = filter(lambda el: el.get_attribute('text') == 'Bu 55', studies)[0]
log.info("Selecting {}...".format(el.text))
el.click()


path = "/Users/nico.albers/Dropbox/02_FSR/Raumplaene/"
_mkdir(path)
_mkdir("/Users/nico.albers/Dropbox/02_FSR/Raumplaene/html_tables/")


browser.switch_to.window(browser.window_handles[0])

for room_type in ['Hörs', 'Seminarräum']:
    studies = browser.find_element_by_id('room_type').find_elements_by_tag_name('option')  # noqa
    el = filter(lambda el: el.get_attribute('text').encode('utf-8').startswith(room_type), studies)[0]  # noqa
    log.info(u"Selecting {}".format(el.text))
    el.click()
    el = browser.find_element('name', 'campusnet_submit')
    el.submit()

    rooms = browser.find_elements_by_name('roomAppointmentsLink')
    this_handle = browser.current_window_handle
    if len(rooms) < 1:
        log.warn("to less events")
    else:
        for room in range(len(rooms)):
            this_room = browser.find_elements_by_name('roomAppointmentsLink')[room]  # noqa
            log.info(u'starting with {}'.format(browser.find_elements_by_name('roomBuilding')[room].text))  # noqa
            this_handle = browser.current_window_handle
            this_room.click()

            cws = browser.find_element_by_name('wk').find_elements_by_tag_name('option')  # noqa
            idx_actual = cws.index(filter(lambda e: e.is_selected(), cws)[0])
            cw = cws[idx_actual]
            log.info("Selecting {}...".format(cw.text))
            table = browser.find_element_by_id('weekTableRoomplan')
            plot_timetable(table)
            browser.back()

print 'DONE'
