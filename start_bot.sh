#!/bin/bash

# Создаем директорию для логов, если она не существует
mkdir -p logs
mkdir -p logs/context_logs

# Проверяем, не запущен ли уже бот
if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    if ps -p $PID > /dev/null; then
        echo "⚠️ Бот уже запущен с PID: $PID"
        echo "Для перезапуска используйте: ./restart.sh"
        exit 1
    else
        echo "⚠️ Найден устаревший PID файл, удаляем..."
        rm bot.pid
    fi
fi

# Выводим полный путь к виртуальному окружению
echo "🔄 Активируем окружение: $(pwd)/new_venv"

# Активация окружения
source "$(pwd)/new_venv/bin/activate"

# Проверка окружения
if ! python3 -c "import openai" &> /dev/null; then
    echo "⚠️ Библиотека OpenAI не установлена, устанавливаем..."
    pip install openai
fi

# Дополнительно устанавливаем необходимые библиотеки
pip install langchain-huggingface

# Проверка наличия файла .env
if [ ! -f .env ]; then
    echo "❌ Ошибка: файл .env не найден!"
    exit 1
fi

# Запуск бота в фоновом режиме с логированием
echo "🚀 Запуск бота..."
source .env
nohup python3 bot.py > logs/bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > bot.pid
echo "✅ Бот запущен, PID: $BOT_PID"

# Проверка запуска через 2 секунды
sleep 2
if ps -p $BOT_PID > /dev/null; then
    echo "✅ Процесс бота успешно работает"
    echo "📊 Вывод логов (Ctrl+C для выхода):"
    tail -f logs/bot.log
else
    echo "❌ Ошибка: бот не удалось запустить, проверьте логи: logs/bot.log"
    exit 1
fi