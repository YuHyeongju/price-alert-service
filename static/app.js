// 최저가 알림봇 - 프론트엔드 (바닐라 JS)
const API = ""; // 같은 서버에서 서빙되므로 빈 문자열(상대경로)
const TOKEN_KEY = "pab_token";
const EMAIL_KEY = "pab_email";

const $ = (id) => document.getElementById(id);
const token = () => localStorage.getItem(TOKEN_KEY);
const authHeaders = () => ({ Authorization: "Bearer " + token() });

function toast(msg, ok = true) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast " + (ok ? "ok" : "err");
  setTimeout(() => { t.className = "toast hidden"; }, 3200);
}

function showApp(email) {
  $("authView").classList.add("hidden");
  $("appView").classList.remove("hidden");
  $("userbar").classList.remove("hidden");
  $("userEmail").textContent = email || localStorage.getItem(EMAIL_KEY) || "";
  refresh();
}

function showAuth() {
  $("appView").classList.add("hidden");
  $("userbar").classList.add("hidden");
  $("authView").classList.remove("hidden");
}

async function register() {
  const email = $("email").value.trim();
  const password = $("password").value;
  if (!email || password.length < 6) {
    toast("이메일과 6자 이상 비밀번호를 입력하세요.", false);
    return;
  }
  const res = await fetch(API + "/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (res.status === 201) {
    toast("가입 완료! 바로 로그인할게요.");
    await login();
  } else if (res.status === 409) {
    toast("이미 가입된 이메일이에요. 로그인하세요.", false);
  } else {
    toast("회원가입 실패", false);
  }
}

async function login() {
  const email = $("email").value.trim();
  const password = $("password").value;
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(API + "/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    toast("로그인 실패: 이메일/비밀번호를 확인하세요.", false);
    return;
  }
  const data = await res.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(EMAIL_KEY, email);
  showApp(email);
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EMAIL_KEY);
  showAuth();
}

async function addWatch() {
  const query = $("query").value.trim();
  const target_price = parseInt($("targetPrice").value, 10);
  const comparison = $("comparison").value;
  if (!query || !target_price) {
    toast("검색어와 목표가를 입력하세요.", false);
    return;
  }
  const res = await fetch(API + "/watches", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ query, target_price, comparison }),
  });
  if (res.status === 201) {
    $("query").value = "";
    $("targetPrice").value = "";
    toast("감시를 추가했어요.");
    loadWatches();
  } else {
    toast("추가 실패", false);
  }
}

async function loadWatches() {
  const res = await fetch(API + "/watches", { headers: authHeaders() });
  if (res.status === 401) { logout(); return; }
  const watches = await res.json();
  const el = $("watchList");
  if (!watches.length) {
    el.innerHTML = '<p class="empty">아직 감시가 없어요. 위에서 추가해보세요.</p>';
    return;
  }
  el.innerHTML = watches.map((w) => `
    <div class="item">
      <div class="item-main">
        <strong>${escapeHtml(w.query)}</strong>
        <span class="badge ${w.comparison}">${w.comparison === "lte" ? "≤" : "≥"} ${w.target_price.toLocaleString()}원</span>
        ${w.is_active ? "" : '<span class="badge off">비활성</span>'}
      </div>
      <div class="item-sub">
        최근 최저가: ${w.last_price != null ? w.last_price.toLocaleString() + "원" : "—"}
        ${w.last_checked_at ? " · 확인: " + fmt(w.last_checked_at) : ""}
      </div>
      <div class="item-actions">
        <button class="small" onclick="checkWatch(${w.id}, this)">지금 확인</button>
        <button class="small danger" onclick="deleteWatch(${w.id})">삭제</button>
      </div>
    </div>
  `).join("");
}

let checking = false; // 중복 클릭 방지용 전역 플래그

async function checkWatch(id, btn) {
  if (checking) {
    toast("확인 중이에요. 잠시만요!", false);
    return;
  }
  checking = true;
  const original = btn ? btn.innerHTML : null;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>확인 중...';
  }
  try {
    const res = await fetch(API + `/watches/${id}/check`, { method: "POST", headers: authHeaders() });
    const r = await res.json();
    if (r.alert) {
      toast(`🔔 알림 발생! 최저가 ${r.current_price.toLocaleString()}원`);
    } else if (r.condition_met) {
      toast("조건은 충족했지만 쿨다운 중이라 알림은 생략됐어요.");
    } else if (r.checked) {
      toast(`조건 미충족 (현재 최저가 ${r.current_price != null ? r.current_price.toLocaleString() + "원" : "—"})`);
    } else {
      toast("가격을 가져오지 못했어요.", false);
    }
    loadWatches(); // 목록을 새로 그리므로 버튼도 새 버튼으로 교체됨(자동 복구)
    loadAlerts();
  } catch (e) {
    toast("확인 중 오류가 발생했어요.", false);
    if (btn && original !== null) {
      btn.disabled = false;
      btn.innerHTML = original;
    }
  } finally {
    checking = false;
  }
}

async function deleteWatch(id) {
  await fetch(API + `/watches/${id}`, { method: "DELETE", headers: authHeaders() });
  toast("삭제했어요.");
  loadWatches();
}

async function loadAlerts() {
  const res = await fetch(API + "/alerts", { headers: authHeaders() });
  if (!res.ok) return;
  const alerts = await res.json();
  const el = $("alertList");
  if (!alerts.length) {
    el.innerHTML = '<p class="empty">아직 알림이 없어요.</p>';
    return;
  }
  el.innerHTML = alerts.map((a) => {
    const hasLink = a.product_link && a.product_link.length > 0;
    const titleHtml = hasLink
      ? `<a href="${escapeHtml(a.product_link)}" target="_blank" rel="noopener"><strong>${escapeHtml(a.product_title)}</strong></a>`
      : `<strong>${escapeHtml(a.product_title)}</strong>`;
    const linkA = hasLink
      ? `<a class="linkbtn" href="${escapeHtml(a.product_link)}" target="_blank" rel="noopener">🔗 구매처로 이동</a>`
      : "";
    return `
    <div class="item alert">
      <div class="item-main">
        ${titleHtml}
        <span class="badge">${a.price.toLocaleString()}원</span>
        ${a.mall_name ? `<span class="badge mall">${escapeHtml(a.mall_name)}</span>` : ""}
      </div>
      <div class="item-sub">${escapeHtml(a.message)}</div>
      <div class="item-actions">
        ${linkA}
        <button class="small danger" onclick="deleteAlert(${a.id})">삭제</button>
      </div>
      <div class="item-time">${fmt(a.created_at)}</div>
    </div>`;
  }).join("");
}

async function deleteAlert(id) {
  await fetch(API + `/alerts/${id}`, { method: "DELETE", headers: authHeaders() });
  toast("알림을 삭제했어요.");
  loadAlerts();
}

async function clearAlerts() {
  const res = await fetch(API + "/alerts", { headers: authHeaders() });
  const alerts = await res.json();
  if (!alerts.length) { toast("삭제할 알림이 없어요.", false); return; }
  if (!confirm(`최근 알림 ${alerts.length}건을 모두 삭제할까요?`)) return;
  await fetch(API + "/alerts", { method: "DELETE", headers: authHeaders() });
  toast("알림을 모두 삭제했어요.");
  loadAlerts();
}

function refresh() {
  loadWatches();
  loadAlerts();
}

// 서버는 naive UTC 문자열을 주므로 Z를 붙여 UTC로 파싱 → 로컬(KST)로 표시
function fmt(iso) {
  try {
    const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
    return d.toLocaleString("ko-KR");
  } catch {
    return iso;
  }
}

function escapeHtml(s) {
  return (s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

// 이벤트 바인딩
$("loginBtn").onclick = login;
$("registerBtn").onclick = register;
$("logoutBtn").onclick = logout;
$("addBtn").onclick = addWatch;
$("clearAlertsBtn").onclick = clearAlerts;

// 시작 시 토큰이 있으면 바로 메인 화면
if (token()) showApp();
else showAuth();
