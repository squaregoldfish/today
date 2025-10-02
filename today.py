from blessed import Terminal
from rtm import rtm
from cal import cal
from gtfs import gtfs
import toml
import time
from operator import itemgetter
from datetime import datetime
import json
from tzlocal import get_localzone
import logging
import sys
import os

def midnight(date_object):
    return date_object.replace(hour=0, minute=0, second=0, microsecond=0)

def center(text, width):
    if len(text) > width:
        return text[:width]
    else:
        return text.center(width, ' ')

def display_tasks(tasks, x_pos, y_start, y_limit, max_length, include_date):
    pos = y_start
    if len(tasks) == 0:
        print(term.move_xy(x_pos, pos) + 'No tasks'[:max_length].ljust(max_length))
    else:
        for task in tasks:
            task_date = datetime.strptime(task['due'], "%Y-%m-%d")

            entry = task['name']

            if include_date:
                name_max_length = max_length - 7
                entry = entry[:name_max_length].ljust(name_max_length)

                formatted_date = task_date.strftime("%b %d").replace(" 0", "  ")
                entry += f' {formatted_date}'

                if task_date.year > datetime.now().year:
                    entry_color = 'red'
            else:
                entry = entry[:max_length].ljust(max_length)                


            entry_color = 'deepskyblue3'
            if task['status'] == rtm.OVERDUE:
                entry_color = 'firebrick1'
            elif task['status'] == rtm.FUTURE:
                entry_color = 'limegreen'

            color = getattr(term, entry_color)
            print(term.move_xy(x_pos, pos) + color(entry), end='')
            pos += 1
            if pos > y_limit:
                break

        while pos <= y_limit:
            print(term.move_xy(x_pos, pos) + ' ' * max_length, end='')
            pos += 1

def display_calendar(events, x_pos, y_start, y_limit, max_length):
    pos = y_start


    if len(events) == 0:
        print(term.move_xy(x_pos, pos) + 'No events')
    else:
        current_date = None

        for event in events:
            process_event = True

            # Don't show finished events
            if isinstance(event['start'], datetime):
                if event['end'] < datetime.now(get_localzone()):
                    process_event = False

            if process_event:
                # If we've changed date, print a new date.
                new_date = False
                if isinstance(event['start'], datetime):
                    start_date = midnight(event['start']).date()
                    if current_date is None or start_date != current_date:
                        current_date = start_date
                        new_date = True
                else:
                    if current_date is None or event['start'] != current_date:
                        current_date = event['start']
                        new_date = True


                if new_date:
                    color = getattr(term, 'white')
                    date_string = current_date.strftime('%a %e')
                    print(term.move_xy(x_pos, pos) + term.bold(color(date_string[:max_length].ljust(max_length))))
                    pos += 1

                color = getattr(term, event['color'])
                if event['time_to_start'] is None:
                    print(term.move_xy(x_pos, pos) + color(f'        {event["name"]}'[:max_length].ljust(max_length)))            
                else:
                    print(term.move_xy(x_pos, pos) + '  ')
                    event_text = f'{event["start"].strftime("%H:%M")} {event["name"]}'
                    to_print = event_text[:max_length - 2].ljust(max_length - 2)

                    seconds_to_start = event['time_to_start'].total_seconds()
                    if seconds_to_start <= 0:
                        print(term.move_xy(x_pos + 2, pos) + term.bold(term.on_firebrick3(to_print)))
                    elif seconds_to_start <= 300:
                        print(term.move_xy(x_pos + 2, pos) + term.bold(term.on_darkorange3(to_print)))
                    elif seconds_to_start <= 900:
                        print(term.move_xy(x_pos + 2, pos) + term.bold(term.on_gold4(to_print)))
                    else:
                        print(term.move_xy(x_pos + 2, pos) + color(to_print))

                pos += 1

                if pos + 3 > y_limit:
                    break

        while pos < y_limit - 1:
            print(term.move_xy(x_pos, pos) + ' ' * max_length)
            pos += 1

def make_color(hex):
    return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))

def display_gtfs(journeys, x_pos, y_start, y_limit, max_length):
    if len(journeys) == 0:
        print(term.move_xy(x_pos, y_start) + 'No journeys'[:max_length].ljust(max_length))
    else:
        pos = y_start

        for journey in journeys:
            color = term.color_rgb(*make_color(journey[0]))
            print(term.move_xy(x_pos, pos) + color + f'{journey[3]}  {journey[2]} {journey[4]}'[:max_length].ljust(max_length))

            pos += 1
            if pos + 2 > y_limit:
                break


## HERE WE GO
logging.basicConfig(filename='today.log', format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
logging.info('STARTUP')

with open('config.toml') as config_file:
    config = toml.load(config_file)

# Work out what GTFS files we've been asked for
if len(sys.argv) == 1:
    gtfs_files = config['gtfs']['files']
else:
    gtfs_files = sys.argv[1:]

# Check that all the files exist
for gtfs_file in gtfs_files:
    if not os.path.exists(gtfs_file):
        raise FileNotFoundError(f'{gtfs_file} does not exist')

rtm_instance = rtm.rtm(config['rtm'])
cal_instance = cal.cal(config['calendar'])
gtfs_instance = gtfs.gtfs(gtfs_files)

term = Terminal()

with term.fullscreen(), term.cbreak(), term.hidden_cursor():
    print(term.clear)

    old_term_width = term.width
    old_term_height = term.height

    half_width = int(term.width / 2)
    half_height = int(term.height / 2)

    overdue_count = 0
    overdue_oldest = 0
    today_count = 0

    while True:
        if term.width != old_term_width or term.height != old_term_height:
            old_term_width = term.width
            old_term_height = term.height
            half_width = int(term.width / 2)
            half_height = int(term.height / 2)
            print(term.clear)

        print(term.move_xy(0, 0) + term.bold(term.on_firebrick3(center(f'OVERDUE TASKS ({overdue_count}, {overdue_oldest}d)', half_width - 1))), end='')
        print(term.move_xy(0, half_height + 1) + term.bold(term.on_webpurple(center('TRANSPORT', half_width - 1))), end='')
        print(term.move_xy(half_width + 1, 0) + term.bold(term.on_deepskyblue4(center(f'TODAY & UPCOMING ({today_count})', half_width - 1))), end='')
        
        if cal_instance.has_error():
            print(term.move_xy(half_width + 1, half_height + 1) + term.bold(term.on_salmon1(center('CALENDER', half_width - 1))), end='')
        else:
            print(term.move_xy(half_width + 1, half_height + 1) + term.bold(term.on_darkgreen(center('CALENDER', half_width - 1))), end='')

        all_tasks = rtm_instance.get_tasks(None)

        overdue_tasks = sorted(
            list([d for d in all_tasks if d['status'] == rtm.OVERDUE]),
            key=itemgetter('due', 'name')
            )

        overdue_count = len(overdue_tasks)

        if (len(overdue_tasks) > 0):
            oldest_date = datetime.strptime(overdue_tasks[0]['due'], "%Y-%m-%d")
            oldest_date = rtm.midnight(oldest_date.astimezone(get_localzone())).date()
            today = rtm.midnight(datetime.now(get_localzone())).date()
            overdue_oldest = (today - oldest_date).days

        display_tasks(overdue_tasks, 0, 1, half_height - 1, half_width - 1, True)

        today_tasks = sorted(
            list([d for d in all_tasks if d['status'] == rtm.TODAY or d['status'] == rtm.FUTURE]),
            key=itemgetter('due', 'name')
            )


        today_count = len(today_tasks)

        display_tasks(today_tasks, half_width + 1, 1, half_height - 1, half_width - 1, False)

        list_tasks = []
        
        display_gtfs(gtfs_instance.get_journeys(), 0, half_height + 2, term.height, half_width - 1)
        
        display_calendar(cal_instance.get_events(), half_width + 1, half_height + 2, term.height, half_width - 1)

        print(term.move_xy(term.width, term.height), end='')
        key = term.inkey(timeout=1)
        if key == 'q':
            break

rtm_instance.stop()
cal_instance.stop()
gtfs_instance.stop()
