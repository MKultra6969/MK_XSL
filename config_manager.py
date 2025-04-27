"""
Модуль для управления конфигурационными файлами xraySpeedLimit.
- config.json: Настройки API и интерфейса.
- user_limits.json: Лимиты скорости для пользователей.
"""

import os
import json
import stat

# Импортируем общие константы и цвета из common.py
try:
    import common
except ImportError:
    print("Ошибка: Не удалось импортировать common.py. Убедитесь, что он находится в той же директории.")
    # В реальном приложении лучше использовать более сложную обработку зависимостей,
    # но для простоты здесь просто выходим.
    import sys
    sys.exit(1)

# --- Функции работы с директорией и файлами конфигурации ---

def ensure_config_dir():
    """
    Проверяет существование директории конфигурации и создает ее при необходимости.
    Устанавливает права 700 на директорию.

    Returns:
        bool: True, если директория существует или успешно создана, False в случае ошибки.
    """
    if not os.path.exists(common.CONFIG_DIR):
        try:
            os.makedirs(common.CONFIG_DIR, mode=0o700) # Права: rwx------
            print(f"{common.Color.GREEN}✓ Создана директория конфигурации: {common.CONFIG_DIR}{common.Color.RESET}")
            # Убедимся, что права точно установлены (makedirs может их изменить из-за umask)
            os.chmod(common.CONFIG_DIR, 0o700)
        except OSError as e:
            print(f"{common.Color.RED}[ОШИБКА] Не удалось создать директорию {common.CONFIG_DIR}: {e}{common.Color.RESET}")
            return False
    # Если директория уже существует, проверим и установим права на всякий случай
    elif not os.path.isdir(common.CONFIG_DIR):
         print(f"{common.Color.RED}[ОШИБКА] Путь {common.CONFIG_DIR} существует, но не является директорией.{common.Color.RESET}")
         return False
    else:
         try:
             # Устанавливаем права, даже если она уже существует
             current_mode = stat.S_IMODE(os.stat(common.CONFIG_DIR).st_mode)
             if current_mode != 0o700:
                 os.chmod(common.CONFIG_DIR, 0o700)
                 print(f"{common.Color.DIM}✓ Установлены права 700 на директорию {common.CONFIG_DIR}{common.Color.RESET}")
         except OSError as e:
              print(f"{common.Color.RED}[ОШИБКА] Не удалось установить права на директорию {common.CONFIG_DIR}: {e}{common.Color.RESET}")
              return False
    return True

def load_config():
    """
    Загружает основную конфигурацию API и интерфейса из config.json.

    Returns:
        dict: Словарь с конфигурацией или пустой словарь при ошибке или отсутствии файла.
    """
    config_path = common.CONFIG_FILE
    if not os.path.exists(config_path):
        # Файла нет - это не ошибка, просто возвращаем пустой конфиг
        return {}

    if not os.path.isfile(config_path):
        print(f"{common.Color.RED}[ОШИБКА] Путь {config_path} существует, но не является файлом.{common.Color.RESET}")
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # Проверяем, что это словарь и содержит нужные ключи
        if not isinstance(config_data, dict):
             print(f"{common.Color.YELLOW}[ПРЕДУПРЕЖДЕНИЕ] Файл {config_path} не содержит корректный JSON объект (словарь).{common.Color.RESET}")
             return {}

        # Мягкая проверка ключей - просто предупреждаем, если чего-то нет
        required_keys = ["api_url", "api_user", "api_pass", "iface"]
        missing_keys = [key for key in required_keys if key not in config_data]
        if missing_keys:
             print(f"{common.Color.YELLOW}[ПРЕДУПРЕЖДЕНИЕ] В файле {config_path} отсутствуют ключи: {', '.join(missing_keys)}. Рекомендуется перенастроить API.{common.Color.RESET}")

        return config_data

    except (json.JSONDecodeError, OSError) as e:
        print(f"{common.Color.RED}[ОШИБКА] Ошибка чтения или парсинга файла конфигурации {config_path}: {e}{common.Color.RESET}")
        return {} # Возвращаем пустой словарь при любой ошибке чтения/парсинга

def save_config(config_data):
    """
    Сохраняет основную конфигурацию (словарь) в config.json.
    Устанавливает права 600 на файл.

    Args:
        config_data (dict): Словарь с конфигурацией для сохранения.

    Returns:
        bool: True при успехе, False при ошибке.
    """
    if not isinstance(config_data, dict):
        print(f"{common.Color.RED}[ОШИБКА] Данные для сохранения в config.json должны быть словарем.{common.Color.RESET}")
        return False

    # Убеждаемся, что директория существует
    if not ensure_config_dir():
        return False

    config_path = common.CONFIG_FILE
    temp_config_path = config_path + ".tmp" # Используем временный файл для атомарности

    try:
        # Записываем во временный файл
        with open(temp_config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False) # ensure_ascii=False для поддержки кириллицы

        # Устанавливаем права на временный файл перед переименованием
        os.chmod(temp_config_path, 0o600) # Права: rw-------

        # Атомарно переименовываем временный файл в основной
        os.replace(temp_config_path, config_path)

        # print(f"{common.Color.GREEN}✓ Конфигурация API успешно сохранена в {config_path}{common.Color.RESET}") # Убрано, сообщение выводится в вызывающей функции
        return True

    except (OSError, TypeError) as e:
        print(f"{common.Color.RED}[ОШИБКА] Ошибка сохранения файла конфигурации {config_path}: {e}{common.Color.RESET}")
        # Попытка удалить временный файл, если он остался
        if os.path.exists(temp_config_path):
            try:
                os.remove(temp_config_path)
            except OSError:
                pass # Игнорируем ошибку удаления временного файла
        return False

def load_user_limits():
    """
    Загружает лимиты пользователей из user_limits.json.

    Returns:
        dict: Словарь с лимитами { 'email': limit_mbps } или пустой словарь при ошибке/отсутствии файла.
    """
    limits_path = common.USER_LIMITS_FILE
    if not os.path.exists(limits_path):
        return {}

    if not os.path.isfile(limits_path):
        print(f"{common.Color.RED}[ОШИБКА] Путь {limits_path} существует, но не является файлом.{common.Color.RESET}")
        return {}

    try:
        with open(limits_path, 'r', encoding='utf-8') as f:
            limits_data = json.load(f)

        if not isinstance(limits_data, dict):
             print(f"{common.Color.YELLOW}[ПРЕДУПРЕЖДЕНИЕ] Файл {limits_path} не содержит корректный JSON объект (словарь).{common.Color.RESET}")
             return {}

        # Можно добавить валидацию значений (что лимиты - числа), но пока оставим так
        return limits_data

    except (json.JSONDecodeError, OSError) as e:
        print(f"{common.Color.RED}[ОШИБКА] Ошибка чтения или парсинга файла лимитов {limits_path}: {e}{common.Color.RESET}")
        return {}

def save_user_limits(limits_data):
    """
    Сохраняет лимиты пользователей (словарь) в user_limits.json.
    Устанавливает права 600 на файл.

    Args:
        limits_data (dict): Словарь с лимитами { 'email': limit_mbps }.

    Returns:
        bool: True при успехе, False при ошибке.
    """
    if not isinstance(limits_data, dict):
        print(f"{common.Color.RED}[ОШИБКА] Данные для сохранения в user_limits.json должны быть словарем.{common.Color.RESET}")
        return False

    # Убеждаемся, что директория существует
    if not ensure_config_dir():
        return False

    limits_path = common.USER_LIMITS_FILE
    temp_limits_path = limits_path + ".tmp"

    try:
        # Записываем во временный файл с сортировкой ключей для консистентности
        with open(temp_limits_path, 'w', encoding='utf-8') as f:
            json.dump(limits_data, f, indent=4, sort_keys=True, ensure_ascii=False)

        # Устанавливаем права
        os.chmod(temp_limits_path, 0o600)

        # Переименовываем
        os.replace(temp_limits_path, limits_path)

        # print(f"{common.Color.GREEN}✓ Лимиты пользователей сохранены в {limits_path}{common.Color.RESET}") # Сообщение выводится в вызывающей функции
        return True

    except (OSError, TypeError) as e:
        print(f"{common.Color.RED}[ОШИБКА] Ошибка сохранения файла лимитов {limits_path}: {e}{common.Color.RESET}")
        if os.path.exists(temp_limits_path):
            try:
                os.remove(temp_limits_path)
            except OSError:
                pass
        return False