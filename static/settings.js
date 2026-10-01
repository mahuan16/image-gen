const SERVER_URL = "http://localhost:8001";

let pendingChanges = {};

// ── Load & render servers ──────────────────────────────────────

async function loadServers() {
    const list = document.getElementById("server-list");
    try {
        const res = await fetch(`${SERVER_URL}/servers`);
        const servers = await res.json();
        renderServers(servers);
    } catch (e) {
        list.innerHTML = `<p class="settings-error">!! could not load servers: ${e.message}</p>`;
    }
}

function renderServers(servers) {
    const list = document.getElementById("server-list");
    list.innerHTML = "";

    if (servers.length === 0) {
        list.innerHTML = `<p class="settings-loading">no servers configured.</p>`;
        return;
    }

    servers.forEach((server, index) => {
        const card = document.createElement("div");
        card.className = `server-card ${server.enabled ? "active" : ""}`;
        card.innerHTML = `
            <div class="server-info">
                <div class="server-name">${server.name}</div>
                <div class="server-url">${server.url}</div>
                <div class="server-status ${server.enabled ? "on" : "off"}">
                    ${server.enabled ? "● enabled" : "○ disabled"}
                </div>
            </div>
            <div class="card-actions">
                <button class="remove-btn" data-index="${index}" title="remove server">✕</button>
                <label class="toggle">
                    <input type="checkbox" ${server.enabled ? "checked" : ""} data-index="${index}" />
                    <div class="toggle-track"></div>
                    <div class="toggle-thumb"></div>
                </label>
            </div>
        `;

        const checkbox = card.querySelector("input");
        checkbox.addEventListener("change", () => {
            const enabled = checkbox.checked;
            pendingChanges[index] = enabled;
            card.className = `server-card ${enabled ? "active" : ""}`;
            card.querySelector(".server-status").className = `server-status ${enabled ? "on" : "off"}`;
            card.querySelector(".server-status").textContent = enabled ? "● enabled" : "○ disabled";
            showApply();
        });

        const removeBtn = card.querySelector(".remove-btn");
        removeBtn.addEventListener("click", async () => {
            removeBtn.textContent = "…";
            removeBtn.disabled = true;
            try {
                await fetch(`${SERVER_URL}/servers/remove`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ index }),
                });
                showApply();
                loadServers();
            } catch (e) {
                removeBtn.textContent = "✕";
                removeBtn.disabled = false;
            }
        });

        list.appendChild(card);
    });
}

// ── Apply / restart ───────────────────────────────────────────

function showApply() {
    document.getElementById("reload-notice").classList.add("visible");
    document.getElementById("apply-btn").classList.add("visible");
}

document.getElementById("apply-btn").addEventListener("click", async () => {
    const btn = document.getElementById("apply-btn");
    btn.textContent = "applying…";
    btn.disabled = true;

    try {
        await fetch(`${SERVER_URL}/servers/toggle`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(pendingChanges),
        });

        pendingChanges = {};
        btn.textContent = "✓ applied — agent restarting";
        setTimeout(() => {
            btn.textContent = "apply & restart agent";
            btn.disabled = false;
            document.getElementById("reload-notice").classList.remove("visible");
            btn.classList.remove("visible");
            loadServers();
        }, 2000);
    } catch (e) {
        btn.textContent = "error — try again";
        btn.disabled = false;
    }
});

// ── Add server modal ──────────────────────────────────────────

const overlay    = document.getElementById("modal-overlay");
const addBtn     = document.getElementById("add-btn");
const cancelBtn  = document.getElementById("modal-cancel");
const confirmBtn = document.getElementById("modal-confirm");
const modalError = document.getElementById("modal-error");

addBtn.addEventListener("click", () => {
    overlay.classList.add("visible");
    document.getElementById("new-name").focus();
});

cancelBtn.addEventListener("click", closeModal);

overlay.addEventListener("click", e => {
    if (e.target === overlay) closeModal();
});

function closeModal() {
    overlay.classList.remove("visible");
    document.getElementById("new-name").value = "";
    document.getElementById("new-url").value = "";
    document.getElementById("new-instruct").value = "";
    modalError.textContent = "";
}

confirmBtn.addEventListener("click", async () => {
    const name     = document.getElementById("new-name").value.trim();
    const url      = document.getElementById("new-url").value.trim();
    const instruct = document.getElementById("new-instruct").value.trim();

    if (!name) { modalError.textContent = "name is required."; return; }
    if (!url)  { modalError.textContent = "url is required."; return; }

    confirmBtn.textContent = "adding…";
    confirmBtn.disabled = true;

    try {
        await fetch(`${SERVER_URL}/servers/add`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, url, instruct }),
        });

        closeModal();
        showApply();
        loadServers();
    } catch (e) {
        modalError.textContent = `error: ${e.message}`;
    } finally {
        confirmBtn.textContent = "add server";
        confirmBtn.disabled = false;
    }
});

loadServers();