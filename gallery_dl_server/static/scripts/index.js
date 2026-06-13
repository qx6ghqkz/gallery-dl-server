const body = document.querySelector("body");
const themeToggle = document.getElementById("dark-mode-toggle");
const themeIcon = themeToggle.querySelector("i");

function applyTheme(theme) {
  body.dataset.theme = theme;
  themeIcon.className = theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-fill";
}

applyTheme(localStorage.getItem("theme") || "light");

themeToggle.onclick = () => {
  const nextTheme = body.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(nextTheme);
  localStorage.setItem("theme", nextTheme);
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
const btnLabel = btn.querySelector("span");

function setLogsShown(shown) {
  box.hidden = !shown;
  btnLabel.textContent = shown ? "Hide" : "Show";

  if (shown) {
    loadBox();
    localStorage.setItem("logs", "shown");
  } else {
    saveBox();
    localStorage.setItem("logs", "hidden");
  }
}

function loadBox() {
  if ("boxHeight" in sessionStorage && sessionStorage.getItem("boxHeight") != "0") {
    box.style.height = sessionStorage.getItem("boxHeight") + "px";
  } else {
    box.style.height = "";
  }

  if ("scrollPos" in sessionStorage) {
    box.scrollTop = sessionStorage.getItem("scrollPos");
  } else {
    box.scrollTop = box.scrollHeight;
  }
}

function saveBox() {
  const boxPos = box.getBoundingClientRect();
  sessionStorage.setItem("boxHeight", boxPos.height);
  sessionStorage.setItem("scrollPos", box.scrollTop);
}

setLogsShown(localStorage.getItem("logs") == "shown");

btn.onclick = () => setLogsShown(box.hidden);

function scrollOnResize() {
  let lastHeight = box.offsetHeight;

  const observer = new ResizeObserver(entries => {
    for (let entry of entries) {
      if (!box.hidden && entry.contentRect.height > lastHeight) {
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

const form = document.getElementById("form");
const submitButton = document.getElementById("button-submit");
const submitLabel = submitButton.querySelector("span");

const toast = window.Swal
  ? Swal.mixin({
    animation: true,
    position: "top-end",
    showConfirmButton: false,
    showCloseButton: true,
    closeButtonHtml: "&times;",
    target: "body",
    timer: 3000,
    timerProgressBar: true,
    toast: true,
    didOpen: (toastElement) => {
      toastElement.onmouseenter = Swal.stopTimer;
      toastElement.onmouseleave = Swal.resumeTimer;
    }
  })
  : null;

function notify(options) {
  if (toast) {
    toast.fire(options);
  } else {
    console.log(options.title || options.text || options);
  }
}

function setSubmitLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.classList.toggle("is-loading", isLoading);
  submitLabel.textContent = isLoading ? "Queueing" : "Queue";
}

form.onsubmit = async (event) => {
  event.preventDefault();

  if (!ws || ws.readyState === WebSocket.CLOSED) {
    connectWebSocket();
  }

  const formData = new FormData(event.target);
  const url = formData.get("url");

  setSubmitLoading(true);

  try {
    const response = await fetch("/gallery-dl/q", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || "Download request failed.");
    }

    event.target.elements.url.value = "";

    notify({
      icon: "success",
      title: "Queued",
      text: url
    });

    window.setTimeout(fetchMedia, 5000);
  } catch (error) {
    console.error(error);
    notify({
      icon: "error",
      title: "Request failed",
      text: error.message
    });
  } finally {
    setSubmitLoading(false);
  }
};

const mediaList = document.getElementById("media-list");
const mediaEmpty = document.getElementById("media-empty");
const mediaCount = document.getElementById("media-count");
const mediaRoot = document.getElementById("media-root");
const refreshMediaButton = document.getElementById("refresh-media");
const playerEmpty = document.getElementById("player-empty");
const mediaImage = document.getElementById("media-image");
const mediaVideo = document.getElementById("media-video");
const mediaAudio = document.getElementById("media-audio");
const mediaDownload = document.getElementById("media-download");
const mediaDetails = document.getElementById("media-details");
const mediaTitle = document.getElementById("media-title");
const mediaSubtitle = document.getElementById("media-subtitle");

let activeMediaPath = localStorage.getItem("activeMediaPath") || "";
let mediaItems = [];

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exponent);

  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

function formatModified(timestamp) {
  if (!timestamp) {
    return "";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(timestamp * 1000));
}

function iconForType(type) {
  if (type === "image") {
    return "bi bi-image";
  }
  if (type === "audio") {
    return "bi bi-music-note-beamed";
  }
  return "bi bi-film";
}

function clearPlayer() {
  mediaVideo.pause();
  mediaAudio.pause();
  mediaImage.removeAttribute("src");
  mediaVideo.removeAttribute("src");
  mediaAudio.removeAttribute("src");
  mediaVideo.load();
  mediaAudio.load();

  mediaImage.hidden = true;
  mediaVideo.hidden = true;
  mediaAudio.hidden = true;
  mediaDownload.hidden = true;
  mediaDetails.hidden = true;
  playerEmpty.hidden = false;
}

function setActiveMediaClass() {
  for (let item of mediaList.querySelectorAll(".media-item")) {
    item.classList.toggle("is-active", item.dataset.path === activeMediaPath);
  }
}

function selectMedia(item) {
  activeMediaPath = item.path;
  localStorage.setItem("activeMediaPath", activeMediaPath);
  clearPlayer();

  playerEmpty.hidden = true;
  mediaDetails.hidden = false;
  mediaDownload.hidden = false;
  mediaDownload.href = item.url;
  mediaDownload.download = item.name;
  mediaTitle.textContent = item.name;
  mediaSubtitle.textContent = [item.directory, formatBytes(item.size), formatModified(item.modified)]
    .filter(Boolean)
    .join(" / ");

  if (item.type === "image") {
    mediaImage.src = item.url;
    mediaImage.alt = item.name;
    mediaImage.hidden = false;
  } else if (item.type === "audio") {
    mediaAudio.src = item.url;
    mediaAudio.hidden = false;
  } else {
    mediaVideo.src = item.url;
    mediaVideo.hidden = false;
  }

  setActiveMediaClass();
}

function buildMediaButton(item) {
  const button = document.createElement("button");
  button.className = "media-item";
  button.type = "button";
  button.dataset.path = item.path;
  button.setAttribute("role", "listitem");

  const icon = document.createElement("span");
  icon.className = "media-icon";
  icon.setAttribute("aria-hidden", "true");

  const iconElement = document.createElement("i");
  iconElement.className = iconForType(item.type);
  icon.append(iconElement);

  const copy = document.createElement("span");
  copy.className = "media-copy";

  const name = document.createElement("span");
  name.className = "media-name";
  name.textContent = item.name;

  const path = document.createElement("span");
  path.className = "media-path";
  path.textContent = item.directory && item.directory !== "." ? item.directory : item.type;

  const size = document.createElement("span");
  size.className = "media-size";
  size.textContent = formatBytes(item.size);

  copy.append(name, path);
  button.append(icon, copy, size);
  button.onclick = () => selectMedia(item);

  return button;
}

function renderMedia(data) {
  mediaItems = data.items || [];
  mediaList.replaceChildren();
  mediaRoot.textContent = data.exists ? data.root : `${data.root} missing`;

  const visibleCount = mediaItems.length;
  const hiddenCount = Math.max((data.total || 0) - visibleCount, 0);
  mediaCount.textContent = hiddenCount
    ? `${visibleCount} of ${data.total} files`
    : `${visibleCount} ${visibleCount === 1 ? "file" : "files"}`;

  mediaEmpty.hidden = visibleCount !== 0;

  for (let item of mediaItems) {
    mediaList.append(buildMediaButton(item));
  }

  const selected = mediaItems.find(item => item.path === activeMediaPath) || mediaItems[0];

  if (selected) {
    selectMedia(selected);
  } else {
    activeMediaPath = "";
    localStorage.removeItem("activeMediaPath");
    clearPlayer();
  }
}

async function fetchMedia() {
  refreshMediaButton.disabled = true;
  refreshMediaButton.classList.add("is-loading");

  try {
    const response = await fetch("/gallery-dl/media", {
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

    renderMedia(await response.json());
  } catch (error) {
    console.error(error);
    mediaCount.textContent = "Unavailable";
    mediaEmpty.hidden = false;
    notify({
      icon: "error",
      title: "Library unavailable",
      text: error.message
    });
  } finally {
    refreshMediaButton.disabled = false;
    refreshMediaButton.classList.remove("is-loading");
  }
}

refreshMediaButton.onclick = fetchMedia;

let ws;
let isConnected = false;
let isPageAlive = true;

const socketStatus = document.getElementById("socket-status");

function setSocketStatus(text, state) {
  socketStatus.textContent = text;
  socketStatus.classList.toggle("is-connected", state === "connected");
  socketStatus.classList.toggle("is-offline", state === "offline");
}

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
  } catch (error) {
    console.error(error.message);
    setSocketStatus("Offline", "offline");
  }
}

function connectWebSocket(allowReconnect = true) {
  if (ws && [WebSocket.CONNECTING, WebSocket.OPEN].includes(ws.readyState)) {
    return;
  }

  const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
  const host = window.location.host;
  const url = `${protocol}${host}/ws/logs`;

  let lastLine = "";
  let lastPos = localStorage.getItem("lastPos") ? parseInt(localStorage.getItem("lastPos")) : 0;

  setSocketStatus("Connecting", "");
  ws = new WebSocket(url);

  ws.onopen = () => {
    isConnected = true;
    setSocketStatus("Live", "connected");
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
    } else if (isLastLineProgress && !isNewLineProgress) {
      lastPos = 0;
    }

    lines.push(...newLines.slice(progressUpdate ? 1 : 0));

    box.textContent = lines.join("\n") + "\n";

    localStorage.setItem("lastPos", lastPos);

    if (!progressUpdate || newLines.length > 1) {
      box.scrollTop = box.scrollHeight;
    }

    if (newLines.some(line => line.includes("Download process exited successfully"))) {
      window.setTimeout(fetchMedia, 1000);
    }
  };

  ws.onerror = (event) => {
    console.error("WebSocket error:", event);
    setSocketStatus("Offline", "offline");
  };

  ws.onclose = () => {
    if (isConnected) {
      isConnected = false;

      if (isPageAlive && allowReconnect) {
        setSocketStatus("Reconnecting", "offline");
        window.setTimeout(() => connectWebSocket(allowReconnect), 2000);
      }
    } else {
      setSocketStatus("Offline", "offline");
    }
  };
}

fetchLogs();
fetchMedia();
body.classList.remove("d-none");

window.onbeforeunload = () => {
  isPageAlive = false;

  if (ws) {
    ws.close(1000, "User is leaving the page");
  }

  if (localStorage.getItem("logs") == "shown") {
    saveBox();
  }
};
