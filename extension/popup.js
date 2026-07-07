// AI Sales Copilot — popup mantığı (Sprint 1).
//
// Akış: panel açılır -> aktif sekmenin URL'si okunur -> kullanıcı butona basar
// -> backend'in /analyze endpoint'ine POST atılır -> sonuç panelde gösterilir.
//
// Sorumluluklar küçük fonksiyonlara bölündü (okunabilirlik + test edilebilirlik).

"use strict";

// --- DOM referansları ---
const els = {
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

// --- Yardımcılar ---
function show(el) {
  el.classList.remove("hidden");
}
function hide(el) {
  el.classList.add("hidden");
}

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

// Aktif sekmenin URL'sini alır. activeTab izni, kullanıcı eklentiyi
// çalıştırdığında bu erişimi geçici olarak verir.
async function getActiveTabUrl() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab?.url ?? null;
}

// Backend'e analiz isteği atar. Hata durumunda anlamlı bir Error fırlatır.
async function requestAnalysis(url) {
  const endpoint = CONFIG.BACKEND_URL + CONFIG.ANALYZE_ENDPOINT;
  let response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  } catch (networkErr) {
    throw new Error(
      "Backend'e ulaşılamadı. Sunucu çalışıyor mu? (" + CONFIG.BACKEND_URL + ")"
    );
  }

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
  els.leadScore.className = "score-badge " + leadScore.tier; // hot|warm|cold
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
  els.scrapeBadge.textContent = scraped.renderer; // static | dynamic
  els.scrapeBadge.className = "renderer-badge " + scraped.renderer;
  els.scrapeMeta.textContent = `${scraped.word_count} kelime çekildi`;
  els.contentPreview.textContent = scraped.content_preview || "";
}

function renderSignals(signals) {
  if (!signals) {
    els.signalsCard.classList.add("hidden");
    return;
  }
  els.signalsCard.classList.remove("hidden");
  const chips = [];
  if (signals.sector) chips.push(`Sektör: ${signals.sector}`);
  if (signals.employee_band) chips.push(`Çalışan: ${signals.employee_band}`);
  if (signals.is_hiring) chips.push("İşe alım var");
  for (const role of signals.hiring_roles || []) chips.push(role);
  for (const g of signals.growth_signals || []) chips.push(g);
  for (const t of signals.technologies || []) chips.push(t);

  els.signals.innerHTML = "";
  if (chips.length === 0) {
    els.signals.textContent = "Belirgin sinyal bulunamadı.";
    return;
  }
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
  // AI kapalıysa: profesyonel bilgi ekranı göster, AI'ya bağlı kartları gizle.
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
async function onAnalyzeClick() {
  clearFeedback();

  if (!activeUrl) {
    showError("Aktif sekmenin adresi okunamadı.");
    return;
  }

  setLoading(true);
  try {
    const data = await requestAnalysis(activeUrl);
    renderResult(data);
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
    const endpoint = CONFIG.BACKEND_URL + CONFIG.EMAIL_ENDPOINT;
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: activeUrl }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(data?.error?.message ?? "Yeniden üretilemedi.");
    }
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
  els.analyzeBtn.addEventListener("click", onAnalyzeClick);
  els.regenerateBtn.addEventListener("click", onRegenerateClick);
  for (const btn of document.querySelectorAll(".copy-btn[data-copy-target]")) {
    btn.addEventListener("click", onCopyClick);
  }

  activeUrl = await getActiveTabUrl();
  els.url.textContent = activeUrl ?? "Adres okunamadı";
}

document.addEventListener("DOMContentLoaded", init);
