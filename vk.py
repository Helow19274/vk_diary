class ApiError(Exception):
    pass


class VkApi(object):
    __slots__ = ('access_token', 'session')

    def __init__(self, access_token, session):
        self.access_token = access_token
        self.session = session

    def method(self, method, payload=None):
        payload = payload.copy() if payload else {}
        payload['access_token'] = self.access_token
        payload['v'] = '5.89'
        json = self.session.post(f'https://api.vk.com/method/{method}', data=payload).json()

        if 'error' in json:
            raise ApiError(json['error']['error_msg'])

        return json['response']


class VkBotLongPoll(object):
    __slots__ = ('vk', 'group_id', 'key', 'server', 'ts')

    def __init__(self, vk, group_id):
        self.vk = vk
        self.group_id = group_id

        self.update_longpoll_server()

    def update_longpoll_server(self, update_ts=True):
        json = self.vk.method('groups.getLongPollServer', {'group_id': self.group_id})

        self.key = json['key']
        self.server = json['server']

        if update_ts:
            self.ts = json['ts']

    def check(self):
        payload = {'act': 'a_check', 'key': self.key, 'ts': self.ts, 'wait': 10}
        json = self.vk.session.get(self.server, params=payload, timeout=20).json()

        if 'failed' not in json:
            self.ts = json['ts']
            return [update for update in json['updates']]

        elif json['failed'] == 1:
            self.ts = json['ts']

        elif json['failed'] == 2:
            self.update_longpoll_server(update_ts=False)

        elif json['failed'] == 3:
            self.update_longpoll_server()

        return []

    def listen(self):
        while True:
            for event in self.check():
                yield event
