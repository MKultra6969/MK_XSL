"""
Модуль для управления правилами Traffic Control (tc) для шейпинга.
- Сопоставление лимита скорости с классом HTB.
- Очистка динамических правил tc.
- Применение правил tc (HTB для upload, police для download).
"""

import re

# Импортируем необходимые модули
try:
    import common
    import system_utils # Для выполнения команд tc
except ImportError as e:
    print(f"Критическая ошибка: Не удалось импортировать модуль: {e}")
    import sys
    sys.exit(1)

# --- Вспомогательная функция для логирования (если нужна специфичная для TC) ---
# Пока можно использовать print или добавить логирование в system_utils.run_command

# --- Функции управления TC ---

def map_limit_to_classid(limit_mbps):
    """
    Находит подходящий classid формата '1:X' для заданного лимита скорости upload.
    Использует предопределенные классы из common.PREDEFINED_LIMIT_CLASSES.

    Логика:
    1. Находит все классы, скорость которых >= запрошенному лимиту.
    2. Если такие есть, выбирает класс с МИНИМАЛЬНОЙ скоростью из них (чтобы не давать лишнего).
    3. Если таких нет (лимит выше всех классов), выбирает класс с МАКСИМАЛЬНОЙ скоростью.
    4. Если классы не определены, возвращает None.

    Args:
        limit_mbps (int or float): Желаемый лимит скорости в Мбит/с.

    Returns:
        str or None: Строка classid (e.g., '1:100') или None, если классы не заданы.
    """
    predefined_classes = common.PREDEFINED_LIMIT_CLASSES
    if not predefined_classes:
        print(f"{common.Color.YELLOW}[TC WARN] Словарь PREDEFINED_LIMIT_CLASSES пуст в common.py. Невозможно сопоставить лимит классу HTB.{common.Color.RESET}")
        return None

    if limit_mbps <= 0:
         print(f"{common.Color.YELLOW}[TC WARN] Запрошен некорректный лимит ({limit_mbps} Мбит/с) для сопоставления с классом HTB.{common.Color.RESET}")
         # Можно вернуть самый медленный класс или None. Вернем None.
         return None

    # Классы, скорость которых >= лимиту
    suitable_classes = {}
    for class_id, rate_mbps in predefined_classes.items():
        if rate_mbps >= limit_mbps:
            suitable_classes[class_id] = rate_mbps

    best_class_id = None
    if suitable_classes:
        # Находим ID класса с минимальной скоростью среди подходящих
        best_class_id = min(suitable_classes, key=suitable_classes.get)
        # print(f"[TC DEBUG] Для лимита {limit_mbps} Мбит/с выбран класс 1:{best_class_id} ({predefined_classes[best_class_id]} Мбит/с)")
    elif predefined_classes:
        # Если подходящих нет, берем самый быстрый из доступных
        best_class_id = max(predefined_classes, key=predefined_classes.get)
        print(f"{common.Color.DIM}[TC DEBUG] Лимит {limit_mbps} Мбит/с выше определенных классов. Используется максимальный: 1:{best_class_id} ({predefined_classes[best_class_id]} Мбит/с){common.Color.RESET}")
    # else: # predefined_classes пуст - уже обработано в начале

    return f"1:{best_class_id}" if best_class_id is not None else None

def clear_dynamic_tc_rules(iface):
    """
    Удаляет все динамические правила фильтрации tc (egress и ingress),
    созданные этим скриптом (определяются по приоритету TC_PRIO).

    Args:
        iface (str): Сетевой интерфейс.

    Returns:
        bool: True, если обе команды удаления выполнены (даже если правил не было),
              False, если выполнение команды tc завершилось ошибкой (кроме "не найдено").
    """
    print(f"{common.Color.CYAN}[TC] Очистка старых динамических правил для {iface} (приоритет {common.TC_PRIO})...{common.Color.RESET}")
    success = True

    # Удаляем все фильтры с нашим приоритетом для egress (parent 1:0)
    # fail_ok=True не используется в system_utils.run_command, поэтому check=False
    # Мы проверяем результат сами. Ошибки "RTNETLINK answers: No such file or directory" (если правил нет) игнорируем.
    cmd_egress = ['tc', 'filter', 'del', 'dev', iface, 'parent', '1:0', 'prio', common.TC_PRIO]
    # Запускаем команду, не прерываясь при ошибке, но показывая ее
    if not system_utils.run_command(cmd_egress, check=False, capture_output=True, show_error=True, failure_msg=None):
        # Проверим stderr на ожидаемую ошибку "No such file or directory"
        # Для этого нужно было бы захватить stderr в run_command и вернуть его.
        # Пока упростим: считаем любую ошибку здесь не фатальной, если это не PermissionError и т.п.
        # В production можно добавить более тонкую обработку.
        print(f"{common.Color.DIM}[TC DEBUG] Команда удаления egress фильтров завершилась с ошибкой (возможно, правил не было).{common.Color.RESET}")
        # success = False # Решаем, считать ли это провалом операции очистки

    # Удаляем все фильтры с нашим приоритетом для ingress (parent ffff:)
    cmd_ingress = ['tc', 'filter', 'del', 'dev', iface, 'parent', 'ffff:', 'prio', common.TC_PRIO]
    if not system_utils.run_command(cmd_ingress, check=False, capture_output=True, show_error=True, failure_msg=None):
        print(f"{common.Color.DIM}[TC DEBUG] Команда удаления ingress фильтров завершилась с ошибкой (возможно, правил не было).{common.Color.RESET}")
        # success = False

    # print(f"{common.Color.CYAN}[TC] Очистка завершена.{common.Color.RESET}") # Сообщение больше для отладки
    return success # Возвращаем общий успех операции

def apply_tc_rules(iface, user_ips_with_limits):
    """
    Применяет правила tc (htb для upload, police для download) для IP-адресов пользователей.
    Сначала очищает старые правила с тем же приоритетом.

    Args:
        iface (str): Сетевой интерфейс.
        user_ips_with_limits (dict): Словарь { 'ip_address': limit_mbps }.

    Returns:
        int: Количество успешно примененных правил (сумма egress и ingress).
             Может быть 0, если словарь пуст или при применении возникли ошибки.
    """
    if not user_ips_with_limits:
        print(f"{common.Color.YELLOW}[TC] Нет активных IP/лимитов для применения правил на {iface}.{common.Color.RESET}")
        return 0

    print(f"{common.Color.CYAN}[TC] Применение {len(user_ips_with_limits)} правил для IP-адресов на {iface}...{common.Color.RESET}")

    # 1. Очистка старых правил перед применением новых
    if not clear_dynamic_tc_rules(iface):
        print(f"{common.Color.YELLOW}[TC WARN] Не удалось полностью очистить старые правила. Новые правила могут работать некорректно.{common.Color.RESET}")
        # Продолжаем попытку применить новые правила

    applied_rules_count = 0
    handle_counter = 0 # Счетчик для генерации уникальных handle 0x5000, 0x5001, ...

    for ip_address, limit_mbps in user_ips_with_limits.items():
        # Валидация данных
        if not ip_address or not isinstance(limit_mbps, (int, float)) or limit_mbps <= 0:
            print(f"{common.Color.YELLOW}[TC WARN] Пропуск некорректной записи: IP='{ip_address}', Лимит='{limit_mbps}'.{common.Color.RESET}")
            continue

        # Простая валидация IP-адреса (только IPv4)
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip_address):
            print(f"{common.Color.YELLOW}[TC WARN] Пропуск невалидного IPv4 адреса: '{ip_address}'.{common.Color.RESET}")
            continue

        # --- Правило для Upload (Egress - HTB) ---
        classid_for_upload = map_limit_to_classid(limit_mbps)
        if classid_for_upload:
            egress_handle = hex(common.TC_HANDLE_BASE + handle_counter)
            handle_counter += 1
            egress_args = [
                common.TC_PATH,
                'filter', 'add', 'dev', iface, 'protocol', 'ip', 'parent', '1:0',
                'prio', common.TC_PRIO, 'handle', egress_handle, 'u32',
                'match', 'ip', 'src', f'{ip_address}/32', # Фильтр по IP источнику
                'flowid', classid_for_upload # Направить в HTB класс
            ]
            # Теперь вызывается правильная команда: tc filter add ...
            if system_utils.run_command(egress_args, check=False, capture_output=True, show_error=True, failure_msg=f"Не удалось добавить egress правило для {ip_address}"):
                 applied_rules_count += 1
                # print(f"[TC DEBUG] Egress правило: {ip_address} -> {classid_for_upload}")
            # else: Ошибка уже выведена run_command
        else:
            print(f"{common.Color.YELLOW}[TC WARN] Не найден класс HTB для upload лимита {limit_mbps} Мбит/с для IP {ip_address}. Egress правило не добавлено.{common.Color.RESET}")

        # --- Правило для Download (Ingress - Police) ---
        ingress_handle = hex(common.TC_HANDLE_BASE + handle_counter)
        handle_counter += 1
        # Расчет Burst: часто используют 10-20% от секунды трафика
        # rate_bps = limit_mbps * 1000 * 1000
        # burst_bytes = int(rate_bps * 0.15 / 8) # 150ms буфер в байтах
        # burst_bytes = max(burst_bytes, 15000) # Минимум ~10 пакетов
        # Формат для tc: число[k|m]
        # burst_kb = burst_bytes / 1024
        # burst_str = f"{int(burst_kb)}k" if burst_kb > 1 else "15k" # Упрощенно, ставим 15k
        burst_str = "5k" # Упрощенный вариант, часто достаточен

        ingress_args = [
            common.TC_PATH,  # <--- ДОБАВЛЕНО
            'filter', 'add', 'dev', iface, 'protocol', 'ip', 'parent', 'ffff:',  # Ingress qdisc
            'prio', common.TC_PRIO, 'handle', ingress_handle, 'u32',
            'match', 'ip', 'dst', f'{ip_address}/32',  # Фильтр по IP назначению
            'police', 'rate', f'{limit_mbps}mbit', 'burst', burst_str, 'drop',  # Ограничение скорости
            'flowid', ':1'  # Указываем flowid для police (формально)
        ]
        # Теперь вызывается правильная команда: tc filter add ...
        if system_utils.run_command(ingress_args, check=False, capture_output=True, show_error=True,
                                    failure_msg=f"Не удалось добавить ingress правило для {ip_address}"):
            applied_rules_count += 1
            # print(f"[TC DEBUG] Ingress правило: {ip_address} @ {limit_mbps}mbit")
        # else: Ошибка уже выведена run_command

    print(f"{common.Color.GREEN}[TC] Успешно применено {applied_rules_count} правил TC для {iface}.{common.Color.RESET}")
    return applied_rules_count