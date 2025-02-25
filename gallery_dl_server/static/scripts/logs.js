const logContainer = document.getElementById("container-logs");
const clearLogsButton = document.getElementById("clear-logs");

logContainer.scrollTop = logContainer.scrollHeight;

clearLogsButton.onclick = () => {
  clearLogsButton.disabled = true;

  fetch("/gallery-dl/logs/clear", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      }
      throw new Error("Network response was not OK.");
    })
    .then((data) => {
      logContainer.innerText = "Cleared logs.";
    })
    .catch((error) => {
      console.error("Error:", error);
      logContainer.innerText = "Failed to clear logs.";
      clearLogsButton.disabled = false;
    });
};
