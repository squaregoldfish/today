import toml
from hashlib import md5
import copy
import requests
import json
from datetime import datetime
import time

RTM_URL = 'https://api.rememberthemilk.com/services/rest/?'
RATE_LIMIT = 1
RATE_LIMIT_BACKOFF = 1
ALL_TASKS = '_all'
OVERDUE = -1
TODAY = 0
FUTURE = 1

class rtm:
    def __init__(self, config):
        self.key = config['api_key']
        self.secret = config['shared_secret']
        self.token = config['token']
        self.tasks = dict()
        self.last_request = None
        self.lists = None

    def _request(self, method, params):

        if self.last_request is not None and (datetime.now() - self.last_request).seconds < RATE_LIMIT:
            time.sleep(RATE_LIMIT_BACKOFF)

        request_params = copy.deepcopy(params)
        request_params['method'] = method
        request_params['api_key'] = self.key
        request_params['auth_token'] = self.token
        request_params['format'] = 'json'

        request_params = dict(sorted(request_params.items()))

        request_string = RTM_URL
        sig = self.secret
        for (key, value) in request_params.items():
            request_string += f'{key}={value}&'
            sig += f'{key}{value}'

        request_string += f'api_sig={md5(sig.encode("utf-8")).hexdigest()}'
        response = requests.get(request_string)

        self.last_request = datetime.now()
        return response.json()

    def _get_lists(self):
        lists_json = self._request('rtm.lists.getList', dict())
        
        self.lists = dict()
        for list_entry in lists_json['rsp']['lists']['list']:
            self.lists[list_entry['name']] = list_entry['id']

    def _get_list_id(self, list_name):
        if self.lists is None:
            self._get_lists()

        return ALL_TASKS if list_name is None else self.lists[list_name]

    def fetch_tasks(self, list_name):
        if list_name is None:
            list_id = None
        else:
            list_id = self._get_list_id(list_name)

        params = dict()
        params['filter'] = 'status:incomplete'

        if list_id is not None:
            params['list_id'] = list_id

        raw_tasks = self._request('rtm.tasks.getList', params)


        today = datetime.today().strftime('%Y-%m-%d')
        store_tasks = list()

        task_series = raw_tasks['rsp']['tasks']['list']

        for series in task_series:
            for task in series['taskseries']:
                task_name = task['name']

                for task_entry in task['task']:
                    entry_date = task_entry['due'][:10]

                    if entry_date < today:
                        status = OVERDUE
                    elif entry_date == today:
                        status = TODAY
                    else:
                        status = FUTURE

                    task_item = dict()
                    task_item['name'] = task_name
                    task_item['due'] = entry_date
                    task_item['status'] = status

                    store_tasks.append(task_item)

        if list_id is None:
            self.tasks[ALL_TASKS] = store_tasks
        else:
            self.tasks[list_id] = store_tasks

    def get_tasks(self, list_name):
        return self.tasks[self._get_list_id(list_name)]


if __name__ == "__main__":
    with open('config.toml') as config_file:
        config = toml.load(config_file)

    instance = rtm(config['rtm'])
    
    print('***ALL***')
    instance.fetch_tasks(None)
    print(instance.get_tasks(None))

    print('***WORK***')
    instance.fetch_tasks('Work')
    print(instance.get_tasks('Work'))