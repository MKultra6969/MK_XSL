"""
Модуль для отображения раздела FAQ (Часто задаваемые вопросы).
"""

# Импортируем общие константы и утилиты
try:
    import common
except ImportError:
    print("Ошибка: Не удалось импортировать common.py.")
    import sys
    sys.exit(1)

# --- Функция отображения FAQ ---

def show_faq():
    """Отображает раздел с часто задаваемыми вопросами."""
    common.clear_screen()
    common.print_header("FAQ - xraySpeedLimit (X-UI API)")

    # Используем f-строки и константы цветов из common.Color
    print(f"{common.Color.CYAN}Q: Зачем это нужно? Что это делает?{common.Color.RESET}")
    print(f"{common.Color.WHITE}A: Эта утилита позволяет {common.Color.BOLD}ограничивать скорость{common.Color.RESET} интернет-соединения для")
    print(f"   {common.Color.BOLD}конкретных пользователей{common.Color.RESET} вашего сервера Xray/V2Ray, управляемого")
    print(f"   через панель {common.Color.YELLOW}X-UI{common.Color.RESET}. Ограничение применяется индивидуально на основе")
    print(f"   {common.Color.YELLOW}Email/Тега пользователя{common.Color.RESET}, указанного в панели.")
    print(f"   Это более гибко, чем стандартное ограничение скорости на весь порт (inbound) в X-UI.")
    common.print_separator("-")

    print(f"{common.Color.CYAN}Q: Как это работает технически?{common.Color.RESET}")
    print(f"{common.Color.WHITE}A: 1. {common.Color.MAGENTA}Настройка:{common.Color.RESET} Вы указываете данные для доступа к API X-UI (URL, логин,")
    print(f"      пароль) и выбираете сетевой интерфейс, на котором работает Xray.")
    print(f"   2. {common.Color.YELLOW}Список лимитов:{common.Color.RESET} Вы создаете список пользователей (по их Email/Тегу)")
    print(f"      и задаете для каждого желаемый лимит скорости в Мбит/с.")
    print(f"   3. {common.Color.CYAN}Установка службы:{common.Color.RESET} Утилита создает два скрипта (базовая настройка")
    print(f"      TC и воркер) и три systemd-юнита (сервис для базы TC, сервис")
    print(f"      для воркера и таймер для его периодического запуска).")
    print(f"   4. {common.Color.BLUE}Базовая настройка TC:{common.Color.RESET} При старте системы (и при установке)")
    print(f"      выполняется скрипт, который создает основную структуру Traffic Control")
    print(f"      ({common.Color.GREEN}tc qdisc htb{common.Color.RESET} для upload, {common.Color.GREEN}tc qdisc ingress{common.Color.RESET} для download) и")
    print(f"      предопределенные классы скорости HTB для upload.")
    print(f"   5. {common.Color.GREEN}Работа воркера (каждую минуту):{common.Color.RESET}")
    print(f"      - Скрипт-воркер (Python) запускается по таймеру.")
    print(f"      - Подключается к {common.Color.YELLOW}API X-UI{common.Color.RESET}, используя сохраненные данные.")
    print(f"      - Получает список {common.Color.BOLD}онлайн пользователей{common.Color.RESET}.")
    print(f"      - Для каждого онлайн пользователя, {common.Color.BOLD}присутствующего в вашем списке лимитов{common.Color.RESET}:")
    print(f"         - Запрашивает у API его {common.Color.BOLD}текущие IP-адреса{common.Color.RESET}.")
    print(f"      - {common.Color.RED}Удаляет все предыдущие{common.Color.RESET} динамические правила TC, созданные им ранее.")
    print(f"      - Создает {common.Color.BOLD}новые правила{common.Color.RESET} {common.Color.GREEN}tc filter{common.Color.RESET} для каждого актуального IP-адреса:")
    print(f"         - Для {common.Color.MAGENTA}Upload (исходящий трафик):{common.Color.RESET} Правило `u32` + `htb flowid`")
    print(f"           направляет трафик от IP пользователя в нужный класс HTB.")
    print(f"         - Для {common.Color.MAGENTA}Download (входящий трафик):{common.Color.RESET} Правило `u32` + `police`")
    print(f"           ограничивает скорость для трафика, идущего к IP пользователя.")
    common.print_separator("-")

    print(f"{common.Color.CYAN}Q: Безопасно ли хранить пароль API?{common.Color.RESET}")
    print(f"{common.Color.WHITE}A: Пароль API хранится в конфигурационном файле {common.Color.DIM}{common.CONFIG_FILE}{common.Color.RESET}.")
    print(f"   Утилита автоматически устанавливает на этот файл права доступа {common.Color.YELLOW}600{common.Color.RESET},")
    print(f"   что означает, что читать и изменять его может {common.Color.BOLD}только владелец файла{common.Color.RESET} (обычно root).")
    print(f"   Это стандартная практика для хранения чувствительных данных конфигурации.")
    print(f"   Сам пароль не хранится в открытом виде в исполняемых скриптах.")
    common.print_separator("-")

    print(f"{common.Color.CYAN}Q: Какие системные требования?{common.Color.RESET}")
    print(f"{common.Color.WHITE}A: - Операционная система: {common.Color.GREEN}Linux{common.Color.RESET} с поддержкой {common.Color.GREEN}systemd{common.Color.RESET}.")
    print(f"   - Установленные пакеты: {common.Color.GREEN}iproute2{common.Color.RESET} (содержит утилиту `tc` и `ip`), {common.Color.GREEN}python3{common.Color.RESET}.")
    print(f"   - Установленная библиотека Python: {common.Color.GREEN}requests{common.Color.RESET} (`pip install requests`).")
    print(f"   - Рабочая панель {common.Color.YELLOW}X-UI{common.Color.RESET} (форк FranzKafkaYu или аналогичный с рабочим API).")
    print(f"   - {common.Color.RED}Права суперпользователя (root){common.Color.RESET} для установки служб и управления `tc`.")
    common.print_separator("-")

    print(f"{common.Color.CYAN}Q: Будет ли это работать, если у пользователя несколько подключений (разные IP)?{common.Color.RESET}")
    print(f"{common.Color.WHITE}A: {common.Color.BOLD}Да.{common.Color.RESET} Воркер запрашивает у API X-UI {common.Color.BOLD}все{common.Color.RESET} активные IP-адреса для")
    print(f"   каждого онлайн пользователя. Если API возвращает несколько IP,")
    print(f"   то правила TC будут созданы для {common.Color.BOLD}каждого из этих IP-адресов{common.Color.RESET}.")
    common.print_separator("-")

    print(f"{common.Color.CYAN}Q: Что если пользователь отключится?{common.Color.RESET}")
    print(f"{common.Color.WHITE}A: При следующем запуске воркера (через минуту) этот пользователь")
    print(f"   не будет в списке онлайн-пользователей от API. Воркер {common.Color.RED}удалит все старые правила{common.Color.RESET}")
    print(f"   и не создаст новые для IP этого пользователя, так как он больше не онлайн.")
    print(f"   Таким образом, правила TC автоматически очищаются для неактивных сессий.")
    common.print_separator("-")

    print(f"{common.Color.DIM}Автор: MKultra69 (https://github.com/MKultra6969){common.Color.RESET}")

    # Вызываем pause из common
    common.pause()