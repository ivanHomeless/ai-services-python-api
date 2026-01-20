
import os
import json
import wave
import base64
import asyncio
import requests
import speech_recognition as sr
from pydub import AudioSegment
from dotenv import load_dotenv

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
from Crypto import Random


load_dotenv()

# Словарь поддерживаемых форматов
SUPPORTED_FORMATS = {
    "wav": "wav",
    "mp3": "mp3",
    "ogg": "ogg",
    "oga": "ogg",  # oga — это Ogg контейнер с Opus
}

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


def speech_to_text(
    file_path: str,
    lang: str = "ru-RU",
    chunk_length_ms: int = 30000
) -> str:
    # Определяем формат по расширению
    ext = file_path.split(".")[-1].lower()
    format_for_pydub = SUPPORTED_FORMATS.get(ext)
    if not format_for_pydub:
        raise ValueError(f"Unsupported audio format: {ext}")

    wav_path = f"{file_path}.wav"

    try:
        # Конвертируем в WAV
        audio_segment = AudioSegment.from_file(file_path, format=format_for_pydub)\
                                   .set_channels(1)\
                                   .set_frame_rate(16000)
        audio_segment.export(wav_path, format="wav")
    except Exception as e:
        raise RuntimeError(f"Failed to convert audio to WAV: {e}")

    recognizer = sr.Recognizer()
    audio = AudioSegment.from_wav(wav_path)
    full_text = ""

    for i, start_ms in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[start_ms:start_ms + chunk_length_ms]
        chunk_file = f"{wav_path}_{i}.wav"

        try:
            chunk.export(chunk_file, format="wav")
            with sr.AudioFile(chunk_file) as source:
                audio_data = recognizer.record(source)
            try:
                part = recognizer.recognize_google(audio_data, language=lang)
                full_text += " " + part
            except sr.UnknownValueError:
                full_text += " [неразборчиво] "
            except sr.RequestError as e:
                full_text += f" [ошибка сервиса: {e}] "
        finally:
            # Удаляем chunk файл
            if os.path.exists(chunk_file):
                os.remove(chunk_file)

    # Удаляем WAV файл после обработки
    if os.path.exists(wav_path):
        os.remove(wav_path)

    return full_text.strip()


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
jwt_token = get_jwt()  # получаем токен один раз при старте

def synthesize_speech(text: str, voice_name: str = "Oleg:master", filename="output.wav"):
    global jwt_token
    payload = {
        "text": f"<speak>{text}</speak>",
        "samplerate": 16000,
        "offline": True,
        "voice_name": voice_name,
        "enable_normalization": True,
        "speed": 0.9
    }
    headers = {
        "Content-Type": "application/json",
        "X-Token": jwt_token
    }

    response = requests.post(key_data["endpoint_tts"], headers=headers, json=payload)

    # если токен истёк — обновляем и повторяем один раз
    if response.status_code == 401:
        jwt_token = get_jwt()
        headers["X-Token"] = jwt_token
        response = requests.post(key_data["endpoint_tts"], headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"TTS request failed: {response.status_code} {response.text}")

    audio_data = response.content
    save_wav(filename, audio_data)
    print(f"Saved TTS to {filename}")