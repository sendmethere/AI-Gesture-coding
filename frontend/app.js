"use strict";

const $ = (id) => document.getElementById(id);
const api = (p, opts) => fetch(p, opts).then(async (r) => {
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("json") ? r.json() : r.text();
});

// ------------------------------------------------------------------- i18n ---
const STRINGS = {
  ko: {
    brandSub: "마이크로티칭",
    secVideo: "1. 영상", btnSelectVideo: "영상 선택…", noVideo: "선택된 영상 없음",
    secLLM: "2. LLM 설정", lblProvider: "Provider",
    optMock: "Mock (테스트 · API 키 불필요)",
    lblApiKey: "API Key", phApiKey: "sk-… (mock은 비워둬도 됨)",
    btnClearKey: "지우기", lblModel: "Model", phModel: "예: gpt-4o",
    btnSaveSettings: "설정 저장",
    secSchema: "3. 제스처 분류체계", btnEditSchema: "JSON 편집",
    secOptions: "4. 분석 옵션",
    lblInterval: "스냅샷 간격(초)", lblSegFrames: "윈도우 크기(프레임)",
    windowDur: "· 윈도우 길이 {0}초 ({1}프레임 × {2}초)",
    lblStartAt: "분석 시작 지점", hintStartAt: "· 분 : 초", phMin: "분", phSec: "초",
    lblMaxDur: "분석 길이 제한(초)", hintMaxDur: "· 시작점부터 · 0 = 끝까지",
    lblMinConf: "최소 신뢰도", hintMinConf: "· 이하면 None 처리 · 0 = 끔",
    lblIncludeConf: "CSV에 confidence 포함",
    lblMotionFilter: "모션 사전필터 (토큰 절감)",
    lblStillThr: "정지 임계값", lblStartThr: "시작 임계값",
    hintMotion: "· 시작 임계값에 도달하는 프레임이 없으면 제스처 없음(GT-None)·AI 생략 · 골격은 YOLO-pose 설치 시 활성",
    lblStt: "발화 전사(STT) · 윈도우별 문장",
    lblSttModel: "STT 모델", lblSttLang: "언어",
    hintStt: "· faster-whisper 설치 필요 · 첫 실행 시 모델 다운로드 · 결과는 윈도우별 발화로 부착",
    speechLabel: "발화", ovNoSpeech: "(발화 없음)",
    sttLoading: "💬 발화 전사 중… (영상에서 음성 추출 · 첫 실행 시 모델 다운로드)",
    btnStart: "▶ 분석 시작", btnStop: "■ 중지",
    btnOverview: "🔍 Overview (이미지+코드)", btnExport: "⬇ CSV 내보내기",
    playerEmpty: "영상을 선택하면 여기서 재생됩니다.",
    tabResults: "결과", tabLog: "로그",
    thTime: "시간", thGesture: "제스처", thConf: "신뢰도", resultsEmpty: "아직 결과가 없습니다.",
    schemaTitle: "제스처 분류체계 (gesture_schema.json)",
    schemaDesc: "name/description 을 자유롭게 추가·수정하세요. 저장 시 즉시 반영됩니다.",
    btnCancel: "취소", btnSave: "저장", editTitle: "제스처 수정", btnApply: "적용",
    stripTitle: "AI에 전송된 이미지",
    stripDesc: "왼쪽→오른쪽 순서로 이어붙인 strip 입니다. 프레임 하단 컬러바: 회색=정지 · 노랑=준비 · 초록=시작 · 파랑=진행, 숫자는 손 이동량.",
    btnClose: "닫기", ovTitle: "Overview — AI 전송 이미지 + 코드",
    ovDesc: "각 구간에 AI로 보낸 strip(6프레임)과 자동 코딩 결과입니다. 스크롤하여 확인하세요.",
    // dynamic
    segments: "{0} / {1} 세그먼트", ovCount: "({0}개 구간)",
    toastSettingsSaved: "설정 저장됨", toastSchemaSaved: "분류체계 저장됨",
    errJsonParse: "JSON 파싱 오류: {0}", toastUploading: "영상 업로드 중…",
    toastUploadDone: "업로드 완료", errPickFile: "파일 선택 실패: {0}",
    errStartFail: "시작 실패: {0}", toastStopReq: "중지 요청됨",
    toastEdited: "수정됨 (#{0})", errEditFail: "수정 실패: {0}",
    toastSaved: "저장됨: {0} ({1}행)", errExportFail: "내보내기 실패: {0}",
    toastKeySaved: "API Key 저장됨", toastKeyCleared: "API Key 삭제됨",
    errStripLoad: "이미지를 불러올 수 없습니다. (분석 옵션에서 strip 저장이 켜져 있어야 합니다)",
    errLoadResults: "결과를 불러오지 못했습니다: {0}",
    ovNoResults: "아직 분석 결과가 없습니다.",
    ovNoImg: "(strip 이미지 없음 — 분석 옵션의 strip 저장이 꺼져 있었음)",
    emptyTag: "— 없음", keySaved: "✓ API Key 저장됨", keyNone: "저장된 키 없음",
    phApiKeySaved: "저장된 키 사용 중 — 변경 시에만 입력",
    titleEditTag: "클릭하여 수정", titleViewStrip: "AI에 전송된 이미지 보기",
    titleSeek: "클릭하면 이 시점으로 이동",
    doneToast: "분석 완료 ({0} segments)", errorToast: "오류: {0}",
  },
  en: {
    brandSub: "for Microteaching",
    secVideo: "1. Video", btnSelectVideo: "Select Video…", noVideo: "No video selected",
    secLLM: "2. LLM Settings", lblProvider: "Provider",
    optMock: "Mock (test · no API key)",
    lblApiKey: "API Key", phApiKey: "sk-… (leave empty for mock)",
    btnClearKey: "Clear", lblModel: "Model", phModel: "e.g. gpt-4o",
    btnSaveSettings: "Save Settings",
    secSchema: "3. Gesture Schema", btnEditSchema: "Edit JSON",
    secOptions: "4. Analysis Options",
    lblInterval: "Snapshot interval (s)", lblSegFrames: "Window size (frames)",
    windowDur: "· window {0}s ({1} frames × {2}s)",
    lblStartAt: "Start at", hintStartAt: "· min : sec", phMin: "min", phSec: "sec",
    lblMaxDur: "Length limit (sec)", hintMaxDur: "· from start · 0 = to end",
    lblMinConf: "Min confidence", hintMinConf: "· below → None · 0 = off",
    lblIncludeConf: "Include confidence in CSV",
    lblMotionFilter: "Motion pre-filter (save tokens)",
    lblStillThr: "Still threshold", lblStartThr: "Start threshold",
    hintMotion: "· no frame reaching the start threshold = no gesture (GT-None), AI skipped · skeleton needs YOLO-pose",
    lblStt: "Speech transcription (STT) · per-window text",
    lblSttModel: "STT model", lblSttLang: "Language",
    hintStt: "· needs faster-whisper · downloads the model on first run · attached as per-window speech",
    speechLabel: "Speech", ovNoSpeech: "(no speech)",
    sttLoading: "💬 Transcribing speech… (extracting audio · downloads model on first run)",
    btnStart: "▶ Start", btnStop: "■ Stop",
    btnOverview: "🔍 Overview (images+codes)", btnExport: "⬇ Export CSV",
    playerEmpty: "Select a video to play it here.",
    tabResults: "Results", tabLog: "Log",
    thTime: "Timestamp", thGesture: "Gesture", thConf: "Conf.", resultsEmpty: "No results yet.",
    schemaTitle: "Gesture Schema (gesture_schema.json)",
    schemaDesc: "Add or edit name/description freely. Applied immediately on save.",
    btnCancel: "Cancel", btnSave: "Save", editTitle: "Edit gestures", btnApply: "Apply",
    stripTitle: "Image sent to the AI",
    stripDesc: "Frames concatenated left → right. Bottom colorbar: gray=still · yellow=prep · green=start · blue=in motion; the number is hand displacement.",
    btnClose: "Close", ovTitle: "Overview — images sent to AI + codes",
    ovDesc: "Each segment's strip (6 frames) sent to the AI and its auto-coded result. Scroll to review.",
    segments: "{0} / {1} segments", ovCount: "({0} segments)",
    toastSettingsSaved: "Settings saved", toastSchemaSaved: "Schema saved",
    errJsonParse: "JSON parse error: {0}", toastUploading: "Uploading video…",
    toastUploadDone: "Upload complete", errPickFile: "File selection failed: {0}",
    errStartFail: "Start failed: {0}", toastStopReq: "Stop requested",
    toastEdited: "Edited (#{0})", errEditFail: "Edit failed: {0}",
    toastSaved: "Saved: {0} ({1} rows)", errExportFail: "Export failed: {0}",
    toastKeySaved: "API Key saved", toastKeyCleared: "API Key cleared",
    errStripLoad: "Could not load image. (strip saving must be enabled in Analysis Options)",
    errLoadResults: "Could not load results: {0}",
    ovNoResults: "No analysis results yet.",
    ovNoImg: "(no strip image — strip saving was off)",
    emptyTag: "— none", keySaved: "✓ API Key saved", keyNone: "No saved key",
    phApiKeySaved: "Using saved key — enter only to change",
    titleEditTag: "Click to edit", titleViewStrip: "View image sent to the AI",
    titleSeek: "Click to jump to this time",
    doneToast: "Analysis complete ({0} segments)", errorToast: "Error: {0}",
  },
};

let LANG = localStorage.getItem("lang") || "ko";

function t(key, ...args) {
  let s = (STRINGS[LANG] && STRINGS[LANG][key]);
  if (s == null) s = STRINGS.en[key] != null ? STRINGS.en[key] : key;
  args.forEach((a, i) => (s = s.replace(`{${i}}`, a)));
  return s;
}

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
    if (el.id !== "apiKey" || !el.dataset.hasSavedKey) el.placeholder = t(el.dataset.i18nPh);
  });
  document.documentElement.lang = LANG;
  $("langToggle").textContent = LANG === "ko" ? "EN" : "한";
  // refresh dynamic bits that hold translated text
  reflectKeyStatus(lastHasKey);
  refreshProgressLabels();
  if ($("interval")) reflectWindowDur();
}

function setLang(l) {
  LANG = l;
  localStorage.setItem("lang", l);
  applyI18n();
}

let SCHEMA = { gestures: [] };
let pollTimer = null;
let resultCount = 0;
let editIndex = null;
let lastHasKey = false;
let lastSnap = { done: 0, total: 0 };
let lastSeek = -1;

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(t._t);
  t._t = setTimeout(() => (t.hidden = true), 2600);
}

// ---------------------------------------------------------------- settings --
async function loadSettings() {
  const s = await api("/api/settings");
  $("provider").value = s.provider || "mock";
  $("model").value = s.model || "";
  $("interval").value = s.interval ?? 0.3;
  $("segmentFrames").value = s.segment_frames ?? 10;
  const off = Math.max(0, Math.floor(s.start_offset ?? 0));
  $("startMin").value = Math.floor(off / 60);
  $("startSec").value = off % 60;
  $("maxDuration").value = s.max_duration ?? 60;
  $("minConfidence").value = s.min_confidence ?? 0;
  $("includeConf").checked = s.include_confidence ?? true;
  $("motionFilter").checked = s.motion_filter ?? true;
  $("stillThreshold").value = s.still_threshold ?? 0.25;
  $("startThreshold").value = s.start_threshold ?? 0.25;
  $("sttEnabled").checked = s.stt_enabled ?? false;
  $("sttModel").value = s.stt_model || "base";
  $("sttLanguage").value = s.stt_language || "";
  reflectMotionFilter();
  reflectStt();
  reflectWindowDur();
  reflectKeyStatus(s.has_api_key);
}

function reflectMotionFilter() {
  $("motionThresholds").style.opacity = $("motionFilter").checked ? "1" : "0.4";
}

function reflectWindowDur() {
  const iv = Math.max(0.1, parseFloat($("interval").value) || 0.3);
  const fr = Math.max(2, parseInt($("segmentFrames").value) || 10);
  $("windowDurHint").textContent = t("windowDur", (iv * fr).toFixed(1), fr, iv);
}

function reflectStt() {
  $("sttOpts").style.opacity = $("sttEnabled").checked ? "1" : "0.4";
}

async function saveSettings() {
  const body = {
    provider: $("provider").value,
    model: $("model").value,
    interval: Math.max(0.1, parseFloat($("interval").value) || 0.3),
    segment_frames: Math.max(2, parseInt($("segmentFrames").value) || 10),
    start_offset:
      Math.max(0, parseInt($("startMin").value) || 0) * 60 +
      Math.max(0, parseInt($("startSec").value) || 0),
    max_duration: Math.max(0, parseInt($("maxDuration").value) || 0),
    min_confidence: Math.min(1, Math.max(0, parseFloat($("minConfidence").value) || 0)),
    include_confidence: $("includeConf").checked,
    motion_filter: $("motionFilter").checked,
    still_threshold: Math.min(3, Math.max(0, parseFloat($("stillThreshold").value) || 0.25)),
    start_threshold: Math.min(3, Math.max(0, parseFloat($("startThreshold").value) || 0.25)),
    stt_enabled: $("sttEnabled").checked,
    stt_model: $("sttModel").value,
    stt_language: $("sttLanguage").value.trim(),
  };
  const key = $("apiKey").value.trim();
  if (key) body.api_key = key;
  await api("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  toast(t("toastSettingsSaved"));
}

function reflectKeyStatus(hasKey) {
  lastHasKey = hasKey;
  const status = $("keyStatus");
  const clear = $("clearKeyBtn");
  const apiKey = $("apiKey");
  if (hasKey) {
    apiKey.dataset.hasSavedKey = "1";
    apiKey.placeholder = t("phApiKeySaved");
    status.textContent = t("keySaved");
    status.style.color = "var(--green)";
    clear.hidden = false;
  } else {
    delete apiKey.dataset.hasSavedKey;
    apiKey.placeholder = t("phApiKey");
    status.textContent = t("keyNone");
    status.style.color = "var(--muted)";
    clear.hidden = true;
  }
}

async function autosaveApiKey() {
  const key = $("apiKey").value.trim();
  if (!key) return;
  await api("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: key, provider: $("provider").value }),
  });
  $("apiKey").value = "";
  reflectKeyStatus(true);
  toast(t("toastKeySaved"));
}

async function clearApiKey() {
  await api("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: "" }),
  });
  $("apiKey").value = "";
  reflectKeyStatus(false);
  toast(t("toastKeyCleared"));
}

// ------------------------------------------------------------------ schema --
async function loadSchema() {
  SCHEMA = await api("/api/schema");
  const list = $("schemaList");
  list.innerHTML = "";
  SCHEMA.gestures.forEach((g) => {
    const el = document.createElement("span");
    el.className = "chip";
    el.textContent = g.name;
    el.title = g.description || "";
    list.appendChild(el);
  });
}

function openSchemaModal() {
  $("schemaText").value = JSON.stringify(SCHEMA, null, 2);
  $("schemaError").textContent = "";
  $("schemaModal").hidden = false;
}

async function saveSchema() {
  let parsed;
  try {
    parsed = JSON.parse($("schemaText").value);
  } catch (e) {
    $("schemaError").textContent = t("errJsonParse", e.message);
    return;
  }
  try {
    SCHEMA = await api("/api/schema", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    });
    $("schemaModal").hidden = true;
    await loadSchema();
    toast(t("toastSchemaSaved"));
  } catch (e) {
    $("schemaError").textContent = e.message;
  }
}

// ------------------------------------------------------------------- video --
function setVideoLoaded(name) {
  $("videoName").textContent = name || t("noVideo");
  if (name) {
    const player = $("player");
    player.src = "/api/video?ts=" + Date.now();
    player.style.display = "block";
    $("playerEmpty").style.display = "none";
    player.load();
  }
}

async function browseVideo() {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.pick_video) {
    try {
      const path = await window.pywebview.api.pick_video();
      if (!path) return;
      const res = await api("/api/load-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      setVideoLoaded(res.name);
      return;
    } catch (e) {
      toast(t("errPickFile", e.message));
    }
  }
  $("fileInput").click();
}

async function uploadVideo(file) {
  if (!file) return;
  toast(t("toastUploading"));
  const fd = new FormData();
  fd.append("file", file);
  const res = await api("/api/upload", { method: "POST", body: fd });
  setVideoLoaded(res.name);
  toast(t("toastUploadDone"));
}

// ---------------------------------------------------------------- analysis --
async function startAnalysis() {
  await saveSettings();
  try {
    await api("/api/analyze", { method: "POST" });
  } catch (e) {
    toast(t("errStartFail", e.message));
    return;
  }
  resultCount = 0;
  lastSeek = -1;
  $("resultsBody").innerHTML = "";
  $("startBtn").disabled = true;
  $("stopBtn").disabled = false;
  startPolling();
}

async function stopAnalysis() {
  await api("/api/stop", { method: "POST" });
  toast(t("toastStopReq"));
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(poll, 600);
  poll();
}
function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}

function refreshProgressLabels() {
  $("progressCount").textContent = t("segments", lastSnap.done, lastSnap.total);
}

// Seek the (paused) preview video to the segment being analyzed, so the user
// can see which part of the video is currently being coded.
function seekPreview(seconds) {
  if (seconds === lastSeek) return;
  const player = $("player");
  if (!player.src || !isFinite(player.duration) || player.readyState < 1) return;
  if (!player.paused) return; // don't fight the user if they're watching
  try {
    player.currentTime = Math.min(seconds, Math.max(0, player.duration - 0.05));
    lastSeek = seconds;
  } catch (_) {}
}

async function poll() {
  let snap;
  try {
    snap = await api("/api/status?since=" + resultCount);
  } catch (e) {
    return;
  }
  lastSnap = { done: snap.done, total: snap.total };
  const pct = snap.total > 0 ? Math.round((snap.done / snap.total) * 100) : 0;
  const pill = $("statusPill");
  $("detectorBadge").textContent = "detector: " + (snap.detector || "—");

  // First phase: speech transcription (STT) runs before any segment is coded;
  // show an indeterminate "transcribing…" state so it doesn't look stuck at 0%.
  const transcribing = snap.status === "running" && snap.phase === "transcribing";
  $("progressFill").classList.toggle("loading", transcribing);
  if (transcribing) {
    $("progressPct").textContent = "";
    $("progressFill").style.width = "100%";
    $("progressCount").textContent = t("sttLoading");
    pill.textContent = "transcribing";
    pill.className = "pill running";
  } else {
    $("progressPct").textContent = pct + "%";
    refreshProgressLabels();
    $("progressFill").style.width = pct + "%";
    pill.textContent = snap.status;
    pill.className = "pill " + snap.status;
  }

  // Move the preview playhead to the segment currently being analyzed.
  if (snap.status === "running" && !transcribing &&
      typeof snap.current_seconds === "number") {
    seekPreview(snap.current_seconds);
  }

  if (snap.results && snap.results.length) {
    snap.results.forEach((row) => appendResult(row));
    resultCount += snap.results.length;
    $("resultsEmpty").style.display = "none";
  }

  if (snap.logs) $("logBox").textContent = snap.logs.join("\n");

  if (["done", "stopped", "error"].includes(snap.status)) {
    stopPolling();
    $("startBtn").disabled = false;
    $("stopBtn").disabled = true;
    if (snap.status === "error") toast(t("errorToast", snap.error || "unknown"));
    else if (snap.status === "done") toast(t("doneToast", snap.done));
  }
}

function appendResult(row) {
  const tbody = $("resultsBody");
  const tr = document.createElement("tr");
  tr.dataset.index = row.no - 1;
  if (row.edited) tr.classList.add("edited");

  if (row.review_flag) tr.classList.add("flagged");

  const tdNo = document.createElement("td");
  tdNo.className = "no";
  tdNo.textContent = row.no;

  const tdTs = document.createElement("td");
  tdTs.className = "ts-cell";
  tdTs.textContent = row.timestamp;
  tdTs.title = row.speech ? row.speech : t("titleSeek");
  // Click the time to move the video playhead to this segment.
  tdTs.onclick = () => seekTo(row.seconds);

  const tdG = document.createElement("td");
  tdG.appendChild(renderTags(row.gesture));
  tdG.querySelector(".gtags").onclick = () => openEdit(row.no - 1, row.gesture);

  const tdC = document.createElement("td");
  tdC.className = "conf";
  tdC.textContent = row.confidence != null ? Number(row.confidence).toFixed(2) : "";

  const tdView = document.createElement("td");
  tdView.className = "view";
  const btn = document.createElement("button");
  btn.className = "stripbtn";
  btn.textContent = "🖼";
  btn.title = t("titleViewStrip");
  btn.onclick = () => openStrip(row.no);
  tdView.appendChild(btn);

  tr.append(tdNo, tdTs, tdG, tdC, tdView);
  tbody.appendChild(tr);

  // Speech transcript (STT) shown as a full-width sub-row under the result.
  if (row.speech) {
    tr.classList.add("has-speech");
    const sr = document.createElement("tr");
    sr.className = "speech-row";
    if (row.review_flag) sr.classList.add("flagged");
    const td = document.createElement("td");
    td.colSpan = 5;
    td.innerHTML = `<span class="speechmark">💬</span> ${escapeHtml(row.speech)}`;
    sr.appendChild(td);
    tbody.appendChild(sr);
  }
}

// Jump the video player to a given time (used by clicking a result's timestamp).
function seekTo(seconds) {
  if (typeof seconds !== "number") return;
  const player = $("player");
  if (!player.src || !isFinite(player.duration) || player.readyState < 1) return;
  try {
    player.currentTime = Math.min(seconds, Math.max(0, player.duration - 0.05));
    lastSeek = seconds;  // keep auto-seek in sync so it doesn't fight the user
  } catch (_) {}
}

function renderTags(gestures) {
  const wrap = document.createElement("div");
  wrap.className = "gtags";
  wrap.title = t("titleEditTag");
  if (!gestures || gestures.length === 0) {
    const e = document.createElement("span");
    e.className = "gtag empty-tag";
    e.textContent = t("emptyTag");
    wrap.appendChild(e);
  } else {
    gestures.forEach((g) => {
      const s = document.createElement("span");
      s.className = "gtag";
      s.textContent = g;
      wrap.appendChild(s);
    });
  }
  return wrap;
}

// -------------------------------------------------------------- edit modal --
function openEdit(index, current) {
  editIndex = index;
  $("editRowLabel").textContent = "#" + (index + 1);
  const box = $("editChecks");
  box.innerHTML = "";
  const cur = new Set(current || []);
  SCHEMA.gestures.forEach((g) => {
    const lab = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = g.name;
    cb.checked = cur.has(g.name);
    const txt = document.createElement("span");
    txt.textContent = g.name;
    const desc = document.createElement("small");
    desc.textContent = g.description ? " — " + g.description : "";
    lab.append(cb, txt, desc);
    box.appendChild(lab);
  });
  $("editModal").hidden = false;
}

async function saveEdit() {
  const checked = [...$("editChecks").querySelectorAll("input:checked")].map((c) => c.value);
  try {
    const updated = await api("/api/result/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index: editIndex, gestures: checked }),
    });
    const tr = document.querySelector(`tr[data-index="${editIndex}"]`);
    if (tr) {
      tr.classList.add("edited");
      const tdG = tr.children[2];
      tdG.innerHTML = "";
      tdG.appendChild(renderTags(updated.gesture));
      tdG.querySelector(".gtags").onclick = () => openEdit(editIndex, updated.gesture);
    }
    $("editModal").hidden = true;
    toast(t("toastEdited", editIndex + 1));
  } catch (e) {
    toast(t("errEditFail", e.message));
  }
}

// ----------------------------------------------------------- strip preview --
function openStrip(no) {
  $("stripLabel").textContent = "#" + no;
  $("stripError").textContent = "";
  const img = $("stripImg");
  img.style.display = "none";
  img.onload = () => (img.style.display = "block");
  img.onerror = () => {
    $("stripError").textContent = t("errStripLoad");
  };
  img.src = `/api/strip/${no}?ts=` + Date.now();
  $("stripModal").hidden = false;
}

// --------------------------------------------------------------- overview --
async function openOverview() {
  const body = $("overviewBody");
  body.innerHTML = "";
  let snap;
  try {
    snap = await api("/api/status?since=0");
  } catch (e) {
    toast(t("errLoadResults", e.message));
    return;
  }
  const results = snap.results || [];
  $("overviewCount").textContent = t("ovCount", results.length);
  if (!results.length) {
    body.innerHTML = `<div class="empty">${t("ovNoResults")}</div>`;
    $("overviewModal").hidden = false;
    return;
  }
  results.forEach((row) => {
    const item = document.createElement("div");
    item.className = "ov-item";

    const meta = document.createElement("div");
    meta.className = "ov-meta";
    const tags =
      row.gesture && row.gesture.length
        ? row.gesture.map((g) => `<span class="gtag">${g}</span>`).join(" ")
        : `<span class="gtag empty-tag">${t("emptyTag")}</span>`;
    const grade = row.grade
      ? `<span class="gradebadge g-${row.grade}" title="${
          row.motion != null ? "motion " + Number(row.motion).toFixed(2) : ""
        }${row.source ? " · " + row.source : ""}">${row.grade}</span>` +
        (row.review_flag ? `<span class="flag">⚑</span>` : "")
      : "";
    meta.innerHTML =
      `<span class="ov-no">#${row.no}</span>` +
      `<span class="ov-ts">${row.timestamp}</span>` +
      grade +
      `<span class="ov-tags">${tags}</span>` +
      `<span class="ov-conf">conf ${Number(row.confidence).toFixed(2)}</span>`;

    if (row.speech !== undefined && row.speech !== null && row.speech !== "") {
      const sp = document.createElement("div");
      sp.className = "ov-speech";
      sp.innerHTML = `<span class="ov-speech-label">💬 ${t("speechLabel")}</span> ${escapeHtml(row.speech)}`;
      meta.appendChild(sp);
    }

    const img = document.createElement("img");
    img.className = "ov-img";
    img.loading = "lazy";
    img.alt = "strip #" + row.no;
    img.src = `/api/strip/${row.no}`;
    img.onerror = () => {
      img.replaceWith(
        Object.assign(document.createElement("div"), {
          className: "ov-noimg muted",
          textContent: t("ovNoImg"),
        })
      );
    };

    item.append(meta, img);
    body.appendChild(item);
  });
  $("overviewModal").hidden = false;
}

// ----------------------------------------------------------------- export --
async function exportCsv() {
  const conf = $("includeConf").checked;
  try {
    const res = await api(`/api/export?confidence=${conf}`);
    toast(t("toastSaved", res.path, res.rows));
    // Download the exact file just written (same {video}_{datetime}.csv name).
    const q = `confidence=${conf}&download=true&name=${encodeURIComponent(res.name)}`;
    window.open(`/api/export?${q}`, "_blank");
  } catch (e) {
    toast(t("errExportFail", e.message));
  }
}

// ------------------------------------------------------------------- tabs ---
function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.onclick = () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      tab.classList.add("active");
      $("tab-results").hidden = tab.dataset.tab !== "results";
      $("tab-log").hidden = tab.dataset.tab !== "log";
    };
  });
}

// ------------------------------------------------------------------- init ---
function wire() {
  $("browseBtn").onclick = browseVideo;
  $("fileInput").onchange = (e) => uploadVideo(e.target.files[0]);
  $("apiKey").addEventListener("blur", autosaveApiKey);
  $("clearKeyBtn").onclick = clearApiKey;
  $("saveSettingsBtn").onclick = saveSettings;
  $("motionFilter").onchange = reflectMotionFilter;
  $("sttEnabled").onchange = reflectStt;
  $("interval").oninput = reflectWindowDur;
  $("segmentFrames").oninput = reflectWindowDur;
  $("editSchemaBtn").onclick = openSchemaModal;
  $("schemaCancel").onclick = () => ($("schemaModal").hidden = true);
  $("schemaSave").onclick = saveSchema;
  $("startBtn").onclick = startAnalysis;
  $("stopBtn").onclick = stopAnalysis;
  $("exportBtn").onclick = exportCsv;
  $("editCancel").onclick = () => ($("editModal").hidden = true);
  $("editSave").onclick = saveEdit;
  $("stripClose").onclick = () => ($("stripModal").hidden = true);
  $("overviewBtn").onclick = openOverview;
  $("overviewClose").onclick = () => ($("overviewModal").hidden = true);
  $("langToggle").onclick = () => setLang(LANG === "ko" ? "en" : "ko");
  setupTabs();
}

async function init() {
  wire();
  applyI18n();
  await Promise.all([loadSettings(), loadSchema()]);
  try {
    const cur = await api("/api/current-video");
    if (cur.name) setVideoLoaded(cur.name);
  } catch (_) {}
  poll();
}

document.addEventListener("DOMContentLoaded", init);
