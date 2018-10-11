import requests


class Diary(object):
    __slots__ = ('session', 'login', 'password', 'base', 'pupil_id')

    def __init__(self, login, password):
        self.session = requests.Session()
        self.login = login
        self.password = password
        self.base = 'http://e-school.ryazangov.ru/rest/{}'

    def __del__(self):
        return self.session.close()

    def auth(self):
        payload = {'login': self.login, 'password': self.password}
        json = self.session.get(self.base.format('login'), params=payload).json()
        if not json['success']:
            raise ValueError
        self.pupil_id = json['childs'][0][0]

    def method(self, method, **kwargs):
        kwargs['pupil_id'] = self.pupil_id
        return self.session.get(self.base.format(method), params=kwargs).json()
