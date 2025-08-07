# 🚀 Развёртывание VK Bot на VPS

## Быстрый старт

### 1. Подготовка репозитория

Загрузите проект на GitHub:

```bash
# В локальной директории проекта
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/evseew/VKbotMain.git
git push -u origin main
```

**❗ Важно:** Username уже настроен в файле `deploy.sh`

### 2. Развёртывание на VPS

Подключитесь к VPS и выполните:

```bash
# Подключение к VPS
ssh root@YOUR_VPS_IP

# Скачивание и запуск установки
wget https://raw.githubusercontent.com/evseew/VKbotMain/main/deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

### 3. Настройка окружения

После установки настройте конфигурацию:

```bash
cd /root/VKbotMain

# Отредактируйте переменные окружения
nano .env
```

Заполните следующие обязательные поля:
- `VK_GROUP_TOKEN` - токен группы ВКонтакте
- `OPENAI_API_KEY` - ключ OpenAI API
- `GOOGLE_FOLDER_ID` - ID папки Google Drive

### 4. Загрузка Google Service Account

Загрузите файл `service-account-key.json`:

```bash
# Способ 1: через scp с локальной машины
scp service-account-key.json root@YOUR_VPS_IP:/root/VKbotMain/

# Способ 2: создать файл и вставить содержимое
nano /root/VKbotMain/service-account-key.json
```

### 5. Запуск бота

```bash
cd /root/VKbotMain

# Запуск
./control.sh start

# Проверка статуса
./control.sh status

# Просмотр логов
./control.sh logs
```

## Управление ботом

### Команды управления

```bash
./control.sh start    # Запуск бота
./control.sh stop     # Остановка бота  
./control.sh restart  # Перезапуск бота
./control.sh status   # Статус бота
./control.sh logs     # Просмотр логов
./control.sh check    # Проверка конфигурации
```

### Обновление бота

```bash
cd /root/VKbotMain
git pull origin main
./control.sh restart
```

### Мониторинг

```bash
# Статус службы systemd
systemctl status google-vk-bot

# Живые логи
tail -f /root/VKbotMain/logs/bot.log

# Использование ресурсов
htop
```

## Структура файлов на VPS

```
/root/VKbotMain/
├── bot.py                    # Основной файл бота
├── .env                      # Переменные окружения (создаётся из .env.example)
├── service-account-key.json  # Ключ Google Service Account (загружаете вручную)
├── requirements.txt          # Python зависимости
├── control.sh               # Скрипт управления ботом
├── deploy.sh                # Скрипт развёртывания
├── google-vk-bot.service    # Конфигурация systemd
├── logs/                    # Логи бота
├── local_vector_db/         # Векторная база данных
├── history_vk/              # История чатов
└── new_venv/                # Виртуальное окружение Python
```

## Решение проблем

### Бот не запускается

1. Проверьте логи:
```bash
./control.sh logs
# или
cat /root/VKbotMain/logs/bot.log
```

2. Проверьте конфигурацию:
```bash
./control.sh check
```

3. Проверьте переменные окружения:
```bash
cat /root/VKbotMain/.env
```

### Проблемы с зависимостями

```bash
cd /root/VKbotMain
source new_venv/bin/activate
pip install -r requirements.txt
```

### Проблемы с правами доступа

```bash
chown -R root:root /root/VKbotMain
chmod +x /root/VKbotMain/*.sh
```

### Очистка и переустановка

```bash
# Остановка службы
systemctl stop google-vk-bot
systemctl disable google-vk-bot

# Удаление проекта
rm -rf /root/VKbotMain

# Повторная установка
./deploy.sh
```

## Автозапуск

Бот автоматически настраивается на запуск при старте системы через systemd.

Проверить автозапуск:
```bash
systemctl is-enabled google-vk-bot
```

Отключить автозапуск:
```bash
systemctl disable google-vk-bot
```

Включить автозапуск:
```bash
systemctl enable google-vk-bot
```

## Бэкап

### Создание бэкапа

```bash
# Бэкап конфигурации и данных
tar -czf vkbot-backup-$(date +%Y%m%d).tar.gz \
  /root/VKbotMain/.env \
  /root/VKbotMain/service-account-key.json \
  /root/VKbotMain/local_vector_db/ \
  /root/VKbotMain/history_vk/
```

### Восстановление бэкапа

```bash
# Распаковка бэкапа
tar -xzf vkbot-backup-YYYYMMDD.tar.gz -C /
``` 