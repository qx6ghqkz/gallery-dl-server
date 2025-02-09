let isPageAlive = true;

window.addEventListener("beforeunload", () => {
  isPageAlive = false;
});

const urlParams = new URLSearchParams(window.location.search);
const added = urlParams.get("added");

const Success = Swal.mixin({
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
  },
});

if (added) {
  Success.fire({
    title: "Success!",
    html: "Added <a id='success-alert' href=" + added + ">one item</a> to the download queue.",
  });
}

document.addEventListener("DOMContentLoaded", (event) => {
  setSelectedValue();
  const selectElement = document.querySelector("select[name='video-opts']");
  selectElement.addEventListener("change", storeSelectedValue);
});

function setSelectedValue() {
  const selectedValue = localStorage.getItem("selectedValue");
  if (selectedValue) {
    const selectElement = document.querySelector("select[name='video-opts']");
    selectElement.value = selectedValue;
  }
}

function storeSelectedValue() {
  const selectElement = document.querySelector("select[name='video-opts']");
  localStorage.setItem("selectedValue", selectElement.value);
}

scrollOnResize();

function scrollOnResize() {
  const resizableBox = document.getElementById("box");

  let lastHeight = resizableBox.offsetHeight;

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

  observer.observe(resizableBox);
}

let ws;
let isConnected = false;

fetchLogs();

async function fetchLogs() {
  const box = document.getElementById("box");

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
      connectWebSocket(box);
    }
  }
  catch (error) {
    console.error(error.message);
  }
}

function connectWebSocket(box, allowReconnect = true) {
  const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
  const host = window.location.host;
  const url = `${protocol}${host}/ws/logs`;

  ws = new WebSocket(url);

  ws.onopen = function(event) {
    console.log("WebSocket connection established.");
    isConnected = true;
  };

  ws.onmessage = function(event) {
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

  ws.onerror = function(event) {
    console.error("WebSocket error:", event);
  };

  ws.onclose = function(event) {
    if (isConnected) {
      isConnected = false

      if (isPageAlive && allowReconnect) {
        console.log("WebSocket connection closed. Attempting to reconnect...");
        setTimeout(() => connectWebSocket(box, allowReconnect), 1000);
      }
    } else {
      console.log("WebSocket connection could not be established.")
    }
  };
}

document.addEventListener("beforeunload", function() {
  ws.close(1000, "User is leaving the page");
});

if (localStorage.getItem("logs") == "shown") {
  toggleLogs();
}

function toggleLogs() {
  const box = document.getElementById("box");
  const btn = document.getElementById("button-logs");

  if (btn.innerText == "Show Logs") {
    btn.innerText = "Hide Logs";
    box.style.display = "inline";
    loadBox();
    localStorage.setItem("logs", "shown");
  }
  else {
    saveBox();
    btn.innerText = "Show Logs";
    box.style.display = "none";
    localStorage.setItem("logs", "hidden");
  }
}

function loadBox() {
  const box = document.getElementById("box");

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
  const box = document.getElementById("box");
  const boxPos = box.getBoundingClientRect();
  sessionStorage.setItem("boxHeight", boxPos.height);
  sessionStorage.setItem("scrollPos", box.scrollTop);
}

window.onbeforeunload = function(event) {
  if (localStorage.getItem("logs") == "shown") {
    saveBox();
  }
}
