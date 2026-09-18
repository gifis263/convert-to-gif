const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const form = document.getElementById("upload-form");
const startBtn = document.getElementById("start-btn");
const statusCard = document.getElementById("status-card");
const progressFill = document.getElementById("progress-fill");
const statusText = document.getElementById("status-text");
const elapsedEl = document.getElementById("elapsed");
const resultCard = document.getElementById("result-card");
const logBox = document.getElementById("log-box");
const downloadLink = document.getElementById("download-link");
const preview = document.getElementById("preview");

let selectedFile = null;
let taskId = null;
let pollTimer = null;

dropzone.addEventListener("click", () => fileInput.click());

["dragenter", "dragover"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    })
);
["dragleave", "drop"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
    })
);

dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) setFile(file);
});

fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(file) {
    selectedFile = file;
    const size = (file.size / (1024 * 1024)).toFixed(1);
    dropzone.classList.add("selected");
    dropzone.querySelector(".dz-main").textContent = file.name;
    dropzone.querySelector(".dz-sub").textContent = `${size} МБ — нажмите «Создать GIF»`;
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!selectedFile) {
        alert("Сначала выберите видео.");
        return;
    }
    const data = new FormData();
    data.append("video", selectedFile);
    data.append("start", document.getElementById("start").value || 0);
    data.append("duration", document.getElementById("duration").value || 0);
    data.append("fps", document.getElementById("fps").value);
    data.append("width", document.getElementById("width").value);

    startBtn.disabled = true;
    startBtn.textContent = "Обработка...";
    resultCard.classList.add("hidden");
    preview.removeAttribute("src");
    logBox.textContent = "";
    statusCard.classList.remove("hidden");
    statusText.textContent = "Загрузка файла...";
    elapsedEl.textContent = "";
    progressFill.style.width = "0%";

    try {
        const res = await fetch("/upload", { method: "POST", body: data });
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || "Ошибка загрузки");
        taskId = json.task_id;
        poll();
    } catch (err) {
        finishError(err.message);
    }
});

function poll() {
    fetch(`/status/${taskId}`)
        .then((r) => r.json())
        .then((json) => {
            if (json.error) return finishError(json.error);
            const logs = json.logs || [];
            logBox.textContent = logs.join("\n");
            statusText.textContent = logs.length ? logs[logs.length - 1] : "Обработка...";
            elapsedEl.textContent = `${json.elapsed || 0} c`;
            progressFill.style.width = (json.progress || 0) + "%";
            logBox.scrollTop = logBox.scrollHeight;

            if (json.done) {
                progressFill.style.width = "100%";
                statusText.textContent = "Готово!";
                downloadLink.href = `/download/${taskId}`;
                preview.src = `/download/${taskId}`;
                resultCard.classList.remove("hidden");
                startBtn.disabled = false;
                startBtn.textContent = "Создать GIF";
                stopPoll();
            } else {
                pollTimer = setTimeout(poll, 700);
            }
        })
        .catch((err) => finishError(err.message));
}

function finishError(msg) {
    stopPoll();
    startBtn.disabled = false;
    startBtn.textContent = "Создать GIF";
    statusCard.classList.remove("hidden");
    statusText.textContent = "Ошибка";
    elapsedEl.textContent = "";
    logBox.textContent = "Ошибка: " + msg;
    resultCard.classList.remove("hidden");
}

function stopPoll() {
    if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
    }
}