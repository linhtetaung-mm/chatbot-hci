"use strict";
// Study version: one neutral chatbot for every condition. The participant never sees the assigned style or memory.
const root = document.querySelector("#app");
const isAdmin = location.pathname === "/admin";
const params = new URLSearchParams(location.search);
let visit = ["first", "final"].includes(params.get("visit"))
  ? params.get("visit")
  : "home";
let state = null,
  current = params.get("conversation_id"),
  busy = false,
  invitation = null,
  thanks = false,
  pendingSend = null,
  pendingRatings = null,
  pendingPre = null;
let operations = 0;
function applyBusy() {
  root.setAttribute("aria-busy", String(busy));
  for (const button of root.querySelectorAll("button:not(#stop)")) {
    if (busy && !button.disabled) {
      button.dataset.busyDisabled = "1";
      button.disabled = true;
    } else if (!busy && button.dataset.busyDisabled) {
      delete button.dataset.busyDisabled;
      button.disabled = false;
    }
  }
}
function begin() {
  operations++;
  busy = true;
  applyBusy();
}
function end() {
  operations = Math.max(0, operations - 1);
  busy = operations > 0;
  applyBusy();
}

const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
function announce(s) {
  const e = document.querySelector("#notice");
  e.textContent = s;
  e.hidden = false;
  clearTimeout(announce.timer);
  announce.timer = setTimeout(() => (e.hidden = true), 15000);
}
async function api(path, data) {
  let response;
  try {
    response = await fetch("/api/" + path, {
      method: data ? "POST" : "GET",
      headers: data
        ? { "Content-Type": "application/json", "X-Chatbot-Request": "1" }
        : {},
      body: data ? JSON.stringify(data) : undefined,
    });
  } catch (_) {
    throw new Error(
      "Connection lost. Check your internet, keep this page open and try again.",
    );
  }
  let result;
  try {
    result = await response.json();
  } catch (_) {
    throw new Error(
      `The server is temporarily unavailable (HTTP ${response.status}). Wait a moment and try again.`,
    );
  }
  if (!response.ok) {
    const error = new Error(
      result.error || "The request failed. Please try again.",
    );
    error.status = response.status;
    throw error;
  }
  return result;
}
function values(form) {
  const o = {};
  for (const f of form.elements)
    if (f.name) o[f.name] = f.type === "checkbox" ? f.checked : f.value;
  return o;
}
function banner(mode, storage) {
  const preview =
    storage === "temporary"
      ? '<p class="help">Temporary team preview · no saved memory or ratings.</p>'
      : "";
  const text =
    mode === "setup"
      ? "OpenAI API not connected · waiting for your API key."
      : mode === "demo"
        ? "Demo · simulated examples only, not an AI conversation."
        : "";
  return preview + (text ? `<p class="mode demo">${text}</p>` : "");
}
function setCurrent(id) {
  current = id;
  const q = new URLSearchParams();
  if (visit !== "home") q.set("visit", visit);
  if (id) q.set("conversation_id", id);
  history.replaceState(
    null,
    "",
    location.pathname + (q.toString() ? "?" + q : ""),
  );
}
function append(html) {
  root.insertAdjacentHTML("beforeend", html);
}
function scale7(name, label) {
  return `<fieldset class="scale"><legend>${label}</legend><div class="scale-row"><span class="muted">Strongly disagree</span>${[1, 2, 3, 4, 5, 6, 7].map((n) => `<label class="pt"><input type="radio" name="${name}" value="${n}" required><span>${n}</span></label>`).join("")}<span class="muted">Strongly agree</span></div></fieldset>`;
}
function slider(name, label) {
  return `<label for="${name}">${label}</label><div class="slider"><span class="muted">0 Not at all</span><input id="${name}" name="${name}" type="range" min="0" max="100" step="1" value="50"><span class="muted">100 Extremely</span></div><p class="slider-value">Your answer: <strong id="${name}-value">50</strong></p>`;
}
function wireSlider(name) {
  const r = document.querySelector("#" + name);
  r.oninput = () =>
    (document.querySelector("#" + name + "-value").textContent = r.value);
}
function support() {
  const clean = (s) => esc(String(s || "").replace(/[.\s]+$/, ""));
  return `<p class="help">This chatbot is an AI and is not monitored live. If you feel very distressed: ${clean(state.support)}. Research team: ${clean(state.contact)}.</p>`;
}

function login() {
  document.querySelector("#logout").hidden = true;
  root.innerHTML = `<h1>${isAdmin ? "Researcher sign in" : "Welcome"}</h1><p class="muted">${isAdmin ? "Use the ADMIN_KEY from your private settings (Render Environment or local .env)." : "Enter the access code you received from the research team."}</p><form id="login" spellcheck="false"><label for="code">${isAdmin ? "Researcher secret" : "Access code"}</label><input id="code" name="code" inputmode="text" autocorrect="off" type="${isAdmin ? "password" : "text"}" autocomplete="off" autocapitalize="characters" required maxlength="200"><button>Sign in</button></form>`;
  document.querySelector("#login").onsubmit = async (ev) => {
    ev.preventDefault();
    if (busy) return;
    begin();
    try {
      await api("login", { code: ev.target.code.value, admin: isAdmin });
      pendingSend = null;
      pendingRatings = null;
      pendingPre = null;
      await load();
    } catch (e) {
      announce(e.message);
    } finally {
      end();
    }
  };
}
async function load() {
  try {
    if (isAdmin) {
      await adminPage();
      return;
    }
    // One request when the chat is already known (faster after each message); a second only to resume an open chat.
    state = await api(
      "state" +
        (current ? "?conversation_id=" + encodeURIComponent(current) : ""),
    );
    if (!current && state.open_conversation) {
      setCurrent(state.open_conversation);
      state = await api("state?conversation_id=" + encodeURIComponent(current));
    }
    document.querySelector("#logout").hidden = false;
    render();
    return true;
  } catch (e) {
    if (e.status === 401 || e.message === "Please sign in.") login();
    else if (e.message === "Conversation unavailable.") {
      setCurrent(null);
      await load();
    } else {
      if (state && !isAdmin) render();
      else if (!state && !document.querySelector("#login")) {
        root.innerHTML =
          '<h1>Unable to connect</h1><p>Please check your internet connection and try again. If the problem continues, contact the research team.</p><button id="reconnect">Try again</button>';
        document.querySelector("#reconnect").onclick = load;
      }
      announce(e.message);
    }
    return false;
  }
}
function render() {
  renderContent();
  applyBusy();
}
function renderContent() {
  if (
    pendingRatings &&
    state.pending_rating !== pendingRatings.conversation_id
  ) {
    pendingRatings = null;
    thanks = true;
    visit = "home";
    setCurrent(null);
  }
  if (!state.conversation || state.conversation.status !== "open")
    pendingSend = null;
  root.innerHTML = `<h1>Chatbot</h1>${banner(state.mode, state.storage_mode)}`;
  if (state.suspended) {
    append(
      `<h2>This chat is paused</h2><p>Please contact the research team before continuing.</p>${support()}`,
    );
    return;
  }
  if (!state.consented) {
    append(
      `<h2>Before you start</h2><p>In this study you chat with an AI chatbot about mild, everyday stress, like study pressure or a small disagreement. Please do not share real names, contact details or anything very serious.</p><p>Your chats and short ratings are stored under your study code, not your name, and only the research team can read them. Messages are processed by OpenAI to create replies. Different participants may use slightly different chatbot settings; this is explained at the end of the study. You can stop at any time and ask the research team to delete your records. Planned deletion date: ${esc(state.delete_date)}.</p>${support()}<form id="consent">${[
        ["adult", "I am 18 or older and comfortable chatting in English."],
        ["mild", "I will only talk about mild, everyday topics."],
        ["voluntary", "I understand I can stop at any time."],
        [
          "data_consent",
          "I agree to my chats and ratings being stored and analysed as described.",
        ],
      ]
        .map(
          ([k, l]) =>
            `<label class="check"><input name="${k}" type="checkbox" required><span>${l}</span></label>`,
        )
        .join("")}<button>Agree and continue</button></form>`,
    );
    document.querySelector("#consent").onsubmit = (ev) => {
      ev.preventDefault();
      act("consent", values(ev.target));
    };
    return;
  }
  if (state.pending_rating) {
    append(
      `<h2>Three quick questions</h2><p class="muted">About the chat you just finished.</p><form id="rate">${slider("post_distress", "How upset do you feel about the situation now?")}${scale7("support_needed", "The chatbot gave me the kind of support I needed.")}${scale7("felt_understood", "I felt understood by the chatbot.")}<button>Submit</button></form>`,
    );
    wireSlider("post_distress");
    if (pendingRatings?.conversation_id === state.pending_rating) {
      const slider = document.querySelector("#post_distress");
      slider.value = pendingRatings.post_distress;
      slider.oninput();
      for (const name of ["support_needed", "felt_understood"]) {
        const choice = document.querySelector(
          `input[name="${name}"][value="${pendingRatings[name]}"]`,
        );
        if (choice) choice.checked = true;
      }
    }
    document.querySelector("#rate").onsubmit = (ev) => {
      ev.preventDefault();
      const v = values(ev.target);
      const f = ev.target;
      const pick = (n) => {
        const c = f.querySelector(`input[name="${n}"]:checked`);
        return c ? Number(c.value) : null;
      };
      rate({
        post_distress: Number(v.post_distress),
        support_needed: pick("support_needed"),
        felt_understood: pick("felt_understood"),
      });
    };
    return;
  }
  const c = state.conversation;
  if (!c || c.status !== "open") {
    if (thanks)
      append(
        `<p class="saved">Thank you, your answers are saved. You can close this page now. Come back here whenever you would like to chat again.</p>`,
      );
    append(
      `<h2>${visit === "home" ? "Start a chat" : "Start the chat for this session"}</h2><p>Think about what you would like to talk about, something mildly stressful from your day or week.</p><form id="start">${slider("pre_distress", "How upset do you feel about it right now?")}<button ${state.mode === "setup" ? "disabled" : ""}>Start chat</button></form>${support()}`,
    );
    wireSlider("pre_distress");
    if (pendingPre !== null) {
      const slider = document.querySelector("#pre_distress");
      slider.value = pendingPre;
      slider.oninput();
    }
    document.querySelector("#start").onsubmit = (ev) => {
      ev.preventDefault();
      startChat(Number(values(ev.target).pre_distress));
    };
    return;
  }
  pendingPre = null;
  if (pendingSend) {
    const saved = state.messages.find(
      (m) => m.role === "user" && m.request_id === pendingSend.id,
    );
    if (pendingSend.conversation_id !== current || saved?.status === "success")
      pendingSend = null;
  }
  const localPending =
    pendingSend &&
    !state.messages.some(
      (m) => m.role === "user" && m.request_id === pendingSend.id,
    )
      ? {
          role: "user",
          text: pendingSend.text,
          status: "failed",
          request_id: pendingSend.id,
        }
      : null;
  const messages = localPending
    ? [...state.messages, localPending]
    : state.messages;
  const unfinished = messages.find(
    (m) => m.role === "user" && m.status !== "success",
  );
  const need = state.min_messages || 1;
  const enough = state.turns >= need;
  append(
    `<div class="messages" aria-live="polite">${messages.map((m) => `<div class="message ${m.role === "user" ? "user" : ""} ${m.status !== "success" ? "failed" : ""}"><span class="speaker">${m.role === "user" ? "You" : "Chatbot"}${m.status !== "success" ? " · not answered" : ""}</span>${esc(m.text)}</div>`).join("")}</div>`,
  );
  append(
    `<form id="send" class="composer"><label class="sr-only" for="text">Your message</label><textarea id="text" maxlength="1500" rows="2" placeholder="Type your message…" ${unfinished ? "disabled" : ""} required></textarea><button ${unfinished || state.turns >= 20 ? "disabled" : ""}>Send</button></form>${unfinished ? '<p class="error">Your last message needs a reply. Retry sends the same message without creating a duplicate. <button class="text-button" id="retry">Try again</button></p>' : ""}<div class="chat-actions"><button id="finish" ${unfinished || !enough ? "disabled" : ""}>Finish chat</button><button id="stop" class="danger">Stop</button></div>${need > 1 && !enough ? `<p class="help">In this session, please send at least ${need} messages before finishing (${state.turns} so far).</p>` : ""}${state.turns >= 18 ? '<p class="help">This chat is near its 20-message limit. Please finish it soon.</p>' : ""}${support()}`,
  );
  document.querySelector("#send").onsubmit = (ev) => {
    ev.preventDefault();
    const t = document.querySelector("#text").value;
    if (t.trim()) send(t, crypto.randomUUID());
  };
  document.querySelector("#text").onkeydown = (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) {
      ev.preventDefault();
      document.querySelector("#send").requestSubmit();
    }
  };
  if (unfinished)
    document.querySelector("#retry").onclick = () =>
      send(unfinished.text, unfinished.request_id, true);
  document.querySelector("#finish").onclick = () => act("finish");
  document.querySelector("#stop").onclick = () => {
    if (confirm("Stop this chat now? It will not be continued."))
      act("stop", {}, true);
  };
  const box = document.querySelector(".messages");
  box.scrollTop = box.scrollHeight;
}
async function startChat(pre) {
  if (busy) return;
  pendingPre = pre;
  begin();
  thanks = false;
  try {
    const r = await api("action", {
      action: "start",
      chat_type: visit,
      pre_distress: pre,
    });
    setCurrent(r.id);
    await load();
  } catch (e) {
    announce(e.message);
    await load();
  } finally {
    end();
  }
}
async function rate(v) {
  if (busy) return;
  if (v.support_needed === null || v.felt_understood === null) {
    announce("Please answer each question.");
    return;
  }
  pendingRatings = { conversation_id: state.pending_rating, ...v };
  begin();
  try {
    await api("action", {
      action: "rate",
      conversation_id: state.pending_rating,
      ...v,
    });
    pendingRatings = null;
    thanks = true;
    visit = "home";
    setCurrent(null);
    await load();
  } catch (e) {
    announce(e.message);
    await load();
  } finally {
    end();
  }
}
// Show the participant's message at once, with a "typing" bubble, while the reply is written.
function showPending(text, retry) {
  const box = document.querySelector(".messages");
  if (!box) return;
  box.insertAdjacentHTML(
    "beforeend",
    (retry
      ? ""
      : `<div class="message user"><span class="speaker">You</span>${esc(text.trim())}</div>`) +
      '<div class="message typing" id="typing" aria-label="The chatbot is typing"><span class="speaker">Chatbot</span><span class="dots" aria-hidden="true"><span></span><span></span><span></span></span></div>',
  );
  box.scrollTop = box.scrollHeight;
  const input = document.querySelector("#text");
  if (input) {
    input.value = "";
    input.disabled = true;
  }
  for (const el of document.querySelectorAll("#send button,#finish,#retry"))
    el.disabled = true;
}
async function send(text, id, retry = false) {
  if (busy) return;
  pendingSend = { conversation_id: current, text, id };
  begin();
  showPending(text, retry);
  try {
    const r = await api("action", {
      action: "send",
      conversation_id: current,
      text,
      request_id: id,
    });
    if (r.safety)
      announce(
        "This chat has been paused. Please use the support contacts shown.",
      );
    await load();
  } catch (e) {
    announce(e.message);
    await load();
  } finally {
    end();
    const input = document.querySelector("#text");
    if (input && !input.disabled) input.focus({ preventScroll: true });
  }
}
async function act(action, data = {}, interrupt = false) {
  if (busy && !interrupt) return;
  begin();
  if (action === "finish") {
    const b = document.querySelector("#finish");
    if (b) {
      b.disabled = true;
      b.textContent = "Saving…";
    }
  }
  try {
    const r = await api("action", {
      action,
      conversation_id: current,
      ...data,
    });
    if (["finish", "stop"].includes(action)) {
      pendingSend = null;
      setCurrent(null);
    }
    if (r.warning && !state.participant) announce(r.warning);
    await load();
  } catch (e) {
    announce(e.message);
    await load();
  } finally {
    end();
  }
}
async function adminPage() {
  const s = await api("admin/state");
  document.querySelector("#logout").hidden = false;
  const label = (t) =>
    t.study_id ? esc(t.study_id) : "TEST " + esc(t.id.slice(0, 7));
  const testerById = new Map(s.testers.map((t) => [t.id, t]));
  const opts = (list) =>
    list
      .map(
        (t) =>
          `<option value="${esc(t.id)}">${label(t)}${t.suspended ? " · paused" : ""}</option>`,
      )
      .join("");
  const participants = s.testers.filter((t) => t.locked),
    tests = s.testers.filter((t) => !t.locked);
  const styles =
      '<option value="reassure">Reassure</option><option value="guide">Guide</option>',
    memories =
      '<option value="persistent">Persistent memory</option><option value="fresh">Fresh (no memory)</option>';
  const base = location.origin;
  root.innerHTML =
    banner(s.mode, s.storage_mode) +
    `<h1>Researcher</h1><p class="muted">Mode: ${esc(s.mode)} · storage: ${esc(s.storage_mode)} / ${esc(s.database_backend)} · model: ${esc(s.model)}</p>
 <section class="panel"><h2>Enroll the next participant</h2>${s.storage_mode === "temporary" ? '<p class="error">Participant enrollment is unavailable in temporary storage. Use test accounts below for a team preview.</p>' : ""}<p class="muted">Gives the next unused study ID in list order with its locked condition (${esc(s.unused_study_ids)} IDs left). The condition is not shown here. Save the access code now: it is shown only once.</p><button id="enroll" ${s.unused_study_ids && s.storage_mode !== "temporary" ? "" : "disabled"}>Enroll next participant</button><pre id="invitation">${invitation ? esc(invitation) : "No new participant yet."}</pre><form id="add-ids" class="row"><label>Need more participants? Add study IDs (in shuffled blocks of 4)<select name="count"><option value="4">4 more</option><option value="8">8 more</option><option value="12">12 more</option></select></label><button class="quiet">Add study IDs</button></form></section>
 <section class="panel"><h2>Participants (${participants.length})</h2><div class="table-wrap" role="region" aria-label="Study records" tabindex="0"><table><thead><tr><th>Study ID</th><th>Consent</th><th>Finished chats: first / home / final</th><th>Status</th></tr></thead><tbody>${participants.map((t) => `<tr><td>${label(t)}</td><td>${t.consent ? "yes" : "no"}</td><td>${t.finished_chats.first} / ${t.finished_chats.home} / ${t.finished_chats.final}</td><td>${t.suspended ? "<strong>paused (safety)</strong>" : "active"}</td></tr>`).join("") || '<tr><td colspan="4">No participants enrolled yet.</td></tr>'}</tbody></table></div>
 <form id="handoff" class="row"><label>Open a participant's chat screen on this device<select name="tester_id" required>${opts(s.testers)}</select></label><button ${s.testers.length ? "" : "disabled"}>Open chat screen</button></form><p class="muted">This signs this browser in as that person (for guided sessions on a lab device). Sign out afterwards to return here.</p></section>
 <details><summary>Replace a lost access code</summary><p class="muted">Verify the person against the private booking record first. This keeps their existing condition and chats, replaces the old code and signs out their devices. Save the replacement immediately.</p><form id="reissue"><label>Existing person<select name="tester_id" required>${opts(s.testers)}</select></label><label>Type REPLACE CODE<input name="confirmation" required></label><button class="quiet" ${s.testers.length ? "" : "disabled"}>Replace code</button></form><pre id="replacement" hidden></pre></details>
 <details><summary>AI usage and pause switch</summary><p>${s.usage?.paused ? "AI requests paused" : "AI requests enabled"} · ${esc(s.usage?.attempts_today ?? 0)} attempts today · ${esc(s.usage?.attempts_total ?? 0)} total.</p><dl class="usage-grid">${Object.entries(
   {
     TESTER_MINUTE_API_LIMIT: "AI attempts per person / minute",
     TESTER_DAILY_API_LIMIT: "AI attempts per person / day",
     GLOBAL_DAILY_API_LIMIT: "AI attempts for everyone / day",
     GLOBAL_TOTAL_API_LIMIT: "AI attempts for this database",
     GLOBAL_CONCURRENT_API_LIMIT: "Simultaneous AI requests",
     TESTER_DAILY_CHAT_LIMIT: "New chats per person / day",
   },
 )
   .map(
     ([key, label]) =>
       `<div><dt>${label}</dt><dd>${esc(s.usage?.limits?.[key] ?? "—")}</dd></div>`,
   )
   .join(
     "",
   )}</dl><button id="pause-api">${s.usage?.paused ? "Resume AI requests" : "Pause AI requests"}</button></details>
 <details><summary>Test accounts (team and pilot only, not in the study sample)</summary><form id="create" class="row"><label>Style<select name="style">${styles}</select></label><label>Memory<select name="memory">${memories}</select></label><button>Create test account</button></form>
 <div class="table-wrap" role="region" aria-label="Test accounts" tabindex="0"><table><thead><tr><th>Test account</th><th>Condition</th><th>Chats first / home / final</th></tr></thead><tbody>${tests.map((t) => `<tr><td>${label(t)}</td><td>${esc(t.active_style)} · ${esc(t.memory)}</td><td>${t.finished_chats.first} / ${t.finished_chats.home} / ${t.finished_chats.final}</td></tr>`).join("")}</tbody></table></div>
 <form id="assign" class="row"><label>Change a test account<select name="tester_id">${opts(tests)}</select></label><label>Style<select name="style">${styles}</select></label><label>Memory<select name="memory">${memories}</select></label><button ${tests.length ? "" : "disabled"}>Save</button></form>
 <form id="reset"><label>Reset a test account's memory<select name="tester_id">${opts(tests)}</select></label><label>Style<select name="style">${styles}</select></label><label>Type RESET MEMORY<input name="confirmation" required></label><button class="danger" ${tests.length ? "" : "disabled"}>Reset memory</button></form></details>
 <details><summary>Saved conversations (${s.conversations.length})</summary><div class="table-wrap" role="region" aria-label="Study records" tabindex="0"><table><thead><tr><th>Person / style</th><th>Status</th><th>Notes</th><th>Review</th></tr></thead><tbody>${s.conversations.map((c) => `<tr><td>${esc((testerById.get(c.tester_id) || {}).study_id || c.tester_id)}<br>${esc(c.style)}</td><td>${esc(c.status)}</td><td>${esc(c.memory_status || "Not created")}</td><td><button class="quiet inspect" data-id="${esc(c.id)}">Inspect</button></td></tr>`).join("")}</tbody></table></div></details><div id="inspection"></div>
 <details><summary>Data downloads and deletion</summary><p class="muted">Both downloads contain the conditions. Never give them to the blind coders.</p><div class="panel row">${s.storage_mode === "temporary" ? '<p class="muted">Downloads are disabled in the temporary preview.</p>' : '<a class="button quiet" href="/api/admin/export_chats">One row per chat (CSV)</a><a class="button quiet" href="/api/admin/export">All records (JSON)</a>'}<button id="refresh" class="quiet">Refresh</button></div>
 <form id="delete"><label>Delete a person and all their records (withdrawal)<select name="tester_id">${opts(s.testers)}</select></label><label>Type DELETE TESTER<input name="confirmation" required></label><button class="danger">Delete records</button></form></details>`;
  document.querySelector("#enroll").onclick = async () => {
    if (busy) return;
    begin();
    try {
      const r = await api("admin/enroll", {});
      invitation = `Study ID: ${r.study_id}\nAccess code: ${r.code}\nFinal-form scenario: ${r.scenario}\n\nFirst session link:  ${base}/?visit=first\nUse-any-time link:   ${base}/\nFinal session link:  ${base}/?visit=final`;
      await adminPage();
    } catch (e) {
      announce(e.message);
    } finally {
      end();
    }
  };
  document.querySelector("#reissue").onsubmit = async (ev) => {
    ev.preventDefault();
    if (busy) return;
    begin();
    try {
      const r = await api("admin/reissue", values(ev.target));
      const output = document.querySelector("#replacement");
      output.textContent = `Existing account: ${r.study_id || r.id}\nReplacement access code: ${r.code}\nSave privately now. The old code no longer works.`;
      output.hidden = false;
      ev.target.reset();
    } catch (e) {
      announce(e.message);
    } finally {
      end();
    }
  };
  document.querySelector("#add-ids").onsubmit = async (ev) => {
    ev.preventDefault();
    if (busy) return;
    begin();
    try {
      const r = await api("admin/add_ids", {
        count: Number(values(ev.target).count),
      });
      announce(`Added ${r.added} study IDs (${r.first} to ${r.last}).`);
      await adminPage();
    } catch (e) {
      announce(e.message);
    } finally {
      end();
    }
  };
  document.querySelector("#pause-api").onclick = async () => {
    try {
      await api("admin/pause", { paused: !s.usage.paused });
      await adminPage();
    } catch (e) {
      announce(e.message);
    }
  };
  document.querySelector("#create").onsubmit = async (ev) => {
    ev.preventDefault();
    if (busy) return;
    begin();
    try {
      const r = await api("admin/create", values(ev.target));
      invitation = `Test account (not in the study)\nAccess code: ${r.code}`;
      await adminPage();
    } catch (e) {
      announce(e.message);
    } finally {
      end();
    }
  };
  document.querySelector("#assign").onsubmit = async (ev) => {
    ev.preventDefault();
    if (busy) return;
    begin();
    try {
      await api("admin/assign", values(ev.target));
      announce("Saved. The test account must sign in again.");
      await adminPage();
    } catch (e) {
      announce(e.message);
    } finally {
      end();
    }
  };
  document.querySelector("#handoff").onsubmit = async (ev) => {
    ev.preventDefault();
    if (busy) return;
    begin();
    try {
      await api("admin/handoff", values(ev.target));
      location.href = "/";
    } catch (e) {
      announce(e.message);
    } finally {
      end();
    }
  };
  document.querySelector("#refresh").onclick = load;
  for (const b of root.querySelectorAll(".inspect"))
    b.onclick = () => inspect(b.dataset.id);
  for (const action of ["reset", "delete"])
    document.querySelector("#" + action).onsubmit = async (ev) => {
      ev.preventDefault();
      if (busy) return;
      begin();
      try {
        await api("admin/" + action, values(ev.target));
        await adminPage();
        announce("Saved.");
      } catch (e) {
        announce(e.message);
      } finally {
        end();
      }
    };
  applyBusy();
}
async function inspect(id) {
  try {
    const x = await api("admin/inspect", { conversation_id: id });
    const el = document.querySelector("#inspection");
    el.innerHTML = `<section class="panel"><h2>Conversation inspection</h2><p class="meta">${esc(x.conversation.id)} · ${esc(x.conversation.style)} · ${esc(x.conversation.status)}</p><h2>Automatically generated notes</h2><pre>${esc(x.memory?.notes ? JSON.stringify(JSON.parse(x.memory.notes), null, 2) : "No ready notes. Status: " + (x.memory?.status || "not created"))}</pre>${x.memory && ["pending", "failed"].includes(x.memory.status) ? '<button id="retry-summary">Retry summary</button>' : ""}<details><summary>Read the source transcript</summary><div class="messages">${x.messages.map((m) => `<div class="message ${m.role === "user" ? "user" : ""}"><span class="speaker">${esc(m.role)} · ${esc(m.status)}</span>${esc(m.text)}</div>`).join("")}</div></details><details><summary>Memory source IDs and frozen prompt version</summary><pre>${esc(JSON.stringify({ memory_refs: JSON.parse(x.conversation.memory_refs), prompt_version: x.conversation.prompt_version }, null, 2))}</pre></details></section>`;
    if (document.querySelector("#retry-summary"))
      document.querySelector("#retry-summary").onclick = async (ev) => {
        ev.target.disabled = true;
        ev.target.textContent = "Preparing memory…";
        try {
          const r = await api("admin/retry", { conversation_id: id });
          if (r.warning) announce(r.warning);
          await adminPage();
          await inspect(id);
        } catch (e) {
          announce(e.message);
          await inspect(id);
        }
      };
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    announce(e.message);
  }
}
document.querySelector("#logout").onclick = async () => {
  try {
    await api("logout", {});
    pendingSend = null;
    location.href = isAdmin ? "/admin" : "/";
  } catch (e) {
    announce(e.message);
  }
};
load();
