""""""
import json
import math
import time

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates  # Импортируем шаблонизатор
import uuid as UUID
from fastapi.staticfiles import StaticFiles

templates = Jinja2Templates(directory="templates")  # Добавляем инициализацию шаблонизатора

conns = {} # nickname : websocket
conns_profiles = {} # uuid : Profile
history = []
unknown_conns = []
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
import sqlite3
import os

# Создание или подключение к базе данных SQLite
# def init_db():
#     global conn, cursor, history
# Проверка существования файла базы данных и его создание, если он отсутствует
if not os.path.exists('chat_database.db'):
    with open('chat_database.db', 'w') as f:
        pass  # Создаем пустой файл базы данных, если он не существует
db_conn = sqlite3.connect('chat_database.db')  # Имя файла базы данных
cursor = db_conn.cursor()
# ПОЛЯ СООБЩЕНИЙ
# Создание таблицы пользователей, если она не существует
cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        avatar_emoji TEXT,
        avatar_color_top TEXT,
        avatar_color_bottom TEXT,
        action TEXT,
        type TEXT,
        content TEXT,
        timestamp INTEGER
    )
''')

db_conn.commit()
# Чтение последних n сообщений из базы данных, если она уже существует
cursor.execute("SELECT * FROM messages ORDER BY timestamp ASC LIMIT ?", (100,))
history = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

# Исправление undefined ников
for message in history:
    if not message['sender']:
        message['sender'] = "Неизвестный"

# conn.close()
# Инициализация базы данных при запуске приложения
# init_db()


class Profile:
    def __init__(self, nickname, avatar_emoji, avatar_color_top, avatar_color_bottom):
        self.nickname = nickname
        self.avatar_emoji = avatar_emoji
        self.avatar_color_top = avatar_color_top
        self.avatar_color_bottom = avatar_color_bottom
    def __str__(self):
        return json.dumps({
            "nickname": self.nickname,
            "avatar_emoji": self.avatar_emoji,
            "avatar_color_top": self.avatar_color_top,
            "avatar_color_bottom": self.avatar_color_bottom
        })



@app.get("/")
async def get():
    return templates.TemplateResponse("index.html", {"request": {}})
@app.get("/stats")
async def get():
    return HTMLResponse(f'''
        <DOCTYPE html>
        <html>
            <head>
                <title>DurkaChat Stats</title>
            </head>
            <body>
                <h1>DurkaChat Stats</h1>
                <h1>Connections: ''' + str(len(conns)) + f'''</h1>
                <p>{json.dumps(conns)}</p>
                <h1>Profiles</h1>
                <p>{str(list(conns_profiles.values()))}</p>
            </body>
        </html>
    ''')


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global history, conns, conns_profiles, unknown_conns, db_conn, cursor
    await websocket.accept()
    unknown_conns.append(websocket)

    async def SendMessageToAll(message: str):
        global history, conns, conns_profiles, unknown_conns, db_conn, cursor
        print(message)
        history.append(json.loads(message))
        if len(history) > 100:
            history.pop(0)

        # Добавление сообщения в базу данных
        message_data = json.loads(message)
        cursor.execute('''
            INSERT INTO messages (sender, avatar_emoji, avatar_color_top, avatar_color_bottom, action, type, content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_data["sender"],
            message_data["avatar_emoji"],
            message_data["avatar_color_top"],
            message_data["avatar_color_bottom"],
            message_data["action"],
            message_data["type"],
            message_data["content"],
            message_data["timestamp"]
        ))
        db_conn.commit()

        for conn in conns.keys():
            try:
                await conns[conn].send_text(message)
            except Exception as eee:
                print("Could not send message to: " + conn + "\nBecause: " + str(eee))
    try:
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(str(data_raw))
            action = data["action"]
            if action == "AUTH":
                if not websocket in unknown_conns:
                    await websocket.send_text(str(json.dumps(
                        {"action": "MESSAGE",
                        "type":"error", "content":"Ты уже залогинился!",
                         "timestamp":math.floor(time.time()*1000),
                         "sender": "Ошибка авторизации",
                         "avatar_color_top": "#aa5555",
                         "avatar_color_bottom": "#441111",
                         "avatar_emoji": "🤖"}
                    )))
                else:
                    uuid = str(UUID.uuid4())
                    unknown_conns.remove(websocket)
                    conns[uuid] = websocket
                    conns_profiles[str(uuid)] = Profile(data["nickname"], data["avatar_emoji"], data["avatar_color_top"], data["avatar_color_bottom"])
                    await websocket.send_text(str(json.dumps(
                        {"action": "AUTH_RESULT", "uuid": uuid})
                    ))
                    
                    msg = {"action": "MESSAGE",
                         "type":"user_join", "content":f"Пользователь присоединился к чату! Онлайн: {len(conns)}",
                         "timestamp":math.floor(time.time()*1000),
                         "sender": data["nickname"],
                         "avatar_color_top": data["avatar_color_top"],
                         "avatar_color_bottom": data["avatar_color_bottom"],
                         "avatar_emoji": data["avatar_emoji"]}
                    await SendMessageToAll(str(json.dumps(msg)))
                    await websocket.send_text(str(json.dumps(
                        {"action": "MESSAGES",
                         "content": history,
                         "timestamp": math.floor(time.time() * 1000)}
                    )))
            elif action == "UPDATE_PROFILE":
                current_profile = conns_profiles[str(data["uuid"])]
                if (current_profile.nickname == data["nickname"] and
                    current_profile.avatar_emoji == data["avatar_emoji"] and
                    current_profile.avatar_color_top == data["avatar_color_top"] and
                    current_profile.avatar_color_bottom == data["avatar_color_bottom"]):
                    await websocket.send_text(str(json.dumps(
                        {"action": "MESSAGE",
                         "type": "error", "content": "Нельзя поменять профиль на такой же!",
                         "timestamp": math.floor(time.time() * 1000),
                         "sender": "Ошибка обновления профиля",
                         "avatar_color_top": "#aa5555",
                         "avatar_color_bottom": "#441111",
                         "avatar_emoji": "🤖"}
                    )))
                else:
                    msg = {"action": "MESSAGE",
                             "type": "profile_update", "content": f"{current_profile.nickname} обновил профиль!",
                             "timestamp": math.floor(time.time() * 1000),
                             "sender": data["nickname"],
                             "avatar_color_top": data["avatar_color_top"],
                             "avatar_color_bottom": data["avatar_color_bottom"],
                             "avatar_emoji": data["avatar_emoji"]}
                    await SendMessageToAll(str(json.dumps(msg)))
                    current_profile.nickname = data["nickname"]
                    current_profile.avatar_emoji = data["avatar_emoji"]
                    current_profile.avatar_color_top = data["avatar_color_top"]
                    current_profile.avatar_color_bottom = data["avatar_color_bottom"]
            elif action == "MESSAGE":
                if not data["uuid"] in conns_profiles.keys():
                    await websocket.send_text(str(json.dumps(
                        {"action": "MESSAGE",
                         "type": "error", "content": "Введите ник и настройки профиля!",
                         "timestamp": math.floor(time.time() * 1000),
                         "sender": "Ошибка авторизации",
                         "avatar_color_top": "#aa5555",
                         "avatar_color_bottom": "#441111",
                         "avatar_emoji": "🤖"}
                    )))
                elif data['content'].startswith("/"):
                    command = data['content'].split(" ")[0]
                    if command == "/help":
                        await websocket.send_text(str(json.dumps(
                            {"action": "MESSAGE",
                             "type": "command", "content": "Список доступных команд: /help, /users",
                             "timestamp": math.floor(time.time() * 1000),
                             "sender": "/help", "avatar_color_top": "#aaaaa7",
                             "avatar_color_bottom": "#444344",
                             "avatar_emoji": "🤖"})))
                    elif command == "/users":
                        users = [user.nickname for user in conns_profiles.values()]
                        await websocket.send_text(str(json.dumps(
                            {"action": "MESSAGE",
                             "type": "command", "content": ", ".join(users) + ", всего: " + str(len(users)),
                             "timestamp": math.floor(time.time() * 1000),
                             "sender": "/users", "avatar_color_top": "#aaaaa7",
                             "avatar_color_bottom": "#444344",
                             "avatar_emoji": "🤖"})))
                else:
                    msg = {"action": "MESSAGE",
                         "type": "message", "content": data["content"],
                         "timestamp": math.floor(time.time() * 1000),
                         "sender": conns_profiles[data["uuid"]].nickname,
                         "avatar_color_top": conns_profiles[data["uuid"]].avatar_color_top,
                         "avatar_color_bottom": conns_profiles[data["uuid"]].avatar_color_bottom,
                         "avatar_emoji": conns_profiles[data["uuid"]].avatar_emoji}
                    await SendMessageToAll(str(json.dumps(msg)))




    except Exception as e:
        nick_l = ""
        profile = None
        msg = ""
        for uuid in conns.keys():
            if conns[uuid] == websocket:
                nick_l= conns_profiles[uuid].nickname
                del conns[uuid]
                for profile_uuid in conns_profiles.keys():
                    if profile_uuid == uuid:
                        profile = conns_profiles[profile_uuid]
                        msg = {"action": "MESSAGE", "type": "user_left",
                               "content": f"{nick_l} покинул чат! Онлайн: {len(conns.keys())}",
                               "timestamp": math.floor(time.time() * 1000),
                               "sender": nick_l, "avatar_color_top": profile.avatar_color_top,
                               "avatar_color_bottom": profile.avatar_color_bottom,
                               "avatar_emoji": profile.avatar_emoji}
                        del conns_profiles[profile_uuid]
                        break
                break
        try:
            await SendMessageToAll(str(json.dumps(msg)))
        except Exception as ee:
            print(ee)


import sys

port = 8001  # Порт по умолчанию
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    port = int(sys.argv[1])  # Установка порта из аргументов

uvicorn.run(app, host="0.0.0.0", port=port)