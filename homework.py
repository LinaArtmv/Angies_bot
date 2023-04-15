import requests
import os
from dotenv import load_dotenv
import time
import sys
import logging
import telegram

load_dotenv()


PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: int = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS: dict = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    environment_variables = [PRACTICUM_TOKEN,
                             TELEGRAM_TOKEN,
                             TELEGRAM_CHAT_ID]
    return all(environment_variables)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logging.debug('Отправляем сообщение')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка при отправке сообщения {error}')
        raise ConnectionError(f'Ошибка при отправке сообщения {error}')
    else:
        logging.info('Сообщение отправлено')


def get_api_answer(timestamp):
    """Делает запрос к API-сервису Пракикум.Домашка."""
    logging.debug('Делаем запрос к API сервису')
    REQUEST_PARAMS: dict = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}}
    try:
        homework_statuses = requests.get(**REQUEST_PARAMS)
    except requests.RequestException as error:
        logging.error(f'Ошибка на сервере {error}')
        raise ConnectionError(f'Ошибка на сервере {error}')
    except Exception as error:
        logging.error(f'Ошибка на сервере {error}')
        raise ConnectionError(f'Ошибка на сервере {error}')
    if homework_statuses.status_code == 200:
        logging.info('Сделали успешный запрос')
        return homework_statuses.json()
    else:
        logging.error(f'Сервер недоступен: {homework_statuses.reason}')
        raise ConnectionError(f'Сервер недоступен: {homework_statuses.reason}')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    logging.debug('Проверка соответствия данных')
    if not isinstance(response, dict):
        logging.error('Тип данных отличается от ожидаемого')
        raise TypeError(f'Ожидаемый тип данных - словарь,'
                        f'получен: {type(response)}')
    if 'homeworks' not in response:
        logging.error('Отсутствует ключ homeworks')
        raise KeyError('Отсутствует ключ homeworks')
    if not isinstance(response['homeworks'], list):
        logging.error('Тип данных отличается от ожидаемого')
        raise TypeError('Ожидаемый тип данных - список')
    if 'current_date' not in response:
        logging.error('Отсутствует ключ current_date')
        raise KeyError('Отсутствует ключ current_date')
    logging.info('Данные соответствуют ожидаемым')
    return response


def parse_status(homework):
    """Извлекает статус работы."""
    logging.debug('Извлечение статуса работы')
    if 'status' not in homework:
        logging.error('Отсутствует ключ status')
        raise KeyError('Отсутствует ключ status')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS.keys():
        logging.error('Отсутствует документированный статус')
        raise KeyError('Отсутствует документированный статус')
    verdict = HOMEWORK_VERDICTS[status]
    if 'homework_name' not in homework:
        logging.error('Отсутствует ключ homework_name')
        raise KeyError('Отсутствует ключ homework_name')
    homework_name = homework.get('homework_name')
    if not homework:
        logging.error('Словарь homework не передан')
        raise ValueError('Словарь homework не передан')
    logging.info('Статус извлечен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_message = None
    if not check_tokens():
        logging.critical('Отсутствует переменная окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            logging.debug('Начало работы главной функции')
            timestamp = int(time.time())
            answer = get_api_answer(timestamp)
            response = check_response(answer)
            homework = response.get('homeworks')[0]
            message = parse_status(homework)
            if last_message == message:
                logging.debug('Статус работы не изменился')
            else:
                send_message(bot, message)
                last_message = message
        except Exception as error:
            message_error = f'Сбой в работе программы: {error}'
            logging.error(message_error)
            if last_message != message_error:
                send_message(bot, message_error)
                last_message = message_error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    FORMAT = '%(levelname)s - %(message)s - %(funcName)s - %(lineno)s'
    logging.basicConfig(
        format=FORMAT,
        level=logging.INFO,
        handlers=[
            logging.FileHandler(filename='main.log',
                                encoding='UTF-8', mode='w'),
            logging.StreamHandler(sys.stdout)])
    main()
