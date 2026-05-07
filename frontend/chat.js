function getSelectedVoice() {
  const selected = document.querySelector('input[name="voice"]:checked');
  return selected ? selected.value : "she";
}

function extractMessagesFromResponse(data) {
  // Return an array of message objects: { text, audio }
  if (data.messages && Array.isArray(data.messages) && data.messages.length) {
    return data.messages.map(m => ({ text: m.text || "", audio: m.audio || null }));
  }
  if (data.reply) return [{ text: data.reply, audio: null }];
  if (data.text) return [{ text: data.text, audio: null }];
  return [{ text: "Echo could not interpret this response.", audio: null }];
}



async function send() {
  const dream = document.getElementById("dream").value;
  if (!dream.trim()) return;

  // Only show the loading message if the generation takes longer than 300ms
  let loadingTimer = setTimeout(() => showLoading('Echo is listening…'), 300);
  const payload = { dream, voice: getSelectedVoice() };
  console.log('Sending /dream with payload:', payload);
  const res = await fetch("/dream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  try {
    if (!res.ok) {
      console.log('Server responded with', res.status);
      return;
    }

    const data = await res.json();
    console.log("API response:", data);

    // Robust extraction of message objects (may include server audio)
    const msgs = extractMessagesFromResponse(data);
    msgs.forEach(m => addMessage(m));


  } catch (err) {
    addMessage("Echo couldn\'t respond this time.");
  } finally {
    clearTimeout(loadingTimer);
    hideLoading();
  }
}

function addMessage(obj) {
  const text = typeof obj === 'string' ? obj : (obj.text || '');
  const audio = obj && obj.audio ? obj.audio : null;
  const voice = getSelectedVoice();

  const chat = document.getElementById("chat");

  const msg = document.createElement("div");
  msg.className = "bot-message";

  const p = document.createElement("p");
  p.textContent = text;

  // Always show play button; server is the single source of truth for audio
  const play = document.createElement("button");
  play.textContent = "▶";
  play.onclick = () => {
    if (audio) {
      playAudio(audio);
    } else {
      alert("Voice not ready yet.");
    }
  };

  msg.appendChild(p);
  msg.appendChild(play);

  chat.appendChild(msg);

  chat.scrollTop = chat.scrollHeight;
}



function playAudio(path) {
  const audio = new Audio(path);
  audio.play();
}

// --- Loading indicator and UI locking ---
function showLoading(msg = 'Echo is listening…') {
  // Prevent multiple interactions
  const reflectBtn = document.querySelector('button[onclick="send()"]');
  const sendBtn = document.querySelector('button[onclick="sendChat()"]');
  const input = document.getElementById('chatInput');
  if (reflectBtn) reflectBtn.disabled = true;
  if (sendBtn) sendBtn.disabled = true;
  if (input) input.disabled = true;

  const loader = document.createElement('div');
  loader.id = 'loading';
  loader.innerText = msg;
  loader.style.opacity = '0.6';
  loader.style.fontStyle = 'italic';
  loader.style.margin = '8px 0';
  document.getElementById('chat').appendChild(loader);
  document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
}

function hideLoading() {
  const reflectBtn = document.querySelector('button[onclick="send()"]');
  const sendBtn = document.querySelector('button[onclick="sendChat()"]');
  const input = document.getElementById('chatInput');
  if (reflectBtn) reflectBtn.disabled = false;
  if (sendBtn) sendBtn.disabled = false;
  if (input) input.disabled = false;

  const loader = document.getElementById('loading');
  if (loader) loader.remove();
}

// --- Response parsing helpers & debug (temporary) ---
function extractTextsFromResponse(data) {
  if (data.messages && Array.isArray(data.messages) && data.messages.length) {
    return data.messages.map(m => m.text || "");
  }
  if (data.reply) return [data.reply];
  if (data.text) return [data.text];
  return ["Echo could not interpret this response."];
}



// --- Chat functions ---
function addUserMessage(text) {
  const chat = document.getElementById("chat");
  const msg = document.createElement("div");
  msg.className = "user-message";
  msg.textContent = text;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

async function sendChat() {
  const input = document.getElementById("chatInput");
  const text = input.value.trim();
  if (!text) return;

  addUserMessage(text);
  input.value = "";

  let loadingTimer = setTimeout(() => showLoading('Echo is listening…'), 300);
  const payload = { message: text, voice: getSelectedVoice() };
  console.log('Sending /chat with payload:', payload);
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  try {
    if (!res.ok) {
      console.log('Server responded with', res.status);
      // No placeholder messages — just stop the loader and return
      return;
    }

    const data = await res.json();
    console.log('API response:', data);

    const msgs = extractMessagesFromResponse(data);
    msgs.forEach(m => addMessage(m));


  } catch (err) {
    addMessage("Echo couldn\'t respond this time.");
  } finally {
    clearTimeout(loadingTimer);
    hideLoading();
  }
}

