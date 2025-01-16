import toml
from threading import Thread
import icalendar
import recurring_ical_events
import datetime
from tzlocal import get_localzone
from dateutil import relativedelta
import time
import requests

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
                            day_events.append(event)

            self.day_events = sorted(day_events, key=lambda x: x['start'])
            self.time_events = sorted(time_events, key=lambda x: x['start'])

            sleep_time = 0
            while not self.stop_flag and sleep_time < 300:
                time.sleep(1)
                sleep_time += 1



    def get_event_text(self):

        event_text = []

        current_date = midnight(datetime.datetime.now(get_localzone())).date()
        day_event_index = 0
        time_event_index = 0

        while day_event_index < len(self.day_events) or time_event_index < len(self.time_events):
            while day_event_index < len(self.day_events) and self.day_events[day_event_index]['start'] <= current_date:
                evt = self.day_events[day_event_index]

                ev_text = {
                    'start': datetime.datetime.strftime(evt['start'], '%a %-d %b'),
                    'name': evt['name'],
                    'color': evt['color']
                }

                true_end = evt['end'] - relativedelta.relativedelta(days = 1)
                if true_end == evt['start']:
                    ev_text['end'] = None
                else:
                    ev_text['end'] = datetime.datetime.strftime(true_end, '%a %-d %b'),


                event_text.append(ev_text)

                day_event_index += 1

            while time_event_index < len(self.time_events) and midnight(self.time_events[time_event_index]['start']).date() <= current_date:
                evt = self.time_events[time_event_index]

                ev_text = {
                    'start': datetime.datetime.strftime(evt['start'].astimezone(get_localzone()), '%a %-d %b %-H:%M'),
                    'end': datetime.datetime.strftime(evt['end'].astimezone(get_localzone()), '%-H:%M'),
                    'name': evt['name'],
                    'color': evt['color']
                }

                event_text.append(ev_text)

                time_event_index += 1

            current_date = current_date + relativedelta.relativedelta(days=1)

        return(event_text)

    def stop(self):
        self.stop_flag = True



# Run from parent directory, i.e. python calendar/calendar.py
if __name__ == "__main__":
    with open('config.toml') as config_file:
        config = toml.load(config_file)

    instance = cal(config['calendar'])

    while True:
        print(instance.get_event_text())
        time.sleep(5)

