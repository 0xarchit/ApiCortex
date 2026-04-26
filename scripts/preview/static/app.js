const uploadForm = document.getElementById('upload-form');
const fileInput = document.getElementById('dataset-file');
const fileName = document.getElementById('file-name');
const uploadStatus = document.getElementById('upload-status');
const processStatus = document.getElementById('process-status');
const uploadButton = document.getElementById('upload-button');
const startButton = document.getElementById('start-button');
const rowsProcessed = document.getElementById('rows-processed');
const highRisk = document.getElementById('high-risk');
const watchRisk = document.getElementById('watch-risk');
const avgRisk = document.getElementById('avg-risk');
const playbackCount = document.getElementById('playback-count');
const liveBand = document.getElementById('live-band');
const liveTime = document.getElementById('live-time');
const liveRisk = document.getElementById('live-risk');
const liveLatency = document.getElementById('live-latency');
const liveError = document.getElementById('live-error');
const liveTraffic = document.getElementById('live-traffic');
const liveLabel = document.getElementById('live-label');
const progressBar = document.getElementById('progress-bar');
const alertsBody = document.getElementById('alerts-body');
const judgeNotes = document.getElementById('judge-notes');
const riskChart = document.getElementById('risk-chart');

let uploadId = null;
let playback = [];
let timer = null;

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  fileName.textContent = file ? file.name : 'Choose the generated demo CSV or your own telemetry export';
});

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    uploadStatus.textContent = 'Select a CSV file before uploading.';
    return;
  }

  stopPlayback();
  uploadButton.disabled = true;
  startButton.disabled = true;
  uploadStatus.textContent = 'Uploading dataset...';
  processStatus.textContent = 'Waiting for uploaded file';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail));
    }
    uploadId = payload.upload_id;
    uploadStatus.textContent = `${payload.filename} uploaded successfully. ${payload.rows} rows ready.`;
    processStatus.textContent = 'Ready to start model playback';
    startButton.disabled = false;
    judgeNotes.innerHTML = `
      <li>Uploaded file: ${payload.filename}</li>
      <li>Detected columns: ${payload.columns.length}</li>
      <li>Press Start Demo to run model inference and animate the timeline.</li>
    `;
  } catch (error) {
    uploadStatus.textContent = `Upload failed: ${error.message}`;
  } finally {
    uploadButton.disabled = false;
  }
});

startButton.addEventListener('click', async () => {
  if (!uploadId) {
    processStatus.textContent = 'Upload a file first.';
    return;
  }

  stopPlayback();
  startButton.disabled = true;
  processStatus.textContent = 'Processing uploaded dataset with XGBoost...';

  try {
    const response = await fetch(`/api/process/${uploadId}`, {
      method: 'POST',
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail));
    }
    playback = payload.playback || [];
    rowsProcessed.textContent = payload.summary.rows_processed;
    highRisk.textContent = payload.summary.high_risk_rows;
    watchRisk.textContent = payload.summary.watch_rows;
    avgRisk.textContent = payload.summary.average_risk.toFixed(4);
    processStatus.textContent = 'Playback running on processed inference output';
    renderAlerts(payload.alerts || []);
    renderNotes(payload.summary, payload.metrics || {});
    runPlayback(playback);
  } catch (error) {
    processStatus.textContent = `Processing failed: ${error.message}`;
    startButton.disabled = false;
  }
});

function runPlayback(frames) {
  if (!frames.length) {
    processStatus.textContent = 'No frames available for playback.';
    startButton.disabled = false;
    return;
  }

  let index = 0;
  const seen = [];
  playbackCount.textContent = `0 / ${frames.length}`;
  timer = setInterval(() => {
    const frame = frames[index];
    seen.push(frame);
    updateLivePanel(frame, index + 1, frames.length);
    drawChart(seen);
    index += 1;
    if (index >= frames.length) {
      stopPlayback(false);
      processStatus.textContent = 'Playback complete. You can upload another file or replay the same one.';
      startButton.disabled = false;
    }
  }, 120);
}

function stopPlayback(resetButton = true) {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  if (resetButton) {
    startButton.disabled = !uploadId;
  }
}

function updateLivePanel(frame, currentIndex, total) {
  playbackCount.textContent = `${currentIndex} / ${total}`;
  liveTime.textContent = formatTimestamp(frame.timestamp);
  liveRisk.textContent = Number(frame.risk_score).toFixed(4);
  liveLatency.textContent = `${Number(frame.p95_latency).toFixed(2)} ms`;
  liveError.textContent = Number(frame.error_rate).toFixed(4);
  liveTraffic.textContent = `${Number(frame.traffic_rps).toFixed(2)} rps`;
  liveLabel.textContent = frame.actual_label === null || frame.actual_label === undefined ? '-' : frame.actual_label;
  progressBar.style.width = `${(currentIndex / total) * 100}%`;
  liveBand.textContent = frame.risk_band.replaceAll('_', ' ');
  liveBand.className = `badge ${badgeClass(frame.risk_band)}`;
}

function renderAlerts(alerts) {
  if (!alerts.length) {
    alertsBody.innerHTML = '<tr><td colspan="5">No alerts generated</td></tr>';
    return;
  }

  alertsBody.innerHTML = alerts.map((alert) => `
    <tr>
      <td>${formatTimestamp(alert.timestamp)}</td>
      <td>${Number(alert.risk_score).toFixed(4)}</td>
      <td>${alert.risk_band.replaceAll('_', ' ')}</td>
      <td>${Number(alert.p95_latency).toFixed(2)} ms</td>
      <td>${Number(alert.error_rate).toFixed(4)}</td>
    </tr>
  `).join('');
}

function renderNotes(summary, metrics) {
  const notes = [
    `<li>Processed ${summary.rows_processed} rows through the trained model artifact.</li>`,
    `<li>Peak risk score reached ${Number(summary.peak_risk).toFixed(4)} with ${summary.high_risk_rows} high-risk windows.</li>`,
    `<li>Playback is sampled from the full processed dataset for fast judge-friendly rendering.</li>`,
  ];
  if (metrics.agreement !== undefined) {
    notes.push(`<li>Prediction agreement with the supplied label column: ${(Number(metrics.agreement) * 100).toFixed(2)}%.</li>`);
  }
  judgeNotes.innerHTML = notes.join('');
}

function drawChart(points) {
  if (!points.length) {
    riskChart.innerHTML = '';
    return;
  }

  const width = 900;
  const height = 320;
  const padding = 22;
  const chartHeight = height - padding * 2;
  const chartWidth = width - padding * 2;
  const maxIndex = Math.max(points.length - 1, 1);
  const polyline = points.map((point, index) => {
    const x = padding + (index / maxIndex) * chartWidth;
    const y = padding + (1 - Number(point.risk_score)) * chartHeight;
    return `${x},${y}`;
  }).join(' ');

  const latest = points[points.length - 1];
  const latestX = padding + (maxIndex / maxIndex) * chartWidth;
  const latestY = padding + (1 - Number(latest.risk_score)) * chartHeight;

  riskChart.innerHTML = `
    <rect x="0" y="0" width="900" height="320" rx="20" fill="transparent"></rect>
    <line x1="22" y1="260" x2="878" y2="260" stroke="rgba(73,53,36,0.16)" stroke-width="1"></line>
    <line x1="22" y1="138" x2="878" y2="138" stroke="rgba(73,53,36,0.08)" stroke-width="1" stroke-dasharray="6 6"></line>
    <line x1="22" y1="87" x2="878" y2="87" stroke="rgba(197,59,44,0.12)" stroke-width="1" stroke-dasharray="6 6"></line>
    <polyline fill="none" stroke="#8f2d13" stroke-width="4" points="${polyline}"></polyline>
    <circle cx="${latestX}" cy="${latestY}" r="7" fill="${bandColor(latest.risk_band)}"></circle>
  `;
}

function bandColor(band) {
  if (band === 'high_failure_risk') {
    return '#c53b2c';
  }
  if (band === 'watch') {
    return '#d9a441';
  }
  return '#2e8b78';
}

function badgeClass(band) {
  if (band === 'high_failure_risk') {
    return 'alert-badge';
  }
  if (band === 'watch') {
    return 'watch-badge';
  }
  return 'stable-badge';
}

function formatTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
