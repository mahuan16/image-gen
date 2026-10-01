
const SERVER_URL = "http://localhost:8001";


const messagesEl  = document.getElementById("messages");
const userInput   = document.getElementById("user-input");
const sendBtn     = document.getElementById("send-btn");
const statusLabel = document.getElementById("status-label");
const clearBtn    = document.getElementById("clear-btn");

// ----------------- Auto-grow text area -----------------------
userInput.addEventListener("input", () => {
  userInput.style.height = "auto";
  userInput.style.height = Math.min(userInput.scrollHeight, 140) + "px";
});

userInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});

sendBtn.addEventListener("click", send);

clearBtn.addEventListener("click", () => {
  messagesEl.innerHTML = "";
});

// ---------------- Message helpers -------------

function addMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const label = document.createElement("div");
  label.className = "msg-role";
  label.textContent = role === "user" ? "you" : "agent";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  wrap.appendChild(label);
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  scrollBottom();
  return bubble;
}

function addTyping() {
  const wrap = document.createElement("div");
  wrap.className = "msg agent";
  wrap.id = "typing";

  const label = document.createElement("div");
  label.className = "msg-role";
  label.textContent = "agent";

  const bubble = document.createElement("div");
  bubble.className = "typing-bubble";
  bubble.innerHTML = "<span></span><span></span><span></span>";

  wrap.appendChild(label);
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  scrollBottom();
}

function removeTyping() {
  document.getElementById("typing")?.remove();
}

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function stripTrailingUrlPunctuation(text) {
  return text.replace(/[)\]\}.,!?:;]+$/g, "");
}

// check for URLS and make them <img> or <a>
function renderContent(bubble, text) {
  const urlRe = /(https?:\/\/[^\s<>"')\]]+)/g;
  const imgExts = /\.(png|jpg|jpeg|gif|webp)(\?[^\s]*)?$/i;
  const parts = text.split(urlRe);

  bubble.innerHTML = "";

  parts.forEach(part => {
    if (/^https?:\/\//i.test(part)) {
      const cleanUrl = stripTrailingUrlPunctuation(part);

      if (imgExts.test(cleanUrl)) {
        const img = document.createElement("img");
        img.src = cleanUrl;
        img.alt = "generated image";
        bubble.appendChild(img);
      } else {
        const a = document.createElement("a");
        a.href = cleanUrl;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = cleanUrl;
        a.style.color = "var(--accent-dim)";
        bubble.appendChild(a);
      }
    } else if (part) {
      bubble.appendChild(document.createTextNode(part));
    }
  });
}

// ------ Send & stream -------------------

async function send() {
  const text = userInput.value.trim();
  if (!text) return; // if the user sends nothing then just don't do anythning

  // reset ui so user cant spam messages
  userInput.value = "";
  userInput.style.height = "auto";
  sendBtn.disabled = true;
  statusLabel.textContent = "thinking…";

  // update screen to show the user's message
  addMessage("user", text);
  addTyping(); // t yping animation!

  // creating the message bubble for agent
  const agentWrap = document.createElement("div");
  agentWrap.className = "msg agent";
  const agentLabel = document.createElement("div");
  agentLabel.className = "msg-role";
  agentLabel.textContent = "agent";
  const agentBubble = document.createElement("div");
  agentBubble.className = "bubble";
  agentWrap.appendChild(agentLabel);
  agentWrap.appendChild(agentBubble);

  
  let fullText = "";
  let agentVisible = false;


  
  try {
    // post to server and get agent's response
    const resp = await fetch(`${SERVER_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!resp.ok) throw new Error(`Server returned ${resp.status}`);

    // gets the response chunk by chunk and converts to str
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();


    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      fullText += decoder.decode(value, { stream: true }); // add next chunk to displayed text

      // if the agent message hasn't loaded yet, then start displaying messages (get rid of typing anim)
      if (!agentVisible) {
        removeTyping(); 
        messagesEl.appendChild(agentWrap);
        agentVisible = true;
      }

      // render and keep screen scrolled to the bottom
      renderContent(agentBubble, fullText);
      scrollBottom();
    }

  } catch (err) {
    removeTyping();
    if (!agentVisible) messagesEl.appendChild(agentWrap);
    agentBubble.textContent = `!! Could not reach server: ${err.message}\n\nMake sure server.py is running at ${SERVER_URL}`;
    scrollBottom();
  }

  // prepare for next user message
  statusLabel.textContent = "connected";
  sendBtn.disabled = false; 
  userInput.focus();
}