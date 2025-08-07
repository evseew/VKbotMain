#!/bin/bash

# Создаем функцию для остановки бота
stop_bot() {
    local pid=$1
    echo "📦 Останавливаем бота с PID: $pid"
    
    # Сначала отправляем SIGTERM для корректного завершения
    kill -15 $pid
    
    # Ждем до 10 секунд для корректного завершения
    for i in {1..10}; do
        if ! ps -p $pid > /dev/null; then
            echo "✅ Бот успешно остановлен"
            return 0
        fi
        echo "⏳ Ожидаем завершения процесса... $i/10"
        sleep 1
    done
    
    # Если процесс всё еще работает, применяем SIGKILL
    if ps -p $pid > /dev/null; then
        echo "⚠️ Процесс не завершился корректно, применяем принудительное завершение"
        kill -9 $pid
        sleep 1
        
        if ! ps -p $pid > /dev/null; then
            echo "✅ Бот принудительно остановлен"
            return 0
        else
            echo "❌ Не удалось остановить бота"
            return 1
        fi
    fi
}

# Остановка бота
if [ -f bot.pid ]; then
    echo "🔍 Найден файл bot.pid"
    PID=$(cat bot.pid)
    
    if ps -p $PID > /dev/null; then
        stop_bot $PID
        if [ $? -eq 0 ]; then
            rm bot.pid
        fi
    else
        echo "⚠️ Процесс с PID $PID не найден"
        rm bot.pid
        echo "🗑️ Удален устаревший файл bot.pid"
    fi
else
    echo "⚠️ Файл bot.pid не найден, ищем процесс бота..."
    BOT_PID=$(ps aux | grep "python3\? bot.py" | grep -v grep | awk '{print $2}')
    
    if [ -n "$BOT_PID" ]; then
        echo "🔍 Найден процесс бота с PID: $BOT_PID"
        stop_bot $BOT_PID
    else
        echo "ℹ️ Процесс бота не найден. Возможно, бот не запущен."
    fi
fi

# Проверка запущенности после остановки
if pgrep -f "python3\? bot.py" > /dev/null; then
    echo "❌ Внимание! Бот все еще запущен. Проверьте процессы вручную."
else
    echo "✅ Бот не запущен."
fi 