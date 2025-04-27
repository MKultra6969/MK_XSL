"""
Модуль для генерации содержимого скриптов и файлов systemd.
- Скрипт воркера (xray_limit_worker.py)
- Скрипт базовой настройки TC (setup_base_tc.sh)
- Файлы systemd (worker.service, worker.timer, base-tc.service)
"""

import os, stat, json
from xui_api import IP_FETCH_API, IP_FETCH_LOG

# Импортируем общие константы и цвета
try:
    import common
except ImportError:
    print("Ошибка: Не удалось импортировать common.py.")
    import sys
    sys.exit(1)

# --- Генерация скрипта Воркера ---

def create_worker_script(worker_script_path, config_file_path, limits_file_path):
    print(f"{common.Color.CYAN}Генерация скрипта воркера ({common.WORKER_SCRIPT_NAME})...{common.Color.RESET}")
    abs_config_path = os.path.abspath(config_file_path)
    abs_limits_path = os.path.abspath(limits_file_path)
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Окончательно исправленный код воркера
    worker_code = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Скрипт воркера xraySpeedLimit (генерируется автоматически)

import sys
import os
import time
from datetime import datetime
import traceback # Для детального логирования ошибок

# --- Добавляем путь к директории с модулями ---
project_path = '{project_dir}'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# --- Импорт наших модулей ---
try:
    import common
    import config_manager
    import xui_api
    import tc_manager
    # Импортируем константы для метода получения IP
    from xui_api import IP_FETCH_API, IP_FETCH_LOG
except ImportError as e:
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Используем двойные фигурные скобки для экранирования внутри f-строки
    print(f"{{timestamp}} [CRITICAL] Ошибка импорта модуля: {{e}}. Убедитесь, что все .py файлы находятся в {{project_path}}")
    sys.exit(1)

# --- Константы Воркера ---
# Пути к файлам больше не используются напрямую для load_config/load_user_limits,
# но оставим их для информации или будущих нужд.
CONFIG_FILE = '{abs_config_path}'
USER_LIMITS_FILE = '{abs_limits_path}'
DEFAULT_LOG_PATH = "/usr/local/x-ui/access.log" # Стандартный путь, если не задан в конфиге
DEFAULT_LOG_LINES = 500                     # Стандартное кол-во строк, если не задано

# --- Логирование Воркера ---
def log_worker(level, message):
    \"\"\"Логирование сообщений воркера с временной меткой.\"\"\"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Проверяем наличие common.Color перед использованием
    color = getattr(common, 'Color', None)
    reset_color = getattr(color, 'RESET', '') if color else ''
    level_upper = level.upper()

    color_map = {{
        'ERROR': getattr(color, 'RED', '') if color else '',
        'WARNING': getattr(color, 'YELLOW', '') if color else '',
        'INFO': getattr(color, 'GREEN', '') if color else '',
        'DEBUG': getattr(color, 'DIM', '') if color else '',
        'CRITICAL': (getattr(color, 'RED', '') + getattr(color, 'BOLD', '')) if color else ''
    }}
    log_color = color_map.get(level_upper, reset_color)

    # Используем двойные фигурные скобки для экранирования внутри f-строки
    print(f"{{timestamp}} {{log_color}}[{{level_upper}}] {{message}}{{reset_color}}")
    sys.stdout.flush()

# --- Основная логика Воркера ---
def run_worker_cycle():
    log_worker('info', "Запуск цикла обновления правил TC...")

    # 1. Загрузка конфигурации и лимитов (используются пути по умолчанию из common.py)
    config = config_manager.load_config() # <-- БЕЗ АРГУМЕНТА
    user_limits = config_manager.load_user_limits() # <-- БЕЗ АРГУМЕНТА

    if not config:
        # Используем common.CONFIG_FILE для сообщения об ошибке
        log_worker('critical', f"Ошибка: Конфигурационный файл {{common.CONFIG_FILE}} отсутствует или пуст.")
        return
    required_keys = ["api_url", "api_user", "api_pass", "iface"]
    if not all(k in config for k in required_keys):
        missing = [k for k in required_keys if k not in config]
        # Используем common.CONFIG_FILE для сообщения об ошибке
        log_worker('critical', f"Ошибка: Конфигурационный файл {{common.CONFIG_FILE}} неполный. Отсутствуют ключи: {{', '.join(missing)}}")
        return
    if user_limits is None: # Проверяем на None (ошибка загрузки)
        # Используем common.USER_LIMITS_FILE для сообщения об ошибке
        log_worker('critical', f"Ошибка: Не удалось загрузить файл лимитов {{common.USER_LIMITS_FILE}}.")
        return # Выходим, если лимиты не загрузились

    network_interface = config['iface']
    # Получаем метод получения IP из конфига, по умолчанию - API
    ip_fetch_method = config.get('ip_fetch_method', IP_FETCH_API)
    # Получаем параметры для парсинга логов (если они есть в конфиге)
    log_file_path = config.get('log_file_path', DEFAULT_LOG_PATH)
    log_read_lines = config.get('log_read_lines', DEFAULT_LOG_LINES)

    # Используем двойные фигурные скобки для экранирования внутри f-строки
    log_worker('info', f"Используется интерфейс: {{network_interface}}")
    # Используем f-string для вычисления выражения *во время выполнения* воркера
    log_worker('info', f"Метод получения IP: {{'API' if ip_fetch_method == IP_FETCH_API else 'Парсинг лога'}}")
    if ip_fetch_method == IP_FETCH_LOG:
        # Используем двойные фигурные скобки для экранирования внутри f-строки
        log_worker('info', f"Параметры лога: Путь={{log_file_path}}, Строк={{log_read_lines}}")

    # Проверка, есть ли вообще лимиты пользователей
    if not user_limits:
        log_worker('info', "Список лимитов пользователей пуст. Очистка динамических правил TC...")
        tc_manager.clear_dynamic_tc_rules(network_interface)
        log_worker('info', "Работа завершена (нет настроенных лимитов).")
        return

    # 2. Инициализация API клиента
    try:
        # Используем двойные фигурные скобки для экранирования внутри f-строки
        log_worker('debug', f"Попытка инициализации API клиента для {{config['api_url']}}")
        api_client = xui_api.XUIApiClient(
            panel_url=config['api_url'],
            username=config['api_user'],
            password=config['api_pass'],
            log_file_path=log_file_path,  # Передаем параметры лога
            log_read_lines=log_read_lines # в клиент
        )
        log_worker('info', f"API клиент успешно инициализирован.")
    except ConnectionError as e:
        # Используем двойные фигурные скобки для экранирования внутри f-строки
        log_worker('critical', f"Критическая ошибка: Не удалось подключиться/войти в API X-UI: {{e}}")
        log_worker('info', "Очистка динамических правил TC из-за ошибки инициализации API...")
        tc_manager.clear_dynamic_tc_rules(network_interface) # Очищаем правила при ошибке входа
        return # Прерываем цикл, т.к. без API не получить онлайн (если метод API)
    except Exception as e: # Отступ этой строки проверен
        # Используем двойные фигурные скобки для экранирования внутри f-строки
        log_worker('critical', f"!!! Непредвиденная ошибка при инициализации API (Generic Exception): {{e}}")
        # log_worker('critical', "Трейсбек временно отключен для отладки синтаксиса.")
        return # Прерываем цикл

    # 3. Получение онлайн пользователей (нужно для сверки)
    online_users_set = api_client.get_online_users_emails()
    if online_users_set is None:
        log_worker('error', "Не удалось получить список онлайн пользователей из API. Обновление правил отложено.")
        return
    if not online_users_set:
        log_worker('info', "Нет активных онлайн пользователей по данным API. Очистка правил...")
        tc_manager.clear_dynamic_tc_rules(network_interface)
        log_worker('info', "Работа завершена (нет онлайн пользователей).")
        return

    # 4. Определение релевантных пользователей и сбор их IP
    users_with_limits_set = set(user_limits.keys())
    relevant_online_users = online_users_set.intersection(users_with_limits_set)

    if not relevant_online_users:
        log_worker('info', "Нет онлайн пользователей с настроенными лимитами. Очистка правил...")
        tc_manager.clear_dynamic_tc_rules(network_interface)
        log_worker('info', "Работа завершена (нет релевантных онлайн).")
        return

    # Используем двойные фигурные скобки для экранирования внутри f-строки
    log_worker('info', f"Обнаружено {{len(relevant_online_users)}} онлайн пользователей с лимитами: {{', '.join(sorted(list(relevant_online_users)))}}")
    active_ips_to_limit = {{}} # Словарь {{ip: limit_mbps}} # Отступ этой строки проверен
    processed_users_count = 0

    for user_email in relevant_online_users:
        limit = user_limits.get(user_email) # Получаем лимит из загруженного словаря
        if not limit or limit <= 0:
            # Используем двойные фигурные скобки для экранирования внутри f-строки
            log_worker('debug', f"Пропуск пользователя '{{user_email}}' с недействительным лимитом: {{limit}}")
            continue

        # Получаем IP выбранным методом!
        user_ip_list = api_client.get_client_ip_addresses(user_email, method=ip_fetch_method)

        if user_ip_list is None:
            # Используем двойные фигурные скобки для экранирования внутри f-строки
            log_worker('warning', f"Не удалось получить IP для пользователя '{{user_email}}' (метод: {{ip_fetch_method}}). Пропускаем.")
            continue # Пропускаем пользователя, но продолжаем с другими

        if user_ip_list: # Если список не пустой (IP найдены)
            # Используем двойные фигурные скобки для экранирования внутри f-строки
            log_worker('debug', f"Пользователь '{{user_email}}' ({{limit}} Мбит/с) -> IP: {{', '.join(user_ip_list)}} (метод: {{ip_fetch_method}})")
            processed_users_count += 1
            for ip in user_ip_list:
                 if ip in active_ips_to_limit and active_ips_to_limit[ip] != limit:
                     # Используем двойные фигурные скобки для экранирования внутри f-строки
                     log_worker('warning', f"IP {{ip}} используется несколькими пользователями. Лимит будет перезаписан: {{active_ips_to_limit[ip]}} -> {{limit}} (для '{{user_email}}')")
                 active_ips_to_limit[ip] = limit
        else:
            # Используем двойные фигурные скобки для экранирования внутри f-строки
            log_worker('debug', f"IP для пользователя '{{user_email}}' не найдены методом '{{ip_fetch_method}}'.")

    # 5. Применение правил TC
    # Используем двойные фигурные скобки для экранирования внутри f-строки
    log_worker('info', f"Собраны IP для {{processed_users_count}} пользователей. Всего IP для ограничения: {{len(active_ips_to_limit)}}.")
    if active_ips_to_limit:
        applied_count = tc_manager.apply_tc_rules(network_interface, active_ips_to_limit)
        # Используем двойные фигурные скобки для экранирования внутри f-строки
        log_worker('info', f"Применение правил TC завершено. Успешно применено/обновлено правил: {{applied_count}}.")
    else:
        log_worker('info', "Нет активных IP для применения правил. Очистка динамических правил...")
        tc_manager.clear_dynamic_tc_rules(network_interface)

    log_worker('info', "Цикл обновления правил TC завершен.")


# --- Точка входа скрипта воркера ---
if __name__ == "__main__":
    try:
        run_worker_cycle()
    except Exception as e:
        # Используем двойные фигурные скобки для экранирования внутри f-строки
        log_worker('critical', f"Неперехваченное исключение в главном цикле воркера: {{e}}")
        try:
            # Форматируем трейсбек БЕЗ экранирования для f-string
            tb_str = traceback.format_exc()
            # Выводим трейсбек как отдельное сообщение, НЕ используя f-string для него
            log_worker('critical', "Traceback:\\n" + tb_str) # <-- УПРОЩЕННОЕ ЛОГИРОВАНИЕ ТРЕЙСБЕКА
        except Exception:
            log_worker('error', "Не удалось отформатировать трейсбек.")
        sys.exit(1)
    sys.exit(0)
"""  # Конец f-строки worker_code

    # Комментарий теперь на отдельной строке (или его можно просто удалить)
    try:
        # Записываем код в файл воркера
        with open(worker_script_path, 'w', encoding='utf-8') as f:
            f.write(worker_code)
        # Устанавливаем права на исполнение для владельца (744)
        os.chmod(worker_script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        print(f"{common.Color.GREEN}✓ Скрипт воркера сохранен: {worker_script_path}{common.Color.RESET}")
        return True
    except OSError as e:
        print(
            f"{common.Color.RED}[ОШИБКА] Не удалось записать или изменить права для скрипта воркера {worker_script_path}: {e}{common.Color.RESET}")
        return False

# --- Генерация базовой TC настройки (Shell-скрипт) ---

def create_base_tc_script(script_path, iface):
    """Создает shell-скрипт для начальной настройки TC (qdisc, классы)."""
    print(f"{common.Color.CYAN}Генерация скрипта базовой настройки TC ({common.BASE_TC_SCRIPT_NAME})...{common.Color.RESET}")

    # Генерируем команды для создания предопределенных HTB классов
    class_commands = ""
    # Сортируем классы по ID для порядка в скрипте
    for class_id, limit_mbps in sorted(common.PREDEFINED_LIMIT_CLASSES.items()):
         # rate и ceil одинаковые
         class_commands += f"echo '   - Создание класса 1:{class_id} ({limit_mbps} Мбит/с)...'\n"
         # Используем common.TC_PATH
         # Добавляем || true для игнорирования ошибок, если класс уже существует
         class_commands += f"{common.TC_PATH} class add dev $IFACE parent 1:1 classid 1:{class_id} htb rate {limit_mbps}mbit ceil {limit_mbps}mbit || echo '    (Предупреждение: Класс 1:{class_id} уже существует или ошибка создания)'\n"

    # Содержимое shell-скрипта
    # --- ИЗМЕНЕНИЕ: default 30 вместо default 1 ---
    script_content = f"""#!/bin/bash
# Скрипт базовой настройки TC для xraySpeedLimit

IFACE="{iface}"
TC_CMD="{common.TC_PATH}" # Используем путь из common.py

echo "-----------------------------------------------------"
echo "[TC BASE] Настройка базовой структуры TC для: $IFACE"
echo "-----------------------------------------------------"

# Проверка наличия tc
if ! command -v $TC_CMD &> /dev/null; then
    echo "[TC BASE ERROR] Утилита '$TC_CMD' не найдена. Установите iproute2." >&2
    exit 1
fi

# 1. Очистка существующих qdisc (игнорируем ошибки)
echo "[TC BASE] 1. Очистка qdisc root и ingress..."
$TC_CMD qdisc del dev $IFACE root > /dev/null 2>&1
$TC_CMD qdisc del dev $IFACE ingress > /dev/null 2>&1

# 2. Добавляем корневой qdisc HTB (egress)
# --- ИЗМЕНЕНО ЗДЕСЬ: default 30 ---
echo "[TC BASE] 2. Добавление root qdisc HTB (handle 1:, default 30)..."
if ! $TC_CMD qdisc add dev $IFACE root handle 1: htb default 30; then
    echo "[TC BASE ERROR] Не удалось добавить root qdisc HTB." >&2
    exit 1
fi

# 3. Добавляем основной класс 1:1
# Rate/Ceil можно сделать большими, они ограничивают сумму дочерних
# и трафик по умолчанию (default 30 теперь)
main_rate="1000mbit" # Можно сделать настраиваемым позже
echo "[TC BASE] 3. Добавление основного класса 1:1 (rate $main_rate)..."
if ! $TC_CMD class add dev $IFACE parent 1: classid 1:1 htb rate $main_rate ceil $main_rate; then
    echo "[TC BASE ERROR] Не удалось добавить основной класс 1:1." >&2
    $TC_CMD qdisc del dev $IFACE root > /dev/null 2>&1 # Попытка очистки
    exit 1
fi

# 4. Добавляем предопределенные классы скорости
echo "[TC BASE] 4. Добавление предопределенных классов HTB..."
{class_commands}
echo "[TC BASE]    Добавление классов завершено."

# 5. Добавляем qdisc ingress
echo "[TC BASE] 5. Добавление ingress qdisc (handle ffff:)..."
if ! $TC_CMD qdisc add dev $IFACE handle ffff: ingress; then
    echo "[TC BASE ERROR] Не удалось добавить ingress qdisc." >&2
    $TC_CMD qdisc del dev $IFACE root > /dev/null 2>&1 # Попытка очистки
    exit 1
fi

echo "-----------------------------------------------------"
echo "[TC BASE] Базовая настройка TC для $IFACE завершена."
echo "-----------------------------------------------------"
exit 0
"""
    try:
        # Записываем скрипт и делаем его исполняемым (755)
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH) # Права 755
        print(f"{common.Color.GREEN}✓ Скрипт базы TC сохранен: {script_path}{common.Color.RESET}")
        return True
    except OSError as e:
        print(f"{common.Color.RED}[ОШИБКА] Не удалось записать/изменить права для скрипта базы TC {script_path}: {e}{common.Color.RESET}")
        return False

# --- Генерация файлов systemd ---

def create_base_tc_service(service_path, base_tc_script_path):
    """Создает systemd .service файл для запуска скрипта базовой настройки TC."""
    print(f"{common.Color.CYAN}Генерация systemd сервиса базы TC ({common.BASE_TC_SERVICE_NAME})...{common.Color.RESET}")
    # Извлекаем интерфейс из пути скрипта для Description (не очень надежно, но для информации)
    iface_guess = os.path.basename(base_tc_script_path).replace('setup_base_tc_', '').replace('.sh', '')

    service_content = f"""[Unit]
Description=Setup Base TC Structure for xraySpeedLimit on {iface_guess}
Documentation=https://github.com/MKultra6969/xraySpeedLimit
# Запускается после сети
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=oneshot
# Запускаем наш bash-скрипт
ExecStart=/bin/bash {base_tc_script_path}
StandardOutput=journal+console
StandardError=journal+console
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
    try:
        with open(service_path, 'w', encoding='utf-8') as f:
            f.write(service_content)
        # Права для systemd файлов обычно 644 (rw-r--r--)
        os.chmod(service_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        print(f"{common.Color.GREEN}✓ systemd сервис базы TC сохранен: {service_path}{common.Color.RESET}")
        return True
    except OSError as e:
        print(f"{common.Color.RED}[ОШИБКА] Не удалось записать systemd сервис базы TC {service_path}: {e}{common.Color.RESET}")
        return False

def create_worker_service_files(timer_path, service_path, worker_script_path):
    """Создает systemd .timer и .service файлы для периодического запуска воркера."""
    print(f"{common.Color.CYAN}Генерация systemd файлов воркера ({common.WORKER_SERVICE_NAME}, {common.WORKER_TIMER_NAME})...{common.Color.RESET}")

    # --- Таймер ---
    timer_content = f"""[Unit]
Description=Run xraySpeedLimit Worker periodically
Documentation=https://github.com/MKultra6969/xraySpeedLimit
# Таймер зависит от сервиса, который он запускает
Requires={common.WORKER_SERVICE_NAME}

[Timer]
# Запуск через 1 минуту после загрузки и каждые 60 сек после активации
OnBootSec=1min
OnUnitActiveSec=60s
RandomizedDelaySec=10s # Небольшая рандомизация
AccuracySec=1s
Unit={common.WORKER_SERVICE_NAME}

[Install]
WantedBy=timers.target
"""

    # --- Сервис Воркера ---
    service_content = f"""[Unit]
Description=xraySpeedLimit Worker (Updates TC rules via X-UI API)
Documentation=https://github.com/MKultra6969/xraySpeedLimit
# Запускается после базовой настройки TC и сети
After=network-online.target {common.BASE_TC_SERVICE_NAME}
Wants=network-online.target
Requires={common.BASE_TC_SERVICE_NAME}

[Service]
Type=simple
# Используем /usr/bin/env для поиска python3
ExecStart=/usr/bin/env python3 {worker_script_path}
User=root
Group=root
# Перезапуск при сбое
Restart=on-failure
RestartSec=30s
# Логирование в journald
StandardOutput=journal+console
StandardError=journal+console
# Установим таймаут на запуск/остановку, если воркер зависнет
TimeoutStartSec=120s
TimeoutStopSec=30s

[Install]
# Явно не требуется, т.к. запускается таймером, но оставим
WantedBy=multi-user.target
"""
    try:
        # Записываем таймер
        with open(timer_path, 'w', encoding='utf-8') as f:
            f.write(timer_content)
        os.chmod(timer_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH) # 644
        print(f"{common.Color.GREEN}✓ Файл таймера воркера сохранен: {timer_path}{common.Color.RESET}")

        # Записываем сервис
        with open(service_path, 'w', encoding='utf-8') as f:
            f.write(service_content)
        os.chmod(service_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH) # 644
        print(f"{common.Color.GREEN}✓ Файл сервиса воркера сохранен: {service_path}{common.Color.RESET}")
        return True

    except OSError as e:
        print(f"{common.Color.RED}[ОШИБКА] Не удалось записать systemd файлы воркера: {e}{common.Color.RESET}")
        return False

# --- Генерация файлов для старого режима (лимиты портов) ---

def create_port_limit_script(iface, port, limit, script_path):
    """Создает bash-скрипт для старого режима лимитов (порт/интерфейс)."""
    print(f"{common.Color.CYAN}[PORT LIMIT] Генерация скрипта: {os.path.basename(script_path)}...{common.Color.RESET}")
    limit_str = str(limit)
    # Используем common.TC_PATH
    # ИСПРАВЛЕНО: Заменены {LIMIT} и ${LIMIT} на $LIMIT (ссылка на bash переменную)
    content = f"""#!/bin/bash
# Generated by MK_XSL.py (Port Limit Mode) | MKultra69
IFACE="{iface}"
PORT="{port}"
LIMIT="{limit_str}" # Определяем переменную LIMIT в bash
TC_CMD="{common.TC_PATH}"

echo "[PORT LIMIT SCRIPT] Applying $LIMIT""mb limit to port $PORT on $IFACE..." # Используем $LIMIT

# Clean existing qdiscs
$TC_CMD qdisc del dev $IFACE root > /dev/null 2>&1
$TC_CMD qdisc del dev $IFACE ingress > /dev/null 2>&1

# Setup HTB for Egress (Upload)
echo "[PORT LIMIT SCRIPT] Setting up HTB..."
$TC_CMD qdisc add dev $IFACE root handle 1: htb default 30 || exit 1
# Main class (high rate)
$TC_CMD class add dev $IFACE parent 1: classid 1:1 htb rate 1000mbit ceil 1000mbit || exit 1
# Limit class for the target port (upload)
$TC_CMD class add dev $IFACE parent 1:1 classid 1:10 htb rate $LIMIT""mbit ceil $LIMIT""mbit || exit 1 # Используем $LIMIT
# Filter traffic to the limit class based on source port
$TC_CMD filter add dev $IFACE protocol ip parent 1:0 prio 1 u32 match ip sport $PORT 0xffff flowid 1:10 || exit 1

# Setup Ingress policing for Download
echo "[PORT LIMIT SCRIPT] Setting up Ingress policing..."
$TC_CMD qdisc add dev $IFACE handle ffff: ingress || exit 1
# Police traffic based on destination port (download)
$TC_CMD filter add dev $IFACE parent ffff: protocol ip prio 1 u32 match ip dport $PORT 0xffff police rate $LIMIT""mbit burst 10k drop flowid :1 || exit 1 # Используем $LIMIT

echo "[PORT LIMIT SCRIPT] Limit applied successfully."
exit 0
"""
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        # Права 755 (rwxr-xr-x)
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        print(f"{common.Color.GREEN}✓ Скрипт лимита порта сохранен: {script_path}{common.Color.RESET}")
        return True
    except OSError as e:
        print(f"{common.Color.RED}[ОШИБКА] Запись скрипта лимита порта {script_path}: {e}{common.Color.RESET}")
        return False

def create_port_limit_service(limit, script_path, service_path, iface):
    """Создает systemd .service файл для старого режима лимитов."""
    print(f"{common.Color.CYAN}[PORT LIMIT] Генерация сервиса: {os.path.basename(service_path)}...{common.Color.RESET}")
    # Используем common.TC_PATH в ExecStop
    content = f"""[Unit]
Description=xraySpeedLimit Port Limit Service ({limit}mb)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash {script_path}
# Clean up rules on stop
ExecStop={common.TC_PATH} qdisc del dev {iface} root || true
ExecStop={common.TC_PATH} qdisc del dev {iface} ingress || true
RemainAfterExit=yes
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=multi-user.target
# MKultra69 - Port Limit Mode
"""
    try:
        with open(service_path, 'w', encoding='utf-8') as f:
            f.write(content)
        # Права 644 (rw-r--r--)
        os.chmod(service_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        print(f"{common.Color.GREEN}✓ Сервис лимита порта сохранен: {service_path}{common.Color.RESET}")
        return True
    except OSError as e:
        print(f"{common.Color.RED}[ОШИБКА] Запись сервиса лимита порта {service_path}: {e}{common.Color.RESET}")
        return False