import sys
import os
import time as time_module # Используется
import asyncio
import logging
import datetime # Используется datetime.datetime, datetime.time, datetime.date, datetime.timedelta
# from datetime import timezone # Удалено, будем использовать pytz.utc
import glob # Используется
import io # Используется
from io import BytesIO # Используется
# import signal # Удалено, не используется явно
# from collections import deque # Удалено, не используется
from collections import defaultdict # Используется
from typing import Optional, List, Dict, Any, Union # Добавлены для лучшей типизации

import pytz # Используется
import shutil # Используется
import requests # Используется
import json # Используется
import random # Используется
import re # Используется
import threading # Используется

# --- Dependency Imports ---
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEvent, VkBotEventType
from vk_api.utils import get_random_id

import openai
import chromadb
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import docx
import PyPDF2

# LangChain components for specific tasks
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
# from langchain_core.documents import Document # Удалено, если не используется напрямую

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
# VK API Settings
VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
VK_API_VERSION = os.getenv("VK_API_VERSION", "5.199")
VK_API_REQUESTS_PER_SECOND = int(os.getenv("VK_API_REQUESTS_PER_SECOND", "3"))
VK_API_TIMEOUT_SECONDS = int(os.getenv("VK_API_TIMEOUT_SECONDS", "30"))

# Исправление №9: Преобразование VK_GROUP_ID в int сразу
VK_GROUP_ID_STR = os.getenv("VK_GROUP_ID")
if not VK_GROUP_ID_STR:
    raise ValueError("❌ Ошибка: VK_GROUP_ID не найден в .env!")
try:
    VK_GROUP_ID = int(VK_GROUP_ID_STR)
except ValueError:
    raise ValueError("❌ Ошибка: VK_GROUP_ID должен быть числом в .env!")

# OpenAI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
OPENAI_RUN_TIMEOUT_SECONDS = int(os.getenv("OPENAI_RUN_TIMEOUT_SECONDS", "90"))
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
OPENAI_RETRY_DELAY_SECONDS = int(os.getenv("OPENAI_RETRY_DELAY_SECONDS", "2"))

# Google Drive Settings
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", 'service-account-key.json')
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# User/Manager IDs
try:
    ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
except (TypeError, ValueError):
    raise ValueError("❌ Ошибка: ADMIN_USER_ID должен быть числом в .env!")

try:
    raw_manager_ids = os.getenv("MANAGER_USER_IDS", "").split(',')
    MANAGER_USER_IDS = [int(id_str) for id_str in raw_manager_ids if id_str.strip()]
except ValueError:
     raise ValueError("❌ Ошибка: MANAGER_USER_IDS в .env должны быть числами, разделенными запятыми!")

# NEW BUSINESS FEATURES
SILENCE_AUTO_REMOVE_DAYS = int(os.getenv("SILENCE_AUTO_REMOVE_DAYS", "60"))
BYPASS_SYMBOL = os.getenv("BYPASS_SYMBOL", "§")

# Vector Store Settings
VECTOR_DB_BASE_PATH = os.getenv("VECTOR_DB_BASE_PATH", "./local_vector_db")
ACTIVE_DB_INFO_FILE = os.getenv("ACTIVE_DB_INFO_FILE", "active_db_info.txt")
VECTOR_DB_COLLECTION_NAME = os.getenv("VECTOR_DB_COLLECTION_NAME", "documents_collection")
RELEVANT_CONTEXT_COUNT = int(os.getenv("RELEVANT_CONTEXT_COUNT", "3"))
VECTOR_SEARCH_TIMEOUT_SECONDS = int(os.getenv("VECTOR_SEARCH_TIMEOUT_SECONDS", "10"))

# Message Processing
MESSAGE_COOLDOWN_SECONDS = int(os.getenv("MESSAGE_COOLDOWN_SECONDS", "3"))
MESSAGE_BUFFER_SECONDS = int(os.getenv("MESSAGE_BUFFER_SECONDS", "4"))
MESSAGE_HISTORY_DAYS = int(os.getenv("MESSAGE_HISTORY_DAYS", "100"))
MAX_HISTORY_REPLAY_MESSAGES = int(os.getenv("MAX_HISTORY_REPLAY_MESSAGES", "20"))
MESSAGE_LIFETIME_DAYS = int(os.getenv("MESSAGE_LIFETIME_DAYS", "100"))

# Scheduling
DAILY_UPDATE_HOUR = int(os.getenv("DAILY_UPDATE_HOUR", "5"))
CLEANUP_INTERVAL_HOURS = int(os.getenv("CLEANUP_INTERVAL_HOURS", "24"))
INACTIVE_CHECK_INTERVAL_HOURS = int(os.getenv("INACTIVE_CHECK_INTERVAL_HOURS", "24"))
LOG_RETENTION_SECONDS = int(os.getenv("LOG_RETENTION_SECONDS", "86400"))

# VK LongPoll Settings
VK_LONGPOLL_MAX_RECONNECT_ATTEMPTS = int(os.getenv("VK_LONGPOLL_MAX_RECONNECT_ATTEMPTS", "5"))
VK_LONGPOLL_RECONNECT_DELAY_SECONDS = int(os.getenv("VK_LONGPOLL_RECONNECT_DELAY_SECONDS", "30"))

# Performance Settings
MAX_CONCURRENT_USERS = int(os.getenv("MAX_CONCURRENT_USERS", "50"))

# Logging Settings
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
ENABLE_CONTEXT_LOGGING = os.getenv("ENABLE_CONTEXT_LOGGING", "True").lower() == "true"
ENABLE_PERFORMANCE_LOGGING = os.getenv("ENABLE_PERFORMANCE_LOGGING", "False").lower() == "true"

# Timezone Settings (Work hours removed as requested)
TIMEZONE_STR = os.getenv("TIMEZONE_STR", "Asia/Yekaterinburg")

# Логгер инициализируется позже, поэтому здесь используем logging.error
try:
    TARGET_TZ = pytz.timezone(TIMEZONE_STR)
except pytz.UnknownTimeZoneError:
    logging.error(f"Неизвестный часовой пояс '{TIMEZONE_STR}' в .env. Используется UTC.")
    TARGET_TZ = pytz.utc

# Commands
CMD_SPEAK = os.getenv("CMD_SPEAK", "speak")
CMD_UPDATE = os.getenv("CMD_UPDATE", "/update")
CMD_RESET = os.getenv("CMD_RESET", "/reset")
CMD_RESET_ALL = os.getenv("CMD_RESET_ALL", "/reset_all")
CMD_CHECK_DB = os.getenv("CMD_CHECK_DB", "/check_db")
CMD_STATUS = os.getenv("CMD_STATUS", "/status")
CMD_HELP = os.getenv("CMD_HELP", "/help")
CMD_SILENCE = os.getenv("CMD_SILENCE", "/silence")
CMD_UNSILENCE = os.getenv("CMD_UNSILENCE", "/unsilence")
CMD_LIST_SILENT = os.getenv("CMD_LIST_SILENT", "/list_silent")
CMD_SILENCE_USER = os.getenv("CMD_SILENCE_USER", "/silence_user")
CMD_UNSILENCE_USER = os.getenv("CMD_UNSILENCE_USER", "/unsilence_user")
CMD_CHECK_USER = os.getenv("CMD_CHECK_USER", "/check_user")
CMD_CLEAR_HISTORY = os.getenv("CMD_CLEAR_HISTORY", "/clear_history")

# Logging Settings
LOGS_DIR = "./logs/context_logs"
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Validate Configuration ---
required_vars = {
    "VK_GROUP_TOKEN": VK_GROUP_TOKEN,
    "VK_GROUP_ID": VK_GROUP_ID, # Уже int
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "ASSISTANT_ID": ASSISTANT_ID,
    "FOLDER_ID": FOLDER_ID,
    "ADMIN_USER_ID": ADMIN_USER_ID
}
missing_vars_list = [name for name, value in required_vars.items() if not value and value !=0] # 0 может быть валидным ID для VK_GROUP_ID (хотя обычно нет)
if missing_vars_list:
    raise ValueError(f"❌ Ошибка: Не найдены переменные в .env: {', '.join(missing_vars_list)}")

# --- Global State (In-Memory) ---
user_threads: Dict[str, str] = {}
user_processing_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
user_last_message_time: Dict[int, datetime.datetime] = {}
chat_silence_state: Dict[int, bool] = {}
MY_PENDING_RANDOM_IDS: set = set()

pending_messages: Dict[int, List[str]] = {}
user_message_timers: Dict[int, asyncio.Task] = {}

# NEW: History system variables
user_messages: Dict[int, List[Dict[str, Any]]] = {}
user_last_activity: Dict[int, datetime.datetime] = {}

# File constants
SILENCE_STATE_FILE = "silence_state.json"
HISTORY_DIR = "history_vk"

# Гибридный подход: отслеживание времени изменения файла молчания
silence_file_last_mtime: float = 0.0
USER_THREADS_FILE = "user_threads_vk.json"

# Create history directory
os.makedirs(HISTORY_DIR, exist_ok=True)

# --- Initialize API Clients ---
try:
    openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    logger.info("Клиент OpenAI инициализирован.")
except Exception as e:
    logger.critical(f"Не удалось инициализировать клиент OpenAI: {e}", exc_info=True)
    sys.exit(1)

try:
    vk_session_api = vk_api.VkApi(token=VK_GROUP_TOKEN, api_version=VK_API_VERSION)
    logger.info("VK API сессия инициализирована (СИНХРОННО).")
except vk_api.AuthError as e:
     logger.critical(f"Ошибка авторизации VK: {e}. Проверьте токен группы.", exc_info=True)
     sys.exit(1)
except Exception as e:
    logger.critical(f"Ошибка инициализации VK API: {e}", exc_info=True)
    sys.exit(1)

vector_collection: Optional[chromadb.api.models.Collection.Collection] = None

def _get_active_db_subpath() -> Optional[str]:
    try:
        active_db_info_filepath = os.path.join(VECTOR_DB_BASE_PATH, ACTIVE_DB_INFO_FILE)
        if os.path.exists(active_db_info_filepath):
            with open(active_db_info_filepath, "r", encoding="utf-8") as f:
                active_subdir = f.read().strip()
            if active_subdir:
                if os.path.isdir(os.path.join(VECTOR_DB_BASE_PATH, active_subdir)):
                    logger.info(f"Найдена активная поддиректория БД: '{active_subdir}'")
                    return active_subdir
                else:
                    logger.warning(f"В файле '{ACTIVE_DB_INFO_FILE}' указана несуществующая поддиректория: '{active_subdir}'")
                    return None    
            else:
                logger.warning(f"Файл '{ACTIVE_DB_INFO_FILE}' пуст.")
                return None
        else:
            logger.info(f"Файл информации об активной БД '{ACTIVE_DB_INFO_FILE}' не найден.")
            return None
    except Exception as e:
        logger.error(f"Ошибка при чтении файла информации об активной БД: {e}", exc_info=True)
        return None

async def _initialize_active_vector_collection():
    global vector_collection
    active_subdir = _get_active_db_subpath()
    if active_subdir:
        active_db_full_path = os.path.join(VECTOR_DB_BASE_PATH, active_subdir)
        try:
            os.makedirs(VECTOR_DB_BASE_PATH, exist_ok=True)
            os.makedirs(active_db_full_path, exist_ok=True) 
            
            chroma_client_init = chromadb.PersistentClient(path=active_db_full_path)
            vector_collection = chroma_client_init.get_or_create_collection(
                name=VECTOR_DB_COLLECTION_NAME,
            )
            logger.info(f"Успешно подключено к ChromaDB: '{active_db_full_path}'. Коллекция: '{VECTOR_DB_COLLECTION_NAME}'.")
            if vector_collection:
                logger.info(f"Документов в активной коллекции при старте: {vector_collection.count()}")
        except Exception as e:
            logger.error(f"Ошибка инициализации ChromaDB для пути '{active_db_full_path}': {e}. Поиск по базе знаний будет недоступен.", exc_info=True)
            vector_collection = None
    else:
        logger.warning("Не удалось определить активную директорию БД. База знаний будет недоступна.")
        vector_collection = None

def get_drive_service():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=credentials)
        logger.info("Сервис Google Drive инициализирован.")
        return service
    except FileNotFoundError:
        logger.error(f"Файл ключа Google Service Account не найден: {SERVICE_ACCOUNT_FILE}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении сервиса Google Drive: {e}", exc_info=True)
        return None

drive_service = get_drive_service()

# --- Helper Functions ---
def get_user_key(user_id: int) -> str:
    return str(user_id)

# Work hours functionality removed as requested

# --- History Management Functions ---
def add_message_to_file_history(user_id: int, role: str, content: str):
    """Сохранение сообщения в JSONL файл (синхронно)"""
    filename = os.path.join(HISTORY_DIR, f"history_{user_id}.jsonl")
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "role": role,
        "content": content
    }
    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.debug(f"Сообщение сохранено в историю для user_id={user_id}")
    except Exception as e:
        logger.error(f"Ошибка сохранения истории для user_id={user_id}: {e}", exc_info=True)

def load_user_history_from_file(user_id: int, days: int = None) -> List[Dict]:
    """Загрузка истории пользователя из файла"""
    if days is None:
        days = MESSAGE_HISTORY_DAYS
    
    filename = os.path.join(HISTORY_DIR, f"history_{user_id}.jsonl")
    if not os.path.exists(filename):
        logger.debug(f"Файл истории для user_id={user_id} не найден")
        return []
    
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    history = []
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    ts = datetime.datetime.fromisoformat(entry["timestamp"])
                    if ts >= cutoff:
                        history.append({
                            'role': entry['role'],
                            'content': entry['content'],
                            'timestamp': ts
                        })
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue  # пропускаем битые строки
        
        logger.info(f"Загружено {len(history)} сообщений из истории для user_id={user_id}")
        return history
    except Exception as e:
        logger.error(f"Ошибка загрузки истории для user_id={user_id}: {e}", exc_info=True)
        return []

def save_user_threads_to_file():
    """Сохранение соответствия user_id ↔ thread_id в файл"""
    try:
        # Преобразуем ключи в строки для JSON
        data_to_save = {}
        for user_key, thread_id in user_threads.items():
            # user_key уже строка из get_user_key()
            data_to_save[user_key] = thread_id
            
        with open(USER_THREADS_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        logger.debug(f"Соответствия user_threads сохранены в {USER_THREADS_FILE}")
    except Exception as e:
        logger.error(f"Ошибка сохранения user_threads: {e}", exc_info=True)

def load_user_threads_from_file():
    """Загрузка соответствия user_id ↔ thread_id из файла"""
    global user_threads
    if not os.path.exists(USER_THREADS_FILE):
        logger.info(f"Файл {USER_THREADS_FILE} не найден. Запуск с пустыми тредами.")
        return
        
    try:
        with open(USER_THREADS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            user_threads.clear()
            for user_key_str, thread_id in data.items():
                user_threads[user_key_str] = thread_id
        logger.info(f"Загружено {len(user_threads)} соответствий user_threads из файла")
    except Exception as e:
        logger.error(f"Ошибка загрузки user_threads из файла: {e}", exc_info=True)

async def add_message_to_history(user_id: int, role: str, content: str):
    """Двойное сохранение: в память + в файл"""
    try:
        # Сохраняем в файл (синхронно)
        add_message_to_file_history(user_id, role, content)
        
        # Сохраняем в память
        if user_id not in user_messages:
            user_messages[user_id] = []
        user_messages[user_id].append({
            'role': role,
            'content': content,
            'timestamp': datetime.datetime.now()
        })
        
        # Обновляем активность
        user_last_activity[user_id] = datetime.datetime.now()
        
        logger.debug(f"Сообщение добавлено в историю для user_id={user_id}: {role}")
    except Exception as e:
        logger.error(f"Ошибка в add_message_to_history для user_id={user_id}: {e}", exc_info=True)

async def replay_history_to_thread(user_id: int, thread_id: str, max_messages: int = None) -> int:
    """Досылка истории в новый OpenAI тред. Возвращает количество успешно воспроизведённых сообщений."""
    if max_messages is None:
        max_messages = MAX_HISTORY_REPLAY_MESSAGES
    
    replayed_count = 0
    try:
        # Загружаем историю из файла, если её нет в памяти
        if user_id not in user_messages:
            history_from_file = load_user_history_from_file(user_id)
            if history_from_file:
                user_messages[user_id] = history_from_file
        
        # Берём только последние max_messages
        history = user_messages.get(user_id, [])
        if not history:
            logger.debug(f"История для user_id={user_id} пуста, нечего досылать")
            return 0
            
        recent_history = history[-max_messages:] if len(history) > max_messages else history
        
        logger.info(f"Досылка {len(recent_history)} сообщений в тред {thread_id} для user_id={user_id}")
        
        for msg in recent_history:
            try:
                await openai_client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role=msg['role'],
                    content=msg['content']
                )
                logger.debug(f"Сообщение {msg['role']} досланo в тред {thread_id}")
                replayed_count += 1
            except Exception as e_msg:
                logger.warning(f"Ошибка досылки сообщения в тред {thread_id}: {e_msg}")
                # Продолжаем досылать остальные
        
        logger.info(f"Досылка истории в тред {thread_id} завершена. Успешно: {replayed_count}/{len(recent_history)}")
        return replayed_count
    except Exception as e:
        logger.error(f"Ошибка досылки истории в тред {thread_id} для user_id={user_id}: {e}", exc_info=True)
        return replayed_count

async def send_vk_message(peer_id: int, message: str):
    if not message:
        logger.warning(f"Попытка отправить пустое сообщение в peer_id={peer_id}")
        return
    current_random_id = 0 # Инициализация для блока finally
    try:
        current_random_id = vk_api.utils.get_random_id()
        MY_PENDING_RANDOM_IDS.add(current_random_id)
        logger.debug(f"Добавлен random_id {current_random_id} в MY_PENDING_RANDOM_IDS для peer_id={peer_id}")

        await asyncio.to_thread(
            vk_session_api.method,
            'messages.send',
            {
                'peer_id': peer_id,
                'message': message,
                'random_id': current_random_id
            }
        )
    except vk_api.exceptions.ApiError as e:
        logger.error(f"Ошибка VK API при отправке сообщения в peer_id={peer_id}: {e}", exc_info=True)
        # Исправление №2: Упрощение условия
        if current_random_id in MY_PENDING_RANDOM_IDS:
            MY_PENDING_RANDOM_IDS.remove(current_random_id)
            logger.debug(f"Удален random_id {current_random_id} из MY_PENDING_RANDOM_IDS из-за ошибки отправки для peer_id={peer_id}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при отправке сообщения в peer_id={peer_id}: {e}", exc_info=True)
        # Исправление №2: Упрощение условия
        if current_random_id in MY_PENDING_RANDOM_IDS:
            MY_PENDING_RANDOM_IDS.remove(current_random_id)
            logger.debug(f"Удален random_id {current_random_id} из MY_PENDING_RANDOM_IDS из-за ошибки отправки для peer_id={peer_id}")


async def set_typing_activity(peer_id: int):
     try:
        await asyncio.to_thread(
             vk_session_api.method,
             'messages.setActivity',
             {'type': 'typing', 'peer_id': peer_id}
         )
     except Exception as e:
         logger.warning(f"Не удалось установить статус 'typing' для peer_id={peer_id}: {e}")

# --- Silence Mode Management (Permanent Only) ---
async def save_silence_state_to_file():
    logger.debug("Сохранение состояния постоянных режимов молчания в файл...")
    data_to_save = {str(peer_id): True for peer_id, is_silent in chat_silence_state.items() if is_silent}
    try:
        def _save():
            with open(SILENCE_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4)
        await asyncio.to_thread(_save)
        logger.info(f"Состояние постоянных режимов молчания сохранено в {SILENCE_STATE_FILE}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении состояния режимов молчания: {e}", exc_info=True)

async def load_silence_state_from_file():
    global chat_silence_state, silence_file_last_mtime
    logger.info("Загрузка состояния постоянных режимов молчания из файла...")
    try:
        def _load():
            if not os.path.exists(SILENCE_STATE_FILE):
                logger.info(f"Файл {SILENCE_STATE_FILE} не найден. Пропускаем загрузку.")
                return None
            with open(SILENCE_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        
        loaded_data = await asyncio.to_thread(_load)
        
        # Обновляем время последнего изменения файла
        if os.path.exists(SILENCE_STATE_FILE):
            silence_file_last_mtime = os.path.getmtime(SILENCE_STATE_FILE)
            logger.debug(f"Инициализировано время файла молчания: {silence_file_last_mtime}")

        if not loaded_data:
            # Если файл пустой или данных нет - очищаем состояние
            chat_silence_state.clear()
            logger.info("Файл молчания пуст. Сброшено состояние молчания.")
            return

        # КРИТИЧНО: Очищаем старое состояние перед загрузкой нового
        chat_silence_state.clear()
        logger.debug("Очищено старое состояние молчания перед загрузкой нового.")

        restored_count = 0
        for peer_id_str, should_be_silent in loaded_data.items():
            try:
                peer_id = int(peer_id_str)
                if should_be_silent:
                    chat_silence_state[peer_id] = True
                    logger.info(f"Восстановлен постоянный режим молчания для peer_id={peer_id}")
                    restored_count += 1
            except (ValueError, KeyError) as e:
                logger.error(f"Ошибка при обработке записи для peer_id_str='{peer_id_str}': {e}", exc_info=True)
        
        if restored_count > 0:
            logger.info(f"Успешно восстановлено {restored_count} состояний постоянного молчания.")
        else:
            logger.info("Активных состояний постоянного молчания для восстановления не найдено.")
    except FileNotFoundError: # Обработка FileNotFoundError здесь, если _load() вернет None из-за отсутствия файла
        logger.info(f"Файл {SILENCE_STATE_FILE} не найден. Запуск с чистым состоянием молчания.")
    except json.JSONDecodeError:
        logger.error(f"Ошибка декодирования JSON из файла {SILENCE_STATE_FILE}. Возможно, файл поврежден.")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при загрузке состояния режимов молчания: {e}", exc_info=True)

async def silence_user(peer_id: int):
    if await is_chat_silent_smart(peer_id):
        logger.info(f"Постоянный режим молчания для peer_id={peer_id} уже был активен.")
        return
    logger.info(f"Активация постоянного режима молчания для peer_id={peer_id}.")
    chat_silence_state[peer_id] = True
    await save_silence_state_to_file()

async def unsilence_user(peer_id: int):
    if peer_id in chat_silence_state:
        logger.info(f"Ручная деактивация (командой speak) режима молчания для peer_id={peer_id}.")
        chat_silence_state.pop(peer_id)
        await save_silence_state_to_file()
    else:
         logger.debug(f"Попытка снять молчание для peer_id={peer_id}, но бот и так был активен.")

async def is_chat_silent_smart(peer_id: int) -> bool:
    """
    Умная проверка состояния молчания с автоматической синхронизацией файла.
    Перезагружает файл только при его изменении.
    """
    global silence_file_last_mtime
    
    try:
        # Получаем время последнего изменения файла
        if os.path.exists(SILENCE_STATE_FILE):
            current_mtime = os.path.getmtime(SILENCE_STATE_FILE)
            
            # Если файл изменился с последней проверки
            if current_mtime > silence_file_last_mtime:
                logger.debug(f"Файл {SILENCE_STATE_FILE} изменился (mtime: {current_mtime}). Перезагружаем состояние молчания.")
                await load_silence_state_from_file()
                silence_file_last_mtime = current_mtime
            # Если файл не изменился, используем кэш из памяти
        else:
            # Файл не существует - сбрасываем кэш
            if silence_file_last_mtime > 0:
                logger.debug(f"Файл {SILENCE_STATE_FILE} удалён. Сбрасываем состояние молчания.")
                chat_silence_state.clear()
                silence_file_last_mtime = 0
                
    except Exception as e:
        logger.warning(f"Ошибка при проверке времени файла {SILENCE_STATE_FILE}: {e}")
        # В случае ошибки используем текущее состояние из памяти
    
    # Возвращаем состояние из кэша в памяти
    return chat_silence_state.get(peer_id, False)

# --- Функции буферизации сообщений ---
async def schedule_buffered_processing(peer_id: int, original_user_id: int):
    log_prefix = f"schedule_buffered_processing(peer:{peer_id}, user:{original_user_id}):"
    current_task = asyncio.current_task()
    try:
        logger.debug(f"{log_prefix} Ожидание {MESSAGE_BUFFER_SECONDS} секунд...")
        await asyncio.sleep(MESSAGE_BUFFER_SECONDS)
        task_in_dict = user_message_timers.get(peer_id)
        if task_in_dict is not current_task:
            logger.info(f"{log_prefix} Таймер сработал, но он устарел. Обработка отменена.")
            return
        if peer_id in user_message_timers:
            del user_message_timers[peer_id]
        logger.debug(f"{log_prefix} Таймер сработал и удален. Вызов process_buffered_messages.")
        asyncio.create_task(process_buffered_messages(peer_id, original_user_id))
    except asyncio.CancelledError:
        logger.info(f"{log_prefix} Таймер отменен.")
    except Exception as e:
        logger.error(f"{log_prefix} Ошибка в задаче таймера: {e}", exc_info=True)
        if peer_id in user_message_timers and user_message_timers.get(peer_id) is current_task:
            del user_message_timers[peer_id]

async def process_buffered_messages(peer_id: int, original_user_id: int):
    log_prefix = f"process_buffered_messages(peer:{peer_id}, user:{original_user_id}):"
    logger.debug(f"{log_prefix} Начало обработки буферизованных сообщений.")
    async with user_processing_locks[peer_id]:
        logger.debug(f"{log_prefix} Блокировка для peer_id={peer_id} получена.")
        messages_to_process = pending_messages.pop(peer_id, [])
        if peer_id in user_message_timers:
            logger.warning(f"{log_prefix} Таймер для peer_id={peer_id} все еще существовал! Отменяем и удаляем.")
            timer_to_cancel = user_message_timers.pop(peer_id)
            if not timer_to_cancel.done():
                try:
                    timer_to_cancel.cancel()
                except Exception as e_inner_cancel:
                    logger.debug(f"{log_prefix} Ошибка при попытке отменить таймер: {e_inner_cancel}")
        if not messages_to_process:
            logger.info(f"{log_prefix} Нет сообщений в буфере для peer_id={peer_id}.")
            return
        combined_input = "\n".join(messages_to_process)
        num_messages = len(messages_to_process)
        logger.info(f'{log_prefix} Объединенный запрос для peer_id={peer_id} ({num_messages} сообщ.): "{combined_input[:200]}..."')
        try:
            await set_typing_activity(peer_id)
            response_text = await chat_with_assistant(original_user_id, combined_input)
            await send_vk_message(peer_id, response_text)
            logger.info(f"{log_prefix} Успешно обработан и отправлен ответ для peer_id={peer_id}.")
        except Exception as e:
            logger.error(f"{log_prefix} Ошибка при обработке или отправке ответа для peer_id={peer_id}: {e}", exc_info=True)
            try:
                await send_vk_message(peer_id, "Произошла внутренняя ошибка при обработке вашего запроса. Попробуйте позже.")
            except Exception as send_err_e:
                logger.error(f"{log_prefix} Не удалось отправить сообщение об ошибке peer_id={peer_id}: {send_err_e}")
        finally:
            logger.debug(f"{log_prefix} Блокировка для peer_id={peer_id} освобождена.")

# --- OpenAI Assistant Interaction ---
async def get_or_create_thread(user_id: int) -> Optional[str]:
    log_prefix = f"get_or_create_thread(user:{user_id}):"
    user_key = get_user_key(user_id)
    
    # === ПРОВЕРКА СУЩЕСТВУЮЩЕГО ТРЕДА ===
    if user_key in user_threads:
        thread_id = user_threads[user_key]
        logger.debug(f"{log_prefix} Найден сохранённый тред {thread_id}, проверяем доступность...")
        
        # Проверяем существование треда с retry логикой
        for attempt in range(1, 3):  # 2 попытки проверки
            try:
                await openai_client.beta.threads.messages.list(thread_id=thread_id, limit=1)
                logger.info(f"{log_prefix} Используем существующий тред {thread_id}")
                return thread_id
            except openai.NotFoundError:
                logger.warning(f"{log_prefix} Тред {thread_id} не найден в OpenAI. Удаляем из локального кэша.")
                if user_key in user_threads: 
                    del user_threads[user_key]
                    save_user_threads_to_file()
                break  # Выходим из retry цикла - тред точно не существует
            except (openai.APIError, Exception) as e:
                logger.warning(f"{log_prefix} Попытка {attempt} проверки треда {thread_id} неуспешна: {e}")
                if attempt < 2:
                    await asyncio.sleep(1)  # Короткая задержка перед повтором
                    continue
                else:
                    logger.error(f"{log_prefix} Не удалось проверить тред {thread_id} за {attempt} попытки. Создаём новый.")
                    if user_key in user_threads: 
                        del user_threads[user_key]
                        save_user_threads_to_file()
                    break
    
    # === СОЗДАНИЕ НОВОГО ТРЕДА ===
    for attempt in range(1, OPENAI_MAX_RETRIES + 1):
        try:
            logger.info(f"{log_prefix} Попытка {attempt} создания нового треда...")
            thread = await openai_client.beta.threads.create()
            thread_id = thread.id
            user_threads[user_key] = thread_id
            save_user_threads_to_file()
            logger.info(f"{log_prefix} Создан новый тред {thread_id}")
            
            # === ЗАГРУЗКА И ВОСПРОИЗВЕДЕНИЕ ИСТОРИИ ===
            try:
                # Загружаем историю в память, если её нет
                if user_id not in user_messages:
                    logger.debug(f"{log_prefix} Загружаем историю из файла...")
                    history_from_file = load_user_history_from_file(user_id, MESSAGE_HISTORY_DAYS)
                    if history_from_file:
                        user_messages[user_id] = history_from_file
                        logger.info(f"{log_prefix} Загружено {len(history_from_file)} сообщений из файла истории")
                    else:
                        logger.debug(f"{log_prefix} История в файле отсутствует или пуста")
                
                # Досылаем историю в новый тред
                logger.debug(f"{log_prefix} Воспроизводим историю в новый тред...")
                replayed_count = await replay_history_to_thread(user_id, thread_id, MAX_HISTORY_REPLAY_MESSAGES)
                if replayed_count > 0:
                    logger.info(f"{log_prefix} Воспроизведено {replayed_count} сообщений в тред {thread_id}")
                else:
                    logger.debug(f"{log_prefix} История для воспроизведения отсутствует")
                
            except Exception as history_error:
                logger.error(f"{log_prefix} Ошибка загрузки/воспроизведения истории: {history_error}", exc_info=True)
                # Продолжаем работу даже если история не загрузилась
            
            logger.info(f"{log_prefix} Новый тред {thread_id} готов к использованию")
            return thread_id
            
        except openai.APIError as e:
            logger.error(f"{log_prefix} OpenAI API ошибка при создании треда (попытка {attempt}): {e}")
            if attempt < OPENAI_MAX_RETRIES:
                logger.info(f"{log_prefix} Повторная попытка через {OPENAI_RETRY_DELAY_SECONDS} секунд...")
                await asyncio.sleep(OPENAI_RETRY_DELAY_SECONDS)
                continue
            else:
                logger.error(f"{log_prefix} Не удалось создать тред за {OPENAI_MAX_RETRIES} попытки")
                return None
        except Exception as e:
            logger.error(f"{log_prefix} Непредвиденная ошибка при создании треда (попытка {attempt}): {e}", exc_info=True)
            if attempt < OPENAI_MAX_RETRIES:
                logger.info(f"{log_prefix} Повторная попытка через {OPENAI_RETRY_DELAY_SECONDS} секунд...")
                await asyncio.sleep(OPENAI_RETRY_DELAY_SECONDS)
                continue
            else:
                logger.error(f"{log_prefix} Критическая ошибка: не удалось создать тред за {OPENAI_MAX_RETRIES} попытки")
                return None

async def chat_with_assistant(user_id: int, message_text: str) -> str:
    log_prefix = f"chat_with_assistant(user:{user_id}):"
    logger.info(f"{log_prefix} Запрос: {message_text[:100]}...")

    thread_id = await get_or_create_thread(user_id)
    if not thread_id:
        return "Произошла внутренняя ошибка (не удалось создать или получить тред OpenAI)."

    context = ""
    if vector_collection:
        logger.debug(f"{log_prefix} Попытка получить контекст из векторной базы...")
        try: 
            context = await get_relevant_context(message_text, k=RELEVANT_CONTEXT_COUNT)
        except Exception as e_ctx: 
            logger.error(f"{log_prefix} Ошибка получения контекста: {e_ctx}", exc_info=True)
        logger.debug(f"{log_prefix} Контекст из векторной базы получен (или пуст).")

    full_prompt = message_text
    if context:
        full_prompt = (
            f"Используй следующую информацию из базы знаний для ответа:\n"
            f"--- НАЧАЛО КОНТЕКСТА ---\n{context}\n--- КОНЕЦ КОНТЕКСТА ---\n\n"
            f"Вопрос пользователя: {message_text}"
        )
        logger.info(f"{log_prefix} Контекст добавлен к запросу.")
    else:
        logger.info(f"{log_prefix} Контекст не найден или база знаний отключена.")

    # --- ДОБАВЛЯЕМ ДАТУ И ВРЕМЯ В НАЧАЛО PROMPT ---
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    full_prompt = f"Сегодня: {now_str}.\n" + full_prompt
    # --- КОНЕЦ ДОБАВЛЕНИЯ ---

    logger.debug(f"{log_prefix} Вызов add_message_to_history для user_input...")
    await add_message_to_history(user_id, "user", message_text) 
    logger.debug(f"{log_prefix} add_message_to_history для user_input ВЫПОЛНЕН.")

    # === НОВАЯ RETRY ЛОГИКА ===
    for attempt in range(1, OPENAI_MAX_RETRIES + 1):
        try:
            logger.debug(f"{log_prefix} Попытка {attempt} отправки запроса в OpenAI...")
            # --- основной блок отправки запроса (скопировано из референсной реализации) ---
            logger.debug(f"{log_prefix} Проверка активных runs для треда {thread_id} ПЕРЕД созданием нового сообщения...")
            active_runs_response = await openai_client.beta.threads.runs.list(thread_id=thread_id)
            active_runs_to_cancel = [run for run in active_runs_response.data if run.status in ['queued', 'in_progress', 'requires_action']]
            if active_runs_to_cancel:
                logger.warning(f"{log_prefix} Найдено {len(active_runs_to_cancel)} активных/ожидающих runs. Отменяем...")
                for run_to_cancel in active_runs_to_cancel:
                    try:
                        logger.debug(f"{log_prefix} Попытка отменить run {run_to_cancel.id}...")
                        await openai_client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run_to_cancel.id)
                        logger.info(f"{log_prefix} Отменен run {run_to_cancel.id}")
                    except Exception as cancel_error: 
                        logger.warning(f"{log_prefix} Не удалось отменить run {run_to_cancel.id}: {cancel_error}")
            logger.debug(f"{log_prefix} Проверка активных runs ЗАВЕРШЕНА.")
            
            logger.debug(f"{log_prefix} Попытка создать сообщение в треде {thread_id}...")
            await openai_client.beta.threads.messages.create(thread_id=thread_id, role="user", content=full_prompt)
            logger.info(f"{log_prefix} Сообщение добавлено в тред {thread_id}. Попытка запустить run...")

            current_run = await openai_client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)
            logger.info(f"{log_prefix} Запущен новый run {current_run.id}. Начало опроса статуса...")

            start_time = time_module.time()
            run_completed_successfully = False
            while time_module.time() - start_time < OPENAI_RUN_TIMEOUT_SECONDS:
                await asyncio.sleep(1.5) 
                run_status = await openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=current_run.id)
                logger.debug(f"{log_prefix} Статус run {current_run.id}: {run_status.status}")
                if run_status.status == 'completed':
                    logger.info(f"{log_prefix} Run {current_run.id} успешно завершен.")
                    run_completed_successfully = True
                    break
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    error_message_detail = f"Run {current_run.id} статус '{run_status.status}'."
                    last_error = getattr(run_status, 'last_error', None)
                    if last_error: 
                        error_message_detail += f" Ошибка: {last_error.message} (Код: {last_error.code})"
                    logger.error(f"{log_prefix} {error_message_detail}")
                    await log_context(user_id, message_text, context, f"ОШИБКА OPENAI: {error_message_detail}")
                    break  # не retry, а сразу выход
                elif run_status.status == 'requires_action':
                     logger.warning(f"{log_prefix} Run {current_run.id} требует действия (Function Calling?).")
                     await openai_client.beta.threads.runs.cancel(thread_id=thread_id, run_id=current_run.id)
                     await log_context(user_id, message_text, context, "ОШИБКА OPENAI: requires_action")
                     break  # не retry, а сразу выход
            
            if not run_completed_successfully:
                logger.warning(f"{log_prefix} Таймаут ({OPENAI_RUN_TIMEOUT_SECONDS}s) для run {current_run.id}")
                try:
                    await openai_client.beta.threads.runs.cancel(thread_id=thread_id, run_id=current_run.id)
                    logger.info(f"{log_prefix} Отменен run {current_run.id} из-за таймаута.")
                except Exception as cancel_error: 
                    logger.warning(f"{log_prefix} Ошибка отмены run {current_run.id} после таймаута: {cancel_error}")
                await log_context(user_id, message_text, context, "ОШИБКА OPENAI: Таймаут")
                if attempt < OPENAI_MAX_RETRIES:
                    logger.info(f"{log_prefix} Повторная попытка через {OPENAI_RETRY_DELAY_SECONDS} секунд...")
                    await asyncio.sleep(OPENAI_RETRY_DELAY_SECONDS)
                    continue
                else:
                    return "Ошибка доставки сообщения. Попробуйте позже."

            messages_response = await openai_client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=5)
            assistant_response_content = None
            for msg in messages_response.data:
                if msg.role == "assistant" and msg.run_id == current_run.id:
                    if msg.content and msg.content[0].type == 'text': # Предполагаем один текстовый блок
                        assistant_response_content = msg.content[0].text.value
                        logger.info(f"{log_prefix} Получен релевантный ответ: {assistant_response_content[:100]}...")
                        break
            
            if assistant_response_content:
                await add_message_to_history(user_id, "assistant", assistant_response_content)
                await log_context(user_id, message_text, context, assistant_response_content)
                return assistant_response_content
            else:
                logger.warning(f"{log_prefix} Текстовый ответ от ассистента для run {current_run.id} не найден.")
                await log_context(user_id, message_text, context, "ОТВЕТ АССИСТЕНТА НЕ НАЙДЕН ИЛИ ПУСТ")
                return "Ошибка доставки сообщения. Попробуйте позже."
                
        except openai.APIError as e: # Более общая ошибка API OpenAI
            logger.error(f"{log_prefix} Ошибка OpenAI API: {e}", exc_info=True)
            if attempt < OPENAI_MAX_RETRIES:
                logger.info(f"{log_prefix} Повторная попытка через {OPENAI_RETRY_DELAY_SECONDS} секунд после ошибки OpenAI API...")
                await asyncio.sleep(OPENAI_RETRY_DELAY_SECONDS)
                continue
            else:
                return f"Ошибка OpenAI: {str(e)}. Попробуйте позже."
        except Exception as e:
            logger.error(f"{log_prefix} Непредвиденная ошибка: {e}", exc_info=True)
            await log_context(user_id, message_text, context, f"НЕПРЕДВИДЕННАЯ ОШИБКА: {e}")
            if attempt < OPENAI_MAX_RETRIES:
                logger.info(f"{log_prefix} Повторная попытка через {OPENAI_RETRY_DELAY_SECONDS} секунд после непредвиденной ошибки...")
                await asyncio.sleep(OPENAI_RETRY_DELAY_SECONDS)
                continue
            else:
                return "Ошибка доставки сообщения. Попробуйте позже."

# --- Vector Store Management (ChromaDB) ---
async def get_relevant_context(query: str, k: int) -> str:
    if not vector_collection:
        logger.warning("Запрос контекста, но ChromaDB не инициализирована.")
        return ""
    try:
        try:
            query_embedding_response = await openai_client.embeddings.create(
                 input=[query],
                 model=EMBEDDING_MODEL,
                 dimensions=EMBEDDING_DIMENSIONS if EMBEDDING_DIMENSIONS else None
            )
            query_embedding = query_embedding_response.data[0].embedding
            logger.debug(f"Эмбеддинг для запроса '{query[:50]}...' создан.")
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддинга запроса: {e}", exc_info=True)
            return ""
        try:
            results = await asyncio.to_thread(
                vector_collection.query,
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            logger.debug(f"Поиск в ChromaDB для '{query[:50]}...' выполнен.")
        except Exception as e:
            logger.error(f"Ошибка при выполнении поиска в ChromaDB: {e}", exc_info=True)
            return ""
        if not results or not results.get("ids") or not results["ids"][0]:
            logger.info(f"Релевантных документов не найдено для запроса: '{query[:50]}...'")
            return ""
        
        # Убедимся, что results["documents"] и другие списки существуют и не пусты
        # Хотя проверка results["ids"][0] уже это частично покрывает
        if not results.get("documents") or not results["documents"][0]: # type: ignore
            logger.info(f"В результатах ChromaDB отсутствуют документы для запроса: '{query[:50]}...'")
            return ""

        documents = results["documents"][0] # type: ignore
        metadatas = results["metadatas"][0] if results.get("metadatas") and results["metadatas"][0] else [{}] * len(documents) # type: ignore
        # distances = results["distances"][0] if results.get("distances") and results["distances"][0] else [0.0] * len(documents) # type: ignore

        context_pieces = []
        logger.info(f"Найдено {len(documents)} док-в для '{query[:50]}...'. Топ {k}:")
        for i, doc_content in enumerate(documents): # Используем enumerate(documents)
            meta = metadatas[i] if i < len(metadatas) else {}
            # dist = distances[i] if i < len(distances) else 0.0 # Дистанция используется только для логирования
            
            source = meta.get('source', 'Неизвестный источник')
            # logger.info(f"  #{i+1}: Источник='{source}', Дистанция={dist:.4f}, Контент='{doc_content[:100]}...'")
            logger.info(f"  #{i+1}: Источник='{source}', Контент='{doc_content[:100]}...'")
            context_piece = f"Из документа '{source}':\n{doc_content}"
            context_pieces.append(context_piece)

        if not context_pieces:
             logger.info(f"Не найдено подходящих фрагментов контекста для '{query[:50]}...'.")
             return ""
        full_context = "\n\n---\n\n".join(context_pieces)
        logger.info(f"Сформирован контекст размером {len(full_context)} символов из {len(context_pieces)} фрагментов.")
        return full_context
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении контекста: {e}", exc_info=True)
        return ""

async def update_vector_store():
    logger.info("--- Запуск обновления базы знаний ---")
    previous_active_subpath = _get_active_db_subpath()
    os.makedirs(VECTOR_DB_BASE_PATH, exist_ok=True)
    if not drive_service:
        logger.error("Обновление БЗ невозможно: сервис Google Drive не инициализирован.")
        return {"success": False, "error": "Сервис Google Drive не инициализирован", "added_chunks": 0, "total_chunks": 0}
    timestamp_dir_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_new"
    new_db_path = os.path.join(VECTOR_DB_BASE_PATH, timestamp_dir_name)
    logger.info(f"Создание новой временной директории для БД: {new_db_path}")
    try:
        os.makedirs(new_db_path, exist_ok=True)
    except Exception as e_mkdir:
        logger.error(f"Не удалось создать временную директорию '{new_db_path}': {e_mkdir}.", exc_info=True)
        return {"success": False, "error": f"Failed to create temp dir: {e_mkdir}", "added_chunks": 0, "total_chunks": 0}
    
    temp_vector_collection: Optional[chromadb.api.models.Collection.Collection] = None
    try:
        temp_chroma_client = chromadb.PersistentClient(path=new_db_path)
        temp_vector_collection = temp_chroma_client.get_or_create_collection(name=VECTOR_DB_COLLECTION_NAME)
        logger.info(f"Временная коллекция '{VECTOR_DB_COLLECTION_NAME}' создана/получена в '{new_db_path}'.")
        logger.info("Получение данных из Google Drive...")
        documents_data = await asyncio.to_thread(read_data_from_drive)
        if not documents_data:
            logger.warning("Не найдено документов в Google Drive. Обновление прервано.")
            if os.path.exists(new_db_path): shutil.rmtree(new_db_path)
            return {"success": False, "error": "No documents in Google Drive", "added_chunks": 0, "total_chunks": 0}
        logger.info(f"Получено {len(documents_data)} документов из Google Drive.")
        all_texts: List[str] = []
        all_metadatas: List[Dict[str, Any]] = []
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]) # Пример
        MD_SECTION_MAX_LEN = 2000
        for doc_info in documents_data:
            doc_name, doc_content_str = doc_info['name'], doc_info['content']
            if not doc_content_str or not doc_content_str.strip():
                logger.warning(f"Документ '{doc_name}' пуст. Пропускаем.")
                continue
            # Исправление №5: Правильное экранирование
            enhanced_doc_content = f"Документ: {doc_name}\n\n{doc_content_str}"
            chunk_idx = 0
            is_md = doc_name.lower().endswith(('.md', '.markdown'))
            try:
                if is_md:
                    md_splits = markdown_splitter.split_text(enhanced_doc_content)
                    for md_split in md_splits:
                        headers_meta = {k: v for k, v in md_split.metadata.items() if k.startswith('h')}
                        if len(md_split.page_content) > MD_SECTION_MAX_LEN:
                            sub_chunks = text_splitter.split_text(md_split.page_content)
                            for sub_chunk_text in sub_chunks:
                                all_texts.append(sub_chunk_text)
                                all_metadatas.append({"source": doc_name, **headers_meta, "type": "md_split", "chunk": chunk_idx})
                                chunk_idx += 1
                        else:
                            all_texts.append(md_split.page_content)
                            all_metadatas.append({"source": doc_name, **headers_meta, "type": "md", "chunk": chunk_idx})
                            chunk_idx += 1
                else:
                    chunks = text_splitter.split_text(enhanced_doc_content)
                    for chunk_text in chunks:
                        all_texts.append(chunk_text)
                        all_metadatas.append({"source": doc_name, "type": "text", "chunk": chunk_idx})
                        chunk_idx += 1
                logger.info(f"Документ '{doc_name}' разбит на {chunk_idx} чанков.")
            except Exception as e_split:
                logger.error(f"Ошибка при разбиении '{doc_name}': {e_split}", exc_info=True)
                if is_md: # Fallback for markdown
                    try:
                        chunks = text_splitter.split_text(enhanced_doc_content)
                        chunk_idx_fb = 0 # Новый счетчик для fallback
                        for chunk_text in chunks:
                            all_texts.append(chunk_text)
                            all_metadatas.append({"source": doc_name, "type": "text_fallback", "chunk": chunk_idx_fb})
                            chunk_idx_fb += 1
                        logger.info(f"Документ '{doc_name}' (fallback) разбит на {chunk_idx_fb} чанков.")
                    except Exception as e_fallback:
                         logger.error(f"Ошибка fallback-разбиения '{doc_name}': {e_fallback}", exc_info=True)
                continue
        if not all_texts:
            logger.warning("Нет текстовых данных для добавления в базу. Обновление прервано.")
            if os.path.exists(new_db_path): shutil.rmtree(new_db_path)
            return {"success": False, "error": "No text data to add", "added_chunks": 0, "total_chunks": 0}
        logger.info(f"Добавление {len(all_texts)} чанков во временную коллекцию...")
        try:
            all_ids = [f"{meta['source']}_{meta.get('type','unknown')}_{meta['chunk']}_{random.randint(1000,9999)}" for meta in all_metadatas]
            logger.info(f"Создание эмбеддингов для {len(all_texts)} чанков...")
            embeddings_response = await openai_client.embeddings.create(
                input=all_texts, model=EMBEDDING_MODEL,
                dimensions=EMBEDDING_DIMENSIONS if EMBEDDING_DIMENSIONS else None
            )
            all_embeddings = [item.embedding for item in embeddings_response.data]
            if temp_vector_collection: # Проверка что коллекция существует
                await asyncio.to_thread(
                   temp_vector_collection.add,
                   ids=all_ids, embeddings=all_embeddings, metadatas=all_metadatas, documents=all_texts
                )
                final_added, final_total = len(all_ids), temp_vector_collection.count()
                logger.info(f"Успешно добавлено {final_added} чанков. Всего: {final_total}.")
            else: # Это не должно произойти если код выше корректен
                logger.error("temp_vector_collection не была инициализирована!")
                return {"success": False, "error": "temp_vector_collection is None", "added_chunks": 0, "total_chunks": 0}

            active_db_info_filepath = os.path.join(VECTOR_DB_BASE_PATH, ACTIVE_DB_INFO_FILE)
            with open(active_db_info_filepath, "w", encoding="utf-8") as f: f.write(timestamp_dir_name)
            logger.info(f"Путь к новой активной базе '{timestamp_dir_name}' сохранен.")
            await _initialize_active_vector_collection() # Перезагружаем глобальную коллекцию
            if not vector_collection: # Проверяем успешность перезагрузки
                 logger.error("Критическая ошибка: не удалось перезагрузить vector_collection на новую активную базу!")
                 return {"success": False, "error": "Failed to reload global vector_collection", "added_chunks": final_added, "total_chunks": final_total}
            if previous_active_subpath and previous_active_subpath != timestamp_dir_name:
                prev_path = os.path.join(VECTOR_DB_BASE_PATH, previous_active_subpath)
                if os.path.exists(prev_path):
                    try:
                        shutil.rmtree(prev_path)
                        logger.info(f"Удалена предыдущая активная директория БД: '{prev_path}'")
                    except Exception as e_rm_old:
                        logger.error(f"Не удалось удалить предыдущую БД '{prev_path}': {e_rm_old}", exc_info=True)
            logger.info("--- Обновление базы знаний успешно завершено ---")
            return {"success": True, "added_chunks": final_added, "total_chunks": final_total, "new_active_path": timestamp_dir_name}
        except openai.APIError as e_openai:
             logger.error(f"OpenAI API ошибка при эмбеддингах: {e_openai}", exc_info=True)
             if os.path.exists(new_db_path): shutil.rmtree(new_db_path)
             return {"success": False, "error": f"OpenAI API error: {e_openai}", "added_chunks": 0, "total_chunks": 0}
        except Exception as e_add:
            logger.error(f"Ошибка при добавлении в ChromaDB: {e_add}", exc_info=True)
            if os.path.exists(new_db_path): shutil.rmtree(new_db_path)
            return {"success": False, "error": f"ChromaDB add error: {e_add}", "added_chunks": 0, "total_chunks": 0}
    except Exception as e_main_update:
        logger.error(f"Критическая ошибка во время обновления БЗ: {e_main_update}", exc_info=True)
        if os.path.exists(new_db_path): shutil.rmtree(new_db_path)
        return {"success": False, "error": f"Critical update error: {e_main_update}", "added_chunks": 0, "total_chunks": 0}

# --- Google Drive Reading ---
# Исправление №6: Циклическая загрузка файлов
def _download_file_content(service, file_id, export_mime_type=None):
    if export_mime_type:
        request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
    else:
        request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        if status: logger.debug(f"Загрузка файла {file_id}: {int(status.progress() * 100)}%.")
    fh.seek(0)
    return fh

def read_data_from_drive() -> List[Dict[str,str]]:
    if not drive_service:
        logger.error("Чтение из Google Drive невозможно: сервис не инициализирован.")
        return []
    result_docs: List[Dict[str,str]] = []
    try:
        files_response = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name, mimeType)", pageSize=1000
        ).execute()
        files = files_response.get('files', [])
        logger.info(f"Найдено {len(files)} файлов в папке Google Drive.")
        downloader_map = {
            'application/vnd.google-apps.document': lambda s, f_id: download_google_doc(s, f_id),
            'application/pdf': lambda s, f_id: download_pdf(s, f_id),
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': lambda s, f_id: download_docx(s, f_id),
            'text/plain': lambda s, f_id: download_text(s, f_id),
            'text/markdown': lambda s, f_id: download_text(s, f_id), # .md как text
        }
        for file_item in files:
            file_id, mime_type, file_name = file_item['id'], file_item['mimeType'], file_item['name']
            if mime_type in downloader_map:
                logger.info(f"Обработка файла: '{file_name}' (ID: {file_id}, Type: {mime_type})")
                try:
                    content_str = downloader_map[mime_type](drive_service, file_id)
                    if content_str and content_str.strip():
                        result_docs.append({'name': file_name, 'content': content_str})
                        logger.info(f"Успешно прочитан файл: '{file_name}' ({len(content_str)} симв)")
                    else:
                        logger.warning(f"Файл '{file_name}' пуст или не удалось извлечь контент.")
                except Exception as e_read_file:
                    logger.error(f"Ошибка чтения файла '{file_name}': {e_read_file}", exc_info=True)
            else:
                logger.debug(f"Файл '{file_name}' имеет неподдерживаемый тип ({mime_type}).")
    except Exception as e:
        logger.error(f"Критическая ошибка при чтении из Google Drive: {e}", exc_info=True)
        return []
    logger.info(f"Чтение из Google Drive завершено. Прочитано {len(result_docs)} документов.")
    return result_docs

def download_google_doc(service, file_id) -> str:
    fh = _download_file_content(service, file_id, export_mime_type='text/plain')
    return fh.getvalue().decode('utf-8', errors='ignore')

def download_pdf(service, file_id) -> str:
    fh = _download_file_content(service, file_id)
    try:
        pdf_reader = PyPDF2.PdfReader(fh)
        return "".join(page.extract_text() + "\n" for page in pdf_reader.pages if page.extract_text())
    except Exception as e:
         logger.error(f"Ошибка обработки PDF (ID: {file_id}): {e}", exc_info=True)
         return ""

def download_docx(service, file_id) -> str:
    fh = _download_file_content(service, file_id)
    try:
        doc = docx.Document(fh)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text)
    except Exception as e:
         logger.error(f"Ошибка обработки DOCX (ID: {file_id}): {e}", exc_info=True)
         return ""

def download_text(service, file_id) -> str:
    fh = _download_file_content(service, file_id)
    try:
        return fh.getvalue().decode('utf-8')
    except UnicodeDecodeError:
         logger.warning(f"Не удалось декодировать {file_id} как UTF-8, пробуем cp1251.")
         try: return fh.getvalue().decode('cp1251', errors='ignore')
         except Exception as e:
              logger.error(f"Не удалось декодировать {file_id}: {e}")
              return ""

# --- History and Context Management ---
async def log_context(user_id: int, message_text: str, context: str, response_text: Optional[str]=None):
    try:
        ts = datetime.datetime.now()
        log_filename = os.path.join(LOGS_DIR, f"context_{user_id}_{ts.strftime('%Y%m%d_%H%M%S')}.log")
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write(f"Timestamp: {ts.isoformat()}\nUser ID: {user_id}\n"
                    f"--- User Query ---\n{message_text}\n"
                    f"--- Retrieved Context ---\n{context or 'Контекст не найден.'}\n")
            if response_text: f.write(f"--- Assistant Response ---\n{response_text}\n")
    except Exception as e:
        logger.error(f"Ошибка при логировании контекста для user_id={user_id}: {e}", exc_info=True)

async def cleanup_old_context_logs():
    # Исправление №7: logger используется корректно
    logger.info("Запуск очистки старых логов контекста...")
    count = 0
    try:
        cutoff = time_module.time() - LOG_RETENTION_SECONDS
        for filename in glob.glob(os.path.join(LOGS_DIR, "context_*.log")):
            try:
                if os.path.getmtime(filename) < cutoff:
                    os.remove(filename)
                    count += 1
            except FileNotFoundError: # Файл мог быть удален другим процессом
                continue
            except Exception as e_remove_log:
                logger.error(f"Ошибка при удалении файла лога {filename}: {e_remove_log}")
        if count > 0:
            logger.info(f"Очистка логов: удалено {count} устаревших файлов.")
        else:
            logger.info("Очистка логов: устаревших файлов не найдено.")
    except Exception as e:
        logger.error(f"Критическая ошибка при очистке логов контекста: {e}", exc_info=True)

# --- Background Cleanup Task ---
last_auto_update_date: Optional[datetime.date] = None

async def background_cleanup_task():
    global last_auto_update_date
    while True:
        await asyncio.sleep(3600)
        logger.info("Запуск периодической фоновой задачи...")
        try:
            now_local = datetime.datetime.now(TARGET_TZ)
            if now_local.hour == DAILY_UPDATE_HOUR and (last_auto_update_date is None or last_auto_update_date < now_local.date()):
                logger.info(f"Время для ежедневного обновления БЗ ({now_local.hour}:00). Запускаем...")
                await run_update_and_notify_admin(ADMIN_USER_ID)
                last_auto_update_date = now_local.date()
        except Exception as e_auto_update:
            logger.error(f"Ошибка в логике ежедневного обновления БЗ: {e_auto_update}", exc_info=True)
        await cleanup_old_context_logs()
        logger.info("Периодическая фоновая задача завершила цикл.")

# --- Inactive Users Cleanup Task ---
async def check_inactive_silence_task():
    """Проверка неактивных пользователей для автоматического снятия молчания"""
    while True:
        try:
            await asyncio.sleep(INACTIVE_CHECK_INTERVAL_HOURS * 3600)
            logger.info("Запуск проверки неактивных пользователей для снятия молчания...")
            
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=SILENCE_AUTO_REMOVE_DAYS)
            removed_count = 0
            removed_users = []
            
            # Проверяем все чаты в режиме молчания
            for peer_id in list(chat_silence_state.keys()):
                if not await is_chat_silent_smart(peer_id):
                    continue  # Пропускаем если молчание уже снято
                
                # Проверяем последнюю активность
                last_activity = user_last_activity.get(peer_id)
                
                if last_activity is None:
                    # Если активности нет в записях, считаем что пользователь неактивен очень давно
                    logger.info(f"Пользователь peer_id={peer_id} без записей активности. Снимаем молчание.")
                    await unsilence_user(peer_id)
                    removed_users.append(peer_id)
                    removed_count += 1
                elif last_activity < cutoff_date:
                    # Пользователь неактивен дольше порогового времени
                    days_inactive = (datetime.datetime.now() - last_activity).days
                    logger.info(f"Пользователь peer_id={peer_id} неактивен {days_inactive} дней (> {SILENCE_AUTO_REMOVE_DAYS}). Снимаем молчание.")
                    await unsilence_user(peer_id)
                    removed_users.append(peer_id)
                    removed_count += 1
                else:
                    # Пользователь ещё активен
                    days_inactive = (datetime.datetime.now() - last_activity).days
                    logger.debug(f"Пользователь peer_id={peer_id} активен (неактивность: {days_inactive} дней)")
            
            # Уведомляем админа о результатах
            if removed_count > 0:
                notification_text = f"🔄 Автоматически снято молчание с {removed_count} неактивных диалогов\n"
                notification_text += f"📅 Порог неактивности: {SILENCE_AUTO_REMOVE_DAYS} дней\n"
                notification_text += f"👥 Затронутые диалоги: {', '.join(map(str, removed_users))}"
                
                try:
                    await send_vk_message(ADMIN_USER_ID, notification_text)
                    logger.info(f"Уведомление админу отправлено: снято молчание с {removed_count} диалогов")
                except Exception as e_notify:
                    logger.error(f"Ошибка отправки уведомления админу о снятии молчания: {e_notify}")
            else:
                logger.info("Неактивных пользователей для снятия молчания не найдено")
                
        except Exception as e:
            logger.error(f"Ошибка в check_inactive_silence_task: {e}", exc_info=True)
            # Продолжаем работу даже при ошибках

# --- Main Event Handler ---
async def handle_new_message(event: VkBotEvent):
    # global user_threads # user_threads и так глобальная
    try:
        if event.object.message and event.object.message.get('from_id') and event.object.message.get('from_id') > 0 : # Сообщение от пользователя
            user_id = event.object.message['from_id']
            peer_id = event.object.message['peer_id']
            message_text = event.object.message.get('text', '').strip() # get с default
            if not message_text:
                 logger.info(f"Пустое сообщение от user_id={user_id}. Игнорируем.")
                 return


            if message_text.lower() == CMD_UPDATE.lower() and user_id == ADMIN_USER_ID:
                logger.info(f"Администратор {user_id} инициировал обновление БЗ.")
                await send_vk_message(peer_id, "🔄 Запускаю обновление базы знаний...")
                asyncio.create_task(run_update_and_notify_admin(peer_id)) 
                return
            
            if message_text.lower() == CMD_RESET.lower():
                user_key = get_user_key(user_id)
                log_prefix = f"handle_new_message(reset for peer:{peer_id}, user:{user_id}):"
                logger.info(f"{log_prefix} Получена команда сброса диалога.") # logger вместо logging
                if peer_id in pending_messages: del pending_messages[peer_id]
                if peer_id in user_message_timers:
                    old_timer = user_message_timers.pop(peer_id)
                    if not old_timer.done(): old_timer.cancel()
                thread_id_to_forget = user_threads.pop(user_key, None)
                if thread_id_to_forget: logger.info(f"{log_prefix} Тред {thread_id_to_forget} удален из памяти.") # logger вместо logging
                await send_vk_message(peer_id, "🔄 Диалог сброшен.")
                return
            
            if message_text.lower() == CMD_RESET_ALL.lower() and user_id == ADMIN_USER_ID:
                log_prefix = f"handle_new_message(reset_all from user:{user_id}):"
                logger.info(f"{log_prefix} Получена команда сброса ВСЕХ диалогов.") # logger вместо logging
                active_timer_count = sum(1 for task in user_message_timers.values() if not task.done())
                for task in list(user_message_timers.values()): # Итерируемся по копии
                    if not task.done(): task.cancel()
                user_message_timers.clear()
                pending_count = len(pending_messages)
                pending_messages.clear()
                threads_count = len(user_threads)
                user_threads.clear()
                await send_vk_message(peer_id, f"🔄 СБРОС ВСЕХ ДИАЛОГОВ ВЫПОЛНЕН.\n- Таймеров: {active_timer_count}\n- Буферов: {pending_count}\n- Тредов: {threads_count}")
                return

            is_manager = user_id in MANAGER_USER_IDS or user_id == ADMIN_USER_ID
            if is_manager:
                command = message_text.lower()
                
                # === ОСНОВНЫЕ КОМАНДЫ ===
                if command == CMD_SPEAK.lower():
                    await unsilence_user(peer_id)
                    await send_vk_message(peer_id, "🤖 Режим молчания снят. Бот снова активен.")
                    return
                
                # === КОМАНДЫ УПРАВЛЕНИЯ МОЛЧАНИЕМ ===
                elif command == CMD_SILENCE.lower():
                    await silence_user(peer_id)
                    await send_vk_message(peer_id, "🔇 Бот переведён в режим молчания.")
                    return
                
                elif command == CMD_UNSILENCE.lower():
                    await unsilence_user(peer_id)
                    await send_vk_message(peer_id, "🔊 Режим молчания снят.")
                    return
                
                elif command == CMD_LIST_SILENT.lower():
                    silent_chats = [str(pid) for pid, is_silent in chat_silence_state.items() if is_silent]
                    if silent_chats:
                        silent_list = '\n'.join([f"• peer_id: {pid}" for pid in silent_chats])
                        response = f"🔇 Диалоги в режиме молчания ({len(silent_chats)}):\n{silent_list}"
                    else:
                        response = "✅ Нет диалогов в режиме молчания"
                    await send_vk_message(peer_id, response)
                    return
                
                # === КОМАНДЫ С ПАРАМЕТРАМИ ===
                elif command.startswith(CMD_SILENCE_USER.lower()):
                    parts = message_text.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        target_peer_id = int(parts[1])
                        await silence_user(target_peer_id)
                        await send_vk_message(peer_id, f"🔇 Включено молчание для peer_id={target_peer_id}")
                    else:
                        await send_vk_message(peer_id, f"❌ Использование: {CMD_SILENCE_USER} <peer_id>")
                    return
                
                elif command.startswith(CMD_UNSILENCE_USER.lower()):
                    parts = message_text.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        target_peer_id = int(parts[1])
                        await unsilence_user(target_peer_id)
                        await send_vk_message(peer_id, f"🔊 Снято молчание для peer_id={target_peer_id}")
                    else:
                        await send_vk_message(peer_id, f"❌ Использование: {CMD_UNSILENCE_USER} <peer_id>")
                    return
                
                elif command.startswith(CMD_CHECK_USER.lower()):
                    parts = message_text.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        target_user_id = int(parts[1])
                        # Информация о пользователе
                        is_silent = await is_chat_silent_smart(target_user_id)
                        last_activity = user_last_activity.get(target_user_id)
                        last_message = user_last_message_time.get(target_user_id)
                        thread_id = user_threads.get(get_user_key(target_user_id))
                        
                        status_text = f"👤 Информация о peer_id={target_user_id}:\n"
                        status_text += f"🔇 Молчание: {'Да' if is_silent else 'Нет'}\n"
                        status_text += f"📅 Последняя активность: {last_activity.strftime('%Y-%m-%d %H:%M:%S') if last_activity else 'Нет данных'}\n"
                        status_text += f"💬 Последнее сообщение: {last_message.strftime('%Y-%m-%d %H:%M:%S') if last_message else 'Нет данных'}\n"
                        status_text += f"🧵 Thread ID: {thread_id[:20] + '...' if thread_id else 'Нет треда'}"
                        
                        await send_vk_message(peer_id, status_text)
                    else:
                        await send_vk_message(peer_id, f"❌ Использование: {CMD_CHECK_USER} <peer_id>")
                    return
                
                elif command.startswith(CMD_CLEAR_HISTORY.lower()):
                    parts = message_text.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        target_user_id = int(parts[1])
                        # Очищаем историю пользователя
                        user_key = get_user_key(target_user_id)
                        
                        # Удаляем из памяти
                        user_messages.pop(target_user_id, None)
                        user_last_activity.pop(target_user_id, None)
                        user_last_message_time.pop(target_user_id, None)
                        
                        # Удаляем тред
                        old_thread = user_threads.pop(user_key, None)
                        if old_thread:
                            save_user_threads_to_file()
                        
                        # Удаляем файл истории
                        history_file = os.path.join(HISTORY_DIR, f"user_{target_user_id}_history.jsonl")
                        if os.path.exists(history_file):
                            os.remove(history_file)
                        
                        await send_vk_message(peer_id, f"🗑️ История пользователя peer_id={target_user_id} очищена")
                    else:
                        await send_vk_message(peer_id, f"❌ Использование: {CMD_CLEAR_HISTORY} <peer_id>")
                    return
                
                # === ИНФОРМАЦИОННЫЕ КОМАНДЫ ===
                elif command == CMD_STATUS.lower():
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    active_threads = len([tid for tid in user_threads.values() if tid])
                    silent_count = sum(1 for is_silent in chat_silence_state.values() if is_silent)
                    pending_count = len(pending_messages)
                    active_timers = sum(1 for task in user_message_timers.values() if not task.done())
                    
                    status_msg = f"📊 СТАТУС БОТА ({current_time}):\n"
                    status_msg += f"🧵 Активных тредов: {active_threads}\n"
                    status_msg += f"🔇 В режиме молчания: {silent_count}\n"
                    status_msg += f"⏳ Ожидающих сообщений: {pending_count}\n"
                    status_msg += f"⏱️ Активных таймеров: {active_timers}\n"
                    status_msg += f"👥 Пользователей с активностью: {len(user_last_activity)}"
                    
                    await send_vk_message(peer_id, status_msg)
                    return
                
                elif command == CMD_CHECK_DB.lower():
                    try:
                        # Проверяем состояние векторной базы
                        collection_info = "🗃️ СОСТОЯНИЕ БАЗЫ ЗНАНИЙ:\n"
                        
                        if vector_collection:
                            try:
                                count = vector_collection.count()
                                collection_info += f"📊 Количество документов: {count}\n"
                            except Exception as e:
                                collection_info += f"❌ Ошибка подсчёта: {str(e)[:50]}...\n"
                        else:
                            collection_info += "❌ Коллекция не инициализирована\n"
                        
                        # Проверяем файлы истории
                        if os.path.exists(HISTORY_DIR):
                            history_files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.jsonl')]
                            collection_info += f"📁 Файлов истории: {len(history_files)}"
                        else:
                            collection_info += "📁 Папка истории не найдена"
                        
                        await send_vk_message(peer_id, collection_info)
                    except Exception as e:
                        await send_vk_message(peer_id, f"❌ Ошибка проверки БД: {str(e)[:100]}...")
                    return
                
                elif command == CMD_HELP.lower():
                    help_text = "🤖 КОМАНДЫ УПРАВЛЕНИЯ БОТОМ:\n\n"
                    help_text += "📢 ОСНОВНЫЕ:\n"
                    help_text += f"• {CMD_SPEAK} - снять молчание с текущего диалога\n"
                    help_text += f"• {CMD_UPDATE} - обновить базу знаний (админ)\n"
                    help_text += f"• {CMD_RESET} - сбросить текущий диалог\n"
                    help_text += f"• {CMD_RESET_ALL} - сбросить все диалоги (админ)\n\n"
                    
                    help_text += "🔇 УПРАВЛЕНИЕ МОЛЧАНИЕМ:\n"
                    help_text += f"• {CMD_SILENCE} - включить молчание\n"
                    help_text += f"• {CMD_UNSILENCE} - снять молчание\n"
                    help_text += f"• {CMD_LIST_SILENT} - список молчащих диалогов\n"
                    help_text += f"• {CMD_SILENCE_USER} <peer_id> - включить молчание для пользователя\n"
                    help_text += f"• {CMD_UNSILENCE_USER} <peer_id> - снять молчание для пользователя\n\n"
                    
                    help_text += "📊 ИНФОРМАЦИЯ:\n"
                    help_text += f"• {CMD_STATUS} - статус бота\n"
                    help_text += f"• {CMD_CHECK_DB} - состояние базы знаний\n"
                    help_text += f"• {CMD_CHECK_USER} <peer_id> - информация о пользователе\n"
                    help_text += f"• {CMD_CLEAR_HISTORY} <peer_id> - очистить историю пользователя\n"
                    help_text += f"• {CMD_HELP} - эта справка"
                    
                    await send_vk_message(peer_id, help_text)
                    return

            if await is_chat_silent_smart(peer_id):
                logger.info(f"Бот в режиме молчания для peer_id={peer_id} (CRM). Сообщение от user_id={user_id} игнорируется.")
                return

            now_dt = datetime.datetime.now()
            last_time = user_last_message_time.get(user_id)
            if last_time and now_dt - last_time < datetime.timedelta(seconds=MESSAGE_COOLDOWN_SECONDS):
                logger.warning(f"Кулдаун для user_id={user_id}. Игнорируем.")
                return
            user_last_message_time[user_id] = now_dt
            # НОВОЕ: Обновляем активность пользователя для системы снятия молчания
            user_last_activity[user_id] = now_dt

            logger.info(f"Получено сообщение от user_id={user_id} (peer_id={peer_id}): '{message_text[:100]}...'")
            pending_messages.setdefault(peer_id, []).append(message_text)
            logger.debug(f"Сообщение от peer_id={peer_id} добавлено в буфер: {pending_messages[peer_id]}")
            if peer_id in user_message_timers:
                old_timer = user_message_timers.pop(peer_id)
                if not old_timer.done():
                    try: old_timer.cancel()
                    except Exception as e_cancel: logger.warning(f"Не удалось отменить таймер: {e_cancel}")
            logger.debug(f"Запуск таймера буферизации для peer_id={peer_id} ({MESSAGE_BUFFER_SECONDS} сек).")
            new_timer_task = asyncio.create_task(schedule_buffered_processing(peer_id, user_id))
            user_message_timers[peer_id] = new_timer_task
        
        # elif event.from_chat: # Убрано, так как from_user/from_chat теперь через event.object.message.from_id
        #     # Логика для чатов, если from_id < 0 (от сообщества) или если это чат (peer_id > 2_000_000_000)
        #     pass
        else:
            logger.debug(f"Получено событие Long Poll типа {event.type}, не MESSAGE_NEW от пользователя, или нет from_id. Пропускается.")

    except Exception as e:
        logger.error(f"Критическая ошибка в handle_new_message: {e}", exc_info=True)

# --- Main Application Logic ---
async def run_update_and_notify_admin(notification_peer_id: int):
    logger.info(f"run_update_and_notify_admin: Запуск обновления БЗ для peer_id={notification_peer_id}")
    update_result = await update_vector_store()
    current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    admin_message = f"🔔 Отчет об обновлении БЗ ({current_time_str}):\n"
    if update_result.get("success"):
        admin_message += (f"✅ Успешно!\n➕ Добавлено: {update_result.get('added_chunks', 'N/A')}\n"
                          f"📊 Всего: {update_result.get('total_chunks', 'N/A')}\n")
        if update_result.get("new_active_path"): admin_message += f"📁 Путь: {update_result['new_active_path']}"
    else:
        admin_message += f"❌ Ошибка: {update_result.get('error', 'N/A')}\nБаза могла не измениться."
    logger.info(f"Результат обновления БЗ: {admin_message}")
    try:
        await send_vk_message(notification_peer_id, admin_message)
        # Исправление №8: Упрощение условия
        if ADMIN_USER_ID > 0 and notification_peer_id != ADMIN_USER_ID:
            await send_vk_message(ADMIN_USER_ID, "[Авто] " + admin_message)
    except Exception as e_notify:
        logger.error(f"Не удалось отправить уведомление админу: {e_notify}", exc_info=True)

async def main():
    logger.info("--- Запуск VK бота ---")
    
    # Исправление №11: Инициализация переменных
    cleanup_task: Optional[asyncio.Task] = None
    listen_task: Optional[asyncio.Task] = None

    await load_silence_state_from_file()
    # НОВОЕ: Загружаем соответствия user_id ↔ thread_id из файла
    load_user_threads_from_file()
    await _initialize_active_vector_collection()
    logger.info("Запуск фонового обновления БЗ при старте...")
    asyncio.create_task(run_update_and_notify_admin(ADMIN_USER_ID))
    cleanup_task = asyncio.create_task(background_cleanup_task())
    # НОВОЕ: Запускаем фоновую задачу проверки неактивных пользователей
    inactive_check_task = asyncio.create_task(check_inactive_silence_task())
    logger.info("Фоновые задачи запущены: очистка + проверка неактивных пользователей")
    logger.warning("Используется СИНХРОННЫЙ VkBotLongPoll. Это БЛОКИРУЕТ асинхронный цикл.")
    
    try:
        loop = asyncio.get_running_loop()
        listen_task = asyncio.create_task(asyncio.to_thread(run_longpoll_sync, loop), name="VKLongPollListener")
        if listen_task: await listen_task # Ждем завершения задачи
    except vk_api.exceptions.ApiError as e:
        logger.critical(f"Критическая ошибка VK API в Long Poll: {e}", exc_info=True)
    except Exception as e:
         logger.critical(f"Критическая ошибка в главном цикле: {e}", exc_info=True)
    finally:
        logger.info("Завершение работы фоновых задач...")
        if cleanup_task and not cleanup_task.done():
            cleanup_task.cancel()
        # НОВОЕ: Завершаем задачу проверки неактивных пользователей
        if inactive_check_task and not inactive_check_task.done():
            inactive_check_task.cancel()
        if listen_task and not listen_task.done():
             listen_task.cancel()
             logger.warning("Запрошена отмена задачи Long Poll.")
        
        tasks_to_gather = []
        if cleanup_task: tasks_to_gather.append(cleanup_task)
        if inactive_check_task: tasks_to_gather.append(inactive_check_task)
        if listen_task: tasks_to_gather.append(listen_task)
        
        if tasks_to_gather:
            await asyncio.gather(*tasks_to_gather, return_exceptions=True)
        
        logger.info("--- Бот остановлен ---")

def run_longpoll_sync(async_loop: asyncio.AbstractEventLoop):
    logger.info("Запуск синхронного Long Poll в отдельном потоке...")
    MAX_RECONNECT_ATTEMPTS, RECONNECT_DELAY_SECONDS = 5, 30
    current_attempts = 0
    # global vk_session_api, VK_GROUP_ID # Они и так доступны как глобальные
    
    while True:
        try:
            if not vk_session_api:
                logger.error("[Thread LongPoll] vk_session_api не инициализирована.")
                time_module.sleep(RECONNECT_DELAY_SECONDS * 5)
                continue

            logger.info(f"[Thread LongPoll] Инициализация VkBotLongPoll (попытка {current_attempts + 1}).")
            # VK_GROUP_ID уже int
            current_longpoll = VkBotLongPoll(vk_session_api, VK_GROUP_ID)
            logger.info("[Thread LongPoll] VkBotLongPoll инициализирован.")
            current_attempts = 0
            logger.info("[Thread LongPoll] Начало прослушивания событий...")
            for event in current_longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    asyncio.run_coroutine_threadsafe(handle_new_message(event), async_loop)
                elif event.type == VkBotEventType.MESSAGE_REPLY:
                    logger.debug(f"Получено MESSAGE_REPLY: {event.object}") # event.object вместо event.obj
                    try:
                        # VK_GROUP_ID уже int
                        is_outgoing_from_group = (event.object.get('out') == 1 and 
                                                  event.object.get('from_id') == -VK_GROUP_ID)
                        
                        if is_outgoing_from_group:
                            event_random_id = event.object.get('random_id')
                            peer_id = event.object.get('peer_id')

                            if event_random_id is not None and event_random_id in MY_PENDING_RANDOM_IDS:
                                MY_PENDING_RANDOM_IDS.remove(event_random_id)
                                logger.debug(f"MESSAGE_REPLY от бота (random_id: {event_random_id}) для peer_id={peer_id}. Удален.")
                            else:
                                crm_message_text = event.object.get('text', '') 
                                
                                # Проверка на символ обхода молчания
                                if BYPASS_SYMBOL in crm_message_text:
                                    logger.info(f"MESSAGE_REPLY с символом обхода '{BYPASS_SYMBOL}' от CRM/оператора для peer_id={peer_id}. Молчание НЕ активируется.")
                                else:
                                    logger.info(f"MESSAGE_REPLY от CRM/оператора (текст: '{crm_message_text[:50]}...', random_id: {event_random_id}) для peer_id={peer_id}. Активируем ПОСТОЯННЫЙ режим молчания.")
                                    if peer_id:
                                        asyncio.run_coroutine_threadsafe(silence_user(peer_id), async_loop)
                                    else:
                                        logger.warning(f"Не удалось определить peer_id из MESSAGE_REPLY для CRM: {event.object}")
                        else:
                             logger.debug(f"Пропускаем MESSAGE_REPLY (не от нашей группы или не исходящее): {event.object}")
                    except Exception as e_reply_proc:
                        logger.error(f"Ошибка при обработке MESSAGE_REPLY: {e_reply_proc}", exc_info=True)
                        logger.debug(f"Ошибочный MESSAGE_REPLY: {event.object}")
                else:
                    logger.debug(f"Пропускаем событие типа {event.type}")
            logger.warning("[Thread LongPoll] Цикл listen() завершился. Перезапуск...")
            current_attempts = 0
            time_module.sleep(RECONNECT_DELAY_SECONDS)
        except (requests.exceptions.RequestException, vk_api.exceptions.VkApiError) as e_net:
            logger.error(f"[Thread LongPoll] Ошибка сети/VK API: {e_net}", exc_info=True)
            current_attempts += 1
            if MAX_RECONNECT_ATTEMPTS > 0 and current_attempts >= MAX_RECONNECT_ATTEMPTS:
                logger.critical(f"[Thread LongPoll] Превышено макс. попыток переподключения. Остановка.")
                if ADMIN_USER_ID > 0: # Отправляем админу только если ID валидный
                    asyncio.run_coroutine_threadsafe(send_vk_message(ADMIN_USER_ID, "Критическая ошибка: VK Long Poll остановлен."), async_loop)
                break
            logger.info(f"[Thread LongPoll] Пауза {RECONNECT_DELAY_SECONDS}с перед попыткой {current_attempts + 1}...")
            time_module.sleep(RECONNECT_DELAY_SECONDS)
        except Exception as e_fatal:
            logger.critical(f"[Thread LongPoll] Непредвиденная критическая ошибка: {e_fatal}", exc_info=True)
            current_attempts += 1
            if MAX_RECONNECT_ATTEMPTS > 0 and current_attempts >= MAX_RECONNECT_ATTEMPTS:
                 logger.critical(f"[Thread LongPoll] Превышено макс. попыток после непредвиденной ошибки. Остановка.")
                 if ADMIN_USER_ID > 0:
                     asyncio.run_coroutine_threadsafe(send_vk_message(ADMIN_USER_ID, "Критическая ошибка: VK Long Poll остановлен (непредвиденная ошибка)."), async_loop)
                 break
            logger.info(f"[Thread LongPoll] Пауза {RECONNECT_DELAY_SECONDS * 2}с перед попыткой {current_attempts + 1}...")
            time_module.sleep(RECONNECT_DELAY_SECONDS * 2)
    logger.info("[Thread LongPoll] Поток Long Poll завершен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt. Завершение работы...")
    except Exception as e:
         logger.critical(f"Критическая ошибка при запуске: {e}", exc_info=True)