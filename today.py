import argparse
from blessed import Terminal
from rtm import rtm
import toml
import time
from operator import itemgetter
from datetime import datetime


def display_tasks(tasks, x_pos, y_start, y_limit, max_length, include_date):
    pos = y_start
    if len(tasks) == 0:
        print(term.move_xy(x_pos, pos) + 'No tasks')
    else:
        for task in tasks:
            task_date = datetime.strptime(task['due'], "%Y-%m-%d")

            entry = task['name']

            if include_date:
                name_max_length = max_length - 7
                entry = entry[:name_max_length].ljust(name_max_length)

                formatted_date = task_date.strftime("%b %d").replace(" 0", "  ")
                entry += formatted_date

                if task_date.year > datetime.now().year:
                    entry_color = 'red'
            else:
                entry = entry[:max_length].ljust(max_length)                


            entry_color = 'royalblue'
            if task['status'] == rtm.OVERDUE:
                entry_color = 'firebrick3'
            elif task['status'] == rtm.FUTURE:
                entry_color = 'forestgreen'

            color = getattr(term, entry_color)
            print(term.move_xy(x_pos, pos) + color(entry), end='')
            pos += 1
            if pos > y_limit:
                break

        while pos <= y_limit:
            print(term.move_xy(x_pos, pos) + ' ' * max_length, end='')
            pos += 1


parser = argparse.ArgumentParser(
                    prog='today')
parser.add_argument('detail_list', help="The specific list to show")
args = parser.parse_args()

with open('config.toml') as config_file:
    config = toml.load(config_file)

rtm_instance = rtm.rtm(config['rtm'], [args.detail_list])

term = Terminal()

with term.fullscreen(), term.cbreak(), term.hidden_cursor():
    print(term.clear)

    old_term_width = term.width
    old_term_height = term.height

    half_width = int(term.width / 2)
    half_height = int(term.height / 2)

    while True:
        if term.width != old_term_width or term.height != old_term_height:
            old_term_width = term.width
            old_term_height = term.height
            half_width = int(term.width / 2)
            half_height = int(term.height / 2)
            print(term.clear)


        print(term.move_xy(0, 0) + term.on_firebrick3('OVERDUE TASKS'.ljust(half_width - 1)), end='')
        print(term.move_xy(0, half_height + 1) + term.on_royalblue('DUE TODAY'.ljust(half_width - 1)), end='')
        print(term.move_xy(half_width + 1, 0) + term.on_webpurple(args.detail_list.upper().ljust(half_width - 1)), end='')
        print(term.move_xy(half_width + 1, half_height + 1) + term.on_olive('CALENDER'.ljust(half_width - 1)), end='')

        
        all_tasks = rtm_instance.get_tasks(None)

        overdue_tasks = sorted(
            list([d for d in all_tasks if d['status'] == rtm.OVERDUE]),
            key=itemgetter('due')
            )

        display_tasks(overdue_tasks, 0, 1, half_height - 1, half_width - 2, True)

        today_tasks = sorted(
            list([d for d in all_tasks if d['status'] == rtm.TODAY]),
            key=itemgetter('name')
            )

        display_tasks(today_tasks, 0, half_height + 2, term.height, half_width - 2, False)


        detail_tasks = rtm_instance.get_tasks(args.detail_list)
        detail_tasks = sorted(detail_tasks, key=itemgetter('due', 'name'))
        display_tasks(detail_tasks, half_width + 1, 1, half_height - 1, half_width - 1, True)


        
        print(term.move_xy(term.width, term.height), end='')
        time.sleep(1)

print(half_width)
#while True:
#    time.sleep(5)