import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
from threading import Thread
import time
import toml

# Make parameters for an IN clause
def make_in_params(count):
    return ','.join([ '?' ] * count)

# Convert a date and time from the SQLite trips query to a timestamp
def make_timestamp(date_str, time_str):
    timestamp = pd.to_datetime(date_str)
    hours = int(time_str[:2])
    if hours > 23:
        timestamp += timedelta(days=1)
        hours = hours - 24

    timestamp += timedelta(hours=hours,minutes=int(time_str[3:5]), seconds=int(time_str[6:8]))
    return timestamp

def day_old(timestamp):
    return (datetime.now() - timestamp).total_seconds() > 86400

class gtfs(Thread):
    def __init__(self, gtfs_files):
        
        self.databases = []

        for gtfs_file in gtfs_files:
            with open(gtfs_file) as gf:
                gf_content = toml.load(gf)

                db = {}
                db['db_file'] = gf_content['gtfs']['database']
                db['departure_stops'] = gf_content['gtfs']['departure_stops']
                db['arrival_stops'] = gf_content['gtfs']['arrival_stops']
                db['replacements'] = gf_content['gtfs']['replacements']
                db['default_color'] = gf_content['gtfs']['default_color']

                self.databases.append(db)

        self.trips = None
        self.trips_time = None

        self.journeys = []

        self.stop_flag = False

        # Kick off the background retrieval thread
        Thread.__init__(self)
        self.start()

    def run(self):
        # Get the lists
        self._extract_trips()

        while not self.stop_flag:
            if self.trips_time is not None and day_old(self.trips_time):
                self._extract_trips()

            self._make_journeys()

            sleep_time = 0
            while not self.stop_flag and sleep_time < 10:
                time.sleep(1)
                sleep_time += 1

    def _extract_trips(self):
        one_day = timedelta(days=1)
        today = date.today().strftime('%Y%m%d')
        yesterday = (date.today() - one_day).strftime('%Y%m%d')
        tomorrow = (date.today() + one_day).strftime('%Y%m%d')
        dates = [yesterday, today, tomorrow]


        collected_trips = []

        for db in self.databases:
            with sqlite3.connect(db['db_file']) as con:
                trip_query = (
                'SELECT st1.trip_id, st1.stop_id, s.stop_name, r.route_short_name AS route, t.trip_headsign AS destination, '
                'r.route_color as color, c.date, st1.departure_time '
                'FROM stop_times st1 INNER JOIN stop_times st2 ON st1.trip_id = st2.trip_id '
                'INNER JOIN stops s ON s.stop_id = st1.stop_id '
                'INNER JOIN trips t ON t.trip_id = st1.trip_id '
                'INNER JOIN routes r ON t.route_id = r.route_id '
                'INNER JOIN calendar_dates c ON c.service_id = t.service_id '
                f'WHERE st1.stop_id IN ({make_in_params(len(db["departure_stops"]))}) AND st2.stop_id IN ({make_in_params(len(db["arrival_stops"]))}) '
                'AND CAST(st2.stop_sequence AS INTEGER) > CAST(st1.stop_sequence AS INTEGER) '
                'AND c.exception_type = 1 '
                f'AND c.date IN ({make_in_params(len(dates))}) '
                'ORDER BY c.date, st1.departure_time'
                )

            trips = pd.read_sql_query(trip_query, con, params=db['departure_stops'] + db['arrival_stops'] + dates)
            trips['timestamp'] = trips.apply(lambda row: make_timestamp(row.date, row.departure_time), axis=1)
            trips['color'] = trips['color'].replace('', db['default_color'])

            for replacement in db['replacements']:
                trips.replace(replacement[0], replacement[1], inplace=True)

            trips = trips.drop_duplicates()

            collected_trips.append(trips)

        self.trips = pd.concat(collected_trips).sort_values(by='timestamp')
        self.trips_time = datetime.now()

    def format_row(self, row):
        timediff = row.timestamp - datetime.now()
        minutes_diff = int(timediff.total_seconds() / 60)
        if minutes_diff > 59:
            hours = int(minutes_diff / 60)
            timediff_str = f'{hours}h{minutes_diff - (hours * 60):02d}m'
        else:
            timediff_str = f'{str(minutes_diff)}m'
        return [row.color, minutes_diff, f'{row.timestamp.strftime("%H:%M")}', timediff_str.rjust(6), f'{row.route.rjust(2)} {row.destination}']

    def _make_journeys(self):
        journey_info = self.trips[self.trips['timestamp'] > datetime.now()]
        self.journeys = journey_info.apply(lambda row: self.format_row(row), axis=1).drop_duplicates()

    def get_journeys(self):
        return self.journeys

    def stop(self):
        self.stop_flag = True
