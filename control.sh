#!/bin/bash

# Определяем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Функция для вывода справки
show_help() {
    echo "Управление ботом Google Business"
    echo "Использование: $0 [команда]"
    echo ""
    echo "Доступные команды:"
    echo "  start   - Запустить бота"
    echo "  stop    - Остановить бота"
    echo "  restart - Перезапустить бота"
    echo "  status  - Показать статус бота"
    echo "  logs    - Показать последние 50 строк логов (используйте Ctrl+C для выхода)"
    echo "  update  - Обновить базу знаний"
    echo "  check   - Проверить настройку сервера"
    echo "  help    - Показать эту справку"
}

# Функция для запуска бота
start_bot() {
    if pgrep -f "python.*bot.py" > /dev/null; then
        echo "⚠️ Бот уже запущен!"
    else
        echo "🚀 Запускаем бота..."
        "${SCRIPT_DIR}/start_bot.sh"
    fi
}

# Функция для остановки бота
stop_bot() {
    if pgrep -f "python.*bot.py" > /dev/null; then
        echo "🛑 Останавливаем бота..."
        "${SCRIPT_DIR}/stop_bot.sh"
    else
        echo "ℹ️ Бот не запущен!"
    fi
}

# Функция для перезапуска бота
restart_bot() {
    echo "🔄 Перезапускаем бота..."
    "${SCRIPT_DIR}/restart.sh"
}

# Функция для проверки статуса бота
status_bot() {
    if [ -f "$SCRIPT_DIR/bot.pid" ]; then
        PID=$(cat "$SCRIPT_DIR/bot.pid")
        if ps -p $PID > /dev/null; then
            UPTIME=$(ps -p $PID -o etime= | tr -d ' ')
            echo "✅ Бот запущен (PID: $PID, активен: $UPTIME)"
            return 0
        else
            echo "⚠️ Найден недействительный PID файл. Бот, возможно, не запущен."
            return 1
        fi
    else
        BOT_PID=$(pgrep -f "python.*bot.py")
        if [ -n "$BOT_PID" ]; then
            UPTIME=$(ps -p $BOT_PID -o etime= | tr -d ' ')
            echo "✅ Бот запущен (PID: $BOT_PID, активен: $UPTIME), но без PID файла"
            return 0
        else
            echo "❌ Бот не запущен!"
            return 1
        fi
    fi
}

# Функция для обновления базы знаний
update_db() {
    echo "📚 Обновляем базу знаний..."
    "${SCRIPT_DIR}/update_db.sh"
}

# Функция для просмотра логов
show_logs() {
    LOG_FILE="$LOG_DIR/bot.log"
    if [ -f "$LOG_FILE" ]; then
        echo "📋 Последние 50 строк логов (используйте Ctrl+C для выхода):"
        tail -n 50 -f "$LOG_FILE"
    else
        echo "❌ Файл логов не найден: $LOG_FILE"
    fi
}

# Функция проверки настройки сервера
check_setup() {
    echo "🔍 Проверка настройки сервера..."
    
    # Проверка Python и виртуального окружения
    if [ -d "$SCRIPT_DIR/new_venv" ]; then
        echo "✅ Виртуальное окружение найдено"
    else
        echo "❌ Виртуальное окружение не найдено!"
    fi
    
    # Проверка конфигурационных файлов
    if [ -f "$SCRIPT_DIR/.env" ]; then
        echo "✅ Файл .env найден"
    else
        echo "❌ Файл .env не найден!"
    fi
    
    if [ -f "$SCRIPT_DIR/service-account-key.json" ]; then
        echo "✅ Ключ сервисного аккаунта Google найден"
    else
        echo "❌ Ключ сервисного аккаунта Google не найден!"
    fi
    
    # Проверка базы данных
    if [ -d "$SCRIPT_DIR/local_vector_db" ]; then
        echo "✅ Векторная база данных найдена"
    else
        echo "❌ Векторная база данных не найдена!"
    fi
    
    # Проверка службы systemd
    if systemctl is-active --quiet google-vk-bot; then
        echo "✅ Служба systemd активна"
    else
        echo "❌ Служба systemd не активна!"
    fi
    
    # Проверка cron-задач
    if crontab -l | grep -q "update_db.sh"; then
        echo "✅ Cron-задача для обновления базы найдена"
    else
        echo "❌ Cron-задача для обновления базы не найдена!"
    fi
}

# Обработка аргументов командной строки
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        status_bot
        ;;
    logs)
        show_logs
        ;;
    update)
        update_db
        ;;
    check)
        check_setup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❓ Неизвестная команда: $1"
        show_help
        exit 1
        ;;
esac

exit 0
