# VK Bot with OpenAI and Google Drive

ВК-бот с интеграцией OpenAI и векторной базой данных документов из Google Drive для автоматических ответов в сообществах.

## Особенности

- 🤖 Автоматические ответы с помощью OpenAI GPT
- 📚 Векторная база знаний из документов Google Drive
- 🔄 Автоматическое обновление базы знаний
- 📊 Логирование и мониторинг
- 🛠️ Управление через systemd службу
- 📝 Поддержка PDF, DOCX, MD файлов

## Быстрое развёртывание на VPS

### Автоматическая установка

```bash
# Скачивание и запуск установки
wget https://raw.githubusercontent.com/evseew/VKbotMain/main/deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

### Настройка после установки

1. **Заполните переменные окружения:**
```bash
cd /root/VKbotMain
nano .env
```

Добавьте:
```env
VK_GROUP_TOKEN=ваш_токен_группы_вк
OPENAI_API_KEY=ваш_ключ_openai
GOOGLE_FOLDER_ID=id_папки_google_drive
VK_API_VERSION=5.199
```

2. **Добавьте Google Service Account ключ:**
```bash
nano /root/VKbotMain/service-account-key.json
# Вставьте содержимое JSON файла
```

3. **Запустите бота:**
```bash
./control.sh start
./control.sh status
```

## Управление ботом

### Основные команды
```bash
./control.sh start    # Запуск бота
./control.sh stop     # Остановка бота  
./control.sh restart  # Перезапуск бота
./control.sh status   # Статус бота
./control.sh logs     # Просмотр логов
./control.sh check    # Проверка конфигурации
```

### Управление через systemd
```bash
sudo systemctl start google-vk-bot
sudo systemctl stop google-vk-bot
sudo systemctl status google-vk-bot
sudo systemctl restart google-vk-bot
```

## Настройка интеграции

### 1. VK API
1. Создайте сообщество ВКонтакте
2. В настройках сообщества → "Работа с API" → "Ключи доступа"
3. Создайте ключ с правами на сообщения
4. В "Callback API" включите события: message_new, message_reply

### 2. OpenAI API
1. Зарегистрируйтесь на https://platform.openai.com
2. Создайте API ключ в разделе API Keys
3. Убедитесь что у аккаунта есть доступ к GPT-3.5/GPT-4

### 3. Google Drive API
1. Создайте проект в Google Cloud Console
2. Включите Google Drive API
3. Создайте Service Account и скачайте JSON ключ
4. Поделитесь папкой Google Drive с email Service Account

## Мониторинг

### Логи
```bash
# Основные логи бота
tail -f /root/VKbotMain/logs/bot.log

# Логи systemd службы
journalctl -u google-vk-bot -f

# Контекстные логи
ls /root/VKbotMain/logs/context_logs/
```

### Проверка работоспособности
```bash
# Статус бота
./control.sh status

# Проверка конфигурации
./control.sh check

# Проверка базы данных
ls /root/VKbotMain/local_vector_db/
```

## Обновление

```bash
cd /root/VKbotMain
git pull origin main
./control.sh restart
```

## Устранение проблем

### Бот не запускается
```bash
# Проверьте логи
./control.sh logs

# Проверьте конфигурацию
./control.sh check

# Проверьте переменные окружения
cat .env
```

### Проблемы с API
- **VK API**: Проверьте токен группы и права доступа
- **OpenAI**: Проверьте баланс аккаунта и лимиты
- **Google Drive**: Проверьте права Service Account на папку

### Проблемы с базой данных
```bash
# Очистка и пересоздание базы
rm -rf local_vector_db/
./control.sh restart
```

## Структура проекта

```
VKbotMain/
├── bot.py                    # Основной файл бота
├── .env                      # Переменные окружения
├── service-account-key.json  # Google Service Account ключ
├── requirements.txt          # Python зависимости
├── control.sh               # Скрипт управления
├── deploy.sh                # Скрипт развёртывания
├── google-vk-bot.service    # Конфигурация systemd
├── logs/                    # Логи бота
├── local_vector_db/         # Векторная база данных
└── history_vk/              # История чатов
```

## Зависимости

- Python 3.8+
- vk-api
- openai
- chromadb
- langchain
- python-dotenv

## Автозапуск

Бот автоматически настраивается на запуск при старте системы через systemd.

```bash
# Проверить статус автозапуска
systemctl is-enabled google-vk-bot

# Включить автозапуск
systemctl enable google-vk-bot

# Отключить автозапуск  
systemctl disable google-vk-bot
```