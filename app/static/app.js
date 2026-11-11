"use strict";
// Study version: one neutral chatbot for every condition. The participant never sees the assigned style or memory.
const root = document.querySelector("#app");
const isAdmin = location.pathname === "/admin";
const params = new URLSearchParams(location.search);
let visit = ["first", "final"].includes(params.get("visit"))
  ? params.get("visit")
  : "home";
let screen = params.get("view") || (params.get("conversation_id") ? "chat" : visit !== "home" ? "start" : "home");
let adminScreen = "overview", adminSearch = "";
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
function setCurrent(id, push = false) {
  current = id;
  const q = new URLSearchParams();
  if (visit !== "home") q.set("visit", visit);
  if (id) q.set("conversation_id", id);
  if (screen !== "chat") q.set("view", screen);
  history[push ? "pushState" : "replaceState"](
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
  return `<label for="${name}-number">${label}</label><div class="slider"><span class="muted">0 Not at all</span><input id="${name}" type="range" min="0" max="100" step="1" value="50" aria-label="${label}"><span class="muted">100 Extremely</span></div><div class="rating-answer"><label for="${name}-number">Your answer (0–100)<input id="${name}-number" name="${name}" type="number" inputmode="numeric" min="0" max="100" step="1" placeholder="Choose a number" required></label><span class="help">Move the slider or type a number, including 50.</span></div>`;
}
function wireSlider(name) {
  const range = document.querySelector("#" + name), number = document.querySelector("#" + name + "-number");
  range.oninput = () => { number.value = range.value; };
  number.oninput = () => { if (number.value !== "" && number.validity.valid) range.value = number.value; };
}
function support() {
  const clean = (s) => esc(String(s || "").replace(/[.\s]+$/, ""));
  return `<p class="help">This chatbot is an AI and is not monitored live. If you feel very distressed: ${clean(state.support)}. Research team: ${clean(state.contact)}.</p>`;
}

function login() {
  document.querySelector("#logout").hidden = true;
  root.innerHTML = `<div class="eyebrow">AI SUPPORT · HCI STUDY</div><h1>${isAdmin ? "Researcher sign in" : "A little space to reflect."}</h1>${!isAdmin ? '<p class="intro">A research study about AI support for everyday stress. Use your study code to continue your conversations.</p>' : ""}<p class="muted">${isAdmin ? "Use the ADMIN_KEY from your private settings (Render Environment or local .env)." : "Enter the access code you received from the research team."}</p><form id="login" spellcheck="false"><label for="code">${isAdmin ? "Researcher secret" : "Access code"}</label><input id="code" name="code" inputmode="text" autocorrect="off" type="${isAdmin ? "password" : "text"}" autocomplete="off" autocapitalize="characters" required maxlength="200"><button>Sign in</button></form>${!isAdmin ? '<details class="login-help"><summary>Need your code or more information?</summary><p>Use the research contact on your invitation to request a replacement code. Please do not enroll again. Participation is voluntary; you can leave at any time. This is a research tool, not a clinical or emergency service.</p></details>' : ""}`;
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
    state = await api("state" + (current ? "?conversation_id=" + encodeURIComponent(current) : ""));
    document.querySelector("#logout").hidden = false;
    render();
    return true;
  } catch (e) {
    if (e.status === 401 || e.message === "Please sign in.") login();
    else if (e.message === "Conversation unavailable.") {
      screen = "home";
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
  const previous = document.querySelector(".messages");
  const keepPosition = previous && previous.dataset.conversation === current && previous.scrollHeight - previous.scrollTop - previous.clientHeight > 80;
  const oldPosition = previous?.scrollTop;
  renderContent();
  if (keepPosition && document.querySelector(".messages")) document.querySelector(".messages").scrollTop = oldPosition;
  applyBusy();
}
const dateLabel = (n) => n ? new Date(n * 1000).toLocaleString([], {dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Bangkok"}) : "—";
const visitLabel = (v) => ({first:"First guided visit",home:"Independent chat",final:"Final guided visit"}[v] || "Study chat");
const statusLabel = (c) => c.status === "open" ? "Ready to resume" : c.status === "completed" ? (c.rated ? "Complete" : "Questions pending") : "Ended early";
function go(view, id = null) {
  if (busy) return;
  const draft = document.querySelector("#text")?.value;
  if (draft?.trim() && !confirm("Your unsent draft will be lost. Sent messages remain saved. Leave this screen?")) return;
  screen = view; setCurrent(id, true); load().then(() => { root.focus(); root.scrollIntoView({block:"start"}); });
}
function shell() {
  root.innerHTML = `<div class="participant-top"><div><span class="eyebrow">YOUR STUDY SPACE</span><p class="identity">${state.study_id ? "Study ID " + esc(state.study_id) : "Team practice account"}</p></div><span class="badge">${state.storage_mode === "temporary" ? "Temporary preview" : "Private study account"}</span></div>
  <nav class="participant-nav" aria-label="Study navigation">${[["home","Home"],["chats","Conversations"],["study","Study activities"],["help","Help & privacy"]].map(([v,l])=>`<button class="nav-item ${screen===v ? "selected" : ""}" ${screen===v ? 'aria-current="page"' : ""} data-view="${v}">${l}</button>`).join("")}</nav>${banner(state.mode,state.storage_mode)}`;
  root.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>go(b.dataset.view));
}
function cards(list) {
  return list.map(c=>`<button class="conversation-card quiet" data-chat="${esc(c.id)}"><span><strong>${esc(c.title || "Session " + c.number)}</strong><small>${esc(dateLabel(c.started))} · ${visitLabel(c.chat_type)}</small></span><span class="badge ${c.status==="open" ? "active" : ""}">${statusLabel(c)}</span></button>`).join("");
}
function wireCards() {
  root.querySelectorAll("[data-chat]").forEach(b=>b.onclick=async()=>{
    try { await api("action",{action:"archive_view",conversation_id:b.dataset.chat}); go("chat",b.dataset.chat); }
    catch(e){announce(e.message);}
  });
}
function materialLinks() {
  const m=state.study_materials||{};
  return `${m.instructions ? `<section class="panel"><h2>From your research team</h2><p class="material-instructions">${esc(m.instructions)}</p></section>` : ""}${m.baseline_url || m.final_url ? `<section class="panel"><h2>Study questionnaires</h2><p>Use these at the times your researcher instructs. Opening a form does not record completion in this app. Please do not enter final assessment tasks before your scheduled visit.</p><div class="row">${[[m.baseline_url,"Baseline questionnaire"],[m.final_url,"Final questionnaire"]].filter(([url])=>url).map(([url,label])=>`<a class="button quiet" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`).join("")}</div></section>` : ""}`;
}
function renderContent() {
  if (pendingRatings && state.pending_rating !== pendingRatings.conversation_id) {
    pendingRatings=null; thanks=true; screen="home"; visit="home"; setCurrent(null);
  }
  if (!state.conversation || state.conversation.status !== "open") pendingSend=null;
  shell();
  if (screen === "help") {
    append(`<div class="page-heading"><span class="eyebrow">YOU ARE IN CONTROL</span><h1>Help & privacy</h1><p class="intro">Understand what is saved, what the AI can use, and how to get help.</p></div>
    <section class="panel"><h2>Need support?</h2>${support()}<p>This service is not monitored live. Use your study information sheet for the team's response times and support procedure.</p></section>
    <section class="panel"><h2>Saved records and AI recall are different</h2><p>In persistent storage, the research team retains sent conversations and ratings under your study code until ${esc(state.delete_date)}. Different study settings may give the chatbot notes from eligible earlier chats, or only the current conversation. A saved transcript does not mean the AI automatically reads it. Reopening a transcript does not send it to the AI.</p><p>The chatbot can make mistakes. You can correct a detail during an open conversation. Messages and eligible notes are processed by OpenAI for live replies. Please avoid names and identifying details.</p></section>
    <section class="panel"><h2>Taking a break or withdrawing</h2><p>Pause and leave keeps your sent conversation available to resume. Finish closes it and asks the post-chat questions. End early closes it without creating recall notes; it does not delete saved records.</p><p>To withdraw or request deletion, contact ${esc(state.contact)} using the details on your invitation. The team must also handle external forms and downloaded copies. You never need to finish a conversation to leave.</p></section>`); return;
  }
  if (state.suspended) { append(`<h1>Your study access is paused</h1><p>Please contact the research team before continuing.</p>${support()}`); return; }
  if (!state.consented) {
    append(`<span class="eyebrow">BEFORE YOUR FIRST CONVERSATION</span><h1>A moment to understand the study.</h1><p class="intro">You will chat with an AI about mild everyday stress, such as study pressure or a small disagreement.</p><section class="panel"><h2>Your participation</h2><p>Follow the visit schedule on your study invitation. You can stop at any time. Please do not share real names, contact details or anything very serious.</p><h2>Your information</h2><p>Your chats and short ratings are stored under your study code, not your name, and only the research team can read them. Messages are processed by OpenAI to create replies. Different participants may use slightly different chatbot settings; this is explained at the end of the study. You can ask the research team to delete your records. Planned deletion date: ${esc(state.delete_date)}.</p>${support()}</section><form id="consent">${[["adult","I am 18 or older and comfortable chatting in English."],["mild","I will only talk about mild, everyday topics."],["voluntary","I understand I can stop at any time."],["data_consent","I agree to my chats and ratings being stored and analysed as described."]].map(([k,l])=>`<label class="check"><input name="${k}" type="checkbox" required><span>${l}</span></label>`).join("")}<button>Agree and continue</button></form>`);
    document.querySelector("#consent").onsubmit=ev=>{ev.preventDefault();act("consent",values(ev.target));}; return;
  }
  const list=state.conversations || [], c=state.conversation;
  if (screen === "study") {
    const first=list.some(x=>x.chat_type==="first" && x.status==="completed" && x.rated);
    const final=list.some(x=>x.chat_type==="final" && x.status==="completed" && x.rated);
    const home=list.filter(x=>x.chat_type==="home" && x.status==="completed" && x.rated).length;
    append(`<span class="eyebrow">YOUR PARTICIPATION</span><h1>One step at a time.</h1><p class="intro">This shows the records saved in this app. Use your invitation for visit dates, required independent chats, and external questionnaires.</p><ol class="activity-list"><li><span class="badge active">Complete</span><h2>Study information & consent</h2><p>You have agreed to participate. You can review the information in Help & privacy.</p></li><li><span class="badge">${first ? "Recorded" : "Not recorded yet"}</span><h2>First guided visit</h2><p>Open the first-visit link provided by your researcher.</p></li><li><span class="badge">${home} completed</span><h2>Independent conversations</h2><p>Follow the number and dates agreed with your researcher. Optional chats are not proof that all study requirements are complete.</p></li><li><span class="badge">${final ? "Recorded" : "Not recorded yet"}</span><h2>Final guided visit & assessment</h2><p>Use your final-visit link and complete the separate final activities as instructed. This app does not verify external forms or the unaided task.</p></li></ol>${materialLinks()}`); return;
  }
  if (screen === "chats") {
    append(`<span class="eyebrow">YOUR CONVERSATION MAP</span><h1>Conversations</h1><p class="intro">Resume an open session or read a saved conversation. Completed sessions are read-only.</p>${list.length ? cards(list) : '<section class="empty-state"><h2>Your space starts here.</h2><p>Your conversations will appear here after you start a session.</p></section>'}`); wireCards(); return;
  }
  if (screen === "home" || !["chat","start","ratings"].includes(screen)) {
    append(`<span class="eyebrow">WELCOME BACK</span><h1>Space to pause.<br>Room to think.</h1><p class="intro">Your conversations and study activities, all in one place.</p>${thanks || (!state.open_conversation && list[0]?.rated) ? '<section class="saved"><h2>This session is complete.</h2><p>Your answers are saved. You can leave now; follow your invitation for your next study activity.</p></section>' : ''}
    <section class="next-card"><span class="eyebrow">YOUR NEXT STEP</span>${state.pending_rating ? '<h2>A quick check-in remains</h2><p>Three questions about your last finished conversation.</p><button id="open-ratings">Complete check-in</button>' : state.open_conversation ? '<h2>Pick up where you left off</h2><p>Your sent messages are saved. Resume your current conversation whenever you are ready.</p><button id="resume-chat">Resume conversation</button>' : '<h2>Ready for a conversation?</h2><p>Choose a mild concern from your day. We will ask a quick question before you begin.</p><button id="begin-start">Start a conversation</button>'}</section>
    <div class="section-heading"><h2>Recent conversations</h2><button class="text-button" id="all-chats">View all</button></div>${list.length ? cards(list.slice(0,3)) : '<p class="empty-state">No conversations yet. Your sessions will appear here.</p>'}<p class="help">This is a research tool for everyday stress, not a clinical or emergency service. Help & privacy is always available above.</p>`);
    document.querySelector("#begin-start")?.addEventListener("click",()=>go("start"));
    document.querySelector("#resume-chat")?.addEventListener("click",()=>go("chat",state.open_conversation));
    document.querySelector("#open-ratings")?.addEventListener("click",()=>go("ratings"));
    document.querySelector("#all-chats").onclick=()=>go("chats"); wireCards(); return;
  }
  if (screen === "ratings" || (screen === "start" && state.pending_rating)) {
    if (!state.pending_rating) {screen="home";renderContent();return;}
    const rated=list.find(x=>x.id===state.pending_rating);
    append(`<span class="eyebrow">SESSION CHECK-IN</span><h1>Three quick questions</h1><p class="muted">${rated ? 'Session '+rated.number+' · '+dateLabel(rated.started) : 'About the chat you just finished.'}</p><form id="rate">${slider("post_distress","How upset do you feel about the situation now?")}${scale7("support_needed","The chatbot gave me the kind of support I needed.")}${scale7("felt_understood","I felt understood by the chatbot.")}<button>Save answers</button></form><p class="help">You can leave and return. These answers are required before another study chat; submitted answers are saved once.</p>`);
    wireSlider("post_distress");
    if (pendingRatings?.conversation_id===state.pending_rating) {
      const input=document.querySelector("#post_distress");input.value=pendingRatings.post_distress;input.oninput();
      for(const name of ["support_needed","felt_understood"]) document.querySelector(`input[name="${name}"][value="${pendingRatings[name]}"]`)?.click();
    }
    document.querySelector("#rate").onsubmit=ev=>{ev.preventDefault();const f=ev.target;rate({post_distress:Number(f.querySelector("#post_distress-number").value),support_needed:Number(f.querySelector('[name=support_needed]:checked')?.value)||null,felt_understood:Number(f.querySelector('[name=felt_understood]:checked')?.value)||null});}; return;
  }
  if (screen === "start") {
    if (state.open_conversation) { screen="chat";setCurrent(state.open_conversation);load();return; }
    append(`<span class="eyebrow">${visitLabel(visit)}</span><h1>Before we begin.</h1><p class="intro">Think about something mildly stressful from your day or week. You do not need to have the right words.</p><p>Both you and the chatbot can use the current conversation. Earlier-chat recall depends on the study settings; saved history and AI recall are different.</p><form id="start">${slider("pre_distress","How upset do you feel about it right now?")}<button ${state.mode==="setup" ? "disabled" : ""}>Start chat</button></form>${support()}`);
    wireSlider("pre_distress");
    if (pendingPre!==null){const input=document.querySelector("#pre_distress");input.value=pendingPre;input.oninput();}
    document.querySelector("#start").onsubmit=ev=>{ev.preventDefault();startChat(Number(ev.target.querySelector("#pre_distress-number").value));};return;
  }
  if (!c) {screen="home";renderContent();return;}
  const open=c.status==="open";
  append(`<div class="session-heading"><div><span class="eyebrow">${visitLabel(c.chat_type)}</span><h1>${esc(c.title || "Session " + c.number)}</h1><p class="muted">${dateLabel(c.started)} (Bangkok) · <span class="badge ${open ? "active" : ""}">${open ? "In progress" : "Read-only · "+statusLabel(list.find(x=>x.id===c.id)||c)}</span></p></div><button class="quiet" id="rename-chat">Edit title</button></div><p class="save-status">${state.storage_mode==="temporary" ? "Temporary preview · sent messages are not retained after sign-out." : "Sent messages are saved. Unsent drafts stay only on this screen."}</p>`);
  const saved=state.messages.find(m=>m.role==="user" && m.request_id===pendingSend?.id);
  if (pendingSend && (pendingSend.conversation_id!==current || saved?.status==="success")) pendingSend=null;
  const local=pendingSend && !saved ? {role:"user",text:pendingSend.text,status:"failed",request_id:pendingSend.id} : null;
  const messages=local ? [...state.messages,local] : state.messages;
  const unfinished=messages.find(m=>m.role==="user" && m.status!=="success");
  append(`<div class="messages" data-conversation="${esc(c.id)}" role="log" aria-label="Conversation messages" aria-live="polite">${messages.map(m=>`<div class="message ${m.role==="user" ? "user" : ""} ${m.status!=="success" ? "failed" : ""}"><span class="speaker">${m.role==="user" ? "You" : "Chatbot"}${m.status!=="success" ? " · reply not received" : ""}</span>${esc(m.text)}</div>`).join("")}</div>`);
  document.querySelector("#rename-chat").onclick=()=>{
    document.querySelector("#title-editor")?.remove();
    append(`<form id="title-editor" class="panel"><label>Optional title (avoid names)<input name="title" maxlength="80" value="${esc(c.title)}"></label><button>Save title</button></form>`);
    document.querySelector("#title-editor").onsubmit=ev=>{ev.preventDefault();act("rename",{title:ev.target.title.value});};
    document.querySelector("#title-editor input").focus();
  };
  if (!open) {append(`<p class="help">This conversation is closed. Reading it does not send it to the chatbot.</p><button id="back-home">Return home</button>`);document.querySelector("#back-home").onclick=()=>go("home");return;}
  pendingPre=null;
  const need=state.min_messages||1,enough=state.turns>=need;
  append(`<form id="send" class="composer"><label class="sr-only" for="text">Your message</label><textarea id="text" maxlength="1500" rows="2" placeholder="Type at your own pace…" ${unfinished ? "disabled" : ""} required></textarea><button ${unfinished || state.turns>=20 ? "disabled" : ""}>Send</button></form>${unfinished ? '<p class="error">Your last message needs a reply. Retry uses the same message without saving a duplicate. <button class="text-button" id="retry">Try again</button></p>' : ''}
  <div class="chat-actions"><button id="pause-chat" class="quiet">Pause and leave</button><button id="finish" ${unfinished || !enough ? "disabled" : ""}>Finish chat</button></div>${!enough ? `<p class="help">${need>1 ? 'This guided session asks for at least '+need+' messages' : 'Send a message before finishing'} (${state.turns} sent). You can pause or end early at any time.</p>` : ''}${state.turns>=18 ? '<p class="help">You are near the 20-message limit. Please finish when ready.</p>' : ''}
  <details class="conversation-options"><summary>Correct a detail or end early</summary><form id="correction"><label for="correction-text">What should the chatbot understand differently?</label><textarea id="correction-text" name="correction" maxlength="1000" required></textarea><p class="help">This adds your correction to the conversation and excludes any earlier-chat notes supplied to this session from future recall. Original transcripts remain saved. It does not generate a new reply or count toward the message minimum.</p><button class="quiet" ${unfinished ? "disabled" : ""}>Save correction</button></form><p>End early closes this chat. It cannot be resumed and does not create recall notes. Saved records remain.</p><button id="stop" class="danger">End early</button></details><p class="help">AI support for everyday stress · not monitored live. Help & privacy is available above.</p>`);
  document.querySelector("#send").onsubmit=ev=>{ev.preventDefault();const t=document.querySelector("#text").value;if(t.trim())send(t,crypto.randomUUID());};
  document.querySelector("#text").onkeydown=ev=>{if(ev.key==="Enter"&&!ev.shiftKey&&!ev.isComposing){ev.preventDefault();document.querySelector("#send").requestSubmit();}};
  if(unfinished)document.querySelector("#retry").onclick=()=>send(unfinished.text,unfinished.request_id,true);
  document.querySelector("#finish").onclick=()=>act("finish");
  document.querySelector("#pause-chat").onclick=()=>go("home");
  document.querySelector("#stop").onclick=()=>{if(confirm("End this conversation early? Sent messages remain saved, but this chat cannot be resumed."))act("stop",{},true);};
  document.querySelector("#correction").onsubmit=ev=>{ev.preventDefault();act("correct_detail",{correction:ev.target.correction.value});};
  const box=document.querySelector(".messages");box.scrollTop=box.scrollHeight;
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
    screen = "chat";
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
    screen = "home";
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
      screen = action === "finish" ? "ratings" : "home";
      setCurrent(null);
    }
    if (r.warning && !state.participant) announce(r.warning);
    await load();
    if (["consent", "finish", "stop"].includes(action)) {root.focus();root.scrollIntoView({block:"start"});}
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
 <section class="panel"><h2>Enroll a participant</h2><p class="muted">Create a new study ID and access code when the participant arrives. No preloaded participant list is needed. Assignment stays locked after enrollment.</p>${!s.enrollment_ready ? '<p class="error">The administrator must configure study settings before enrollment. Open Allocation to define labels and targets.</p>' : ''}<form id="enrollment-options"><label>Assignment method<select name="mode" id="assignment-method"><option value="random">Randomized assignment (recommended)</option>${s.role==='facilitator' ? '' : '<option value="manual">Manual assignment (recorded exception)</option>'}</select></label><div id="manual-fields" hidden><label>Setting<select name="setting">${(s.allocation?.groups||[]).map(g=>`<option value="${esc(g.id)}">${esc(g.label)}</option>`).join('')}</select></label><label>Reason for manual assignment<textarea name="reason" maxlength="1000" placeholder="Explain this pilot assignment or protocol exception"></textarea></label></div><button id="enroll" ${s.enrollment_ready && s.storage_mode!=='temporary' ? '' : 'disabled'}>Create participant</button></form><pre id="invitation">${invitation ? esc(invitation) : "New participant details will appear here once. Save the code privately."}</pre></section>
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
 <details><summary>Saved conversations (${s.conversations.length})</summary><div class="table-wrap" role="region" aria-label="Study records" tabindex="0"><table><thead><tr><th>Person / style</th><th>Status</th><th>Notes</th><th>Review</th></tr></thead><tbody>${s.conversations.map((c) => `<tr><td>${esc((testerById.get(c.tester_id) || {}).study_id || c.tester_id)}<br>${esc(c.style || "Condition concealed")}</td><td>${esc(c.status)}</td><td>${esc(c.memory_status || "Not created")}</td><td>${s.role === "facilitator" ? "Metadata only" : `<button class="quiet inspect" data-id="${esc(c.id)}">Inspect</button>`}</td></tr>`).join("")}</tbody></table></div></details><div id="inspection"></div>
 <details><summary>Data downloads and deletion</summary><p class="muted">Both downloads contain the conditions. Never give them to the blind coders.</p><div class="panel row">${s.storage_mode === "temporary" ? '<p class="muted">Downloads are disabled in the temporary preview.</p>' : '<a class="button quiet" href="/api/admin/export_chats">One row per chat (CSV)</a><a class="button quiet" href="/api/admin/export">All records (JSON)</a>'}<button id="refresh" class="quiet">Refresh</button></div>
 <form id="delete"><label>Delete a person and all their records (withdrawal)<select name="tester_id">${opts(s.testers)}</select></label><label>Type DELETE TESTER<input name="confirmation" required></label><button class="danger">Delete records</button></form></details>`;
  document.querySelector("#assignment-method").onchange=ev=>{document.querySelector("#manual-fields").hidden=ev.target.value!=="manual";};
  document.querySelector("#enrollment-options").onsubmit = async (ev) => {
    ev.preventDefault();
    if (busy) return;
    begin();
    try {
      const r = await api("admin/enroll", values(document.querySelector("#enrollment-options")));
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
  organizeResearcher(s);
  applyBusy();
}
function buildAllocation(pane,s) {
  if(s.role==='facilitator') {pane.hidden=true;return;}
  const groups=s.allocation?.groups||[];
  const max=Math.max(1,...groups.map(g=>g.target||g.count));
  pane.innerHTML=`<span class="eyebrow">ADMINISTRATOR · CONDITION INFORMATION</span><h2 class="display-heading">Study settings & allocation</h2><p>Define names and enrollment targets for your four experimental settings. Participants do not see these labels. Changes do not reassign enrolled people.</p><p>Use randomized assignment for the main study. Manual choices are logged with a reason. Keep this page away from blind coders and facilitators who must not see conditions.</p>
  <form id="allocation-plan" class="panel"><h2>Configure settings</h2><div class="allocation-settings">${groups.map((g,i)=>`<fieldset><legend>${esc(g.style==='reassure'?'Reassure':'Guide')} × ${g.memory==='persistent'?'Persistent':'Fresh'}</legend><label>Setting label<input name="label-${i}" maxlength="80" required value="${esc(g.label)}"></label><label>Enrollment target<input type="number" name="target-${i}" min="1" max="1000" required value="${g.target||''}" placeholder="Enter target"></label></fieldset>`).join('')}</div><p>All four combinations remain part of the existing 2×2 design. Targets count all issued assignments, including people whose account was later removed; they are not a target for selecting only completers. Targets are caps, not randomization weights. Use equal targets for a balanced study and finalize the plan before collection.</p><button>Save study settings</button></form>
  <section class="panel"><h2>Participants by setting</h2><p>Bars show current participant accounts against a common scale of ${max}. Team practice accounts are excluded. Select a setting to see its study IDs.</p><div class="allocation-chart">${groups.map(g=>`<div class="allocation-bar"><button class="text-button" data-setting-filter="${esc(g.id)}">${esc(g.label)}</button><meter min="0" max="${max}" value="${g.count}" aria-label="${esc(g.label)}: ${g.count} current participants"></meter><span><strong>${g.count}</strong> current · ${g.assigned_total} ever assigned${g.target ? ' · target '+g.target : ''}</span></div>`).join('')}</div><button class="quiet" id="show-all-settings">Show all participants</button></section>
  <section class="panel"><h2 id="allocation-roster-heading">Participants in all settings</h2><div class="table-wrap"><table><thead><tr><th>Study ID</th><th>Setting</th><th>Consent</th><th>Access</th></tr></thead><tbody id="allocation-members"></tbody></table></div></section>`;
  function roster(key=null){
    const selected=key ? groups.filter(g=>g.id===key) : groups;
    document.querySelector('#allocation-roster-heading').textContent=key ? 'Participants in '+selected[0].label : 'Participants in all settings';
    document.querySelector('#allocation-members').innerHTML=selected.flatMap(g=>g.participants.map(p=>`<tr><td>${esc(p.study_id)}</td><td>${esc(g.label)}</td><td>${p.consent?'Recorded':'Pending'}</td><td>${p.suspended?'Paused':'Active'}</td></tr>`)).join('')||'<tr><td colspan="4">No participants in this selection.</td></tr>';
  }
  roster();pane.querySelectorAll('[data-setting-filter]').forEach(b=>b.onclick=()=>roster(b.dataset.settingFilter));document.querySelector('#show-all-settings').onclick=()=>roster();
  document.querySelector('#allocation-plan').onsubmit=async ev=>{ev.preventDefault();if(busy)return;begin();try{const f=ev.target;await api('admin/enrollment_plan',{groups:groups.map((g,i)=>({style:g.style,memory:g.memory,label:f.elements.namedItem('label-'+i).value,target:Number(f.elements.namedItem('target-'+i).value)}))});announce('Study settings saved. Enrollment is ready.');await adminPage();}catch(e){announce(e.message);}finally{end();}};
}
function organizeResearcher(s) {
  root.classList.add("research-workspace");
  const enrollment=document.querySelector("#enroll").closest("section");
  const people=document.querySelector("#handoff").closest("section");
  const recovery=document.querySelector("#reissue").closest("details");
  const usage=document.querySelector("#pause-api").closest("details");
  const testing=document.querySelector("#create").closest("details");
  const sessions=root.querySelector(".inspect")?.closest("details") || [...root.children].find(x=>x.tagName==="DETAILS"&&x.textContent.includes("Saved conversations"));
  const exports=document.querySelector("#delete").closest("details");
  const inspection=document.querySelector("#inspection");
  const nav=document.createElement("nav");nav.className="research-nav";nav.setAttribute("aria-label","Researcher navigation");
  const pages=[["overview","Overview"],["allocation","Allocation"],["participants","Participants"],["sessions","Sessions"],["quality","Data quality"],["exports","Exports & withdrawal"],["settings","Settings & testing"]];
  nav.innerHTML=pages.map(([k,l])=>`<button class="nav-item ${adminScreen===k?'selected':''}" data-admin-page="${k}" ${adminScreen===k?'aria-current="page"':''}>${l}</button>`).join("");
  root.querySelector("h1").insertAdjacentElement("beforebegin",nav);
  const panes={};for(const [k,l] of pages){const pane=document.createElement("section");pane.dataset.adminPane=k;pane.hidden=adminScreen!==k;panes[k]=pane;root.append(pane);}
  panes.participants.append(enrollment,people,recovery);
  buildAllocation(panes.allocation,s);
  panes.sessions.append(sessions,inspection);
  panes.exports.append(exports);
  panes.settings.append(usage,testing);
  const materialForm=document.createElement("form");materialForm.id="study-materials";materialForm.className="panel";
  materialForm.innerHTML=`<h2>Participant instructions & questionnaires</h2><p>Enter the approved schedule and links. These are shared identically across conditions. Completion of external forms is verified separately.</p><label>Study instructions<textarea name="instructions" maxlength="3000" rows="5">${esc(s.study_materials?.instructions||"")}</textarea></label><label>Baseline questionnaire URL<input type="url" name="baseline_url" value="${esc(s.study_materials?.baseline_url||"")}" placeholder="https://…"></label><label>Final questionnaire URL<input type="url" name="final_url" value="${esc(s.study_materials?.final_url||"")}" placeholder="https://…"></label><button>Save study materials</button>`;
  panes.settings.prepend(materialForm);
  if (s.role === "facilitator") {
    for(const k of ["exports","settings","allocation"]) { panes[k].hidden=true;nav.querySelector(`[data-admin-page="${k}"]`).hidden=true; }
    if (["exports","settings"].includes(adminScreen)) adminScreen="overview";
    document.querySelector("#handoff").hidden=true;
    document.querySelector("#handoff").nextElementSibling.hidden=true;

    root.querySelector("h1").insertAdjacentHTML("afterend",'<p class="badge">Facilitator access · allocation, transcripts, exports and settings are restricted</p>');
  }
  materialForm.onsubmit=async ev=>{ev.preventDefault();if(busy)return;begin();try{await api("admin/materials",values(ev.target));announce("Study instructions and questionnaire links saved.");}catch(e){announce(e.message);}finally{end();}};
  const participants=s.testers.filter(x=>x.locked), chats=s.conversations.filter(x=>participants.some(p=>p.id===x.tester_id));
  const missing=chats.filter(c=>c.status==="completed"&&!c.rated);
  const failures=s.conversations.filter(c=>["failed","pending"].includes(c.memory_status));
  panes.overview.innerHTML=`<span class="eyebrow">STUDY OPERATIONS</span><h2 class="display-heading">A clear view of your study.</h2><p class="intro">Check progress, follow up on incomplete activities, and keep the experience running smoothly.</p><div class="metric-grid">${[[participants.length,"Enrolled"],[chats.filter(c=>c.status==="completed").length,"Finished study chats"],[missing.length,"Check-ins pending"],[failures.length,"Notes needing attention"]].map(([n,l])=>`<div class="metric"><strong>${n}</strong><span>${l}</span></div>`).join("")}</div><section class="next-card"><h2>Next actions</h2><p>${missing.length ? missing.length+' finished study chats need post-chat answers.' : 'No missing post-chat answers in the current study records.'}</p><p>${failures.length ? failures.length+' summaries need inspection or retry.' : 'No pending or failed summary jobs.'}</p><p>${participants.filter(p=>!p.consent).length} enrolled participants have not completed consent.</p><button class="quiet" data-open-admin="quality">Review data quality</button></section><section class="panel"><h2>Current release</h2><p>${esc(s.mode)} · ${esc(s.storage_mode)} · ${esc(s.database_backend)} · ${esc(s.model)}</p><p>The page has read the database successfully. This does not verify the live AI provider, external forms, or backup recovery.</p><p>${s.usage.paused ? 'AI requests are paused.' : 'AI requests are enabled.'} Enrollment settings ${s.enrollment_ready ? "configured" : "not configured"}.</p></section>`;
  const personLabel=id=>s.testers.find(p=>p.id===id)?.study_id || "Team practice account";
  panes.quality.innerHTML=`<span class="eyebrow">RECORD COMPLETENESS</span><h2 class="display-heading">Things to follow up.</h2><p>These checks use saved app records. Check external questionnaires, scheduling, and withdrawal requests against your private study log.</p><div class="quality-grid"><section class="panel"><h2>Post-chat questions (${missing.length})</h2>${missing.map(c=>`<p><strong>${esc(personLabel(c.tester_id))}</strong> · ${visitLabel(c.chat_type)} · ${dateLabel(c.started)}</p>`).join("")||'<p class="empty-state">All finished study chats have ratings.</p>'}</section><section class="panel"><h2>Summary jobs (${failures.length})</h2>${failures.map(c=>`<p>${esc(personLabel(c.tester_id))} · ${esc(c.memory_status)} ${s.role === "facilitator" ? "Ask the administrator to inspect" : `<button class="quiet quality-inspect" data-id="${esc(c.id)}">Inspect</button>`}</p>`).join("")||'<p class="empty-state">No summary jobs need attention.</p>'}</section></div><section class="panel"><h2>Interrupted or open study sessions</h2>${chats.filter(c=>c.status!=="completed").map(c=>`<p>${esc(personLabel(c.tester_id))} · ${visitLabel(c.chat_type)} · ${esc(c.status)} · ${dateLabel(c.started)}</p>`).join("")||'<p>No unfinished study chats recorded.</p>'}</section>`;
  function showPage(k){adminScreen=k;for(const [name,pane] of Object.entries(panes))pane.hidden=name!==k;nav.querySelectorAll("button").forEach(b=>{b.classList.toggle("selected",b.dataset.adminPage===k);if(b.dataset.adminPage===k)b.setAttribute("aria-current","page");else b.removeAttribute("aria-current");});root.querySelector("h1").tabIndex=-1;root.querySelector("h1").focus({preventScroll:true});}
  nav.querySelectorAll("button").forEach(b=>b.onclick=()=>{if(!busy)showPage(b.dataset.adminPage);});
  panes.overview.querySelector("[data-open-admin]").onclick=()=>showPage("quality");
  panes.quality.querySelectorAll(".quality-inspect").forEach(b=>b.onclick=()=>{showPage("sessions");sessions.open=true;inspect(b.dataset.id);});
  const search=document.createElement("label");search.innerHTML='Find a participant<input type="search" id="participant-search" placeholder="Study ID…" autocomplete="off">';
  people.querySelector(".table-wrap").before(search);
  const tableRows=[...people.querySelectorAll("tbody tr")];
  const searchInput=search.querySelector("input");searchInput.value=adminSearch;
  const filterRows=()=>{adminSearch=searchInput.value;tableRows.forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(adminSearch.toLowerCase()));};searchInput.oninput=filterRows;filterRows();
  tableRows.forEach((row,i)=>{const person=participants[i];if(!person)return;const cell=row.querySelector("td");const button=document.createElement("button");button.className="text-button";button.textContent=person.study_id;cell.replaceChildren(button);button.onclick=()=>{
    document.querySelector("#person-detail")?.remove();
    const detail=document.createElement("section");detail.id="person-detail";detail.className="panel";detail.tabIndex=-1;
    const timeline=chats.filter(c=>c.tester_id===person.id);
    detail.innerHTML=`<h2>${esc(person.study_id)} · participant record</h2><p>Enrolled ${dateLabel(person.created)} · ${person.consent ? 'Consent recorded '+dateLabel(person.consent) : 'Consent pending'}</p><p>Condition remains concealed in this roster. Transcript inspection and raw exports may reveal it.</p>${timeline.map(c=>`<div class="timeline-entry"><strong>${visitLabel(c.chat_type)}</strong><p>${dateLabel(c.started)} · ${esc(c.status)} · ${c.status==='completed' ? c.rated ? 'Ratings saved' : 'Ratings pending' : 'Not complete'}</p></div>`).join("")||'<p>No conversations yet.</p>'}<p>Dates and external assessments must be checked against the booking/form records.</p><button class="quiet" id="close-person">Close record</button>`;
    people.append(detail);detail.querySelector("button").onclick=()=>{detail.remove();button.focus();};detail.focus();
  };});
  if(sessions){sessions.open=true;const table=sessions.querySelector("table");if(table){table.querySelector("thead tr").insertAdjacentHTML("beforeend","<th>Visit & date</th><th>Ratings</th>");[...table.querySelectorAll("tbody tr")].forEach((r,i)=>{const c=s.conversations[i];if(c)r.insertAdjacentHTML("beforeend",`<td>${visitLabel(c.chat_type)}<br>${dateLabel(c.started)}</td><td>${c.status==='completed' ? c.rated ? 'Saved' : 'Pending' : '—'}</td>`);});}}
  exports.open=true;usage.open=true;testing.open=true;
}
async function inspect(id) {
  try {
    const x = await api("admin/inspect", { conversation_id: id });
    const el = document.querySelector("#inspection");
    el.innerHTML = `<section class="panel"><h2>Conversation inspection</h2><p class="meta">${esc(x.conversation.id)} · ${esc(x.conversation.style)} · ${esc(x.conversation.status)}</p><h2>Automatically generated notes</h2>${x.memory?.notes ? `<dl class="note-cards">${Object.entries(JSON.parse(x.memory.notes)).map(([key,value])=>`<div><dt>${esc({situation:"Reported situation",feelings:"Expressed feelings",user_insights:"User-endorsed ideas",bot_said:"Chatbot contributions"}[key]||key)}</dt><dd>${esc(value||"Not stated")}</dd></div>`).join("")}</dl>` : `<p>No ready notes. Status: ${esc(x.memory?.status||"not created")}</p>`}${x.memory && ["pending", "failed"].includes(x.memory.status) ? '<button id="retry-summary">Retry summary</button>' : ""}<details><summary>Read the source transcript</summary><div class="messages">${x.messages.map((m) => `<div class="message ${m.role === "user" ? "user" : ""}"><span class="speaker">${esc(m.role)} · ${esc(m.status)}</span>${esc(m.text)}</div>`).join("")}</div></details><details><summary>Memory source IDs and frozen prompt version</summary><pre>${esc(JSON.stringify({ memory_refs: JSON.parse(x.conversation.memory_refs), prompt_version: x.conversation.prompt_version }, null, 2))}</pre></details></section>`;
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
window.addEventListener("popstate", () => {
  const q=new URLSearchParams(location.search);
  visit=["first","final"].includes(q.get("visit")) ? q.get("visit") : "home";
  current=q.get("conversation_id");
  screen=q.get("view") || (current ? "chat" : visit!=="home" ? "start" : "home");
  load();
});
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
