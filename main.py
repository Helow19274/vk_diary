import os
import sys

from configparser import ConfigParser, MissingSectionHeaderError
from diary import Diary
from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType

parser = ConfigParser()
try:
    file = parser.read('settings.ini', encoding='utf-8')
    if len(file) == 0:
        print('Не найден файл settings.ini')
        os.system('pause')
        sys.exit(1)
except MissingSectionHeaderError:
    print('Неверный формат файла settings.ini')
    os.system('pause')
    sys.exit(1)

vk = VkApi(token=parser['Vk']['vk_token'])

try:
    lp = VkLongPoll(vk)
except Exception as error:
    try:
        import socket
        socket.gethostbyaddr('vk.com')
    except socket.gaierror:
        print('Отсутствует подключение к интернету.')
        os.system('pause')
        sys.exit(1)
    else:
        if str(error) == '[15] Access denied: group messages are disabled':
            print('В настройках группы отключены сообщения.')
        else:
            print('Неверный ключ доступа группы.')
        os.system('pause')
        sys.exit(1)

d = Diary(parser['Diary']['diary_login'], parser['Diary']['diary_password'])
try:
    d.auth()
except ValueError:
    print('Неверный логин или пароль')
    os.system('pause')
    sys.exit(1)


def diary(command, day, peer_id):
    data = d.method('diary', from_date=day, to_date=day)

    if 'error' in data:
        return vk.method('messages.send', {'peer_id': peer_id, 'message': 'Ошибка'})
    if data['success'] is False:
        return vk.method('messages.send', {'peer_id': peer_id, 'message': 'Ошибка'})

    data = data['days'][0][1]

    if 'kind' in data:
        if data['kind'] == 'Выходной':
            return vk.method('messages.send', {'peer_id': peer_id, 'message': 'Выходной!'})
        else:
            return vk.method('messages.send', {'peer_id': peer_id, 'message': 'Ошибка'})

    data = data['lessons']

    strs = []
    for x, lesson in enumerate(data, start=1):
        if command == 'schedule':
            strs.append(f'{x}. {lesson["discipline"]}')

        elif command == 'dz':
            strs.append('{}. {}: {}'.format(
                x,
                lesson['discipline'],
                lesson['homework'] if lesson['homework'] != '' else '—'
            ))

        elif command == 'marks':
            strs.append('{}. {}: {}'.format(
                x,
                lesson['discipline'],
                ', '.join(m[2][0] for m in lesson['marks']) if lesson['marks'] != [] else '—'
            ))

    return vk.method('messages.send', {'peer_id': peer_id, 'message': '\n'.join(strs)})


def progress(args, peer_id):
    args = args.split()
    if len(args) == 1:
        level = 'я'
    else:
        level = args[1].lower()

    data = d.method('progress_average', date=args[0])

    if 'error' in data or not data['success']:
        return vk.method('messages.send', {'peer_id': peer_id, 'message': 'Ошибка'})
    if 'kind' in data:
        if data['kind'] == 'Каникулы':
            return vk.method('messages.send', {'peer_id': peer_id, 'message': 'Каникулы'})
        else:
            return vk.method('messages.send', {'peer_id': peer_id, 'message': 'Ошибка'})

    if level == 'я':
        data = data['self']
    elif level == 'класс':
        data = data['classyear']
    elif level == 'параллель':
        data = data['level']

    strs = []
    strs.append(f'Все предметы: {data["total"]}')

    data = data['data']

    for x, lesson in enumerate(data, start=1):
        strs.append(f'{x}. {lesson}: {data[lesson]}')

    return vk.method('messages.send', {'peer_id': peer_id, 'message': '\n'.join(strs)})


def ping(peer_id):
    return vk.method('messages.send', {'peer_id': peer_id, 'message': 'pong!'})


while True:
    try:
        for event in lp.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                text = event.text

                if text.startswith('/schedule '):
                    diary('schedule', text[10:], event.peer_id)
                elif text.startswith('/dz '):
                    diary('dz', text[4:], event.peer_id)
                elif text.startswith('/marks '):
                    diary('marks', text[7:], event.peer_id)
                elif text.startswith('/average '):
                    progress(text[9:], event.peer_id)
                elif text == '/ping':
                    ping(event.peer_id)
                else:
                    vk.method('messages.send', {'peer_id': event.peer_id, 'message': 'Некорректная команда'})
    except KeyboardInterrupt:
        os.system('pause')
        break
    except Exception:
        pass
