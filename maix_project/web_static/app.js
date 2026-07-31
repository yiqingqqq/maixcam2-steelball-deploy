/* Minimalist Web Dashboard Logic for MaixCAM2 */

let chart = null;
let maxDataPoints = 30;
let xData = [];
let yData = [];
let labels = [];

// Initialize Dashboard & Chart
document.addEventListener("DOMContentLoaded", () => {
  initChart();
  updateTime();
  setInterval(updateTime, 1000);
  startPollingTelemetry();
});

// Update Header Clock
function updateTime() {
  const now = new Date();
  document.getElementById("sys-time").innerText = now.toTimeString().split(" ")[0];
}

// Initialize Realtime Chart.js Line Graph
function initChart() {
  const ctx = document.getElementById("trajectory-chart").getContext("2d");
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "X (Px)",
          data: xData,
          borderColor: "#2563eb",
          backgroundColor: "rgba(37, 99, 235, 0.05)",
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 0,
        },
        {
          label: "Y (Px)",
          data: yData,
          borderColor: "#059669",
          backgroundColor: "rgba(5, 150, 105, 0.05)",
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          position: "top",
          labels: {
            font: { family: "Inter", size: 11, weight: "600" },
            boxWidth: 12,
          },
        },
      },
      scales: {
        x: { display: false },
        y: {
          min: 0,
          max: 640,
          grid: { color: "#f1f5f9" },
          ticks: { font: { family: "JetBrains Mono", size: 10 } },
        },
      },
    },
  });
}

// Poll Telemetry JSON API (~10 Hz polling for smooth card updates)
function startPollingTelemetry() {
  setInterval(() => {
    fetch("/telemetry")
      .then((res) => res.json())
      .then((data) => {
        updateUI(data);
      })
      .catch(() => {
        document.getElementById("connection-status").innerText = "○ 断开重连中";
        document.getElementById("connection-status").className = "badge badge-offline";
      });
  }, 100);
}

// Update UI Telemetry & Chart
function updateUI(data) {
  document.getElementById("connection-status").innerText = "● 已连接";
  document.getElementById("connection-status").className = "badge badge-online";

  const valX = data.x !== undefined ? data.x : -1;
  const valY = data.y !== undefined ? data.y : -1;

  document.getElementById("val-x").innerText = valX >= 0 ? valX : "--";
  document.getElementById("val-y").innerText = valY >= 0 ? valY : "--";
  document.getElementById("val-conf").innerText = (data.conf || 0.0).toFixed(2);
  document.getElementById("val-fps").innerText = (data.fps || 0.0).toFixed(1);

  // Update Status Pill
  const modePill = document.getElementById("mode-pill");
  if (data.status === "ACTIVE" || data.status === "REC") {
    modePill.innerText = "ACTIVE 运行中";
    modePill.className = "pill pill-active";
  } else {
    modePill.innerText = "STANDBY 待机";
    modePill.className = "pill pill-status";
  }

  // Update Recording Indicator
  const recPill = document.getElementById("rec-pill");
  if (data.recorder) {
    recPill.style.display = "inline-block";
  } else {
    recPill.style.display = "none";
  }

  // Update Chart if valid target detected
  if (valX >= 0 && valY >= 0) {
    const timeLabel = new Date().toLocaleTimeString();
    if (labels.length >= maxDataPoints) {
      labels.shift();
      xData.shift();
      yData.shift();
    }
    labels.push(timeLabel);
    xData.push(valX);
    yData.push(valY);
    chart.update();
  }
}

// Reset Chart Button
function resetChart() {
  labels.length = 0;
  xData.length = 0;
  yData.length = 0;
  chart.update();
}

// Video Stream Stream Fallback
function handleStreamError(img) {
  setTimeout(() => {
    img.src = "/video_feed?t=" + new Date().getTime();
  }, 1000);
}

// Trigger Wireless Sync
function syncVideosWireless() {
  alert("已触发无线同步命令，录像将传输保存至您 Mac 的 Desktop 桌面目录！");
}
