import toml
from threading import Thread
import icalendar
import recurring_ical_events
import datetime
from tzlocal import get_localzone
from dateutil import relativedelta
import time
import requests
from copy import deepcopy

def _get_calendar(source):
    if source.startswith('http'):
        return _get_calendar_http(source)
    else:
        return _get_calendar_file(source)

def _get_calendar_file(source):
    with open(source) as f:
        return icalendar.Calendar.from_ical(f.read())

def _get_calendar_http(source):
    try:
        req = requests.get(source)
        return icalendar.Calendar.from_ical(req.text)
    except Exception:
        return None


def midnight(date_object):
    return date_object.replace(hour=0, minute=0, second=0, microsecond=0)


class cal(Thread):
    def __init__(self, config):
        self.calendars = config
        self.day_events = []
        self.time_events = []
        self.stop_flag = False

        Thread.__init__(self)
        self.start()

    def run(self):
        while not self.stop_flag:
            time_events = []
            day_events = []

            now = datetime.datetime.now(get_localzone())
            one_month = now + relativedelta.relativedelta(months=12)

            for name in self.calendars.keys():
                if self.stop_flag:
                    break

                source = self.calendars[name]['calendar']
                color = self.calendars[name]['color']

                cal = _get_calendar(source)
                if cal is not None:
                    events = recurring_ical_events.of(cal).between(now, one_month)
                    for ev in events:
                        event = {
                            'name': ev.get('summary'),
                            'start': ev.get('dtstart').dt,
                            'end': ev.get('dtend').dt,
                            'color': color
                        }

                        if isinstance(event['start'], datetime.datetime):
                            time_events.append(event)
                        else:
                            start_date = event['start']
                            end_date = event['end']

                            current_date = event['start']
                            while current_date < end_date:

                                if current_date >= midnight(now).date():
                                    day_event = deepcopy(event)
                                    day_event['start'] = current_date
                                    day_event['end'] = current_date

                                    day_events.append(day_event)

                                current_date = current_date + relativedelta.relativedelta(days=1)

            self.day_events = sorted(day_events, key=lambda x: x['start'])
            self.time_events = sorted(time_events, key=lambda x: x['start'])

            sleep_time = 0
            while not self.stop_flag and sleep_time < 600:
                time.sleep(1)
                sleep_time += 1

    def get_events(self):
        result = []

        current_date = midnight(datetime.datetime.now(get_localzone())).date()
        day_event_index = 0
        time_event_index = 0

        while day_event_index < len(self.day_events) or time_event_index < len(self.time_events):
            while day_event_index < len(self.day_events) and self.day_events[day_event_index]['start'] <= current_date:
                evt = self.day_events[day_event_index]

                event_object = {
                    'start': evt['start'],
                    'name': evt['name'],
                    'color': evt['color'],
                    'time_to_start': None
                }

                true_end = evt['end'] - relativedelta.relativedelta(days = 1)
                if true_end == evt['start']:
                    event_object['end'] = None
                else:
                    event_object['end'] = true_end

                result.append(event_object)

                day_event_index += 1

            while time_event_index < len(self.time_events) and midnight(self.time_events[time_event_index]['start']).date() <= current_date:
                evt = self.time_events[time_event_index]

                event_object = {
                    'start': evt['start'].astimezone(get_localzone()),
                    'end': evt['end'].astimezone(get_localzone()),
                    'name': evt['name'],
                    'color': evt['color'],
                    'time_to_start': evt['start'].astimezone(get_localzone()) - datetime.datetime.now(get_localzone())
                }

                result.append(event_object)

                time_event_index += 1

            current_date = current_date + relativedelta.relativedelta(days=1)

        return result

    def stop(self):
        self.stop_flag = True



# Run from parent directory, i.e. python calendar/calendar.py
if __name__ == "__main__":
    with open('config.toml') as config_file:
        config = toml.load(config_file)

    instance = cal(config['calendar'])

    while True:
        print(instance.get_result())
        time.sleep(5)

