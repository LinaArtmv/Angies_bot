import requests
import os
from dotenv import load_dotenv
import time
import sys
import logging
import telegram

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='a')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

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
    for variable in environment_variables:
        if variable is None:
            logging.critical('Нет переменных окружения')
            sys.exit()


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение отправлено')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения {error}')


def get_api_answer(timestamp):
    """Делает запрос к API-сервису Пракикум.Домашка."""
    logger.debug('Делаем запрос к API сервису')
    from_date = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(url=ENDPOINT,
                                         headers=HEADERS,
                                         params=from_date)
        if homework_statuses.status_code == 200:
            logger.info('Сделали успешный запрос')
            return homework_statuses.json()
        elif homework_statuses.status_code != 200:
            logger.error('Сервер недоступен')
            raise Exception('Сервер недоступен')
    except requests.RequestException:
        logger.error('Ошибка на сервере')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    logger.debug('Проверка соответствия данных')
    if not isinstance(response, dict):
        logger.error('Тип данных отличается от ожидаемого')
        raise TypeError(f'Ожидаемый тип данных - словарь,'
                        f'получен: {type(response)}')
    if 'homeworks' not in response:
        logger.error('Отсутствует ключ homeworks')
        raise KeyError('Отсутствует ключ homeworks')
    if not isinstance(response['homeworks'], list):
        logger.error('Тип данных отличается от ожидаемого')
        raise TypeError('Ожидаемый тип данных - список')
    if 'current_date' not in response:
        logger.error('Отсутствует ключ current_date')
        raise KeyError('Отсутствует ключ current_date')
    logger.info('Данные соответствуют ожидаемым')
    return response


def parse_status(homework):
    """Извлекает статус работы."""
    logger.debug('Извлечение статуса работы')
    if 'status' not in homework:
        logger.error('Отсутствует ключ status')
        raise KeyError('Отсутствует ключ status')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS.keys():
        logger.error('Отсутствует документированный статус')
        raise KeyError('Отсутствует документированный статус')
    verdict = HOMEWORK_VERDICTS[status]
    if 'homework_name' not in homework:
        logger.error('Отсутствует ключ homework_name')
        raise KeyError('Отсутствует ключ homework_name')
    homework_name = homework.get('homework_name')
    logger.info('Статус извлечен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.info('Отсутствует переменная окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''
    last_error = ''
    while True:
        try:
            logger.debug('Начало работы главной функции')
            answer = get_api_answer(timestamp)
            response = check_response(answer)
            homework = response.get('homeworks')[0]
            message = parse_status(homework)
            if last_message != message:
                send_message(bot, message)
                last_message = message
        except Exception as error:
            message_err = f'Сбой в работе программы: {error}'
            logger.error(message_err)
            if error != last_error:
                send_message(bot, message_err)
                last_error = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
