"""
Модуль для взаимодействия с API панели X-UI.
- Аутентификация.
- Получение списка онлайн пользователей.
- Получение IP-адресов клиента (через API или парсинг лога).
"""

import json
import time
from urllib.parse import quote
import subprocess
import os
import shlex # Для безопасного формирования команд subprocess

# Импортируем requests и общие модули
try:
    import requests
except ImportError:
    print("Критическая ошибка: Библиотека 'requests' не установлена.")
    print("Пожалуйста, установите ее: pip install requests")
    import sys
    sys.exit(1)

try:
    import common # Предполагаем, что common.py содержит Color и API_TIMEOUT
except ImportError:
    print("Ошибка: Не удалось импортировать common.py.")
    # Создаем заглушки, чтобы код не падал, но выводим предупреждение
    print("Предупреждение: Используются значения по умолчанию для common.Color и common.API_TIMEOUT.")
    class Color:
        CYAN = YELLOW = RED = DIM = RESET = '' # Пустые строки, если цвета не нужны
    class common:
        Color = Color
        API_TIMEOUT = 15 # Значение по умолчанию
    # import sys # sys уже импортирован выше
    # sys.exit(1) # Не выходим, пытаемся работать дальше

# --- Константы для выбора метода получения IP ---
IP_FETCH_API = 'api'
IP_FETCH_LOG = 'log'

# --- Вспомогательная функция для логирования ---
def _log_api(level, message):
    """Простое логирование API операций (для отладки)."""
    try:
        colors = {'info': common.Color.CYAN, 'error': common.Color.RED, 'warning': common.Color.YELLOW, 'debug': common.Color.DIM}
        color = colors.get(level.lower(), common.Color.RESET)
        reset_color = common.Color.RESET
    except AttributeError: # Если common.Color не определен
        color = reset_color = ''

    # Выводим Info, Warn, Error всегда. Debug - опционально.
    # TODO: Добавить флаг debug_mode для включения DEBUG логов?
    print(f"{color}[API-{level.upper()}] {message}{reset_color}")


class XUIApiClient:
    """
    Класс для инкапсуляции взаимодействия с API X-UI.
    Хранит сессию и конфигурацию.
    """
    def __init__(self, panel_url, username, password,
                 log_file_path="/usr/local/x-ui/access.log",
                 log_read_lines=500):
        """
        Инициализация клиента. Выполняет вход.

        Args:
            panel_url (str): Базовый URL панели (http://host:port/path).
            username (str): Имя пользователя панели.
            password (str): Пароль пользователя панели.
            log_file_path (str): Путь к файлу access.log Xray (для метода 'log').
            log_read_lines (int): Сколько последних строк лога читать (для метода 'log').
        """
        self.panel_url = panel_url.rstrip('/')
        self.log_file_path = log_file_path
        self.log_read_lines = log_read_lines
        self.session = self._login(username, password) # Получаем сессию при инициализации

    def _login(self, username, password):
        """
        Выполняет вход в панель и возвращает объект сессии requests.
        Вызывается из __init__.
        """
        session = requests.Session()
        session.headers.update({'User-Agent': 'MKXRayScript/1.0'}) # Добавим User-Agent
        login_url = f"{self.panel_url}/login"
        login_data = {'username': username, 'password': password}

        try:
            _log_api('debug', f"Попытка входа в API: {login_url} с пользователем '{username}'")
            response = session.post(login_url, data=login_data, timeout=common.API_TIMEOUT)
            response.raise_for_status()

            # Проверка ответа (как в твоей функции get_xui_session)
            try:
                if 'application/json' in response.headers.get('Content-Type', ''):
                    result = response.json()
                    if result.get("success"):
                        _log_api('info', f"Успешный вход в API X-UI (JSON): {self.panel_url}")
                        if '3x-ui' in session.cookies or '3x-ui=' in response.headers.get('Set-Cookie', ''):
                             return session
                        else:
                             _log_api('warning', f"Вход в API (JSON) успешен, но куки '3x-ui' не установлены.")
                             raise ConnectionError("Не удалось получить сессионные куки после успешного входа (JSON).")
                    else:
                        error_msg = result.get('msg', 'Неизвестная ошибка ответа API')
                        _log_api('error', f"Ошибка входа в API X-UI (success=false): {error_msg}")
                        raise ConnectionError(f"Ошибка входа в API X-UI: {error_msg}")
                elif '3x-ui' in session.cookies or '3x-ui=' in response.headers.get('Set-Cookie', ''):
                     _log_api('info', f"Успешный вход в API X-UI (не-JSON ответ, но куки '3x-ui' установлены): {self.panel_url}")
                     return session
                else:
                     _log_api('error', f"Не удалось войти в API: получен не-JSON ответ и куки '3x-ui' не установлены. Status: {response.status_code}.")
                     raise ConnectionError("Не удалось войти в API: не JSON и нет куки.")

            except json.JSONDecodeError:
                if '3x-ui' in session.cookies or '3x-ui=' in response.headers.get('Set-Cookie', ''):
                     _log_api('info', f"Успешный вход в API X-UI (ответ не JSON, но куки '3x-ui' установлены): {self.panel_url}")
                     return session
                else:
                     _log_api('error', f"Не удалось войти в API: ответ не JSON и куки '3x-ui' не установлены.")
                     raise ConnectionError("Не удалось войти в API: не JSON и нет куки.")

        except requests.exceptions.Timeout:
            _log_api('error', f"Таймаут ({common.API_TIMEOUT} сек) при подключении к API: {login_url}")
            raise ConnectionError(f"Таймаут при подключении к {login_url}")
        except requests.exceptions.ConnectionError as e:
             _log_api('error', f"Ошибка соединения с API {login_url}: {e}")
             raise ConnectionError(f"Ошибка соединения с {login_url}: {e}")
        except requests.exceptions.HTTPError as e:
             body_preview = e.response.text[:200] if hasattr(e.response, 'text') else '(нет тела)'
             _log_api('error', f"HTTP ошибка при входе в API {login_url}: {e.response.status_code} {e.response.reason}. Body(start): {body_preview}...")
             raise ConnectionError(f"HTTP ошибка при входе в API: {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            _log_api('error', f"Общая ошибка запроса при входе в API {login_url}: {e}")
            raise ConnectionError(f"Ошибка запроса при входе в API: {e}")

    def get_online_users_emails(self):
        """
        Получает множество email/тегов онлайн пользователей из API X-UI.
        Использует сессию, созданную при инициализации.
        """
        if not self.session:
            _log_api('error', "Получение онлайн пользователей: Сессия API недействительна.")
            return None # Возвращаем None при ошибке сессии

        online_users_url = f"{self.panel_url}/panel/api/inbounds/onlines"
        try:
            _log_api('debug', f"Запрос списка онлайн пользователей: {online_users_url}")
            response = self.session.post(online_users_url, timeout=common.API_TIMEOUT)
            response.raise_for_status()

            try:
                data = response.json()
                if data.get("success"):
                    online_list = data.get("obj", [])
                    if isinstance(online_list, list):
                         _log_api('info', f"Получено {len(online_list)} онлайн пользователей из API.")
                         return set(online_list)
                    else:
                         _log_api('error', f"API вернуло некорректный формат списка онлайн ('obj' не список): {type(online_list)}")
                         return None # Возвращаем None при ошибке формата
                else:
                    error_msg = data.get('msg', 'Неизвестная ошибка API')
                    _log_api('error', f"Ошибка API при получении онлайн (success=false): {error_msg}")
                    return None # Возвращаем None при ошибке API
            except json.JSONDecodeError:
                 _log_api('error', f"Не удалось декодировать JSON ответа API онлайн: {response.text[:200]}...")
                 return None # Возвращаем None при ошибке парсинга

        # Обработка исключений requests как в твоем коде
        except requests.exceptions.Timeout: _log_api('error', f"Таймаут онлайн"); return None
        except requests.exceptions.ConnectionError as e: _log_api('error', f"Ошибка соединения онлайн: {e}"); return None
        except requests.exceptions.HTTPError as e: _log_api('error', f"HTTP ошибка онлайн: {e.response.status_code}"); return None
        except requests.exceptions.RequestException as e: _log_api('error', f"Ошибка запроса онлайн: {e}"); return None

    def _get_client_ip_from_api(self, user_email):
        """
        [Внутренний метод] Получает IP через API (/clientIps).
        Возвращает список строк IP или пустой список. None при ошибке связи/парсинга.
        """
        if not self.session:
            _log_api('error', f"Получение IP (API) для '{user_email}': Сессия недействительна.")
            return None # Ошибка сессии

        encoded_email = quote(user_email)
        client_ips_url = f"{self.panel_url}/panel/api/inbounds/clientIps/{encoded_email}"
        _log_api('debug', f"Запрос IP (API) для '{user_email}': {client_ips_url}")

        try:
            response = self.session.post(client_ips_url, timeout=common.API_TIMEOUT)
            _log_api('debug', f"Ответ API для IP '{user_email}': Status={response.status_code}, Body='{response.text[:100]}'")

            if response.status_code == 404:
                _log_api('debug', f"API вернуло 404 для '{user_email}'. Считаем как 'не найдено'.")
                return [] # 404 - не ошибка связи, а "не найдено"

            response.raise_for_status() # Проверяем на другие ошибки (5xx, 401 и т.д.)

            try:
                data = response.json()
                _log_api('debug', f"Распарсенный JSON для IP (API) '{user_email}': {data}")
                if data.get("success"):
                    ip_list_obj = data.get("obj")
                    _log_api('debug', f"Поле 'obj' для IP (API) '{user_email}': {ip_list_obj} (тип: {type(ip_list_obj)})")

                    # Обрабатываем и строку "No IP Record", и потенциальный список IP
                    if isinstance(ip_list_obj, str):
                        if "no ip record" in ip_list_obj.lower():
                            _log_api('debug', f"API вернуло 'No IP Record' для '{user_email}'.")
                            return [] # Нормальный ответ "не найдено"
                        else:
                            # Если вернулась строка, но это не "No IP Record", считаем, что это IP
                            valid_ip = ip_list_obj.strip()
                            if valid_ip:
                                 _log_api('debug', f"API вернуло один IP как строку для '{user_email}': {valid_ip}")
                                 return [valid_ip]
                            else:
                                 _log_api('warning', f"API для IP '{user_email}' вернуло пустую строку в 'obj'.")
                                 return []
                    elif isinstance(ip_list_obj, list):
                        valid_ips = [ip for ip in ip_list_obj if isinstance(ip, str) and ip.strip()]
                        if valid_ips: _log_api('debug', f"API вернуло список IP для '{user_email}': {valid_ips}")
                        return valid_ips # Возвращаем список строк
                    else:
                        # Не строка и не список - неожиданный формат
                        _log_api('warning', f"API для IP '{user_email}' вернуло неожиданный тип obj: {type(ip_list_obj)}")
                        return [] # Считаем как "не найдено"
                else:
                    # success=false
                    error_msg = data.get('msg', 'Неизвестная ошибка API').lower()
                    if "client not found" not in error_msg and "клиент не найден" not in error_msg:
                        _log_api('warning', f"Ошибка API при получении IP для '{user_email}' (success=false): {data.get('msg', 'Неизвестная ошибка')}")
                    else:
                         _log_api('debug', f"API сообщило, что клиент '{user_email}' не найден.")
                    return [] # Success=false считаем как "не найдено" (не ошибка связи)

            except json.JSONDecodeError:
                _log_api('error', f"Не удалось декодировать JSON ответа API IP для '{user_email}': {response.text[:200]}...")
                return None # Ошибка парсинга - возвращаем None

        # Обработка исключений requests (возвращаем None при ошибках связи/http)
        except requests.exceptions.Timeout: _log_api('error', f"Таймаут IP (API) '{user_email}'"); return None
        except requests.exceptions.ConnectionError as e: _log_api('error', f"Ошибка соединения IP (API) '{user_email}': {e}"); return None
        except requests.exceptions.HTTPError as e: _log_api('error', f"HTTP ошибка IP (API) '{user_email}': {e.response.status_code}"); return None
        except requests.exceptions.RequestException as e: _log_api('error', f"Ошибка запроса IP (API) '{user_email}': {e}"); return None

    def _get_client_ip_from_log(self, user_email):
        """
        [Внутренний метод] Парсит access.log Xray для поиска последнего IP клиента по email.
        Возвращает список с одним IP (str) или пустой список. None при ошибке доступа/парсинга.
        """
        if not os.path.exists(self.log_file_path):
            _log_api('error', f"Парсинг лога для '{user_email}': Файл лога не найден: {self.log_file_path}")
            return None # Ошибка - файл не найден

        _log_api('debug', f"Парсинг лога для IP '{user_email}' из {self.log_file_path} ({self.log_read_lines} строк)")
        try:
            # Формируем команду безопасно с помощью shlex
            tail_command_list = ['tail', '-n', str(self.log_read_lines), self.log_file_path]
            _log_api('debug', f"Выполнение команды: {' '.join(shlex.quote(c) for c in tail_command_list)}")

            # Выполняем команду tail
            process = subprocess.run(
                tail_command_list,
                capture_output=True,
                text=True,
                check=True, # Выбросит исключение, если tail вернет ошибку
                encoding='utf-8', # Явно указываем кодировку
                errors='ignore' # Игнорируем ошибки декодирования, если в логе мусор
            )
            log_lines = process.stdout.strip().split('\n')

            search_pattern = f"email: {user_email}"
            found_ip = None
            for line in reversed(log_lines):
                if search_pattern in line:
                    parts = line.split()
                    # Ищем "from IP:PORT" - обычно это 2 и 3 части строки
                    if len(parts) >= 4 and parts[2] == 'from' and ':' in parts[3]:
                        ip_port = parts[3] # Берем четвертый элемент
                        ip = ip_port.split(':')[0]
                        # Простая валидация IP (наличие точки или двоеточия)
                        if '.' in ip or ':' in ip:
                            found_ip = ip
                            _log_api('debug', f"Найден IP '{found_ip}' в логе для '{user_email}' в строке: {line.strip()}")
                            break # Нашли самый свежий, выходим
                        else:
                           _log_api('warning', f"Некорректный IP '{ip}' извлечен из строки лога: {line.strip()}")
                    else:
                         # Строка содержит email, но формат не стандартный 'from IP:PORT'
                         _log_api('warning', f"Не удалось извлечь 'IP:PORT' после 'from' из строки лога с email '{user_email}': {line.strip()}")


            if found_ip:
                _log_api('info', f"IP найден через парсинг лога для '{user_email}': {found_ip}")
                return [found_ip] # Возвращаем список с одним IP
            else:
                _log_api('info', f"IP для '{user_email}' не найден в последних {self.log_read_lines} строках лога.")
                return [] # Не нашли - возвращаем пустой список

        except FileNotFoundError:
             _log_api('error', f"Ошибка парсинга лога: команда 'tail' не найдена. Убедитесь, что она установлена и доступна в PATH.")
             return None # Ошибка - нет tail
        except subprocess.CalledProcessError as e:
            # tail может вернуть ошибку, если файл не существует или нет прав
            _log_api('error', f"Ошибка выполнения команды tail для {self.log_file_path}: {e}. Stderr: {e.stderr}")
            return None # Ошибка выполнения tail
        except Exception as e:
            _log_api('error', f"Непредвиденная ошибка при парсинге лога {self.log_file_path} для '{user_email}': {e}")
            return None # Другая ошибка

    def get_client_ip_addresses(self, user_email, method=IP_FETCH_API):
        """
        Получает список текущих IP-адресов для указанного пользователя,
        используя выбранный метод (API или парсинг лога).

        Args:
            user_email (str): Email клиента.
            method (str): Метод получения IP ('api' или 'log').
                          По умолчанию 'api'.

        Returns:
            list or None: Список строк IP-адресов при успехе (может быть пустым, если IP не найдены).
                          None при серьезной ошибке (проблемы с сессией, доступом к логу, парсингом JSON и т.д.).
        """
        _log_api('info', f"Запрос IP для '{user_email}' методом '{method}'")

        if not self.session and method == IP_FETCH_API:
             _log_api('error', "Сессия API недействительна, метод 'api' недоступен.")
             return None

        if method == IP_FETCH_API:
            result = self._get_client_ip_from_api(user_email)
        elif method == IP_FETCH_LOG:
            result = self._get_client_ip_from_log(user_email)
        else:
            _log_api('error', f"Неизвестный метод получения IP: '{method}'. Используйте '{IP_FETCH_API}' или '{IP_FETCH_LOG}'.")
            return None # Неверный метод

        # Логируем финальный результат
        if result is None:
            _log_api('error', f"Не удалось получить IP для '{user_email}' методом '{method}' из-за ошибки.")
        elif not result: # Пустой список
            _log_api('info', f"IP для '{user_email}' не найдены методом '{method}'.")
        else:
            _log_api('info', f"Успешно получены IP для '{user_email}' методом '{method}': {result}")

        return result
