"""
Общие константы и вспомогательные утилиты для xraySpeedLimit.
"""
import os
import sys
import re

# --- Цвета ANSI ---
class Color:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

# --- Константы путей ---
# Базовые директории
SERVICE_DIR = "/etc/systemd/system/"
SCRIPT_DIR = "/usr/local/bin/"
CONFIG_DIR = "/etc/xraySpeedLimit"

# Полные пути к файлам и скриптам
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
USER_LIMITS_FILE = os.path.join(CONFIG_DIR, "user_limits.json")
WORKER_SCRIPT_NAME = "xray_limit_worker.py"
WORKER_SCRIPT_PATH = os.path.join(SCRIPT_DIR, WORKER_SCRIPT_NAME)
BASE_TC_SCRIPT_NAME = "setup_base_tc.sh"
BASE_TC_SCRIPT_PATH = os.path.join(SCRIPT_DIR, BASE_TC_SCRIPT_NAME)
BASE_TC_SERVICE_NAME = "xray-base-tc.service"
BASE_TC_SERVICE_PATH = os.path.join(SERVICE_DIR, BASE_TC_SERVICE_NAME)
WORKER_SERVICE_NAME = "xray-limit-worker.service"
WORKER_SERVICE_PATH = os.path.join(SERVICE_DIR, WORKER_SERVICE_NAME)
WORKER_TIMER_NAME = "xray-limit-worker.timer"
WORKER_TIMER_PATH = os.path.join(SERVICE_DIR, WORKER_TIMER_NAME)

# --- Константы для TC ---
# Предопределенные классы TC HTB (ID -> Мбит/с) для Upload
PREDEFINED_LIMIT_CLASSES = {
    # ID: Rate (Mbps)
    2: 1,
    5: 5,
    10: 10,
    20: 20,
    30: 100,
    50: 50,
    100: 100,
    200: 200,
    500: 500,
    1000: 1000,
}

TC_PRIO = '5000'
TC_HANDLE_BASE = 0x5000
TC_PATH = '/sbin/tc'

# --- Константы API ---
API_TIMEOUT = 15 # Секунды

# --- Простые вспомогательные функции ---
def clear_screen():
    """Очищает экран консоли."""
    os.system('clear' if os.name == 'posix' else 'cls')

def pause():
    """Ожидает нажатия Enter."""
    print(f"\n{Color.DIM}Нажми Enter чтобы продолжить...{Color.RESET}", end='')
    # Используем sys.stdin.readline() для большей совместимости, чем input() в некоторых средах
    try:
        sys.stdin.readline()
    except KeyboardInterrupt:
        # Позволяем Ctrl+C прервать ожидание
        print("\nПрервано.")
        sys.exit(1) # Выходим, если прервали во время паузы

def print_separator(char="=", length=40):
    """Печатает разделитель."""
    print(f"{Color.BLUE}{char * length}{Color.RESET}")

def print_header(title):
    """Печатает заголовок."""
    print_separator()
    print(f"{Color.BOLD}{Color.YELLOW}{title.center(40)}{Color.RESET}")
    print_separator()

PORT_LIMIT_FILENAME_PATTERN = re.compile(r"^xraySpeedLimit(\d+)mb\.(service|sh)$")