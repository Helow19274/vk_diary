import sys
import requests
import traceback
import subprocess

from diary import Diary
from pytz import timezone
from datetime import datetime, timedelta
from vk import VkApi, VkBotLongPoll, ApiError
from configparser import ConfigParser, MissingSectionHeaderError, ParsingError


def check_date(day):
    if day.lower() == 'сегодня':
        return datetime.now(tz=timezone('Europe/Moscow')).strftime('%d.%m.%Y')
    elif day.lower() == 'завтра':
        day = datetime.now(tz=timezone('Europe/Moscow')) + timedelta(days=1)
        return day.strftime('%d.%m.%Y')
    elif day.lower() == 'вчера':
        day = datetime.now(tz=timezone('Europe/Moscow')) + timedelta(days=-1)
        return day.strftime('%d.%m.%Y')
    try:
        datetime.strptime(day, '%d.%m.%Y')
        return day
    except ValueError:
        return


def diary(command, day):
    try:
        data = d.method('diary', from_date=day, to_date=day)
    except requests.exceptions.HTTPError:
        return 'diary_broken'

    if 'error' in data or not data['success']:
        return 'Ошибка'

    data = data['days'][0][1]

    if 'kind' in data:
        if data['kind'] == 'Выходной':
            return 'Выходной!'
        else:
            return 'Ошибка'

    data = data['lessons']

    strs = []
    for x, lesson in enumerate(data, start=1):
        if command == 'schedule':
            strs.append(f'{x}. {lesson["discipline"]}')

        elif command == 'dz':
            strs.append(f'{x}. {lesson["discipline"]}: {lesson["homework"] if lesson["homework"] != "" else "—"}')

        elif command == 'marks':
            strs.append('{}. {}: {}'.format(
                x,
                lesson['discipline'],
                ', '.join(m[2][0] for m in lesson['marks']) if lesson['marks'] != [] else '—'
            ))

        elif command == 'attendance':
            strs.append(f'{x}. {lesson["discipline"]}: {lesson["attendance"][0]}')

    return'\n'.join(strs)


def average(level, day):
    try:
        data = d.method('progress_average', date=day)
    except requests.exceptions.HTTPError:
        return 'diary_broken'

    if 'error' in data or not data['success']:
        return 'Ошибка'

    if 'kind' in data:
        if data['kind'] == 'Каникулы':
            return 'Каникулы'
        else:
            return 'Ошибка'

    if level == 'я':
        data = data['self']
    elif level == 'класс':
        data = data['classyear']
    elif level == 'параллель':
        data = data['level']
    else:
        return 'Некорректная команда'

    strs = [f'Все предметы: {data["total"]}']

    for x, (lesson, mark) in enumerate(data['data'].items(), start=1):
        strs.append(f'{x}. {lesson}: {mark}')

    return '\n'.join(strs)


def totals(day):
    try:
        data = d.method('totals', date=day)
    except requests.exceptions.HTTPError:
        return 'diary_broken'

    if 'error' in data or not data['success']:
        return 'Ошибка'

    if 'kind' in data:
        if data['kind'] == 'Не выставлено ни одной итоговой оценки!':
            return 'Не выставлено ни одной итоговой оценки'
        else:
            return 'Ошибка'

    strs = []
    for x, period in enumerate(data['period_types']):
        if all(data['subjects'][y][x] == '0' for y in data['subjects']):
            continue
        strs.append(f'{period}:')
        for y, (subject, marks) in enumerate(data['subjects'].items(), start=1):
            strs.append(f'{y}. {subject}: {marks[x] if marks[x] != "0" else "—"}')

        strs.append('')

    return '\n'.join(strs)


def marks_all(day):
    try:
        data = d.method('lessons_scores', date=day)
    except requests.exceptions.HTTPError:
        return 'diary_broken'

    strs = [data['subperiod']]
    for x, (lesson, marks) in enumerate(data['data'].items(), start=1):
        strs.append(f'{x}. {lesson}: {",".join(list(mark["marks"].values())[0][0] for mark in marks)}')

    return '\n'.join(strs)


def call_exit(text=None, status=1):
    if text:
        print(text)
    subprocess.call('cmd /c pause')
    sys.exit(status)


parser = ConfigParser()
try:
    file = parser.read('settings.ini', encoding='utf-8')
    if not file:
        call_exit('Не найден файл settings.ini')
except (MissingSectionHeaderError, ParsingError):
    call_exit('Неверный формат файла settings.ini')

if not parser['Vk']['vk_token'] or not parser['Vk']['group_id'] or not parser['Diary']['diary_login'] or not parser['Diary']['diary_password']:
    call_exit('Заполнены не все поля файла settings.ini')

try:
    subprocess.check_call('ping google.com -n 1 -l 1', stdout=-3, stderr=-3)
except subprocess.CalledProcessError:
    call_exit('Отсутствует подключение к интернету')

session = requests.Session()

vk = VkApi(parser['Vk']['vk_token'], session)
try:
    perms = [perm['name'] for perm in vk.method('groups.getTokenPermissions')['permissions']]
    if 'manage' not in perms or 'messages' not in perms:
        call_exit('У ключа недостаточно прав')
except ApiError:
    call_exit('Неверный ключ доступа')

try:
    vk.method('groups.getOnlineStatus', {'group_id': parser['Vk']['group_id']})
except Exception:
    call_exit('В настройках группы отключены сообщения или неверный id группы')

d = Diary(parser['Diary']['diary_login'], parser['Diary']['diary_password'], session)
try:
    d.auth()
except ValueError:
    call_exit('Неверный логин или пароль')
except requests.exceptions.HTTPError:
    call_exit('Электронный дневник не работает. Попробуйте запустить позже')

payload = {
    'group_id': parser['Vk']['group_id'],
    'enabled': 1,
    'api_version': '5.92',
    'message_new': 1
}
try:
    vk.method('groups.setLongPollSettings', payload)
except ApiError:
    call_exit('Неверный id группы')

lp = VkBotLongPoll(vk, group_id=parser['Vk']['group_id'])
print('Запущен!')
while True:
    try:
        for event in lp.listen():
            if event['type'] == 'message_new':
                text = event['object']['text']
                user_id = event['object']['from_id']

                if not text or not text.startswith('/'):
                    vk.method('messages.send', {'peer_id': user_id, 'message': 'Некорректная команда'})
                    continue

                command, _, args = text[1:].partition(' ')

                i = iter(args.split())
                args = dict(zip(i, i))
                day = check_date(args.pop('-d', 'сегодня'))
                if not day:
                    vk.method('messages.send', {'peer_id': user_id, 'message': 'Неверный формат даты'})
                    continue

                if command in ['schedule', 'dz', 'marks', 'attendance']:
                    text = diary(command, day)
                elif command == 'average':
                    text = average(args.pop('-l', 'я').lower(), day)
                elif command == 'totals':
                    text = totals(day)
                elif command == 'marks_all':
                    text = marks_all(day)
                elif command == 'ping':
                    text = 'Pong!'
                else:
                    vk.method('messages.send', {'peer_id': user_id, 'message': 'Некорректная команда'})
                    continue

                if text == 'diary_broken':
                    call_exit('Похоже, что электронный дневник не отвечает. Попробуйте запустить позже')

                vk.method('messages.send', {'peer_id': user_id, 'message': text})
    except KeyboardInterrupt:
        call_exit(status=0)
    except Exception:
        traceback.print_exc()
        call_exit()
