""""""
import json
import math
import time

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, FileResponse
import uuid as UUID

conns = {} # nickname : websocket
conns_profiles = {} # uuid : Profile
history = []
unknown_conns = []
app = FastAPI()
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

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
        <style>
            .msg{
                border-radius: 5px;
                padding: 5px;
                margin: 5px;
                border: 2px solid gray;
                width: fit-content;
                background-color: rgb(200,200,200);
            }
            .nick {
                font-weight: bold;
            }
            .time: {
                color: gray;
                font-size: 10px;
            }
            #typer:{

            }
        </style>

    </head>
    <body>
    <label for="nick" onclick="auth()">Ваш ник</label>
    <input type="text" name="nick" id="nick">
    <button id="auth">Залогиниться</button>
        <h1>DurkaChat</h1>

        <ul id='messages'>
        </ul>
        <form action="" onsubmit="sendMessage(event)" id="typer">
            <input type="text" id="messageText" autocomplete="off" placeholder="Сообщение или /help"/>
            <button>Отправить 🚀</button>
        </form>
        <script>
            let uuid = ""
            let ws = new WebSocket("ws://kihre.xyz:6969/ws");
            document.getElementById("auth").addEventListener("click", auth)
            function auth(){
                if (uuid!="") return
                let inp = document.getElementById("nick").value
                ws.send("AUTH_AS<|PARSE_SPLIT|>" + inp)
                console.log(inp)
                document.getElementById("auth").style= "display:none;"
            }

            ws.onmessage = function(event) {
                console.log(event.data)
                if (event.data.startsWith(`AUTH:`)){
                    uuid = event.data.split(":")[1]
                    return
                }
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
                message.classList.add("msg")
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                if (input.value == "") {
                    event.preventDefault();
                    return;
                }
                ws.send(`SEND<|PARSE_SPLIT|>${uuid}<|PARSE_SPLIT|>${input.value}`)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    #return HTMLResponse(html)
    return FileResponse('developement.html')
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
    await websocket.accept()
    unknown_conns.append(websocket)

    async def SendMessageToAll(message:str):
        # try:
        # print("SENDING TO ALL: " + message)

        history.append(message)
        # print(history)
        if len(history) > 100:
            history.pop(0)
        #     print("SENDING TO ALL - HISTORY CLEANED")
        # print("STARTING SENDING TO ALL")
        for conn in conns.keys():
            # print(conn)
            # print(conns[conn])
            # print(message)
            try:
                await conns[conn].send_text(message)
            except Exception as eee:
                print("Could not send message to: " + conn + "\nBecause: " + str(eee))
        #     print("SENT TO: " + conn)
        # print("FINISHED SENDING TO ALL")
        # except Exception as e:
        #     print("Could not send message: " + str(e))
    try:
        while True:
            data_raw = await websocket.receive_text()
            # print(data_raw)
            data = json.loads(str(data_raw))
            # print(data)
            action = data["action"]
            if action == "AUTH":
                # print("AUTH")
                if not websocket in unknown_conns:
                    # print("ALREADY AUTHED")
                    await websocket.send_text(str(json.dumps(
                        {"action": "MESSAGE",
                        "type":"error", "content":"Ты уже залогинился!",
                         "timestamp":math.floor(time.time()*1000),
                         "sender": "Ошибка авторизации",
                         "avatar_color_top": "#aa5555",
                         "avatar_color_bottom": "#441111",
                         "avatar_emoji": "🤖"}
                    )))
                    # print("ALREADY AUTHED - ERROR SENT")
                else:
                    # print("NOT AUTHED")
                    uuid = str(UUID.uuid4())
                    # print("NOT AUTHED - UUID GENERATED")
                    unknown_conns.remove(websocket)
                    # print("NOT AUTHED - CONNECTION REMOVED FROM UNKNOWN")
                    conns[uuid] = websocket
                    conns_profiles[str(uuid)] = Profile(data["nickname"], data["avatar_emoji"], data["avatar_color_top"], data["avatar_color_bottom"])
                    # print("NOT AUTHED - PROFILE ADDED")
                    await websocket.send_text(str(json.dumps(
                        {"action": "AUTH_RESULT", "uuid": uuid})
                    ))
                    # print("NOT AUTHED - AUTHED")
                    msg = {"action": "MESSAGE",
                         "type":"user_join", "content":f"Пользователь присоединился к чату! Онлайн: {len(conns)}",
                         "timestamp":math.floor(time.time()*1000),
                         "sender": data["nickname"],
                         "avatar_color_top": data["avatar_color_top"],
                         "avatar_color_bottom": data["avatar_color_bottom"],
                         "avatar_emoji": data["avatar_emoji"]}
                    # print("NOT AUTHED - FORMED JOIN MSG")
                    await SendMessageToAll(str(json.dumps(msg)))
                    # print("NOT AUTHED - SENT JOIN MSG. AUTH COMPLETED")
            elif action == "UPDATE_PROFILE":
                # print("UPDATE_PROFILE")
                # conns_profiles[str(data["uuid"])] = Profile(data["nickname"], data["avatar_emoji"], data["avatar_color_top"], data["avatar_color_bottom"])
                # print(data["nickname"], conns_profiles[str(data["uuid"])].nickname, sep=" ")
                msg = {"action": "MESSAGE",
                         "type":"profile_update", "content":f"{conns_profiles[str(data['uuid'])].nickname} обновил профиль!",
                         "timestamp":math.floor(time.time()*1000),
                         "sender": data["nickname"],
                         "avatar_color_top": data["avatar_color_top"],
                         "avatar_color_bottom": data["avatar_color_bottom"],
                         "avatar_emoji": data["avatar_emoji"]}
                await SendMessageToAll(str(json.dumps(msg)))
                conns_profiles[str(data["uuid"])].nickname = data["nickname"]
                conns_profiles[str(data["uuid"])].avatar_emoji = data["avatar_emoji"]
                conns_profiles[str(data["uuid"])].avatar_color_top = data["avatar_color_top"]
                conns_profiles[str(data["uuid"])].avatar_color_bottom = data["avatar_color_bottom"]
                # print("UPDATE_PROFILE - DONE")
            elif action == "MESSAGE":
                # print("MESSAGE")
                if not data["uuid"] in conns_profiles.keys():
                    # print("MESSAGE SENDING - NOT AUTHED")
                    await websocket.send_text(str(json.dumps(
                        {"action": "MESSAGE",
                         "type": "error", "content": "Введите ник и настройки профиля!",
                         "timestamp": math.floor(time.time() * 1000),
                         "sender": "Ошибка авторизации",
                         "avatar_color_top": "#aa5555",
                         "avatar_color_bottom": "#441111",
                         "avatar_emoji": "🤖"}
                    )))
                    # print("MESSAGE SENDING - NOT AUTHED - ERROR SENT")
                elif data['content'].startswith("/"):
                    # print("PROCESSING COMMAND")
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
                    # print("PROCESSING COMMAND - DONE")
                else:
                    # print("NORMAL MESSAGE SENDING")
                    msg = {"action": "MESSAGE",
                         "type": "message", "content": data["content"],
                         "timestamp": math.floor(time.time() * 1000),
                         "sender": conns_profiles[data["uuid"]].nickname,
                         "avatar_color_top": conns_profiles[data["uuid"]].avatar_color_top,
                         "avatar_color_bottom": conns_profiles[data["uuid"]].avatar_color_bottom,
                         "avatar_emoji": conns_profiles[data["uuid"]].avatar_emoji}
                    # print("NORMAL MESSAGE SENDING - FORMED MSG")
                    await SendMessageToAll(str(json.dumps(msg)))
                    # print("NORMAL MESSAGE SENDING - DONE")




    except Exception as e:
        # print("Disconnected: " + str(e))

        nick_l = ""
        profile = None
        # print("CLEANING...")
        msg = ""
        for uuid in conns.keys():
            if conns[uuid] == websocket:
                # print("DISCONNECTED FROM CONN: " + uuid)
                nick_l= conns_profiles[uuid].nickname
                del conns[uuid]
                # print(conns_profiles, list(conns_profiles.keys()), uuid)
                for profile_uuid in conns_profiles.keys():
                    if profile_uuid == uuid:
                        # print("DISCONNECTED FROM PROFILES: " + profile_uuid)
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
            # msg = {"action": "MESSAGE", "type": "user_left", "content": f"{nick_l} покинул чат! Онлайн: {len(conns.keys())}",
            #        "timestamp": math.floor(time.time() * 1000),
            #        "sender": nick_l, "avatar_color_top": profile.avatar_color_top, "avatar_color_bottom": profile.avatar_color_bottom,
            #        "avatar_emoji": profile.avatar_emoji}
            await SendMessageToAll(str(json.dumps(msg)))
        except Exception as ee:
            print(ee)
    # try:
    #     while True:
    #
    #         data = await websocket.receive_text()
    #
    #         if data.startswith("AUTH_AS"):
    #             # print(data)
    #             nick = data.split("<|PARSE_SPLIT|>")[1]
    #             if not nick in conns.keys():
    #                 uuid = UUID.uuid4()
    #                 conns[nick] = websocket
    #                 conns_nicks[str(uuid)] = nick
    #                 unknown_conns.remove(websocket)
    #                 await websocket.send_text(f"AUTH:{uuid}")
    #                 # print(conns_nicks, conns)
    #                 for sock in conns.values():
    #                     await sock.send_text(f"{nick} залетел в беседу с ноги! Онлайн в чате: {len(conns.keys())}")
    #         elif data.startswith("SEND"):
    #             parts = data.split("<|PARSE_SPLIT|>")
    #             # print(conns_nicks, parts, conns)
    #             if conns_nicks.get(parts[1]):
    #                 nick = conns_nicks.get(parts[1])
    #                 if parts[2] != "":
    #                     # print(conns)
    #                     if parts[2] == "/help":
    #                         await websocket.send_text("/help /users")
    #                     elif parts[2] == "/users":
    #                         await websocket.send_text(str(list(conns.keys())))
    #                     else:
    #                         for sock in conns.values():
    #                             try:
    #                                 await sock.send_text(f"{nick}: {parts[2]}")
    #                             except:
    #                                 ...
    #             else:
    #                 await websocket.send_text(f"Не удалось авторизоваться!")
    # except:
    #     nick_l = ""
    #     for nick in conns.keys():
    #         if conns[nick] == websocket:
    #             nick_l = nick
    #             del conns[nick]
    #             for ud in conns_nicks.keys():
    #                 if conns_nicks[ud] == nick_l:
    #                     del conns_nicks[ud]
    #                     break
    #             break
    #     try:
    #         for sock in conns.values():
    #             await sock.send_text(f"{nick_l} потерялся. Онлайн в чате: {len(conns.keys())}")
    #     except:
    #         print(":(")

