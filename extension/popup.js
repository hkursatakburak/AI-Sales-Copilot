// AI Sales Copilot — popup mantığı.
//
// Akış:
//   1. Panel açılır → chrome.storage.local'dan JWT token kontrol edilir.
//   2. Token yoksa → giriş ekranı gösterilir.
//   3. Giriş yapılınca → token kaydedilir, ana görünüme geçilir.
//   4. Analiz/e-posta istekleri → Authorization: Bearer <token> başlığıyla atılır.
//   5. 401 gelirse → token temizlenir, giriş ekranına dönülür.

"use strict";

// --- DOM referansları ---
const els = {
  // Giriş ekranı
  loginView: document.getElementById("login-view"),
  loginEmail: document.getElementById("login-email"),
  loginPassword: document.getElementById("login-password"),
  loginBtn: document.getElementById("login-btn"),
  loginError: document.getElementById("login-error"),

  // Ana görünüm
  mainView: document.getElementById("main-view"),
  logoutBtn: document.getElementById("logout-btn"),

  // Mevcut alanlar
  url: document.getElementById("current-url"),
  analyzeBtn: document.getElementById("analyze-btn"),
  loading: document.getElementById("loading"),
  error: document.getElementById("error"),
  result: document.getElementById("result"),
  aiStatus: document.getElementById("ai-status"),
  aiCards: document.querySelectorAll(".ai-card"),
  companyName: document.getElementById("company-name"),
  scrapeBadge: document.getElementById("scrape-badge"),
  scrapeMeta: document.getElementById("scrape-meta"),
  contentPreview: document.getElementById("content-preview"),
  leadScore: document.getElementById("lead-score"),
  scoreReasons: document.getElementById("score-reasons"),
  summary: document.getElementById("summary"),
  painPoints: document.getElementById("pain-points"),
  signalsCard: document.getElementById("signals-card"),
  signals: document.getElementById("signals"),
  coldEmail: document.getElementById("cold-email"),
  pitch: document.getElementById("pitch"),
  regenerateBtn: document.getElementById("regenerate-btn"),
};

let activeUrl = null;
let jwtToken = null;

// --- Genel yardımcılar ---
function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

function setLoading(isLoading) {
  els.analyzeBtn.disabled = isLoading;
  isLoading ? show(els.loading) : hide(els.loading);
}

function showError(message) {
  els.error.textContent = message;
  show(els.error);
}

function clearFeedback() {
  hide(els.error);
  hide(els.result);
}

// --- Görünüm geçişleri ---
function showLoginView() {
  hide(els.mainView);
  hide(els.logoutBtn);
  hide(els.url);
  show(els.loginView);
}

async function showMainView() {
  hide(els.loginView);
  show(els.mainView);
  show(els.logoutBtn);
  show(els.url);

  activeUrl = await getActiveTabUrl();
  els.url.textContent = activeUrl ?? "Adres okunamadı";
}

// --- Giriş yardımcıları ---
function showLoginError(message) {
  els.loginError.textContent = message;
  show(els.loginError);
}

function clearLoginError() {
  hide(els.loginError);
}

async function saveToken(token) {
  jwtToken = token;
  if (typeof chrome !== "undefined" && chrome.storage) {
    await chrome.storage.local.set({ jwt_token: token });
  }
}

async function clearToken() {
  jwtToken = null;
  if (typeof chrome !== "undefined" && chrome.storage) {
    await chrome.storage.local.remove("jwt_token");
  }
}

async function loadStoredToken() {
  if (typeof chrome !== "undefined" && chrome.storage) {
    const result = await chrome.storage.local.get("jwt_token");
    return result.jwt_token ?? null;
  }
  return null;
}

// --- Sekme URL'si ---
async function getActiveTabUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  const paramUrl = urlParams.get("url");
  if (paramUrl) return paramUrl;
  if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return tab?.url ?? null;
  }
  return null;
}

// --- Kimlik doğrulamalı fetch yardımcısı ---
// 401 gelirse token temizler ve giriş ekranına döner; true döndürür (çağıranın dur).
async function authFetch(url, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(jwtToken ? { Authorization: `Bearer ${jwtToken}` } : {}),
    ...(options.headers ?? {}),
  };
  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    await clearToken();
    showLoginView();
    return null;
  }
  return response;
}

// --- Backend iletişimi ---
async function requestAnalysis(url) {
  const endpoint = CONFIG.BACKEND_URL + CONFIG.ANALYZE_ENDPOINT;
  let response;
  try {
    response = await authFetch(endpoint, {
      method: "POST",
      body: JSON.stringify({ url }),
    });
  } catch {
    throw new Error("Backend'e ulaşılamadı. Sunucu çalışıyor mu? (" + CONFIG.BACKEND_URL + ")");
  }

  if (response === null) return null; // 401 → giriş ekranına döndü

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const msg = data?.error?.message ?? "Bilinmeyen bir hata oluştu.";
    throw new Error(msg);
  }
  return data;
}

// --- Render ---
function renderScore(leadScore) {
  els.leadScore.textContent = leadScore.value;
  els.leadScore.className = "score-badge " + leadScore.tier;
  els.scoreReasons.innerHTML = "";
  for (const reason of leadScore.reasons) {
    const li = document.createElement("li");
    const sign = reason.points >= 0 ? "+" : "";
    li.textContent = `${sign}${reason.points} — ${reason.explanation}`;
    els.scoreReasons.appendChild(li);
  }
}

function renderList(container, items) {
  container.innerHTML = "";
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    container.appendChild(li);
  }
}

function renderScraped(scraped) {
  if (!scraped) {
    els.scrapeBadge.textContent = "";
    els.scrapeMeta.textContent = "İçerik çekilmedi.";
    els.contentPreview.textContent = "";
    return;
  }
  els.scrapeBadge.textContent = scraped.renderer;
  els.scrapeBadge.className = "renderer-badge " + scraped.renderer;
  els.scrapeMeta.textContent = `${scraped.word_count} kelime çekildi`;
  els.contentPreview.textContent = scraped.content_preview || "";
}

function renderSignals(signals) {
  if (!signals) { els.signalsCard.classList.add("hidden"); return; }
  els.signalsCard.classList.remove("hidden");
  const chips = [];
  if (signals.sector) chips.push(`Sektör: ${signals.sector}`);
  if (signals.employee_band) chips.push(`Çalışan: ${signals.employee_band}`);
  if (signals.is_hiring) chips.push("İşe alım var");
  for (const role of signals.hiring_roles || []) chips.push(role);
  for (const g of signals.growth_signals || []) chips.push(g);
  for (const t of signals.technologies || []) chips.push(t);

  els.signals.innerHTML = "";
  if (chips.length === 0) { els.signals.textContent = "Belirgin sinyal bulunamadı."; return; }
  for (const text of chips) {
    const span = document.createElement("span");
    span.className = "chip";
    span.textContent = text;
    els.signals.appendChild(span);
  }
}

function renderResult(data) {
  els.companyName.textContent = data.company_name ?? "—";
  renderScraped(data.scraped);

  const aiOff = Boolean(data.meta?.is_stub);
  els.aiStatus.classList.toggle("hidden", !aiOff);
  for (const card of els.aiCards) card.classList.toggle("hidden", aiOff);

  if (!aiOff) {
    renderSignals(data.signals);
    els.summary.textContent = data.summary;
    els.coldEmail.textContent = data.cold_email;
    els.pitch.textContent = data.pitch;
    renderList(els.painPoints, data.pain_points);
    renderScore(data.lead_score);
  }
  show(els.result);
}

// --- Olay işleyiciler ---
async function onLoginClick() {
  clearLoginError();
  const email = els.loginEmail.value.trim();
  const password = els.loginPassword.value;

  if (!email || !password) {
    showLoginError("E-posta ve şifre alanları boş bırakılamaz.");
    return;
  }

  els.loginBtn.disabled = true;
  els.loginBtn.textContent = "Giriş yapılıyor…";

  try {
    const response = await fetch(CONFIG.BACKEND_URL + "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      showLoginError(data?.detail ?? "E-posta veya şifre hatalı.");
      return;
    }

    await saveToken(data.access_token);
    await showMainView();
  } catch {
    showLoginError("Sunucuya ulaşılamadı. Backend çalışıyor mu?");
  } finally {
    els.loginBtn.disabled = false;
    els.loginBtn.textContent = "Giriş Yap";
  }
}

async function onLogoutClick() {
  await clearToken();
  clearFeedback();
  showLoginView();
}

async function onAnalyzeClick() {
  clearFeedback();
  if (!activeUrl) { showError("Aktif sekmenin adresi okunamadı."); return; }

  setLoading(true);
  try {
    const data = await requestAnalysis(activeUrl);
    if (data !== null) renderResult(data);
  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
}

async function onRegenerateClick() {
  if (!activeUrl) return;
  const btn = els.regenerateBtn;
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Üretiliyor…";
  try {
    const response = await authFetch(CONFIG.BACKEND_URL + CONFIG.EMAIL_ENDPOINT, {
      method: "POST",
      body: JSON.stringify({ url: activeUrl }),
    });
    if (response === null) return; // 401 → login
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(data?.error?.message ?? "Yeniden üretilemedi.");
    els.coldEmail.textContent = data.cold_email;
    els.pitch.textContent = data.pitch;
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

async function onCopyClick(event) {
  const targetId = event.target.dataset.copyTarget;
  const text = document.getElementById(targetId)?.textContent ?? "";
  try {
    await navigator.clipboard.writeText(text);
    const original = event.target.textContent;
    event.target.textContent = "Kopyalandı ✓";
    setTimeout(() => (event.target.textContent = original), 1200);
  } catch {
    showError("Panoya kopyalanamadı.");
  }
}

// --- Başlangıç ---
async function init() {
  els.loginBtn.addEventListener("click", onLoginClick);
  els.logoutBtn.addEventListener("click", onLogoutClick);
  els.analyzeBtn.addEventListener("click", onAnalyzeClick);
  els.regenerateBtn.addEventListener("click", onRegenerateClick);
  for (const btn of document.querySelectorAll(".copy-btn[data-copy-target]")) {
    btn.addEventListener("click", onCopyClick);
  }

  // Enter tuşuyla da giriş yapılabilsin
  els.loginPassword.addEventListener("keydown", (e) => {
    if (e.key === "Enter") onLoginClick();
  });

  const stored = await loadStoredToken();
  if (stored) {
    jwtToken = stored;
    await showMainView();
  } else {
    showLoginView();
  }
}

document.addEventListener("DOMContentLoaded", init);
