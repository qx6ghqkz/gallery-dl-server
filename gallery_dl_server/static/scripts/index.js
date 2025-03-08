const darkModeStyle = document.getElementById("dark-mode");
const darkModeToggle = document.getElementById("dark-mode-toggle");

function enableDarkMode() {
  darkModeStyle.disabled = false;
  darkModeToggle.innerHTML = `<i class="bi bi-sun-fill"></i>`;
}

function disableDarkMode() {
  darkModeStyle.disabled = true;
  darkModeToggle.innerHTML = `<i class="bi bi-moon-fill"></i>`;
}

if (localStorage.getItem("theme") === "dark") {
  enableDarkMode();
}

darkModeToggle.onclick = () => {
  if (darkModeStyle.disabled) {
    enableDarkMode();
    localStorage.setItem("theme", "dark");
  } else {
    disableDarkMode();
    localStorage.setItem("theme", "light");
  }
};

const selectElement = document.querySelector("select[name='video-opts']");

function setSelectedValue() {
  const selectedValue = localStorage.getItem("selectedValue");
  if (selectedValue) {
    selectElement.value = selectedValue;
  }
}

setSelectedValue();

selectElement.onchange = () => {
  localStorage.setItem("selectedValue", selectElement.value);
};

const box = document.getElementById("box");
const btn = document.getElementById("button-logs");

function toggleLogs() {
  if (btn.innerText == "Show Logs") {
    btn.innerText = "Hide Logs";
    box.classList.remove("d-none");
    loadBox();
    localStorage.setItem("logs", "shown");
  }
  else {
    saveBox();
    btn.innerText = "Show Logs";
    box.classList.add("d-none");
    localStorage.setItem("logs", "hidden");
  }
}

function loadBox() {
  if ("boxHeight" in sessionStorage && sessionStorage.getItem("boxHeight") != "0") {
    box.style.height = sessionStorage.getItem("boxHeight") + "px";
  }
  else {
    box.style.height = "";
  }

  if ("scrollPos" in sessionStorage) {
    box.scrollTop = sessionStorage.getItem("scrollPos");
  }
  else {
    box.scrollTop = box.scrollHeight;
  }
}

function saveBox() {
  const boxPos = box.getBoundingClientRect();
  sessionStorage.setItem("boxHeight", boxPos.height);
  sessionStorage.setItem("scrollPos", box.scrollTop);
}

if (localStorage.getItem("logs") == "shown") {
  toggleLogs();
}

btn.onclick = () => toggleLogs();

function scrollOnResize() {
  let lastHeight = box.offsetHeight;

  const observer = new ResizeObserver(entries => {
    for (let entry of entries) {
      if (entry.contentRect.height > lastHeight) {
        window.scrollTo({
          top: entry.target.getBoundingClientRect().bottom + window.scrollY,
          behavior: "smooth"
        });
      }
      lastHeight = entry.contentRect.height;
    }
  });

  observer.observe(box);
}

scrollOnResize();

document.querySelector("body").classList.remove("d-none");

const form = document.getElementById("form");
const successAlert = Swal.mixin({
  animation: true,
  position: "top-end",
  icon: "success",
  iconColor: "#550572",
  color: "#550572",
  showConfirmButton: false,
  confirmButtonText: "OK",
  confirmButtonColor: "#550572",
  showCloseButton: true,
  closeButtonHtml: "&times;",
  target: "body",
  timer: 3000,
  timerProgressBar: true,
  toast: true,
  didOpen: (toast) => {
    toast.onmouseenter = Swal.stopTimer;
    toast.onmouseleave = Swal.resumeTimer;
  }
});

form.onsubmit = async (event) => {
  event.preventDefault();

  if (ws.readyState === WebSocket.CLOSED) {
    connectWebSocket();
  }

  const formData = new FormData(event.target);
  const url = formData.get("url");

  try {
    const response = await fetch("/gallery-dl/q", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }

    const data = await response.json();
    console.log(data);

    event.target.url.value = "";

    if (url) {
      successAlert.fire({
        title: "Success!",
        html: `Added
          <a href="${url}" target="_blank" rel="noopener noreferrer">one item</a>
          to the download queue.`
      });
    }
  }
  catch (error) {
    console.error(error);
  }
};

let ws;
let isConnected = false;
let isPageAlive = true;

async function fetchLogs() {
  try {
    const response = await fetch("/stream/logs", {
      method: "GET",
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
      }
    });

    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }

    const logs = await response.text();

    if (box.textContent != logs) {
      box.textContent = logs;
      box.scrollTop = box.scrollHeight;
    }

    if (!isConnected) {
      connectWebSocket();
    }
  }
  catch (error) {
    console.error(error.message);
  }
}

function connectWebSocket(allowReconnect = true) {
  const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
  const host = window.location.host;
  const url = `${protocol}${host}/ws/logs`;

  let lastLine = "";
  let lastPos = 0;

  ws = new WebSocket(url);

  ws.onopen = () => {
    console.log("WebSocket connection established.");
    isConnected = true;
  };

  ws.onmessage = (event) => {
    const newLines = event.data.split("\n").filter(Boolean);
    if (!newLines.length) return;

    const lines = box.textContent.split("\n").filter(Boolean);

    lastLine = lastPos ? lines[lastPos] : lines[lines.length - 1] || null;

    const isLastLineProgress = lastLine?.includes("B/s");
    const isNewLineProgress = newLines[0].includes("B/s");

    if (newLines.length > 1 && isNewLineProgress && newLines[1].includes("B/s")) {
      newLines.pop();
    }

    let progressUpdate = false;

    if (isLastLineProgress && isNewLineProgress) {
      progressUpdate = true;
      lastPos = lastPos || lines.length - 1;
      lines[lastPos] = newLines[0];
    }
    else if (isLastLineProgress && !isNewLineProgress) {
      lastPos = 0;
    }

    lines.push(...newLines.slice(progressUpdate ? 1 : 0));

    box.textContent = lines.join("\n") + "\n";

    if (!progressUpdate || newLines.length > 1) {
      box.scrollTop = box.scrollHeight;
    }
  };

  ws.onerror = (event) => {
    console.error("WebSocket error:", event);
  };

  ws.onclose = () => {
    if (isConnected) {
      isConnected = false;

      if (isPageAlive && allowReconnect) {
        console.log("WebSocket connection closed. Attempting to reconnect...");
        setTimeout(() => connectWebSocket(allowReconnect), 2000);
      }
    } else {
      console.log("WebSocket connection could not be established.");
    }
  };
}

fetchLogs();

window.onbeforeunload = () => {
  isPageAlive = false;

  ws.close(1000, "User is leaving the page");

  if (localStorage.getItem("logs") == "shown") {
    saveBox();
  }
};
