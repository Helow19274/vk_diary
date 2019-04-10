class Diary(object):
    __slots__ = ('session', 'login', 'password', 'base', 'pupil_id')

    def __init__(self, login, password, session):
        self.session = session
        self.login = login
        self.password = password
        self.base = 'https://e-school.ryazangov.ru/rest/{}'
        self.pupil_id = None

    def __del__(self):
        return self.session.close()

    def auth(self):
        json = self.method('login', login=self.login, password=self.password)
        if not json['success']:
            raise ValueError
        self.pupil_id = json['childs'][0][0]

    def method(self, method, **kwargs):
        if self.pupil_id and method != 'login':
            kwargs['pupil_id'] = self.pupil_id
        r = self.session.get(self.base.format(method), params=kwargs)
        if r.status_code == 502:
            r.raise_for_status()

        return r.json()
