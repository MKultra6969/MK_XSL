"""
Модуль для взаимодействия с операционной системой:
- Запуск внешних команд (subprocess).
- Управление службами systemd.
- Получение списка сетевых интерфейсов.
- Проверка наличия необходимых утилит.
"""

import os
import subprocess
import shlex
import re
import time

# Импортируем общие константы и цвета
try:
    import common
except ImportError:
    print("Ошибка: Не удалось импортировать common.py.")
    import sys
    sys.exit(1)

# --- Запуск внешних команд ---

def run_command(command, check=True, capture_output=True, show_error=True, success_msg=None, failure_msg="Ошибка выполнения команды"):
    """
    Выполняет команду оболочки с улучшенной обработкой ошибок и выводом.

    Args:
        command (list or str): Команда для выполнения (список или строка).
        check (bool): Вызывать исключение CalledProcessError, если команда завершилась с ошибкой (код != 0).
                      Если False, функция вернет False при ошибке.
        capture_output (bool): Захватывать stdout/stderr команды.
        show_error (bool): Показывать stderr и сообщение об ошибке при неудаче.
        success_msg (str, optional): Сообщение для вывода при успешном выполнении (код 0).
        failure_msg (str, optional): Сообщение для вывода при неудаче (код != 0 или исключение).

    Returns:
        bool: True при успехе (код 0), False при неудаче (код != 0 и check=False) или исключении.
              Если check=True, при ошибке будет вызвано исключение CalledProcessError.
    """
    if isinstance(command, str):
        command = shlex.split(command) # Безопасное разделение строки

    cmd_str = ' '.join(shlex.quote(str(c)) for c in command) # Экранированная строка для логов

    # Определяем, является ли это командой проверки статуса systemd
    is_status_check_cmd = isinstance(command, list) and len(command) > 1 and \
                          command[0].endswith('systemctl') and \
                          command[1] in ['is-active', 'is-enabled', 'status']

    # Не захватываем вывод для 'systemctl status', чтобы он отобразился на экране
    use_capture = capture_output and not (is_status_check_cmd and command[1] == 'status')

    try:
        result = subprocess.run(command,
                                check=check, # Вызовет CalledProcessError при ошибке, если True
                                capture_output=use_capture,
                                text=True,
                                encoding='utf-8',
                                errors='ignore') # Игнорируем ошибки декодирования вывода

        # Если check=False и код возврата не 0
        if result.returncode != 0 and not check:
            if show_error and not (is_status_check_cmd and command[1] != 'status'): # Не показываем ошибку для is-active/is-enabled
                print(f"{common.Color.YELLOW}[ПРЕДУПРЕЖДЕНИЕ]{common.Color.RESET} Команда завершилась с кодом {result.returncode}: {cmd_str}")
                if use_capture and result.stderr:
                    print(f"{common.Color.YELLOW}STDERR:{common.Color.RESET} {result.stderr.strip()}")
            # failure_msg выводится только если он есть и это не is-active/is-enabled
            if failure_msg and not is_status_check_cmd:
                 print(f"{common.Color.YELLOW}{failure_msg}{common.Color.RESET}")
            return False # Явно возвращаем False при неуспехе с check=False

        # Успешное выполнение (returncode == 0)
        if success_msg:
            print(f"{common.Color.GREEN}✓ {success_msg}{common.Color.RESET}")
        return True # Явно возвращаем True при успехе

    except subprocess.CalledProcessError as e:
        # Эта ошибка возникает только если check=True и код возврата != 0
        if show_error: # check=True подразумевается
            print(f"{common.Color.RED}[ОШИБКА]{common.Color.RESET} Выполнение команды не удалось (код {e.returncode}): {common.Color.WHITE}{cmd_str}{common.Color.RESET}")
            # Печатаем stderr, если он был захвачен
            captured_stderr = e.stderr if hasattr(e, 'stderr') else None
            if captured_stderr:
                print(f"{common.Color.RED}STDERR:{common.Color.RESET} {captured_stderr.strip()}")
        if failure_msg:
            print(f"{common.Color.RED}{failure_msg}{common.Color.RESET}")
        # Если check=True, исключение будет проброшено дальше, если его не поймать здесь.
        # Но наша функция должна вернуть bool, поэтому возвращаем False.
        # Вызывающий код должен сам решать, как обрабатывать неудачу.
        return False

    except FileNotFoundError:
         if show_error:
             print(f"{common.Color.RED}[ОШИБКА]{common.Color.RESET} Команда не найдена: {common.Color.WHITE}{command[0]}{common.Color.RESET}")
         if failure_msg:
             print(f"{common.Color.RED}{failure_msg}{common.Color.RESET}")
         return False

    except PermissionError as e:
         if show_error:
             print(f"{common.Color.RED}[ОШИБКА]{common.Color.RESET} Отказано в доступе при выполнении '{cmd_str}': {e}")
         if failure_msg:
             print(f"{common.Color.RED}{failure_msg}{common.Color.RESET}")
         return False

    except Exception as e: # Другие возможные исключения
        if show_error:
            print(f"{common.Color.RED}[КРИТИЧЕСКАЯ ОШИБКА]{common.Color.RESET} При выполнении '{cmd_str}': {e}")
            # Можно добавить вывод traceback для отладки
            # import traceback
            # traceback.print_exc()
        if failure_msg:
            print(f"{common.Color.RED}{failure_msg}{common.Color.RESET}")
        return False


# --- Управление службами systemd ---

def manage_service(action, service_name, check_status=True, quiet=False):
    """
    Управляет службой systemd (start, stop, enable, disable, restart, status, is-active, is-enabled).
    Обертка над run_command для удобства.

    Args:
        action (str): Действие systemctl.
        service_name (str): Имя службы (с расширением .service или .timer).
        check_status (bool): Проверять ли статус 'is-active' после действий 'start', 'restart', 'enable'.
        quiet (bool): Подавлять стандартный вывод сообщений об успехе/неудаче (кроме ошибок).

    Returns:
        bool: True при успехе основного действия, False при ошибке.
              Для 'is-active'/'is-enabled' возвращает их результат (True/False).
    """
    if not quiet:
        print(f"{common.Color.CYAN}Выполнение: systemctl {action} {service_name}...{common.Color.RESET}")

    # Для статуса не захватываем вывод, чтобы он отобразился
    capture = action != 'status'
    # Для проверок is-active/is-enabled не показываем ошибку при неуспехе (код не 0)
    show_err = action not in ['is-active', 'is-enabled']
    # Сообщения об успехе/неудаче
    succ_msg = None if quiet else f"systemctl {action} {service_name} выполнен"
    fail_msg = f"Ошибка при выполнении 'systemctl {action} {service_name}'"

    # Выполняем основную команду
    success = run_command(['systemctl', action, service_name],
                          check=False, # Всегда False, чтобы обработать результат здесь
                          capture_output=capture,
                          show_error=show_err,
                          success_msg=None, # Сообщения обрабатываем ниже
                          failure_msg=None if quiet else fail_msg)

    # Обработка результата
    if action in ['is-active', 'is-enabled']:
        # Для этих команд run_command вернет True если код 0, False иначе
        if not quiet:
             status_text = "Активен/Включен" if success else "Неактивен/Выключен"
             print(f"{common.Color.DIM}Результат '{action}' для {service_name}: {status_text}{common.Color.RESET}")
        return success # Возвращаем результат проверки

    if not success:
        # Если основное действие (не is-active/is-enabled) не удалось
        if not quiet:
            # failure_msg уже был выведен в run_command, если show_error=True
            # Дополнительно покажем статус для диагностики, если это не была команда status
            if action != 'status':
                print(f"{common.Color.YELLOW}Попытка показать статус {service_name} для диагностики:{common.Color.RESET}")
                run_command(['systemctl', 'status', service_name], check=False, capture_output=False, show_error=True)
        return False # Неудача

    # Если основное действие успешно (и это не is-active/is-enabled/status)
    if success and action not in ['status', 'is-active', 'is-enabled']:
         if not quiet and succ_msg:
             print(f"{common.Color.GREEN}✓ {succ_msg}{common.Color.RESET}")

         # Опциональная проверка статуса 'is-active' после действия
         if check_status:
             time.sleep(0.5) # Небольшая пауза перед проверкой
             if not quiet:
                 print(f"{common.Color.CYAN}Проверка статуса 'is-active' для {service_name} после '{action}'...{common.Color.RESET}")
             is_active = run_command(['systemctl', 'is-active', service_name], check=False, capture_output=True, show_error=False)

             expected_active = action in ['start', 'restart', 'enable'] # Для enable ожидаем, что он может быть активен

             if is_active == expected_active:
                 if not quiet:
                     status_text = "активен" if expected_active else "не активен"
                     print(f"{common.Color.GREEN}✓ Статус {service_name} соответствует ожидаемому ({status_text}).{common.Color.RESET}")
             else:
                 if not quiet:
                     status_text_is = "активен" if is_active else "не активен"
                     status_text_expected = "активен" if expected_active else "не активен"
                     print(f"{common.Color.YELLOW}Предупреждение: Статус {service_name} '{status_text_is}', хотя ожидался '{status_text_expected}' после '{action}'.{common.Color.RESET}")
                     # Помощь в диагностике
                     print(f"{common.Color.DIM}Проверьте логи: journalctl -u {service_name} -n 20 --no-pager{common.Color.RESET}")

    return success # Возвращаем результат выполнения основной команды 'action'

# --- Получение списка сетевых интерфейсов ---

def get_network_interfaces():
    """
    Получает список активных физических сетевых интерфейсов, используя 'ip' или /sys/class/net.
    Исключает loopback, виртуальные (veth, docker, br, virbr, tun, tap, bond, dummy).

    Returns:
        list: Отсортированный список имен активных физических интерфейсов.
              Пустой список при ошибке или если ничего не найдено.
    """
    interfaces = []
    # 1. Попытка через 'ip link' (предпочтительно)
    try:
        # '-o' для краткого вывода, '-br' для более простого парсинга (но может не быть на старых ip)
        # Попробуем сначала с -br
        try:
            result_br = subprocess.run(['ip', '-br', 'link'], capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            lines = result_br.stdout.strip().split('\n')
            # Формат: IFACE STATE MAC ADDR ...
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    ifname = parts[0]
                    state = parts[1].upper() # UP, DOWN, UNKNOWN

                    is_loopback = (ifname == 'lo')
                    is_virtual = ifname.startswith(('veth', 'docker', 'br-', 'virbr', 'tun', 'tap', 'bond', 'dummy'))

                    if not is_loopback and not is_virtual and state == 'UP':
                        if ifname not in interfaces:
                            interfaces.append(ifname)

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Если 'ip -br link' не сработал, пробуем 'ip -o link show'
            print(f"{common.Color.DIM}Команда 'ip -br link' не удалась, пробую 'ip -o link show'...{common.Color.RESET}")
            result_o = subprocess.run(['ip', '-o', 'link', 'show'], capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            lines_o = result_o.stdout.strip().split('\n')
            # Формат: 1: lo: <LOOPBACK,UP,LOWER_UP> ...
            for line in lines_o:
                parts = line.split(': ')
                if len(parts) > 1:
                    ifname_part = parts[1].split('@')[0].strip() # Удаляем возможное @iface для veth
                    ifname = ifname_part

                    flags_match = re.search(r'<(\S+)>', parts[0])
                    flags = flags_match.group(1).upper() if flags_match else ""

                    is_loopback = (ifname == 'lo')
                    is_virtual = ifname.startswith(('veth', 'docker', 'br-', 'virbr', 'tun', 'tap', 'bond', 'dummy'))

                    if not is_loopback and not is_virtual and ('UP' in flags or 'LOWER_UP' in flags):
                         if ifname not in interfaces:
                             interfaces.append(ifname)

    except FileNotFoundError:
        print(f"{common.Color.YELLOW}[ПРЕДУПРЕЖДЕНИЕ] Команда 'ip' не найдена. Попытка через /sys/class/net...{common.Color.RESET}")
        # Очищаем список, если 'ip' не найден, чтобы использовать только sysfs
        interfaces = []
    except (subprocess.CalledProcessError, Exception) as e:
        print(f"{common.Color.YELLOW}[ПРЕДУПРЕЖДЕНИЕ] Не удалось получить список интерфейсов через 'ip': {e}{common.Color.RESET}")
        # Не очищаем список, возможно, '-br' сработал частично

    # 2. Запасной вариант через /sys/class/net (если 'ip' не сработал или не найден)
    sysfs_path = '/sys/class/net'
    if not interfaces and os.path.isdir(sysfs_path):
         print(f"{common.Color.DIM}Использую /sys/class/net для поиска интерфейсов...{common.Color.RESET}")
         try:
             potential_ifaces = os.listdir(sysfs_path)
             for ifname in potential_ifaces:
                 is_loopback = (ifname == 'lo')
                 # Проверяем, что это не виртуальный интерфейс (по наличию /sys/class/net/ifname/device)
                 # Физические интерфейсы обычно имеют эту символическую ссылку
                 is_physical = os.path.islink(os.path.join(sysfs_path, ifname, 'device'))
                 # Дополнительно проверяем на известные префиксы виртуальных
                 is_known_virtual = ifname.startswith(('veth', 'docker', 'br-', 'virbr', 'tun', 'tap', 'bond', 'dummy'))

                 if not is_loopback and is_physical and not is_known_virtual:
                     # Проверяем состояние operstate
                     operstate_path = os.path.join(sysfs_path, ifname, 'operstate')
                     try:
                         if os.path.exists(operstate_path):
                             with open(operstate_path, 'r') as f_oper:
                                 if f_oper.read().strip().lower() == 'up':
                                     if ifname not in interfaces:
                                         interfaces.append(ifname)
                     except OSError:
                         continue # Пропускаем, если не можем прочитать operstate
         except OSError as e_sys:
              print(f"{common.Color.YELLOW}[ПРЕДУПРЕЖДЕНИЕ] Не удалось получить список через /sys/class/net: {e_sys}{common.Color.RESET}")

    if not interfaces:
         print(f"{common.Color.RED}[ОШИБКА] Не удалось определить активные физические сетевые интерфейсы.{common.Color.RESET}")

    return sorted(interfaces) # Возвращаем отсортированный список


# --- Проверка наличия утилит ---

def check_required_utils(utils_to_check=['tc', 'systemctl', 'python3', 'ip']): # Добавляем аргумент со списком по умолчанию
    """
    Проверяет наличие необходимых для работы скрипта системных утилит.

    Args:
        utils_to_check (list): Список строк с именами утилит для проверки.

    Returns:
        bool: True, если все утилиты найдены, False в противном случае.
    """
    missing_utils = []
    print(f"{common.Color.DIM}Проверка наличия утилит: {', '.join(utils_to_check)}...{common.Color.RESET}")
    for util in utils_to_check: # Используем переданный список
        try:
            run_command(['which', util], check=True, capture_output=True, show_error=False)
            print(f"{common.Color.GREEN}✓ {util} найден.{common.Color.RESET}")
        except Exception: # Ловим любую ошибку как "не найден"
            print(f"{common.Color.RED}✗ {util} не найден.{common.Color.RESET}")
            missing_utils.append(util)

    if missing_utils:
        print(f"\n{common.Color.RED}{common.Color.BOLD}Критическая ошибка: Отсутствуют утилиты:{common.Color.RESET}")
        # ... (остальная часть функции как была) ...
        for util in missing_utils:
            package_suggestion = ""
            if util in ['tc', 'ip']: package_suggestion = "(обычно в пакете 'iproute2')"
            if util == 'systemctl': package_suggestion = "(основная часть 'systemd')"
            if util == 'python3': package_suggestion = "(пакет 'python3')"
            if util == 'bash': package_suggestion = "(пакет 'bash')" # Добавлено
            print(f"  - {common.Color.WHITE}{util}{common.Color.RESET} {common.Color.DIM}{package_suggestion}{common.Color.RESET}")
        print(f"\n{common.Color.YELLOW}Установите отсутствующие пакеты и повторите запуск.{common.Color.RESET}")
        return False
    else:
        return True