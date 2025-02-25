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

const urlParams = new URLSearchParams(window.location.search);
const added = urlParams.get("added");

const successAlert = Swal.mixin({
  animation: true,
  position: "top-end",
  icon: "success",
  iconColor: "#550572",
  color: "#43045a",
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

if (added) {
  successAlert.fire({
    title: "Success!",
    html: `Added
      <a id="success-alert" href="${added}" target="_blank" rel="noopener noreferrer">one item</a>
      to the download queue.`
  });
}

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

  ws = new WebSocket(url);

  ws.onopen = () => {
    console.log("WebSocket connection established.");
    isConnected = true;
  };

  ws.onmessage = (event) => {
    const newLines = event.data.split("\n").map(line => line.trim()).filter(Boolean);
    if (newLines.length === 0) return;

    let progressUpdate = false;

    const lines = box.textContent.split("\n").filter(Boolean);
    const lastLine = lines.length > 0 ? lines[lines.length - 1] : null;

    if (lastLine && lastLine.includes("B/s") && newLines[0].includes("B/s")) {
      progressUpdate = true;

      lines[lines.length - 1] = newLines[0];
      lines.push(...newLines.slice(1));
    } else {
      lines.push(...newLines);
    }
    box.textContent = lines.join("\n") + "\n";

    if (!progressUpdate) {
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
