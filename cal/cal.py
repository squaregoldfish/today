import toml
from threading import Thread, Lock
import icalendar
import recurring_ical_events
from datetime import datetime
from tzlocal import get_localzone
from dateutil import relativedelta
import time
import requests
from copy import deepcopy
import logging

def _get_calendar(source):
    if source.startswith('http'):
        return _get_calendar_http(source)
    else:
        return _get_calendar_file(source)

def _get_calendar_file(source):
    with open(source) as f:
        return icalendar.Calendar.from_ical(f.read())

def _get_calendar_http(source):
    req = requests.get(source)
    return icalendar.Calendar.from_ical(req.text)


def midnight(date_object):
    return date_object.replace(hour=0, minute=0, second=0, microsecond=0)


class cal(Thread):
    def __init__(self, config):
        self.calendars = config
        self.stop_flag = False
        self.calendar_data = dict()
        self.lock = Lock()
        self.output_time = None
        self.output = None

        Thread.__init__(self)
        self.start()

    def run(self):
        while not self.stop_flag:
            for name in self.calendars.keys():
                if self.stop_flag:
                    break

                cal_valid = True
                cal = None
                try:
                    cal = _get_calendar(self.calendars[name]['calendar'])
                except Exception as e:
                    cal_valid = False
                    logging.error(f'Error getting calendar {name}')
                    logging.error(e)

                with self.lock:
                    if name not in self.calendar_data.keys() or cal_valid:
                        self.calendar_data[name] = {'error': not cal_valid, 'data': cal}
                    else:
                        self.calendar_data[name]['error'] = not cal_valid

            sleep_time = 0
            while not self.stop_flag and sleep_time < 600:
                time.sleep(1)
                sleep_time += 1

    def get_events(self):

        if self.output is None or (datetime.now() - self.output_time).total_seconds() >= 15:

            day_events = []
            time_events = []
            now = datetime.now(get_localzone())
            cal_period = now + relativedelta.relativedelta(days=7)

            with self.lock:
                for name in self.calendar_data.keys():
                    cal = self.calendar_data[name]['data']
                    if cal is not None:
                        events = recurring_ical_events.of(cal).between(now, cal_period)
                        for ev in events:
                            event = {
                                'name': ev.get('summary'),
                                'start': ev.get('dtstart').dt,
                                'end': ev.get('dtend').dt,
                                'color': self.calendars[name]['color']
                            }

                            if isinstance(event['start'], datetime):
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

            day_events = sorted(day_events, key=lambda x: x['start'])
            time_events = sorted(time_events, key=lambda x: x['start'])

            result = []

            current_date = midnight(datetime.now(get_localzone())).date()
            day_event_index = 0
            time_event_index = 0

            while day_event_index < len(day_events) or time_event_index < len(time_events):
                while day_event_index < len(day_events) and day_events[day_event_index]['start'] <= current_date:
                    evt = day_events[day_event_index]

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

                while time_event_index < len(time_events) and midnight(time_events[time_event_index]['start']).date() <= current_date:
                    evt = time_events[time_event_index]

                    event_object = {
                        'start': evt['start'].astimezone(get_localzone()),
                        'end': evt['end'].astimezone(get_localzone()),
                        'name': evt['name'],
                        'color': evt['color'],
                        'time_to_start': evt['start'].astimezone(get_localzone()) - datetime.now(get_localzone())
                    }

                    result.append(event_object)

                    time_event_index += 1

                current_date = current_date + relativedelta.relativedelta(days=1)
                if (current_date - now.date()).days > 7:
                    break

            self.output = result
            self.output_time = datetime.now()

        return self.output

    def has_error(self):
        has_error = False

        with self.lock:
            for name in self.calendars.keys():
                if name in self.calendar_data.keys():
                    if self.calendar_data[name]['error']:
                        has_error = True
                        break

        return has_error

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

