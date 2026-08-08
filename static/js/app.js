/**
 * ╔══════════════════════════════════════════════════════════════╗
 * ║   NutriBot — Frontend Application Logic                      ║
 * ║   IBM Watsonx.ai Nutrition Agent                             ║
 * ╚══════════════════════════════════════════════════════════════╝
 */

"use strict";

// ─────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────
const State = {
  currentSection: "chat",
  theme: localStorage.getItem("nutribot-theme") || "light",
  familyMembers: [],
  memberCount: 0,
};

// ─────────────────────────────────────────────────────────────────
// Initialisation
// ─────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  applyTheme(State.theme);
  setupThemeToggle();
  setupChatInput();
  initFamilySection();
  showSection("chat");
  checkAgentStatus();
  loadUsageBar();
  loadProfileFromDB();
  loadChatHistoryFromDB();
});

// ─────────────────────────────────────────────────────────────────
// Theme
// ─────────────────────────────────────────────────────────────────
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const icon = document.querySelector("#themeToggle i");
  if (icon) icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
  localStorage.setItem("nutribot-theme", theme);
}

function setupThemeToggle() {
  document.getElementById("themeToggle").addEventListener("click", () => {
    State.theme = State.theme === "dark" ? "light" : "dark";
    applyTheme(State.theme);
  });
}

// ─────────────────────────────────────────────────────────────────
// Section Navigation
// ─────────────────────────────────────────────────────────────────
function showSection(sectionName) {
  State.currentSection = sectionName;

  // Hide hero after first nav away from default
  document.querySelectorAll(".content-section").forEach((s) => s.classList.remove("active"));
  document.querySelectorAll(".navbar-nav .nav-link").forEach((l) => l.classList.remove("active"));

  const sectionMap = {
    chat: "chatSection",
    dashboard: "dashboardSection",
    mealplan: "mealplanSection",
    bmi: "bmiSection",
    family: "familySection",
  };

  const el = document.getElementById(sectionMap[sectionName]);
  if (el) el.classList.add("active");

  // Mark correct nav link active
  document.querySelectorAll(".navbar-nav .nav-link").forEach((link) => {
    if (link.getAttribute("onclick")?.includes(`'${sectionName}'`)) {
      link.classList.add("active");
    }
  });

  // Hide hero banner after first section switch
  if (sectionName !== "chat") {
    const hero = document.getElementById("heroBanner");
    if (hero) hero.style.display = "none";
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ─────────────────────────────────────────────────────────────────
// Agent status check
// ─────────────────────────────────────────────────────────────────
async function checkAgentStatus() {
  try {
    const res = await fetch("/api/health/status");
    const data = await res.json();
    if (data.status === "online") {
      showToast(`✅ Connected to ${data.agent} (${data.model})`, "success");
    }
  } catch {
    showToast("⚠️ Agent offline — check Flask server", "error");
  }
}

// ─────────────────────────────────────────────────────────────────
// ── CHAT ──────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────
function setupChatInput() {
  const textarea = document.getElementById("chatInput");
  if (!textarea) return;

  // Auto-expand textarea
  textarea.addEventListener("input", () => {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 140) + "px";
  });

  // Enter = send, Shift+Enter = newline
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

async function sendMessage() {
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;

  input.value = "";
  input.style.height = "auto";

  // Hide welcome screen
  const welcome = document.querySelector(".chat-welcome");
  if (welcome) welcome.remove();

  appendMessage("user", message);
  showTypingIndicator(true);
  setSendDisabled(true);

  const context = gatherUserContext();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, context }),
    });
    const data = await res.json();

    showTypingIndicator(false);
    setSendDisabled(false);

    if (data.error === "limit_reached") {
      appendMessage("bot", `⚠️ **Usage limit reached**\n\n${data.message}`);
      showToast("Monthly limit reached. Upgrade your plan!", "error");
    } else if (data.error) {
      appendMessage("bot", `❌ Error: ${data.error}`);
    } else {
      appendMessage("bot", data.response, data.timestamp);
      loadUsageBar();
    }
  } catch (err) {
    showTypingIndicator(false);
    setSendDisabled(false);
    appendMessage("bot", "❌ Network error. Please check the server is running.");
  }
}

function sendQuick(text) {
  const input = document.getElementById("chatInput");
  if (input) input.value = text;
  showSection("chat");
  setTimeout(sendMessage, 100);
}

function appendMessage(role, text, timestamp) {
  const chatWindow = document.getElementById("chatWindow");

  const wrap = document.createElement("div");
  wrap.className = `message-wrap ${role}`;

  const avatar = document.createElement("div");
  avatar.className = `message-avatar ${role}`;
  avatar.textContent = role === "bot" ? "🥗" : "👤";

  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${role}`;
  bubble.innerHTML = formatMarkdown(text);

  const time = document.createElement("div");
  time.className = "message-time";
  time.textContent = formatTime(timestamp || new Date().toISOString());

  const contentWrap = document.createElement("div");
  contentWrap.appendChild(bubble);
  contentWrap.appendChild(time);

  wrap.appendChild(avatar);
  wrap.appendChild(contentWrap);
  chatWindow.appendChild(wrap);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function showTypingIndicator(show) {
  const el = document.getElementById("typingIndicator");
  el.classList.toggle("show", show);
}

function setSendDisabled(disabled) {
  const btn = document.getElementById("sendBtn");
  if (btn) btn.disabled = disabled;
}

async function clearChat() {
  try {
    await fetch("/api/chat/clear", { method: "POST" });
    const win = document.getElementById("chatWindow");
    win.innerHTML = `
      <div class="chat-welcome">
        <div class="welcome-avatar">🥗</div>
        <h5>Hello! I'm NutriBot</h5>
        <p>Your AI nutrition expert powered by <strong>IBM Watsonx.ai</strong>. How can I help you today?</p>
        <div class="welcome-chips">
          <span class="chip" onclick="sendQuick('What should I eat for breakfast today?')">Breakfast ideas</span>
          <span class="chip" onclick="sendQuick('How many calories should I eat daily?')">Daily calories</span>
          <span class="chip" onclick="sendQuick('Explain the benefits of Indian spices')">Indian spices</span>
        </div>
      </div>`;
    showToast("Conversation cleared", "info");
  } catch { showToast("Could not clear conversation", "error"); }
}

function gatherUserContext() {
  return {
    age: document.getElementById("profileAge")?.value || "",
    gender: document.getElementById("profileGender")?.value || "",
    weight_kg: document.getElementById("profileWeight")?.value || "",
    height_cm: document.getElementById("profileHeight")?.value || "",
    health_goal: document.getElementById("profileGoal")?.value || "",
    dietary_preference: document.getElementById("profileDiet")?.value || "",
  };
}

// ─────────────────────────────────────────────────────────────────
// ── DASHBOARD ─────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────
async function analyzeMeal() {
  const meal = document.getElementById("mealInput")?.value.trim();
  const servings = document.getElementById("servingsInput")?.value || 1;
  if (!meal) { showToast("Please describe your meal", "error"); return; }

  showLoading("Analysing meal nutrition…");
  try {
    const res = await fetch("/api/nutrition/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ meal, servings: parseFloat(servings) }),
    });
    const data = await res.json();
    hideLoading();

    const box = document.getElementById("mealAnalysisResult");
    box.style.display = "block";
    box.innerHTML = `<div class="plan-rendered">${formatMarkdown(data.analysis || data.error)}</div>`;

    // Update stat cards (demo extraction)
    updateStatCards(data.analysis || "");
  } catch (err) {
    hideLoading();
    showToast("Analysis failed: " + err.message, "error");
  }
}

function updateStatCards(text) {
  const calMatch = text.match(/(\d+)\s*(?:kcal|calories?)/i);
  const protMatch = text.match(/protein[:\s]+(\d+)/i);
  const carbMatch = text.match(/carb[:\s]+(\d+)/i);
  const fatMatch  = text.match(/fat[:\s]+(\d+)/i);

  if (calMatch)  document.getElementById("statCalories").textContent = calMatch[1] + " kcal";
  if (protMatch) document.getElementById("statProtein").textContent  = protMatch[1] + " g";
  if (carbMatch) document.getElementById("statCarbs").textContent    = carbMatch[1] + " g";
  if (fatMatch)  document.getElementById("statFats").textContent     = fatMatch[1] + " g";
}

async function loadTips() {
  const container = document.getElementById("tipsContainer");
  container.innerHTML = `<div class="text-center py-3"><div class="loading-spinner" style="width:32px;height:32px;border-width:3px;margin:0 auto;"></div></div>`;
  try {
    const res = await fetch("/api/health/tips");
    const data = await res.json();
    container.innerHTML = `<div class="plan-rendered">${formatMarkdown(data.tips || data.error)}</div>`;
  } catch (err) {
    container.innerHTML = `<p class="text-danger">Failed to load tips: ${err.message}</p>`;
  }
}

// ─────────────────────────────────────────────────────────────────
// ── MEAL PLAN ─────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────
async function generateMealPlan() {
  const calories    = parseInt(document.getElementById("planCalories")?.value) || 2000;
  const duration    = parseInt(document.getElementById("planDuration")?.value) || 7;
  const dietaryPref = document.getElementById("planDietPref")?.value || "Balanced";
  const goal        = document.getElementById("planGoal")?.value || "Maintain weight";
  const cuisine     = document.getElementById("planCuisine")?.value || "Indian";
  const allergiesRaw = document.getElementById("planAllergies")?.value || "";
  const allergies   = allergiesRaw ? allergiesRaw.split(",").map(s => s.trim()).filter(Boolean) : [];

  showLoading("Generating your personalised meal plan…");

  try {
    const res = await fetch("/api/mealplan/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ calories, duration, dietary_preference: dietaryPref, health_goal: goal, cuisine, allergies }),
    });
    const data = await res.json();
    hideLoading();

    const resultEl = document.getElementById("mealPlanResult");
    if (data.error) {
      resultEl.innerHTML = `<p class="text-danger">${data.error}</p>`;
    } else {
      resultEl.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary border-opacity-25">
          <span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-2">✅ Meal Plan Ready</span>
          <a href="/account" class="btn btn-sm btn-outline-primary rounded-3">
            <i class="bi bi-file-earmark-pdf me-1"></i> Download PDF from Account
          </a>
        </div>
        <div class="plan-rendered">${formatMarkdown(data.meal_plan)}</div>
      `;
      loadUsageBar();
    }
  } catch (err) {
    hideLoading();
    showToast("Meal plan failed: " + err.message, "error");
  }
}

// ─────────────────────────────────────────────────────────────────
// ── BMI ───────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────
async function calculateBMI() {
  const weight = parseFloat(document.getElementById("bmiWeight")?.value);
  const height = parseFloat(document.getElementById("bmiHeight")?.value);
  const age    = parseInt(document.getElementById("bmiAge")?.value) || 30;
  const gender = document.getElementById("bmiGender")?.value || "";

  if (!weight || !height) { showToast("Please enter weight and height", "error"); return; }

  showLoading("Calculating your BMI…");

  try {
    const res = await fetch("/api/bmi/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ weight_kg: weight, height_cm: height, age, gender }),
    });
    const data = await res.json();
    hideLoading();

    if (data.error) {
      document.getElementById("bmiResult").innerHTML = `<p class="text-danger">${data.error}</p>`;
      return;
    }

    const bmi = data.bmi;
    const cat = data.category;
    const colorMap = {
      "Underweight": "#3b82f6",
      "Normal weight": "#22c55e",
      "Overweight": "#f59e0b",
      "Obese": "#ef4444",
    };
    const color = colorMap[cat] || "#64748b";

    document.getElementById("bmiResult").innerHTML = `
      <div class="text-center mb-4">
        <div class="bmi-result-badge" style="background:${color}22;color:${color};border:2px solid ${color};">${bmi}</div>
        <h4 style="color:${color};">${cat}</h4>
        <p class="text-muted small">Ideal weight range: <strong>${data.ideal_weight_range.min_kg} – ${data.ideal_weight_range.max_kg} kg</strong></p>
      </div>
      <div class="plan-rendered">${formatMarkdown(data.advice)}</div>`;

    animateBMINeedle(bmi);
  } catch (err) {
    hideLoading();
    showToast("BMI calculation failed: " + err.message, "error");
  }
}

function animateBMINeedle(bmi) {
  const container = document.getElementById("bmiNeedleContainer");
  const needle    = document.getElementById("bmiNeedle");
  const label     = document.getElementById("bmiNeedleLabel");

  container.style.display = "block";

  // Map BMI 10–40 → 0–100%
  const pct = Math.min(100, Math.max(0, ((bmi - 10) / 30) * 100));
  needle.style.left = pct + "%";
  label.style.left  = pct + "%";
  label.textContent = bmi;
}

// ─────────────────────────────────────────────────────────────────
// ── FAMILY ────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────
function initFamilySection() {
  // Add two default members
  addFamilyMember("Dad", 45, "Male", "Hypertension", "Low-sodium");
  addFamilyMember("Mom", 40, "Female", "None", "Vegetarian");
}

function addFamilyMember(name = "", age = "", gender = "", conditions = "", diet = "") {
  State.memberCount++;
  const id = State.memberCount;
  const initials = name ? name[0].toUpperCase() : "#" + id;

  const container = document.getElementById("familyMembersContainer");
  const div = document.createElement("div");
  div.className = "family-member-card";
  div.id = `member-${id}`;
  div.innerHTML = `
    <button class="family-member-remove" onclick="removeFamilyMember(${id})" title="Remove"><i class="bi bi-x-lg"></i></button>
    <div class="d-flex align-items-center gap-2 mb-2">
      <div class="member-avatar">${initials}</div>
      <input type="text" class="form-control form-control-sm" placeholder="Name" value="${name}" oninput="updateAvatar(${id}, this.value)" />
    </div>
    <div class="row g-2">
      <div class="col-4"><input type="number" class="form-control form-control-sm" placeholder="Age" value="${age}" /></div>
      <div class="col-8">
        <select class="form-select form-select-sm">
          <option ${gender==="Male"?"selected":""}>Male</option>
          <option ${gender==="Female"?"selected":""}>Female</option>
          <option ${gender==="Other"?"selected":""}>Other</option>
        </select>
      </div>
      <div class="col-12"><input type="text" class="form-control form-control-sm" placeholder="Health conditions (e.g. diabetes)" value="${conditions}" /></div>
      <div class="col-12">
        <select class="form-select form-select-sm">
          <option ${diet==="Balanced"?"selected":""}>Balanced</option>
          <option ${diet==="Vegetarian"?"selected":""}>Vegetarian</option>
          <option ${diet==="Vegan"?"selected":""}>Vegan</option>
          <option ${diet==="Non-vegetarian"?"selected":""}>Non-vegetarian</option>
          <option ${diet==="Low-sodium"?"selected":""}>Low-sodium</option>
          <option ${diet==="Diabetic-friendly"?"selected":""}>Diabetic-friendly</option>
          <option ${diet==="Keto"?"selected":""}>Keto</option>
        </select>
      </div>
    </div>`;

  container.appendChild(div);
}

function updateAvatar(id, name) {
  const avatar = document.querySelector(`#member-${id} .member-avatar`);
  if (avatar) avatar.textContent = name ? name[0].toUpperCase() : "#" + id;
}

function removeFamilyMember(id) {
  document.getElementById(`member-${id}`)?.remove();
  showToast("Member removed", "info");
}

async function generateFamilyPlan() {
  const cards = document.querySelectorAll(".family-member-card");
  if (cards.length === 0) { showToast("Add at least one family member", "error"); return; }

  const members = Array.from(cards).map((card) => {
    const inputs = card.querySelectorAll("input, select");
    return {
      name: inputs[0]?.value || "Member",
      age: inputs[1]?.value || "?",
      gender: inputs[2]?.value || "?",
      health_conditions: inputs[3]?.value || "none",
      dietary_preference: inputs[4]?.value || "Balanced",
    };
  });

  showLoading("Generating family nutrition plan…");

  try {
    const res = await fetch("/api/family/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ members }),
    });
    const data = await res.json();
    hideLoading();

    const resultEl = document.getElementById("familyPlanResult");
    if (data.error) {
      resultEl.innerHTML = `<p class="text-danger">${data.error}</p>`;
    } else {
      resultEl.innerHTML = `<div class="plan-rendered">${formatMarkdown(data.family_plan)}</div>`;
    }
  } catch (err) {
    hideLoading();
    showToast("Family plan failed: " + err.message, "error");
  }
}

// ─────────────────────────────────────────────────────────────────
// ── UTILITIES ─────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────

/** Minimal Markdown → HTML renderer */
function formatMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")  // sanitise
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")                     // bold
    .replace(/\*(.+?)\*/g, "<em>$1</em>")                                 // italic
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")                               // h4
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")                                // h3
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")                                 // h2
    .replace(/^\- (.+)$/gm, "<li>$1</li>")                                // list items
    .replace(/(<li>[\s\S]+?<\/li>)/g, "<ul>$1</ul>")                      // wrap lists
    .replace(/<\/ul>\n<ul>/g, "")                                          // merge consecutive lists
    .replace(/⚠️(.+)/g, '<div class="warning-note">⚠️$1</div>')           // warnings
    .replace(/\n{2,}/g, "</p><p>")                                         // paragraphs
    .replace(/^(?!<[hup])(.+)$/gm, (m) => m.trim() ? m : "")             // pass-through
    .replace(/^\s*$[\n\r]{1,}/gm, "");                                    // remove empty lines
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}

// ── Loading overlay ──
function showLoading(text = "Processing…") {
  document.getElementById("loadingText").textContent = text;
  document.getElementById("loadingOverlay").classList.add("show");
}

function hideLoading() {
  document.getElementById("loadingOverlay").classList.remove("show");
}

// ── Toast notifications ──
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast-msg ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ─────────────────────────────────────────────────────────────────
// Usage bar (navbar dropdown)
// ─────────────────────────────────────────────────────────────────
async function loadUsageBar() {
  try {
    const res  = await fetch("/api/usage");
    if (!res.ok) return;
    const data = await res.json();
    const pct  = Math.min(Math.round((data.chats_used / data.chats_limit) * 100), 100);
    const countEl = document.getElementById("navChatCount");
    const barEl   = document.getElementById("navChatBar");
    if (countEl) countEl.textContent = `${data.chats_used} / ${data.chats_limit}`;
    if (barEl)   barEl.style.width   = pct + "%";
  } catch (_) {}
}

// ─────────────────────────────────────────────────────────────────
// Load profile from DB into sidebar fields
// ─────────────────────────────────────────────────────────────────
async function loadProfileFromDB() {
  try {
    const res  = await fetch("/api/profile");
    if (!res.ok) return;
    const data = await res.json();
    if (data.age)    document.getElementById("profileAge").value    = data.age;
    if (data.gender) document.getElementById("profileGender").value = data.gender;
    if (data.weight_kg) document.getElementById("profileWeight").value = data.weight_kg;
    if (data.height_cm) document.getElementById("profileHeight").value = data.height_cm;
    if (data.goal)   document.getElementById("profileGoal").value   = data.goal;
    if (data.diet)   document.getElementById("profileDiet").value   = data.diet;
  } catch (_) {}
}

// ─────────────────────────────────────────────────────────────────
// Load chat history from DB on page load
// ─────────────────────────────────────────────────────────────────
async function loadChatHistoryFromDB() {
  try {
    const res  = await fetch("/api/chat/history");
    if (!res.ok) return;
    const rows = await res.json();
    if (!rows.length) return;

    // Clear welcome screen
    const chatWindow = document.getElementById("chatWindow");
    const welcome    = chatWindow.querySelector(".chat-welcome");
    if (welcome) welcome.remove();

    rows.forEach(r => appendMessage(r.role === "user" ? "user" : "bot", r.content, r.timestamp));

    // Scroll to bottom
    chatWindow.scrollTop = chatWindow.scrollHeight;
  } catch (_) {}
}

// ─────────────────────────────────────────────────────────────────
// Food Photo Scanner (Multimodal AI)
// ─────────────────────────────────────────────────────────────────
async function uploadFoodPhoto(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  
  // Display preview message in chat window
  const chatWindow = document.getElementById("chatWindow");
  const welcome = chatWindow.querySelector(".chat-welcome");
  if (welcome) welcome.remove();

  appendMessage("user", `📸 Uploaded food photo: <i>${file.name}</i>`);
  showTyping(true);

  const formData = new FormData();
  formData.append("image", file);

  try {
    const res = await fetch("/api/nutrition/analyze-image", {
      method: "POST",
      body: formData,
    });
    showTyping(false);
    const data = await res.json();
    if (res.ok) {
      appendMessage("bot", data.analysis);
      loadUsageBar();
    } else {
      appendMessage("bot", `⚠️ Image Analysis Error: ${data.error || "Failed to process photo."}`);
    }
  } catch (err) {
    showTyping(false);
    appendMessage("bot", "⚠️ Network error trying to analyze photo.");
  } finally {
    input.value = "";
  }
}

