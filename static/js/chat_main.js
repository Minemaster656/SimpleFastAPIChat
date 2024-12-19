let messageSound = document.getElementById("message-sound");
let joinSound = document.getElementById("join-sound");
let leaveSound = document.getElementById("leave-sound");
let connectSound = document.getElementById("connect-sound");
let isTabFocused = true;
let connected = false;
let uuid = "";
let server = "kihre.xyz:6969";
const md = window.markdownit();
md.use(window.markdownitEmoji);

document
  .getElementById("show-hide-customise")
  .addEventListener("click", ShowHideCustomisation);
let ws = null;
let sendQueue = [];
const WORKER_INTERVAL = 100;

document.addEventListener("visibilitychange", () => {
  isTabFocused = !document.hidden;
  console.log("Tab is focused:", isTabFocused);
});

function OpenSocket() {
  let server = document.getElementById("servers").value;
  ws = new WebSocket(`ws://${server}/ws`);
  console.log(`Connected to ws://${server}/ws`);
  ws.onclose = function (event) {
    connected = false;
    document.getElementById("not-connected").style = "display:block";
    console.log("Connection closed");
  };
  ws.onopen = function (event) {
    connected = true;
    document.getElementById("not-connected").style = "display:none";
    console.log("Connection opened");
  };
  ws.onmessage = function (event) {
    console.log("Message recieved: ", event.data);
    //console.log(event.data)
    let data = JSON.parse(event.data);
    if (data.action == "AUTH_RESULT") {
      uuid = data.uuid;
    } else if (data.action == "MESSAGE") {
      MakeMessage(data);
    } else if (data.action == "MESSAGES") {
      for (let i = 0; i < data.content.length; i++) {
        // const messageData = JSON.parse(data.content[i]);
        MakeMessage(data.content[i]);
      }
    }
  };
}
function ShowHideCustomisation() {
  document.getElementById("customisation").classList.toggle("hidden");
}

document.getElementById("auth").addEventListener("click", auth);
function auth() {
  if (connected == false) {
    OpenSocket();
  }
  let name = document.getElementById("nick").value;
  let avatar_emoji = document.getElementById("avatar-emoji").value;
  let avatar_color_top = document.getElementById("avatar-color-top").value;
  let avatar_color_bottom = document.getElementById(
    "avatar-color-bottom"
  ).value;

  if (uuid == "") {
    sendQueue.push(
      JSON.stringify({
        action: "AUTH",
        nickname: name,
        avatar_emoji: avatar_emoji,
        avatar_color_top: avatar_color_top,
        avatar_color_bottom: avatar_color_bottom,
      })
    );
    //console.log(inp)
    //document.getElementById("auth").style = "display:none;"
  } else {
    ws.send(
      JSON.stringify({
        action: "UPDATE_PROFILE",
        uuid: uuid,
        nickname: name,
        avatar_emoji: avatar_emoji,
        avatar_color_top: avatar_color_top,
        avatar_color_bottom: avatar_color_bottom,
      })
    );
  }
}
function MakeMessage(data) {
  let div = document.createElement("div");
  div.classList.add("message");
  if (data.type == "error") {
    div.classList.add("error");
  } else if (data.type == "command") {
    div.classList.add("command");
  } else if (data.type == "system") {
    div.classList.add("system");
  } else if (data.type == "user_join") {
    div.classList.add("user-join");
    if (!isMuted) {
      joinSound.play();
    }
  } else if (data.type == "user_left") {
    div.classList.add("user-left");
    if (!isMuted) {
      leaveSound.play();
    }
  } else if (data.type == "profile_update") {
    div.classList.add("profile-update");
  } else if (data.type == "message") {
    div.classList.add("message");
    if (!isMuted) {
      messageSound.play();
    }
  }
  let senderdata = document.createElement("div");
  senderdata.classList.add("senderdata");
  let avatar = document.createElement("div");
  avatar.classList.add("avatar");
  avatar.style = `background: linear-gradient(0deg, ${data.avatar_color_bottom} 0%, ${data.avatar_color_top} 100%);`;
  avatar.innerText = data.avatar_emoji;
  senderdata.appendChild(avatar);
  let message_time_and_sender = document.createElement("div");
  message_time_and_sender.classList.add("message-time-and-sender");
  let sender_name = document.createElement("span");
  sender_name.classList.add("sender-name");
  sender_name.innerText = data.sender;
  message_time_and_sender.appendChild(sender_name);
  let timestamp = document.createElement("div");
  timestamp.classList.add("timestamp");
  
  // Преобразуем UNIX-время в формат HH:MM DD:MM:YY
  const date = new Date(data.timestamp);
  const formattedTimestamp = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')} ${String(date.getDate()).padStart(2, '0')}.${String(date.getMonth() + 1).padStart(2, '0')}.${date.getFullYear()}`;
  
  timestamp.innerText = formattedTimestamp;
  message_time_and_sender.appendChild(timestamp);
  senderdata.appendChild(message_time_and_sender);
  div.appendChild(senderdata);
  let messagecontent = document.createElement("div");
  messagecontent.classList.add("messagecontent");
  // Заменяем символы новой строки на <br> для корректного отображения
//   const md = window.markdownit();
//   const formattedContent = data.content.replace(/\n/g, "<br>");
//   messagecontent.innerHTML = DOMPurify.sanitize(md.render(formattedContent));
  // Используем библиотеку markdown-it для преобразования Markdown в HTML
  messagecontent.innerHTML = md.render(data.content.replace(/\n/g, "  \n"));
  
  
  
  div.appendChild(messagecontent);
  document.getElementById("messages").appendChild(div);
}

function sendMessageToServer(content) {
  if (content === "" || !connected) {
    return;
  }
  ws.send(
    JSON.stringify({
      action: "MESSAGE",
      uuid: uuid,
      content: content,
    })
  );
}

function handleKeyDown(event) {
  if (event.key === "Enter") {
    // Если зажат Shift или Ctrl, добавляем новую строку
    if (event.shiftKey || event.ctrlKey) {
      var input = document.getElementById("messageText");
      input.value += "\n"; // Добавляем новую строку
    } else {
      event.preventDefault(); // Отменяем стандартное поведение формы
      var input = document.getElementById("messageText");
      console.log("SENDING MESSAGE", connected, input.value);
      sendMessageToServer(input.value);
      input.value = ""; // Очищаем поле ввода
    }
  }
}

function submitMessage(event) {
  event.preventDefault(); // Отменяем стандартное поведение формы
  var input = document.getElementById("messageText");
  sendMessageToServer(input.value);
  input.value = ""; // Очищаем поле ввода
}

// Добавляем обработчик событий для текстового поля
document.getElementById("messageText").addEventListener("keydown", handleKeyDown);

setInterval(() => {
  if (sendQueue.length > 0 && connected && ws != null) {
    let str = sendQueue.shift();
    ws.send(str);
    console.log(str);
  }
}, WORKER_INTERVAL);

// Функция для управления темой
function initTheme() {
  const themeToggle = document.getElementById("themeToggle");

  // Проверяем сохранённую тему
  const savedTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);

  // Скрываем текущую тему
  if (savedTheme === "light") {
    themeToggle.querySelector(".light-icon").style.display = "none";
  } else {
    themeToggle.querySelector(".dark-icon").style.display = "none";
  }

  themeToggle.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "light" ? "dark" : "light";

    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);

    // Обновляем видимость иконок
    themeToggle.querySelector(".light-icon").style.display =
      newTheme === "light" ? "none" : "inline";
    themeToggle.querySelector(".dark-icon").style.display =
      newTheme === "dark" ? "none" : "inline";
  });
}

// Вызываем функцию при загрузке страницы
document.addEventListener("DOMContentLoaded", initTheme);

const root = document.documentElement;

const lightGradientColors = ["#e0e0e0", "#d0d0d0", "#c0c0c0"];
const darkGradientColors = ["#2a2a2a", "#3a3a3a", "#4a4a4a"];
const gradientChangeSpeed = 1000; // скорость изменения градиента в миллисекундах
const stepsPerUpdate = 100; // количество шагов для обновления градиента
let currentColorIndex = 0;
let nextColorIndex = 1;
let step = 0;

function interpolateColor(color1, color2, factor) {
  const result = color1
    .slice(1)
    .match(/.{2}/g)
    .map((hex, i) => {
      const value1 = parseInt(hex, 16);
      const value2 = parseInt(color2.slice(1).match(/.{2}/g)[i], 16);
      const interpolatedValue = Math.round(value1 + (value2 - value1) * factor);
      return ("0" + interpolatedValue.toString(16)).slice(-2);
    });
  return `#${result.join("")}`;
}

function setGradient() {
  const currentTheme = document.documentElement.getAttribute("data-theme");
  const colors =
    currentTheme === "light" ? lightGradientColors : darkGradientColors;

  const color1 = colors[currentColorIndex];
  const color2 = colors[nextColorIndex];
  const factor = step / stepsPerUpdate;
  const interpolatedColor = interpolateColor(color1, color2, factor);

  root.style.setProperty("--msg-container-bg-color", interpolatedColor);

  step++;
  if (step >= stepsPerUpdate) {
    currentColorIndex = nextColorIndex;
    nextColorIndex = (nextColorIndex + 1) % colors.length;
    step = 0; // сбрасываем шаг
  }
}

// Устанавливаем градиент при загрузке страницы
setGradient();
setInterval(setGradient, gradientChangeSpeed / stepsPerUpdate);

// Обновляем градиент при смене темы
document.getElementById("themeToggle").addEventListener("click", () => {
  currentColorIndex = 0; // сбрасываем индекс при смене темы
  nextColorIndex = 1; // сбрасываем следующий индекс
  step = 0; // сбрасываем шаг
  setGradient();
});
