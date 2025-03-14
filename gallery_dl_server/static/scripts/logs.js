const logsContainer = document.getElementById("container-logs");
const clearLogsButton = document.getElementById("clear-logs");
const refreshLogsButton = document.getElementById("refresh-logs");

logsContainer.scrollTop = logsContainer.scrollHeight;

clearLogsButton.onclick = async () => {
  clearLogsButton.disabled = true;

  try {
    const response = await fetch("/gallery-dl/logs/clear", {
      method: "POST"
    });

    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }

    const data = await response.json();
    console.log(data);

    logsContainer.textContent = "Cleared logs.";
  }
  catch (error) {
    console.error(error);
  }
  finally {
    clearLogsButton.disabled = false;
  }
};

refreshLogsButton.onclick = async () => {
  refreshLogsButton.disabled = true;

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
    console.log(response);

    logsContainer.textContent = logs.length ? logs : "No logs to display.";
    logsContainer.scrollTop = logsContainer.scrollHeight;
  }
  catch (error) {
    console.error(error);
  }
  finally {
    refreshLogsButton.disabled = false;
  }
};
