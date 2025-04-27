#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xraySpeedLimit Utility Menu (User & Port Modes)
Made by MKultra69
https://github.com/MKultra6969
"""
import os
import sys
import time
import re


# --- Импорт наших модулей ---
try:
    # Порядок импорта важен, common должен быть первым
    import common
    import config_manager
    import system_utils
    import xui_api
    import tc_manager
    import generators
    import faq
    from xui_api import IP_FETCH_API, IP_FETCH_LOG
except ImportError as e:
    # Выводим ошибку без использования common.Color, т.к. он мог не импортироваться
    print(f"\033[91mОшибка: Не удалось импортировать модуль: {e}\033[0m")
    print("Убедитесь, что все файлы (.py): common.py, config_manager.py, system_utils.py, xui_api.py, tc_manager.py, generators.py, faq.py")
    print("находятся в той же директории, что и MK_XSL.py")
    sys.exit(1)

# --- Проверка и импорт requests ---
try:
    import requests
except ImportError:
    print(f"{common.Color.RED}Ошибка: Библиотека 'requests' не найдена.{common.Color.RESET}")
    print("Пожалуйста, установите ее: pip install requests")
    sys.exit(1)

ASCII_LOGO = fr"""
{common.Color.DIM}#  ______  ______  ______  ______  ______  ______  ______  ______  ______  ______  ______  ______ {common.Color.RESET}
{common.Color.DIM}# | |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| |{common.Color.RESET}
{common.Color.DIM}# |  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  |{common.Color.RESET}
{common.Color.DIM}# |______||______||______||______||______||______||______||______||______||______||______||______|{common.Color.RESET}
{common.Color.MAGENTA}#  ______ {common.Color.RESET}...██████...██████.█████...████...........█████.█████..█████████..█████.........{common.Color.MAGENTA} ______ {common.Color.RESET}
{common.Color.MAGENTA}# | |__| |{common.Color.RESET}..░░██████.██████.░░███...███░...........░░███.░░███..███░░░░░███░░███..........{common.Color.MAGENTA}| |__| |{common.Color.RESET}
{common.Color.MAGENTA}# |  ()  |{common.Color.RESET}...░███░█████░███..░███..███..............░░███.███..░███....░░░..░███..........{common.Color.MAGENTA}|  ()  |{common.Color.RESET}
{common.Color.MAGENTA}# |______|{common.Color.RESET}...░███░░███.░███..░███████................░░█████...░░█████████..░███..........{common.Color.MAGENTA}|______|{common.Color.RESET}
{common.Color.MAGENTA}#  ______ {common.Color.RESET}...░███.░░░..░███..░███░░███................███░███...░░░░░░░░███.░███..........{common.Color.MAGENTA} ______ {common.Color.RESET}
{common.Color.MAGENTA}# | |__| |{common.Color.RESET}...░███......░███..░███.░░███..............███.░░███..███....░███.░███......█...{common.Color.MAGENTA}| |__| |{common.Color.RESET}
{common.Color.MAGENTA}# |  ()  |{common.Color.RESET}...█████.....█████.█████.░░████.█████████.█████.█████░░█████████..███████████...{common.Color.MAGENTA}|  ()  |{common.Color.RESET}
{common.Color.MAGENTA}# |______|{common.Color.RESET}..░░░░░.....░░░░░.░░░░░...░░░░.░░░░░░░░░.░░░░░.░░░░░..░░░░░░░░░..░░░░░░░░░░░....{common.Color.MAGENTA}|______|{common.Color.RESET}
{common.Color.DIM}#  ______  ______  ______  ______  ______  ______  ______  ______  ______  ______  ______  ______ {common.Color.RESET}
{common.Color.DIM}# | |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| || |__| |{common.Color.RESET}
{common.Color.DIM}# |  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  ||  ()  |{common.Color.RESET}
{common.Color.DIM}# |______||______||______||______||______||______||______||______||______||______||______||______|{common.Color.RESET}
"""

# === Функции для режима "Лимиты Пользователей (API)" ===

def configure_api_menu():
    """Отображает меню настройки API, Интерфейса и Метода получения IP."""
    common.clear_screen()
    common.print_header("Настройка API, Интерфейса и Метода IP (Режим Пользователей)")
    config = config_manager.load_config()

    current_ip_method = config.get('ip_fetch_method', IP_FETCH_API)

    print("Текущие настройки:")
    print(f"  URL панели: {config.get('api_url', f'{common.Color.YELLOW}Не задан{common.Color.RESET}')}")
    print(f"  Логин API:  {config.get('api_user', f'{common.Color.YELLOW}Не задан{common.Color.RESET}')}")
    print(f"  Пароль API: {common.Color.GREEN}********{common.Color.RESET}" if config.get("api_pass") else f"{common.Color.YELLOW}Не задан{common.Color.RESET}")
    print(f"  Интерфейс:  {config.get('iface', f'{common.Color.YELLOW}Не задан{common.Color.RESET}')}")
    # Отображаем текущий метод получения IP
    method_display = "API (рекомендовано)" if current_ip_method == IP_FETCH_API else "Парсинг лога (fallback)"
    print(f"  Метод IP:   {common.Color.CYAN}{method_display}{common.Color.RESET}")
    common.print_separator("-")

    import getpass # Импортируем здесь, т.к. нужен только тут
    new_url = input(f"Новый URL панели X-UI (Enter - оставить '{config.get('api_url', '')}'): ").strip()
    new_user = input(f"Новый логин API (Enter - оставить '{config.get('api_user', '')}'): ").strip()
    new_pass_prompt = f"Новый пароль API ({common.Color.GREEN}Enter - оставить текущий{common.Color.RESET}): "
    try:
        new_pass = getpass.getpass(prompt=new_pass_prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nВвод пароля прерван.")
        new_pass = None

    interfaces = system_utils.get_network_interfaces()
    selected_iface = config.get('iface', None)
    new_iface = selected_iface

    if interfaces:
        print(f"\n{common.Color.BOLD}Доступные активные сетевые интерфейсы:{common.Color.RESET}")
        for i, iface_name in enumerate(interfaces):
            current_marker = f" {common.Color.GREEN}<- текущий{common.Color.RESET}" if iface_name == selected_iface else ""
            print(f"  {common.Color.CYAN}{i + 1}.{common.Color.RESET} {iface_name}{current_marker}")
        common.print_separator("-")
        while True:
            prompt = f"Выберите номер интерфейса (Enter - оставить '{selected_iface or 'не выбран'}'): "
            choice = input(prompt).strip()
            if not choice and selected_iface: break
            elif not choice and not selected_iface: print(f"{common.Color.RED}Выберите интерфейс.{common.Color.RESET}"); continue
            try:
                choice_int = int(choice)
                if 1 <= choice_int <= len(interfaces): new_iface = interfaces[choice_int - 1]; break
                else: print(f"{common.Color.RED}Неверный номер.{common.Color.RESET}")
            except ValueError: print(f"{common.Color.RED}Введите число.{common.Color.RESET}")
    elif not selected_iface:
        print(f"{common.Color.RED}Не удалось найти интерфейсы!{common.Color.RESET}")
        common.pause(); return
    # --- Конец выбора интерфейса ---

    # --- Выбор метода получения IP ---
    common.print_separator("-")
    print(f"\n{common.Color.BOLD}Выберите метод получения IP адресов клиентов:{common.Color.RESET}")
    print(f"  {common.Color.CYAN}1.{common.Color.RESET} Через API панели X-UI ({common.Color.GREEN}Рекомендуется{common.Color.RESET})")
    print(f"  {common.Color.CYAN}2.{common.Color.RESET} Парсинг access.log ({common.Color.YELLOW}Fallback, если API не работает{common.Color.RESET})")
    current_method_choice = '1' if current_ip_method == IP_FETCH_API else '2'
    new_ip_method = current_ip_method # По умолчанию оставляем текущий
    while True:
        ip_choice = input(f"Ваш выбор [1-2] (Enter - оставить '{method_display}'): ").strip()
        if not ip_choice:
            break # Оставляем текущий
        if ip_choice == '1':
            new_ip_method = IP_FETCH_API
            break
        elif ip_choice == '2':
            new_ip_method = IP_FETCH_LOG
            break
        else:
            print(f"{common.Color.RED}Неверный выбор. Введите 1 или 2.{common.Color.RESET}")

    # --- Конец выбора метода IP ---
    config_changed = False
    if new_url: config['api_url'] = new_url.rstrip('/'); config_changed = True
    if new_user: config['api_user'] = new_user; config_changed = True
    if new_pass is not None and new_pass: config['api_pass'] = new_pass; config_changed = True
    if new_iface and new_iface != selected_iface: config['iface'] = new_iface; config_changed = True
    # Проверяем изменение метода IP
    if new_ip_method != current_ip_method:
        config['ip_fetch_method'] = new_ip_method
        config_changed = True
        # Добавляем уведомление о необходимости переустановки службы
        print(f"\n{common.Color.YELLOW}ВНИМАНИЕ: Метод получения IP изменен.{common.Color.RESET}")
        print(f"{common.Color.YELLOW}Чтобы изменения вступили в силу, необходимо {common.Color.BOLD}переустановить службу{common.Color.RESET}{common.Color.YELLOW} (опция 3 в предыдущем меню).{common.Color.RESET}")


    # Проверяем, все ли обязательные параметры заданы (URL, user, pass, iface)
    # Параметр ip_fetch_method не является строго обязательным, т.к. есть дефолт
    required_api_keys = ["api_url", "api_user", "api_pass", "iface"]
    missing_keys = [k for k in required_api_keys if not config.get(k)]

    if missing_keys:
         print(f"\n{common.Color.YELLOW}Внимание: Не все основные параметры заданы: {', '.join(missing_keys)}.{common.Color.RESET}")
         save_anyway = input("Сохранить конфигурацию как есть? (да/нет): ").strip().lower()
         if save_anyway.startswith('д') or save_anyway.startswith('y'):
             if config_manager.save_config(config):
                 print(f"{common.Color.GREEN}✓ Конфигурация сохранена (возможно, неполная).{common.Color.RESET}")
         else:
             print("Изменения не сохранены.")
    elif config_changed:
        if config_manager.save_config(config):
            print(f"\n{common.Color.GREEN}✓ Конфигурация успешно сохранена.{common.Color.RESET}")
    else:
        print("\nИзменений не было.")
    common.pause()

def manage_user_limits_menu():
    """Отображает меню управления лимитами пользователей (API)."""
    while True:
        common.clear_screen()
        common.print_header("Управление Лимитами Пользователей (API)")
        limits = config_manager.load_user_limits()

        if not limits:
            print(f"{common.Color.YELLOW}Лимиты пользователей не настроены.{common.Color.RESET}")
        else:
            print(f"{common.Color.BOLD}Email/Тег                  Лимит (Мбит/с){common.Color.RESET}")
            common.print_separator("-")
            sorted_users = sorted(limits.keys())
            for user in sorted_users: print(f" {common.Color.WHITE}{user:<28}{common.Color.RESET} {common.Color.CYAN}{limits[user]}{common.Color.RESET}")
            common.print_separator("-")

        print(f"Действия: [{common.Color.GREEN}A{common.Color.RESET}] Добавить/Изменить, [{common.Color.RED}D{common.Color.RESET}] Удалить, [{common.Color.BLUE}N{common.Color.RESET}] Назад")
        common.print_separator("-"); choice = input("Действие: ").strip().upper()

        if choice == 'N': return
        elif choice == 'A':
            email = input("Email/Тег пользователя: ").strip()
            if not email: print(f"{common.Color.RED}Email/Тег не может быть пустым.{common.Color.RESET}"); time.sleep(1.5); continue
            while True:
                limit_str = input(f"Лимит для '{email}' Мбит/с (1-1000, 0=удалить): ").strip()
                if limit_str.isdigit():
                    limit = int(limit_str)
                    if 0 <= limit <= 1000: break
                    else: print(f"{common.Color.RED}Неверный лимит (0-1000).{common.Color.RESET}")
                else: print(f"{common.Color.RED}Введите целое число.{common.Color.RESET}")

            if limit == 0:
                 if email in limits:
                     del limits[email]
                     # Сообщение об удалении будет выведено после сохранения
                 else: print(f"{common.Color.YELLOW}Пользователь '{email}' не найден.{common.Color.RESET}"); time.sleep(1.5); continue
            else: limits[email] = limit

            if config_manager.save_user_limits(limits):
                 if limit == 0:
                     print(f"{common.Color.YELLOW}Лимит для '{email}' удален из списка.{common.Color.RESET}")
                 else:
                     print(f"{common.Color.GREEN}Список лимитов обновлен. Лимит для '{email}' = {limit} Мбит/с.{common.Color.RESET}")
            time.sleep(1.5)

        elif choice == 'D':
            email = input("Email/Тег пользователя для удаления лимита: ").strip()
            if email in limits:
                 del limits[email]
                 if config_manager.save_user_limits(limits): print(f"{common.Color.GREEN}Лимит для '{email}' удален.{common.Color.RESET}")
            else: print(f"{common.Color.YELLOW}Пользователь '{email}' не найден.{common.Color.RESET}")
            time.sleep(1.5)
        else: print(f"{common.Color.RED}Неверное действие '{choice}'.{common.Color.RESET}"); time.sleep(1.5)

def install_user_worker_service():
    """Установка/переустановка службы для лимитов пользователей (API)."""
    common.clear_screen()
    common.print_header("Установка Службы Лимитов Пользователей (API)")
    config = config_manager.load_config()
    if not config or not all(k in config for k in ["api_url", "api_user", "api_pass", "iface"]):
        print(f"{common.Color.RED}Ошибка: Конфигурация API неполная.{common.Color.RESET}")
        print(f"{common.Color.YELLOW}Настройте API в пункте 1 этого меню.{common.Color.RESET}")
        common.pause(); return
    iface = config['iface']
    print(f"Интерфейс: {common.Color.WHITE}{iface}{common.Color.RESET}, API: {common.Color.WHITE}{config['api_url']}{common.Color.RESET}")
    common.print_separator("-")
    confirm = input(f"Начать установку/переустановку службы? (да/нет): ").strip().lower()
    if not (confirm.startswith('д') or confirm.startswith('y')): print(f"\n{common.Color.YELLOW}Отмена.{common.Color.RESET}"); common.pause(); return
    common.print_separator("-")
    print(f"{common.Color.CYAN}1: Создание директорий...{common.Color.RESET}")
    if not config_manager.ensure_config_dir(): common.pause(); return
    try:
        if not os.path.exists(common.SCRIPT_DIR): os.makedirs(common.SCRIPT_DIR, mode=0o755)
        if not os.path.exists(common.SERVICE_DIR): os.makedirs(common.SERVICE_DIR, mode=0o755)
    except OSError as e: print(f"{common.Color.RED}Ошибка создания директорий: {e}{common.Color.RESET}"); common.pause(); return
    print(f"{common.Color.GREEN}✓ OK.{common.Color.RESET}")
    print(f"\n{common.Color.CYAN}2: Генерация файлов...{common.Color.RESET}")
    if not generators.create_base_tc_script(common.BASE_TC_SCRIPT_PATH, iface): common.pause(); return
    if not generators.create_base_tc_service(common.BASE_TC_SERVICE_PATH, common.BASE_TC_SCRIPT_PATH): common.pause(); return
    if not generators.create_worker_script(common.WORKER_SCRIPT_PATH, common.CONFIG_FILE, common.USER_LIMITS_FILE): common.pause(); return
    if not generators.create_worker_service_files(common.WORKER_TIMER_PATH, common.WORKER_SERVICE_PATH, common.WORKER_SCRIPT_PATH): common.pause(); return
    print(f"\n{common.Color.CYAN}3: Systemd reload...{common.Color.RESET}")
    if not system_utils.run_command(['systemctl', 'daemon-reload'], check=True, success_msg="OK"): common.pause(); return
    print(f"\n{common.Color.CYAN}4: Запуск базы TC...{common.Color.RESET}")
    if system_utils.manage_service("enable", common.BASE_TC_SERVICE_NAME, check_status=False):
        if not system_utils.manage_service("restart", common.BASE_TC_SERVICE_NAME): print(f"{common.Color.YELLOW}WARN: Не удалось запустить {common.BASE_TC_SERVICE_NAME}.{common.Color.RESET}")
    else: print(f"{common.Color.RED}Не удалось включить {common.BASE_TC_SERVICE_NAME}.{common.Color.RESET}"); common.pause(); return
    print(f"\n{common.Color.CYAN}5: Запуск таймера воркера...{common.Color.RESET}")
    system_utils.manage_service("stop", common.WORKER_TIMER_NAME, check_status=False, quiet=True)
    if system_utils.manage_service("enable", common.WORKER_TIMER_NAME, check_status=True):
        if system_utils.manage_service("restart", common.WORKER_TIMER_NAME, check_status=True):
            common.print_separator("-"); print(f"{common.Color.GREEN}{common.Color.BOLD}УСПЕХ!{common.Color.RESET} Служба установлена и запущена.")
            print(f"Ограничения для пользователей будут применяться на интерфейсе '{iface}'.")
            print(f"\nПолезные команды:")
            print(f" Таймер: {common.Color.DIM}systemctl status {common.WORKER_TIMER_NAME}{common.Color.RESET}")
            print(f" Воркер: {common.Color.DIM}systemctl status {common.WORKER_SERVICE_NAME}{common.Color.RESET}")
            print(f" Логи:   {common.Color.DIM}journalctl -u {common.WORKER_SERVICE_NAME} -f{common.Color.RESET}")
        else: print(f"{common.Color.RED}{common.Color.BOLD}ОШИБКА:{common.Color.RESET}{common.Color.RED} Не удалось перезапустить таймер.{common.Color.RESET}")
    else: print(f"{common.Color.RED}{common.Color.BOLD}ОШИБКА:{common.Color.RESET}{common.Color.RED} Не удалось включить таймер.{common.Color.RESET}")
    common.pause()

def uninstall_user_worker_service():
    """Удаление службы для лимитов пользователей (API)."""
    common.clear_screen(); common.print_header("Удаление Службы Лимитов Пользователей (API)")
    print(f"{common.Color.YELLOW}{common.Color.BOLD}ВНИМАНИЕ!{common.Color.RESET}")
    print(f"Удалит службы: {common.WORKER_TIMER_NAME}, {common.WORKER_SERVICE_NAME}, {common.BASE_TC_SERVICE_NAME}")
    print(f"Удалит скрипты: {common.WORKER_SCRIPT_PATH}, {common.BASE_TC_SCRIPT_PATH}")
    print(f"{common.Color.DIM}Конфигурационные файлы ({common.CONFIG_DIR}) НЕ будут удалены.{common.Color.RESET}")
    confirm = input(f"\nПодтвердить удаление? ({common.Color.GREEN}да{common.Color.RESET}/{common.Color.RED}нет{common.Color.RESET}): ").strip().lower()
    if not (confirm.startswith('д') or confirm.startswith('y')): print(f"\n{common.Color.YELLOW}Отмена.{common.Color.RESET}"); common.pause(); return
    common.print_separator("-"); errors = []
    print(f"{common.Color.CYAN}1: Остановка и отключение служб...{common.Color.RESET}")
    services_to_manage = [common.WORKER_TIMER_NAME, common.WORKER_SERVICE_NAME, common.BASE_TC_SERVICE_NAME]
    for service in services_to_manage:
        service_path = os.path.join(common.SERVICE_DIR, service)
        if os.path.exists(service_path):
             print(f"  - {service}...")
             system_utils.manage_service("stop", service, check_status=False, quiet=True)
             if not system_utils.manage_service("disable", service, check_status=False, quiet=True): errors.append(f"disable {service}")
    print(f"\n{common.Color.CYAN}2: Удаление файлов...{common.Color.RESET}")
    files_to_remove = [common.WORKER_TIMER_PATH, common.WORKER_SERVICE_PATH, common.BASE_TC_SERVICE_PATH, common.WORKER_SCRIPT_PATH, common.BASE_TC_SCRIPT_PATH]
    removed_count = 0
    for f_path in files_to_remove:
        if os.path.exists(f_path):
            try: os.remove(f_path); removed_count += 1; print(f"  - rm: {f_path}")
            except OSError as e: errors.append(f"rm {f_path}: {e}"); print(f"{common.Color.RED}  - ERR rm: {f_path}: {e}{common.Color.RESET}")
    if removed_count > 0:
        print(f"\n{common.Color.CYAN}3: Systemd reload...{common.Color.RESET}")
        if not system_utils.run_command(['systemctl', 'daemon-reload'], check=True, success_msg="OK"): errors.append("daemon-reload")
    common.print_separator("-")
    if not errors: print(f"{common.Color.GREEN}{common.Color.BOLD}Удаление завершено.{common.Color.RESET}")
    else:
        print(f"{common.Color.RED}{common.Color.BOLD}Удаление с ошибками:{common.Color.RESET}")
        for err in errors: print(f"{common.Color.RED}- {err}{common.Color.RESET}")
    common.pause()

# === Функции для режима "Лимиты Портов (Старый режим)" ===

def find_port_limits():
    """Ищет существующие лимиты портов по именам файлов."""
    limits = set()
    pattern = common.PORT_LIMIT_FILENAME_PATTERN # Используем шаблон из common
    try:
        if os.path.isdir(common.SERVICE_DIR):
            for filename in os.listdir(common.SERVICE_DIR):
                match = pattern.match(filename)
                if match and match.group(2) == 'service': limits.add(int(match.group(1)))
    except OSError as e: pass # Игнорируем ошибки доступа
    try:
        if os.path.isdir(common.SCRIPT_DIR):
             for filename in os.listdir(common.SCRIPT_DIR):
                match = pattern.match(filename)
                if match and match.group(2) == 'sh': limits.add(int(match.group(1)))
    except OSError as e: pass # Игнорируем ошибки доступа
    return sorted(list(limits))

def disable_and_remove_port_service(limit):
    """Останавливает, отключает и удаляет сервис и скрипт для лимита порта."""
    limit_int = int(limit)
    service_name = f"xraySpeedLimit{limit_int}mb.service"
    script_name = f"xraySpeedLimit{limit_int}mb.sh"
    service_path = os.path.join(common.SERVICE_DIR, service_name)
    script_path = os.path.join(common.SCRIPT_DIR, script_name)
    removed_files = False
    errors = []
    iface_for_stop = "unknown"

    # Остановка сервиса или ручная очистка правил
    if os.path.exists(service_path):
        print(f"{common.Color.DIM}  Остановка сервиса {service_name}...{common.Color.RESET}")
        try: # Пытаемся извлечь интерфейс из сервиса
             with open(service_path, 'r') as f: service_content = f.read()
             # Улучшенный поиск интерфейса в ExecStop
             match = re.search(r'ExecStop=.*?del dev\s+(\S+)', service_content)
             if match: iface_for_stop = match.group(1)
        except Exception: pass
        system_utils.manage_service("stop", service_name, check_status=False, quiet=True)
    elif os.path.exists(script_path):
         print(f"{common.Color.DIM}  Сервис не найден, попытка очистки правил из скрипта {script_name}...{common.Color.RESET}")
         try: # Пытаемся извлечь интерфейс из скрипта
             with open(script_path, 'r') as f: script_content = f.read()
             match_iface = re.search(r'^IFACE="?([^"\s]+)"?', script_content, re.MULTILINE)
             if match_iface:
                 iface_for_stop = match_iface.group(1)
                 print(f"{common.Color.DIM}    Найден интерфейс: {iface_for_stop}. Выполняю tc qdisc del...{common.Color.RESET}")
                 # Используем TC_PATH из common для консистентности
                 system_utils.run_command([common.TC_PATH, 'qdisc', 'del', 'dev', iface_for_stop, 'root'], check=False, show_error=False)
                 system_utils.run_command([common.TC_PATH, 'qdisc', 'del', 'dev', iface_for_stop, 'ingress'], check=False, show_error=False)
             else: print(f"{common.Color.YELLOW}    Не удалось определить интерфейс из скрипта.{common.Color.RESET}")
         except Exception as e: print(f"{common.Color.YELLOW}    Ошибка чтения скрипта для очистки: {e}{common.Color.RESET}")

    # Отключение сервиса
    if os.path.exists(service_path):
        print(f"{common.Color.DIM}  Отключение автозапуска {service_name}...{common.Color.RESET}")
        if not system_utils.manage_service("disable", service_name, check_status=False, quiet=True): errors.append(f"disable {service_name}")

    # Удаление файлов
    files_to_remove = {service_path: "сервис", script_path: "скрипт"}
    for f_path, f_type in files_to_remove.items():
        if os.path.exists(f_path):
            print(f"{common.Color.DIM}  Удаление файла ({f_type}): {f_path}...{common.Color.RESET}")
            try: os.remove(f_path); removed_files = True
            except OSError as e: errors.append(f"remove {f_path}: {e}"); print(f"{common.Color.RED}    Ошибка удаления: {e}{common.Color.RESET}")

    # Перезагрузка systemd
    if removed_files:
        print(f"{common.Color.DIM}  Перезагрузка systemd...{common.Color.RESET}")
        if not system_utils.run_command(['systemctl', 'daemon-reload'], check=True, show_error=False, success_msg=None): errors.append("daemon-reload")

    # Итог
    if not removed_files and not os.path.exists(service_path) and not os.path.exists(script_path) and not errors:
        print(f"{common.Color.YELLOW}Лимит {limit_int}mb не найден (файлы отсутствуют).{common.Color.RESET}")
    elif errors:
         print(f"{common.Color.RED}{common.Color.BOLD}Удаление {limit_int}mb завершено с ошибками:{common.Color.RESET}")
         for error in errors: print(f"{common.Color.RED}- {error}{common.Color.RESET}")
    else: print(f"{common.Color.GREEN}{common.Color.BOLD}Лимит {limit_int}mb успешно удален.{common.Color.RESET}")
    return not errors

def install_port_limit_menu():
    """Меню для установки лимита порта (старый режим)."""
    common.clear_screen(); common.print_header("Установка Лимита Порта (Старый режим)")
    interfaces = system_utils.get_network_interfaces()
    if not interfaces: print(f"{common.Color.YELLOW}Активные интерфейсы не найдены.{common.Color.RESET}"); common.pause(); return
    print(f"{common.Color.BOLD}Доступные интерфейсы:{common.Color.RESET}")
    for i, iface_name in enumerate(interfaces): print(f"  {common.Color.CYAN}{i + 1}.{common.Color.RESET} {iface_name}")
    common.print_separator("-")
    while True:
        try: choice = input(f"Номер интерфейса [1-{len(interfaces)}]: "); iface = interfaces[int(choice) - 1]; break
        except (ValueError, IndexError): print(f"{common.Color.RED}Неверный номер.{common.Color.RESET}")
    while True:
        port_str = input("Порт для ограничения (1-65535): ").strip()
        if port_str.isdigit() and 1 <= int(port_str) <= 65535: port = int(port_str); break
        else: print(f"{common.Color.RED}Неверный порт.{common.Color.RESET}")
    while True:
        limit_str = input("Лимит скорости Мбит/с (1-1000): ").strip()
        if limit_str.isdigit() and 1 <= int(limit_str) <= 1000: limit = int(limit_str); break
        else: print(f"{common.Color.RED}Неверный лимит.{common.Color.RESET}")

    script_name = f"xraySpeedLimit{limit}mb.sh"; service_name = f"xraySpeedLimit{limit}mb.service"
    script_path = os.path.join(common.SCRIPT_DIR, script_name); service_path = os.path.join(common.SERVICE_DIR, service_name)
    common.print_separator("-"); print(f"Установка: {limit}Мбит/с порт {port} на {iface}")

    if os.path.exists(service_path) or os.path.exists(script_path):
         print(f"{common.Color.YELLOW}{common.Color.BOLD}ВНИМАНИЕ!{common.Color.RESET}{common.Color.YELLOW} Лимит {limit}mb уже существует.{common.Color.RESET}")
         overwrite = input(f"Перезаписать? (да/нет): ").strip().lower()
         if overwrite.startswith('д') or overwrite.startswith('y'):
             print(f"\n{common.Color.MAGENTA}--- Перезапись {limit}mb ---{common.Color.RESET}")
             disable_and_remove_port_service(limit)
             print(f"{common.Color.MAGENTA}--- Установка ---{common.Color.RESET}")
         else: print(f"\n{common.Color.YELLOW}Установка отменена.{common.Color.RESET}"); common.pause(); return

    if generators.create_port_limit_script(iface, port, limit, script_path):
        if generators.create_port_limit_service(limit, script_path, service_path, iface):
            if system_utils.run_command(['systemctl', 'daemon-reload'], check=True, success_msg="OK"):
                if system_utils.manage_service("enable", service_name):
                    if system_utils.manage_service("restart", service_name):
                         common.print_separator("-"); print(f"{common.Color.GREEN}{common.Color.BOLD}УСПЕХ!{common.Color.RESET} Лимит {limit}Мбит/с установлен."); print(f"{common.Color.DIM}Сервис: {service_name}{common.Color.RESET}")
                    else: print(f"{common.Color.RED}{common.Color.BOLD}ОШИБКА:{common.Color.RESET}{common.Color.RED} Не удалось перезапустить сервис.{common.Color.RESET}")
                else: print(f"{common.Color.RED}{common.Color.BOLD}ОШИБКА:{common.Color.RESET}{common.Color.RED} Не удалось включить сервис.{common.Color.RESET}")
    common.pause()

def get_port_service_status(service_name):
    """Проверяет статус сервиса лимита порта."""
    service_path = os.path.join(common.SERVICE_DIR, service_name)
    if not os.path.exists(service_path): return {"exists": False, "active": False, "enabled": False}
    is_active = system_utils.manage_service('is-active', service_name, quiet=True)
    is_enabled = system_utils.manage_service('is-enabled', service_name, quiet=True)
    return {"exists": True, "active": is_active, "enabled": is_enabled}

def manage_port_limits_menu():
    """Меню для управления лимитами портов."""
    while True:
        common.clear_screen(); common.print_header("Управление Лимитами Портов (Старый)")
        limits = find_port_limits()
        if not limits: print(f"{common.Color.YELLOW}Активные лимиты портов не найдены.{common.Color.RESET}"); common.pause(); return

        print(f"{common.Color.BOLD}№  Лимит          Статус Автозапуска   Статус Работы{common.Color.RESET}"); common.print_separator("-")
        limit_details = []
        for i, limit in enumerate(limits):
            service_name = f"xraySpeedLimit{limit}mb.service"; status = get_port_service_status(service_name)
            script_exists = os.path.exists(os.path.join(common.SCRIPT_DIR, f"xraySpeedLimit{limit}mb.sh"))
            if not status["exists"]:
                 status_enabled_str = f"{common.Color.RED}Н/Д (нет .service){common.Color.RESET}"
                 status_active_str = f"{common.Color.DIM}(скрипт {'✓' if script_exists else '✗'}){common.Color.RESET}"
            else:
                 status_enabled_str = f"{common.Color.GREEN}Включен {common.Color.RESET}" if status["enabled"] else f"{common.Color.YELLOW}Выключен{common.Color.RESET}"
                 status_active_str = f"{common.Color.GREEN}Активен {common.Color.RESET}" if status["active"] else f"{common.Color.RED}Неактивен{common.Color.RESET}"
            limit_details.append({"limit": limit, "service_name": service_name, "status": status, "script_exists": script_exists})
            print(f"{common.Color.CYAN}{i + 1:<2}{common.Color.RESET} {f'xraySpeedLimit{limit}mb':<15} {status_enabled_str:<18} {status_active_str:<15}")

        common.print_separator("-")
        print(f"Действия: [{common.Color.CYAN}S{common.Color.RESET}] Статус, [{common.Color.YELLOW}A{common.Color.RESET}] Автозапуск, [{common.Color.GREEN}R{common.Color.RESET}] Старт/Стоп, [{common.Color.RED}U{common.Color.RESET}] Удалить, [{common.Color.BLUE}N{common.Color.RESET}] Назад")
        common.print_separator("-"); choice = input("Номер и действие (напр., '1 S') или 'N': ").strip().upper()

        if choice == 'N': return
        if not choice or len(choice.split()) != 2: print(f"{common.Color.RED}Неверный формат.{common.Color.RESET}"); time.sleep(1.5); continue
        parts = choice.split()
        try:
            num = int(parts[0]); action = parts[1]
            if not (1 <= num <= len(limit_details)): print(f"{common.Color.RED}Неверный номер.{common.Color.RESET}"); time.sleep(1.5); continue
            if action not in ['S', 'A', 'R', 'U']: print(f"{common.Color.RED}Неверное действие ({action}).{common.Color.RESET}"); time.sleep(1.5); continue
            selected = limit_details[num - 1]; limit_val = selected["limit"]; service_name = selected["service_name"]; current_status = selected["status"]
            common.print_separator(); print(f"Выбрано: {limit_val}mb, Действие: {action}"); common.print_separator()

            if not current_status["exists"] and action != 'U':
                 print(f"{common.Color.RED}Действие '{action}' недоступно: нет {service_name}.{common.Color.RESET}"); common.pause(); continue

            if action == 'S':
                if current_status["exists"]:
                    print(f"{common.Color.CYAN}--- Статус {service_name} ---{common.Color.RESET}")
                    system_utils.run_command(['systemctl', 'status', service_name], check=False, capture_output=False, show_error=True)
                else: print(f"{common.Color.YELLOW}Сервис {service_name} не существует.{common.Color.RESET}")
                common.pause()
            elif action == 'A':
                target_action = "disable" if current_status["enabled"] else "enable"
                system_utils.manage_service(target_action, service_name); common.pause()
            elif action == 'R':
                target_action = "stop" if current_status["active"] else "start"
                system_utils.manage_service(target_action, service_name); common.pause()
            elif action == 'U':
                print(f"Удаление лимита: {limit_val}mb")
                confirm = input(f"Подтвердить? (да/нет): ").strip().lower()
                if confirm.startswith('д') or confirm.startswith('y'):
                    print(f"\n{common.Color.MAGENTA}--- Удаление {limit_val}mb ---{common.Color.RESET}")
                    disable_and_remove_port_service(limit_val)
                    print(f"{common.Color.MAGENTA}--- Готово ---{common.Color.RESET}"); common.pause()
                else: print(f"{common.Color.YELLOW}Удаление отменено.{common.Color.RESET}"); common.pause()
        except ValueError: print(f"{common.Color.RED}Неверный номер.{common.Color.RESET}"); time.sleep(1.5)
        except Exception as e: print(f"{common.Color.RED}Ошибка: {e}{common.Color.RESET}"); common.pause()

def remove_port_limit_menu():
    """Меню для быстрого удаления лимита порта."""
    common.clear_screen(); common.print_header("Быстрое удаление лимита порта")
    limits = find_port_limits()
    if not limits: print(f"{common.Color.YELLOW}Активные лимиты портов не найдены.{common.Color.RESET}"); common.pause(); return
    print(f"{common.Color.BOLD}Найденные лимиты портов:{common.Color.RESET}")
    for i, limit in enumerate(limits): print(f"  {common.Color.CYAN}{i + 1}.{common.Color.RESET} xraySpeedLimit{limit}mb")
    common.print_separator("-")
    while True:
        try:
            choice = input(f"Номер для удаления [1-{len(limits)}] (0=отмена): ")
            choice_int = int(choice)
            if choice_int == 0: print(f"\n{common.Color.YELLOW}Отмена.{common.Color.RESET}"); common.pause(); return
            if 1 <= choice_int <= len(limits): selected_limit = limits[choice_int - 1]; break
            else: print(f"{common.Color.RED}Неверный номер.{common.Color.RESET}")
        except ValueError: print(f"{common.Color.RED}Введите число.{common.Color.RESET}")

    common.print_separator("-"); print(f"Удалить: {selected_limit}mb?"); confirm = input(f"Подтвердить? (да/нет): ").strip().lower()
    if confirm.startswith('д') or confirm.startswith('y'):
        print(f"\n{common.Color.MAGENTA}--- Удаление {selected_limit}mb ---{common.Color.RESET}")
        disable_and_remove_port_service(selected_limit)
        print(f"{common.Color.MAGENTA}--- Готово ---{common.Color.RESET}")
    else: print(f"\n{common.Color.YELLOW}Удаление отменено.{common.Color.RESET}")
    common.pause()

# --- Главное меню ---
def main_menu():
    """Главное меню скрипта с выбором режима."""
    while True:
        common.clear_screen(); print(ASCII_LOGO); common.print_header("xraySpeedLimit Utility by MKultra69")
        api_timer_active = os.path.exists(common.WORKER_TIMER_PATH) and system_utils.manage_service('is-active', common.WORKER_TIMER_NAME, quiet=True)
        api_status_color = common.Color.GREEN if api_timer_active else common.Color.RED
        api_status_text = "Активна" if api_timer_active else "Неактивна"
        port_limits_count = len(find_port_limits())
        port_status_color = common.Color.GREEN if port_limits_count > 0 else common.Color.DIM

        print(f"{common.Color.BOLD}Выберите режим работы:{common.Color.RESET}")
        print(f" {common.Color.CYAN}1){common.Color.RESET} Лимиты Пользователей (API) | Статус: {api_status_color}{api_status_text}{common.Color.RESET}")
        print(f" {common.Color.MAGENTA}2){common.Color.RESET} Лимиты Портов (Старый)    | Установлено: {port_status_color}{port_limits_count}{common.Color.RESET}")
        print(f"\n {common.Color.YELLOW}F){common.Color.RESET} FAQ (Оба режима)")
        print(f" {common.Color.RED}Q){common.Color.RESET} Выход")
        common.print_separator(); choice = input("Выберите режим [1, 2] или опцию [F, Q]: ").strip().upper()

        if choice == '1': user_limits_submenu()
        elif choice == '2': port_limits_submenu()
        elif choice == 'F': faq.show_faq()
        elif choice == 'Q': print(f"\n{common.Color.MAGENTA}Пока!{common.Color.RESET}"); sys.exit(0)
        else: print(f"\n{common.Color.RED}Неверный выбор '{choice}'.{common.Color.RESET}"); common.pause()

# --- Подменю для режимов ---
def user_limits_submenu():
    """Подменю для управления лимитами пользователей (API)."""
    while True:
        common.clear_screen(); common.print_header("Режим: Лимиты Пользователей (API)")
        api_timer_active = os.path.exists(common.WORKER_TIMER_PATH) and system_utils.manage_service('is-active', common.WORKER_TIMER_NAME, quiet=True)
        status_color = common.Color.GREEN if api_timer_active else common.Color.RED
        status_text = "Активна" if api_timer_active else "Неактивна/Не установлена"
        print(f" Статус службы воркера: {status_color}{status_text}{common.Color.RESET}"); common.print_separator("-")
        print(f" {common.Color.YELLOW}1){common.Color.RESET} Настроить API и Интерфейс"); print(f" {common.Color.GREEN}2){common.Color.RESET} Управление списком лимитов")
        print(f" {common.Color.CYAN}3){common.Color.RESET} Установить / Переустановить службу"); print(f" {common.Color.RED}4){common.Color.RESET} Удалить службу")
        print(f" {common.Color.BLUE}5){common.Color.RESET} Проверить статус служб"); print(f" {common.Color.YELLOW}N){common.Color.RESET} Назад в главное меню"); common.print_separator()
        choice = input("Выберите опцию [1-5, N]: ").strip().upper()

        if choice == '1': configure_api_menu()
        elif choice == '2': manage_user_limits_menu()
        elif choice == '3': install_user_worker_service() # Переименованная функция
        elif choice == '4': uninstall_user_worker_service() # Переименованная функция
        elif choice == '5':
             common.clear_screen(); common.print_header("Статус служб (Режим API)")
             services = [common.WORKER_TIMER_NAME, common.WORKER_SERVICE_NAME, common.BASE_TC_SERVICE_NAME]
             for svc in services:
                 print(f"{common.Color.CYAN}Статус {svc}...{common.Color.RESET}")
                 system_utils.run_command(['systemctl', 'status', svc], check=False, capture_output=False); common.print_separator("-")
             common.pause()
        elif choice == 'N': return
        else: print(f"\n{common.Color.RED}Неверная опция '{choice}'.{common.Color.RESET}"); common.pause()

def port_limits_submenu():
    """Подменю для управления лимитами портов (Старый режим)."""
    while True:
        common.clear_screen(); common.print_header("Режим: Лимиты Портов (Старый)")
        num_limits = len(find_port_limits()); print(f" Найдено лимитов: {common.Color.YELLOW}{num_limits}{common.Color.RESET}"); common.print_separator("-")
        print(f" {common.Color.GREEN}1){common.Color.RESET} Установить / Перезаписать лимит"); print(f" {common.Color.CYAN}2){common.Color.RESET} Управление установленными лимитами")
        print(f" {common.Color.YELLOW}3){common.Color.RESET} Удалить лимит (быстрое меню)"); print(f" {common.Color.YELLOW}N){common.Color.RESET} Назад в главное меню"); common.print_separator()
        choice = input("Выберите опцию [1-3, N]: ").strip().upper()

        if choice == '1': install_port_limit_menu()
        elif choice == '2': manage_port_limits_menu()
        elif choice == '3': remove_port_limit_menu()
        elif choice == 'N': return
        else: print(f"\n{common.Color.RED}Неверная опция '{choice}'.{common.Color.RESET}"); common.pause()

# --- Точка входа ---
if __name__ == '__main__':
    # 1. Проверка root
    if os.geteuid() != 0:
        print(f"{common.Color.RED}{common.Color.BOLD}Ошибка: Нужны права root.{common.Color.RESET}")
        print(f"{common.Color.YELLOW}Запустите: {common.Color.WHITE}sudo python3 {sys.argv[0]}{common.Color.RESET}")
        sys.exit(1)

    # 2. Проверка утилит
    # Используем список из system_utils.check_required_utils (он уже содержит 'bash' после прошлого исправления)
    required_utils_list = ['tc', 'systemctl', 'python3', 'ip', 'bash'] # Явно задаем полный список здесь
    if not system_utils.check_required_utils(required_utils_list):
        sys.exit(1)
    # Сообщение об успехе убрано из check_required_utils, выводим здесь
    print(f"{common.Color.GREEN}Все необходимые утилиты найдены.{common.Color.RESET}")
    time.sleep(1)

    # 3. Запуск главного меню
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{common.Color.YELLOW}Выход по Ctrl+C.{common.Color.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{common.Color.RED}{common.Color.BOLD}Непредвиденная ошибка:{common.Color.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)