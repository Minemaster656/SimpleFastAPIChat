""""""
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uuid as UUID

conns = {}
conns_nicks = {}
unknown_conns = []
app = FastAPI()

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
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    unknown_conns.append(websocket)
    try:
        while True:

            data = await websocket.receive_text()
            if data.startswith("AUTH_AS"):
                # print(data)
                nick = data.split("<|PARSE_SPLIT|>")[1]
                if not nick in conns.keys():
                    uuid = UUID.uuid4()
                    conns[nick] = websocket
                    conns_nicks[str(uuid)] = nick
                    unknown_conns.remove(websocket)
                    await websocket.send_text(f"AUTH:{uuid}")
                    # print(conns_nicks, conns)
                    for sock in conns.values():
                        await sock.send_text(f"{nick} залетел в беседу с ноги! Онлайн в чате: {len(conns.keys())}")
            elif data.startswith("SEND"):
                parts = data.split("<|PARSE_SPLIT|>")
                # print(conns_nicks, parts, conns)
                if conns_nicks.get(parts[1]):
                    nick = conns_nicks.get(parts[1])
                    if parts[2] != "":
                        # print(conns)
                        if parts[2] == "/help":
                            await websocket.send_text("/help /users")
                        elif parts[2] == "/users":
                            await websocket.send_text(str(list(conns.keys())))
                        else:
                            for sock in conns.values():
                                try:
                                    await sock.send_text(f"{nick}: {parts[2]}")
                                except:
                                    ...
                else:
                    await websocket.send_text(f"Не удалось авторизоваться!")
    except:
        nick_l = ""
        for nick in conns.keys():
            if conns[nick] == websocket:
                nick_l = nick
                del conns[nick]
                for ud in conns_nicks.keys():
                    if conns_nicks[ud] == nick_l:
                        del conns_nicks[ud]
                        break
                break
        try:
            for sock in conns.values():
                await sock.send_text(f"{nick_l} потерялся. Онлайн в чате: {len(conns.keys())}")
        except:
            print(":(")

