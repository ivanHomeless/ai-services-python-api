import os
import io
import json
import wave
import time
import base64
import uuid
import asyncio
import edge_tts
import requests
import threading
import speech_recognition as sr

from pydub import AudioSegment
from dotenv import load_dotenv

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
from Crypto import Random



# --- КОНСТАНТЫ ---
TMP_DIR = "/tmp"
DEFAULT_LANG = "ru-RU"
CHUNK_LENGTH_MS = 30000
SAMPLE_RATE = 16000
CHANNELS = 1

SUPPORTED_FORMATS = {
    "wav": "wav",
    "mp3": "mp3",
    "ogg": "ogg",
    "oga": "ogg",
}
# Голоса
VOICES = {
    "Karina2:master": "Женский русский голос",
    "Alex2:master": "Мужской русский голос",
    "Anna:master": "Женский русский голос",
    "Oleg:master": "Мужской русский голос",
    "en_female:dev": "Женский английский голос",
    "en_male:dev": "Мужской английский голос"
}
load_dotenv()
# ==== Загружаем данные из .env ====
key_data = {
    "organization_uuid": os.getenv("ORG_UUID"),
    "company_uuid": os.getenv("COMPANY_UUID"),
    "user_uuid": os.getenv("USER_UUID"),
    "key_name": os.getenv("KEY_NAME"),
    "key_uuid": os.getenv("KEY_UUID"),
    "private_key": os.getenv("PRIVATE_KEY"),
    "public_key_url": os.getenv("PUBLIC_KEY_URL"),
    "auth_url": os.getenv("AUTH_URL"),  # должен быть полный: https://auth-asraas-prod.neuro.net/api/v1/auth
    "endpoint_tts": os.getenv("ENDPOINT_TTS")
}

# ==== Загружаем приватный ключ клиента ====
raw_key = key_data["private_key"]
private_key = "\n".join(line.strip() for line in raw_key.strip().splitlines())
client_private_key = RSA.importKey(private_key)

# ==== Получаем публичный ключ сервера ====
resp = requests.get(key_data["public_key_url"])
resp.raise_for_status()
server_pub_b64 = resp.json()["public_key"]
server_pub_der = base64.b64decode(server_pub_b64)
server_public_key = RSA.importKey(server_pub_der)
TMP_DIR = "/tmp"


async def speech_to_text(file_bytes: bytes, original_filename: str, lang: str = "ru-RU") -> str:
    """
    Принимает байты файла, сохраняет во временное хранилище
    и запускает процесс транскрибации.
    """
    ext = original_filename.split(".")[-1].lower()
    request_id = uuid.uuid4()
    # Создаем путь для временного сохранения входящих байтов
    input_temp_path = f"{TMP_DIR}/input_{request_id}.{ext}"

    try:
        # Пишем байты в файл
        with open(input_temp_path, "wb") as f:
            f.write(file_bytes)

        # Запускаем тяжелую логику в потоке, передавая ПУТЬ к файлу
        return await asyncio.to_thread(transcribe_audio_with_chunks, input_temp_path, lang, request_id)

    finally:
        # Гарантированно удаляем входной временный файл
        if os.path.exists(input_temp_path):
            os.remove(input_temp_path)


def transcribe_audio_with_chunks(file_path: str, lang: str, request_id: uuid.UUID) -> str:
    """
    Внутренняя логика обработки файла (конвертация + нарезка + распознавание).
    """
    ext = file_path.split(".")[-1].lower()
    format_pydub = SUPPORTED_FORMATS.get(ext, "wav")
    wav_path = f"{TMP_DIR}/convert_{request_id}.wav"

    try:
        # Конвертируем исходный файл в нужный формат WAV
        audio = AudioSegment.from_file(file_path, format=format_pydub).set_channels(1).set_frame_rate(16000)
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        full_text = []

        # Загружаем сконвертированный WAV для нарезки
        audio_src = AudioSegment.from_wav(wav_path)

        for i, start_ms in enumerate(range(0, len(audio_src), CHUNK_LENGTH_MS)):
            chunk = audio_src[start_ms:start_ms + CHUNK_LENGTH_MS]
            chunk_name = f"{TMP_DIR}/chunk_{request_id}_{i}.wav"

            try:
                chunk.export(chunk_name, format="wav")
                with sr.AudioFile(chunk_name) as source:
                    audio_data = recognizer.record(source)

                # Распознавание через Google (игнорируем предупреждение атрибута)
                text = recognizer.recognize_google(audio_data, language=lang)
                full_text.append(text)
            except (sr.UnknownValueError, Exception):
                # Если фрагмент не распознан или ошибка — ставим метку
                full_text.append("[...]")
            finally:
                if os.path.exists(chunk_name):
                    os.remove(chunk_name)

        return " ".join(full_text).strip()

    finally:
        # Удаляем основной рабочий WAV файл
        if os.path.exists(wav_path):
            os.remove(wav_path)


async def text_to_speech_edge(text: str, voice: str = "ru-RU-DmitryNeural") -> str:
    """
    Генерирует речь через Microsoft Edge TTS.
    Здесь цикл не нужен, API отвечает мгновенно.
    """
    try:
        communicate = edge_tts.Communicate(text, voice)
        output_path = f"temp_tts_{int(time.time())}.mp3"
        await communicate.save(output_path)
        return output_path
    except Exception as e:
        # Если Microsoft недоступен, пробрасываем ошибку сразу
        raise RuntimeError(f"EdgeTTS failed: {e}")


# Neuro Временно отключено
async def text_to_speech(text: str, voice_name: str = "Oleg:master"):
    audio_bytes = await asyncio.to_thread(synthesize_speech, text, voice_name)
    return audio_bytes

# ==== Функция шифрования авторизационного запроса ====
def encrypt_message(plaintext: bytes):
    # Хешируем сообщение
    text_hash = SHA.new(plaintext)

    # Подпись клиента
    client_signature = PKCS1_v1_5.new(client_private_key).sign(text_hash)

    # Шифрование подписи серверным ключом блоками
    server_cipher = PKCS1_OAEP.new(server_public_key)
    block_size = server_public_key.size_in_bytes() - 42  # OAEP padding
    client_signature_final = b""
    for i in range(0, len(client_signature), block_size):
        client_signature_final += server_cipher.encrypt(client_signature[i:i + block_size])

    # Генерация сессионного ключа и IV
    session_key = Random.new().read(32)  # AES-256
    iv = Random.new().read(16)

    # AES шифрование сообщения
    aes_obj = AES.new(session_key, AES.MODE_CFB, iv)
    cipher_text = iv + aes_obj.encrypt(plaintext)

    # Шифрование сессионного ключа серверным ключом
    session_key_encrypted = server_cipher.encrypt(session_key)

    return cipher_text, session_key_encrypted, client_signature_final

# ==== Получаем JWT ====
def get_jwt():
    auth_payload = {
        "organization_uuid": key_data["organization_uuid"],
        "company_uuid": key_data["company_uuid"],
        "user_uuid": key_data["user_uuid"],
        "key_name": key_data["key_name"],
        "key_uuid": key_data["key_uuid"],
        "public_key": client_private_key.publickey().export_key().decode()
    }

    plaintext_bytes = json.dumps(auth_payload).encode("utf-8")
    cipher_text, session_key_encrypted, client_signature_final = encrypt_message(plaintext_bytes)

    auth_request = {
        "key_uuid": key_data["key_uuid"],
        "cipher_text": base64.b64encode(cipher_text).decode(),
        "session_key_encrypted": base64.b64encode(session_key_encrypted).decode(),
        "signature_final": base64.b64encode(client_signature_final).decode()
    }

    response = requests.post(key_data["auth_url"], json=auth_request)
    if response.status_code != 200:
        raise Exception(f"AUTH FAILED: {response.status_code} {response.text}")

    return response.json()["access_token"]

# ==== Сохраняем WAV ====
def save_wav(filename, audio_bytes, samplerate=16000):
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(samplerate)
        wav_file.writeframes(audio_bytes)

# ==== Синтез речи ====
#jwt_token = get_jwt()  # получаем токен один раз при старте
#token_lock = threading.Lock() # Создаем замок
def synthesize_speech(text: str, voice_name: str = "Oleg:master"):
    #global jwt_token
    jwt_token = get_jwt() # переместить в глобальный
    token_lock = threading.Lock()  # Создаем замок, переместить в глобальный
    payload = {
        "text": f"<speak>{text}</speak>",
        "samplerate": 16000,
        "offline": True,
        "voice_name": voice_name,
        "enable_normalization": True,
        "speed": 0.9
    }
    with token_lock:
        current_token = jwt_token

    headers = {
        "Content-Type": "application/json",
        "X-Token": jwt_token
    }

    response = requests.post(key_data["endpoint_tts"], headers=headers, json=payload)

    if response.status_code == 401:
        with token_lock:
            jwt_token = get_jwt()  # Обновляем глобально
            current_token = jwt_token

        headers["X-Token"] = current_token
        response = requests.post(key_data["endpoint_tts"], headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"TTS error: {response.status_code}")

    # Создаем WAV файл в оперативной памяти
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Моно
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(16000)  # Частота
        wav_file.writeframes(response.content)

    return buffer.getvalue()  # Возвращаем байты уже с заголовком WAV