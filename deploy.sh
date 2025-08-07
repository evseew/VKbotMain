#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода информации
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка, что скрипт запущен от root
if [ "$EUID" -ne 0 ]; then
    print_error "Скрипт должен быть запущен от root"
    echo "Используйте: sudo ./deploy.sh"
    exit 1
fi

print_info "🚀 Начинаем развёртывание VK Bot на VPS"

# Определяем директорию проекта
PROJECT_DIR="/root/VKbotMain"
SERVICE_NAME="google-vk-bot"

# 1. Обновление системы
print_info "📦 Обновляем систему..."
apt update && apt upgrade -y

# 2. Установка необходимых пакетов
print_info "🔧 Устанавливаем необходимые пакеты..."
apt install -y python3 python3-pip python3-venv git curl wget htop nano

# 3. Проверяем, существует ли уже проект
if [ -d "$PROJECT_DIR" ]; then
    print_warning "Директория проекта уже существует. Обновляем..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    print_info "📥 Клонируем репозиторий..."
    git clone https://github.com/evseew/VKbotMain.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# 4. Создание виртуального окружения
print_info "🐍 Создаём виртуальное окружение..."
python3 -m venv new_venv
source new_venv/bin/activate

# 5. Установка зависимостей
print_info "📋 Устанавливаем зависимости..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. Настройка конфигурации
print_info "⚙️  Настраиваем конфигурацию..."

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    print_warning "Файл .env не найден. Создаём из шаблона..."
    cp .env.example .env
    print_warning "❗ ВАЖНО: Отредактируйте файл .env с вашими API ключами:"
    print_warning "   nano $PROJECT_DIR/.env"
    echo
fi

# Проверяем наличие Google сервисного ключа
if [ ! -f "service-account-key.json" ]; then
    print_warning "❗ ВАЖНО: Загрузите файл service-account-key.json в директорию проекта"
    echo
fi

# 7. Создание необходимых директорий
print_info "📁 Создаём необходимые директории..."
mkdir -p logs logs/context_logs local_vector_db history_vk

# 8. Настройка прав доступа
print_info "🔐 Настраиваем права доступа..."
chown -R root:root "$PROJECT_DIR"
chmod +x *.sh

# 9. Установка systemd службы
print_info "🔧 Настраиваем systemd службу..."

# Обновляем пути в service файле
sed -i "s|/root/GoogleVKBot|$PROJECT_DIR|g" google-vk-bot.service

# Копируем service файл
cp google-vk-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# 10. Проверка конфигурации
print_info "🔍 Проверяем конфигурацию..."
./control.sh check

print_success "🎉 Развёртывание завершено!"
echo
print_info "📋 Следующие шаги:"
echo "1. Отредактируйте файл .env: nano $PROJECT_DIR/.env"
echo "2. Загрузите файл service-account-key.json в $PROJECT_DIR"
echo "3. Запустите бота: ./control.sh start"
echo "4. Проверьте статус: ./control.sh status"
echo "5. Просмотр логов: ./control.sh logs"
echo
print_info "📖 Управление ботом:"
echo "• Запуск: ./control.sh start"
echo "• Остановка: ./control.sh stop"
echo "• Перезапуск: ./control.sh restart"
echo "• Статус: ./control.sh status"
echo "• Логи: ./control.sh logs" 