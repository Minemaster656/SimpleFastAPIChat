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
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

templates = Jinja2Templates(directory="templates")  # Добавляем инициализацию шаблонизатора

conns = {} # nickname : websocket
conns_profiles = {} # uuid : Profile
history = []
unknown_conns = []
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Создание базы данных с использованием SQLAlchemy
DATABASE_URL = "sqlite:///data.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
from sqlalchemy.orm import declarative_base
Base = declarative_base()

# Определение модели сообщений
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, nullable=False)
    avatar_emoji = Column(String)
    avatar_color_top = Column(String)
    avatar_color_bottom = Column(String)
    action = Column(String)
    type = Column(String)
    content = Column(Text)
    timestamp = Column(Integer)
    sender_puuid = Column(String)
    uuid = Column(String)
    reactions = Column(Text, default="{}")

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Инициализация сессии
db = SessionLocal()

# Чтение последних n сообщений из базы данных
history = [{"sender": message.sender, "avatar_emoji": message.avatar_emoji, "avatar_color_top": message.avatar_color_top, "avatar_color_bottom": message.avatar_color_bottom, "action": message.action, "type": message.type, "content": message.content, "timestamp": message.timestamp, "sender_puuid": message.sender_puuid, "uuid": message.uuid, "reactions": json.loads(message.reactions)} for message in db.query(Message).order_by(Message.timestamp.asc()).limit(100).all()]
print(history)
# Исправление undefined ников
# for message in history:
#     if not message.sender:
#         message.sender = "Неизвестный"

# Инициализация базы данных при запуске приложения
# init_db()


class Profile:
    def __init__(self, nickname, avatar_emoji, avatar_color_top, avatar_color_bottom):
        self.nickname = nickname
        self.avatar_emoji = avatar_emoji
        self.avatar_color_top = avatar_color_top
        self.avatar_color_bottom = avatar_color_bottom
        self.public_uuid = str(UUID.uuid4())
        self.last_message = None
        self.last_timestamp = 0

    def update_last_message(self, message_text):
        self.last_message = message_text
        self.last_timestamp = int(time.time())

    def is_message_too_soon(self, message_text):
        current_time = int(time.time())
        if (self.last_message == message_text and (current_time - self.last_timestamp) < 3) or (current_time - self.last_timestamp) < 1:
            return False
        return True

    def __str__(self):
        return json.dumps({
            "nickname": self.nickname,
            "avatar_emoji": self.avatar_emoji,
            "avatar_color_top": self.avatar_color_top,
            "avatar_color_bottom": self.avatar_color_bottom,
            "public_uuid": self.public_uuid
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
    global history, conns, conns_profiles, unknown_conns, db
    await websocket.accept()
    unknown_conns.append(websocket)

    async def SendMessageToAll(message: str):

        global history, conns, conns_profiles, unknown_conns, db
        print("BROADCASTING: " + message)
        history.append(json.loads(message))
        if len(history) > 100:
            history.pop(0)

        # Добавление сообщения в базу данных
        message_data = json.loads(message)
        new_message = Message(
            sender=message_data["sender"],
            avatar_emoji=message_data["avatar_emoji"],
            avatar_color_top=message_data["avatar_color_top"],
            avatar_color_bottom=message_data["avatar_color_bottom"],
            action=message_data["action"],
            type=message_data["type"],
            content=message_data["content"],
            timestamp=message_data["timestamp"],
            sender_puuid=message_data["sender_puuid"],
            uuid=message_data["uuid"],
            reactions=json.dumps(message_data["reactions"])
        )
        db.add(new_message)
        db.commit()

        for conn in conns.keys():
            try:
                await conns[conn].send_text(message)
            except Exception as eee:
                print("Could not send message to: " + conn + "\nBecause: " + str(eee) + " [Ошибка в SendMessageToAll]")
    try:
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(str(data_raw))
            print(data)
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
                    # print("SENDING CONNECTION MESSAGE")
                    # print("DEBUG: nickname =", data["nickname"])
                    # print("DEBUG: avatar_color_top =", data["avatar_color_top"])
                    # print("DEBUG: avatar_color_bottom =", data["avatar_color_bottom"])
                    # print("DEBUG: avatar_emoji =", data["avatar_emoji"])
                    # print("DEBUG: uuid =", uuid)
                    # print(data)
                    # print(data["uuid"])
                    # print("DEBUG: public_uuid =", conns_profiles[data["uuid"]].public_uuid)

                    msg = {"action": "MESSAGE",
                         "type":"user_join", "content":f"Пользователь присоединился к чату! Онлайн: {len(conns)}",
                         "timestamp":math.floor(time.time()*1000),
                         "sender": data["nickname"],
                         "avatar_color_top": data["avatar_color_top"],
                         "avatar_color_bottom": data["avatar_color_bottom"],
                         "avatar_emoji": data["avatar_emoji"],
                         "sender_puuid": "SYSTEM",
                         "uuid": str(UUID.uuid4()),
                         "reactions": {}}
                    print(str(json.dumps(msg)))
                    await SendMessageToAll(str(json.dumps(msg)))
                    print(history)
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
                    print("SENDING PROFILE UPDATE MESSAGE")
                    msg = {"action": "MESSAGE",
                             "type": "profile_update", "content": f"{current_profile.nickname} обновил профиль!",
                             "timestamp": math.floor(time.time() * 1000),
                             "sender": data["nickname"],
                             "avatar_color_top": data["avatar_color_top"],
                             "avatar_color_bottom": data["avatar_color_bottom"],
                             "avatar_emoji": data["avatar_emoji"],
                             "sender_puuid": conns_profiles[data["uuid"]].public_uuid,
                             "uuid": str(UUID.uuid4()),
                             "reactions": {}}
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
                    profile = conns_profiles[data["uuid"]]
                    if not profile.is_message_too_soon(data["content"]):
                        await websocket.send_text(str(json.dumps(
                            {"action": "MESSAGE",
                             "type": "error", "content": "Спамить сообщениями нельзя! Можете съесть это сообщение, засунуть куда-нибудь, кинуть в костёр, отправить его чату гпт или своему психологу, но не отправлять в чат так часто!",
                             "timestamp": math.floor(time.time() * 1000),
                             "sender": "Система посыла спамеров лесом",
                             "avatar_color_top": "#aa5555",
                             "avatar_color_bottom": "#441111",
                             "avatar_emoji": "🤖"}
                        )))
                    else:
                        print("SENDING MESSAGE: " + data_raw)
                        print("DEBUG: Preparing message with the following values:")
                        print("DEBUG: content =", data["content"])
                        print("DEBUG: timestamp =", math.floor(time.time() * 1000))
                        print("DEBUG: sender =", profile.nickname)
                        print("DEBUG: avatar_color_top =", profile.avatar_color_top)
                        print("DEBUG: avatar_color_bottom =", profile.avatar_color_bottom)
                        print("DEBUG: avatar_emoji =", profile.avatar_emoji)
                        print("DEBUG: sender_puuid =", profile.public_uuid)
                        print("DEBUG: uuid =", str(UUID.uuid4()))
                        
                        msg = {"action": "MESSAGE",
                             "type": "message", "content": data["content"],
                             "timestamp": math.floor(time.time() * 1000),
                             "sender": profile.nickname,
                             "avatar_color_top": profile.avatar_color_top,
                             "avatar_color_bottom": profile.avatar_color_bottom,
                             "avatar_emoji": profile.avatar_emoji,
                             "sender_puuid": profile.public_uuid,
                             "uuid": str(UUID.uuid4()),
                             "reactions": {}}
                        await SendMessageToAll(str(json.dumps(msg)))
                        profile.update_last_message(data["content"])



    except Exception as e:
        print("Websocket error: " + str(e) + " [Ошибка в /ws e]")
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
                               "avatar_emoji": profile.avatar_emoji,
                               "sender_puuid": profile.public_uuid,
                               "uuid": str(UUID.uuid4()),
                               "reactions": {}}
                        del conns_profiles[profile_uuid]
                        break
                break
        try:
            await SendMessageToAll(str(json.dumps(msg)))
        except Exception as ee:
            print("Websocket error: " + str(ee) + " [Ошибка в /ws ee]")


import sys

port = 8001  # Порт по умолчанию
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    port = int(sys.argv[1])  # Установка порта из аргументов

# Закрытие сессии
# db.close()



uvicorn.run(app, host="0.0.0.0", port=port)