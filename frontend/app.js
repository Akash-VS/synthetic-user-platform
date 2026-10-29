
/* ============================================================
   PERSONASTUDIO — COMPLETE app.js
   Dashboard | Personas | Generate | Research Lab
   ============================================================ */

/* 1. Configuration */

const API_BASE = (
    window.PERSONASTUDIO_API_BASE || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const $ = selector => document.querySelector(selector);

let personas = [];
let lastGenerated = null;

/* 2. Utilities */

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function displayValue(value) {
    if (value == null) return "";
    if (Array.isArray(value)) return value.map(displayValue).join(", ");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
}

function parseList(value) {
    if (Array.isArray(value)) return value;
    if (value == null || value === "") return [];
    if (typeof value === "object") return [value];

    return String(value)
        .split(/[,;\n]/)
        .map(item => item.trim())
        .filter(Boolean);
}

function getPersonaId(persona) {
    return persona?.persona_id ?? persona?.id;
}

function getStatus(persona) {
    return String(persona?.persona_status ?? persona?.status ?? "active")
        .toLowerCase();
}

function normalizeObject(data) {
    if (typeof data !== "string") return data;

    try {
        return JSON.parse(data);
    } catch {
        return { result: data };
    }
}

function normalizeListResponse(data) {
    if (Array.isArray(data)) return data;

    for (const key of ["personas", "items", "results", "data"]) {
        if (Array.isArray(data?.[key])) return data[key];
    }

    return [];
}

function humanize(key) {
    return String(key)
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, char => char.toUpperCase());
}

/* 3. API helper */

async function apiRequest(path, options = {}) {
    let response;

    try {
        response = await fetch(`${API_BASE}${path}`, {
            ...options,
            headers: {
                Accept: "application/json",
                ...(options.body ? { "Content-Type": "application/json" } : {}),
                ...options.headers
            }
        });
    } catch {
        throw new Error(
            `Cannot connect to ${API_BASE}. Check your backend URL, ` +
            "server status, and CORS configuration."
        );
    }

    const text = await response.text();
    let data = null;

    if (text) {
        try {
            data = JSON.parse(text);
        } catch {
            data = text;
        }
    }

    if (!response.ok) {
        const detail = data?.detail;

        const message = typeof detail === "string"
            ? detail
            : Array.isArray(detail)
                ? detail.map(item => item.msg || JSON.stringify(item)).join("; ")
                : typeof data === "string" && data.trim()
                    ? data
                    : `Request failed (${response.status})`;

        throw new Error(message);
    }

    return data;
}

/* 4. Notifications */

function showNotice(message, isError = false) {
    const notice = $("#notice");
    if (!notice) return;

    notice.textContent = message;
    notice.classList.toggle("error", isError);
    notice.classList.remove("hidden");

    clearTimeout(showNotice.timer);

    showNotice.timer = setTimeout(() => {
        notice.classList.add("hidden");
    }, 5000);
}

/* 5. Persona cards */

function initials(persona) {
    return String(persona?.persona_label || persona?.role || "UX")
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map(word => word[0]?.toUpperCase() || "")
        .join("");
}

function personaCard(persona) {
    const id = getPersonaId(persona);
    const archived = getStatus(persona) === "archived";
    const role = persona.role || "Role not specified";
    const label = persona.persona_label || persona.archetype || role;
    const goals = parseList(persona.goals);
    const skills = parseList(persona.skills ?? persona.relevant_skills);

    return `
        <article class="persona-card">
            <div class="persona-card-head">
                <div class="persona-avatar">${escapeHTML(initials(persona))}</div>
                <div class="persona-title">
                    <h3>${escapeHTML(label)}</h3>
                    <p>${escapeHTML(role)}</p>
                </div>
            </div>

            <p class="persona-summary">
                ${escapeHTML(goals[0] || persona.working_style || "No summary available.")}
            </p>

            <div class="tag-row">
                <span class="status-badge ${archived ? "archived" : ""}">
                    ${archived ? "Archived" : "Active"}
                </span>
                ${skills.slice(0, 3).map(skill => `
                    <span class="tag">${escapeHTML(displayValue(skill))}</span>
                `).join("")}
            </div>

            <div class="persona-actions">
                <button class="small-button" data-action="view"
                    data-id="${escapeHTML(id)}" type="button">View details</button>

                ${archived ? `
                    <button class="small-button" data-action="restore"
                        data-id="${escapeHTML(id)}" type="button">Restore</button>
                ` : `
                    <button class="small-button" data-action="edit"
                        data-id="${escapeHTML(id)}" type="button">Edit</button>
                    <button class="small-button danger" data-action="archive"
                        data-id="${escapeHTML(id)}" type="button">Archive</button>
                `}
            </div>
        </article>
    `;
}

function renderPersonaList(selector, list) {
    const container = $(selector);
    if (!container) return;

    container.innerHTML = list.length
        ? list.map(personaCard).join("")
        : `<div class="empty-state">No personas found.</div>`;
}

function renderStats() {
    if ($("#totalCount")) $("#totalCount").textContent = personas.length;

    if ($("#activeCount")) {
        $("#activeCount").textContent = personas.filter(
            persona => getStatus(persona) !== "archived"
        ).length;
    }

    if ($("#archivedCount")) {
        $("#archivedCount").textContent = personas.filter(
            persona => getStatus(persona) === "archived"
        ).length;
    }
}

function applyPersonaFilters() {
    const query = ($("#searchInput")?.value || "").trim().toLowerCase();
    const status = $("#statusFilter")?.value || "all";

    const filtered = personas.filter(persona => {
        const searchable = [
            persona.persona_label,
            persona.archetype,
            persona.role,
            persona.experience_level,
            persona.goals,
            persona.skills,
            persona.preferences,
            persona.challenges
        ].map(displayValue).join(" ").toLowerCase();

        return searchable.includes(query) &&
            (status === "all" || getStatus(persona) === status);
    });

    renderPersonaList("#allPersonas", filtered);
}

function renderAll() {
    renderStats();
    renderPersonaList("#recentPersonas", [...personas].reverse().slice(0, 3));
    applyPersonaFilters();
    populateResearchPersonas();
}

/* 6. Backend and persona loading */

async function checkBackend() {
    const dot = $("#statusDot");
    const label = $("#backendStatus");

    try {
        await apiRequest("/health");
        if (dot) dot.className = "status-dot online";
        if (label) label.textContent = "Backend online";
    } catch {
        if (dot) dot.className = "status-dot offline";
        if (label) label.textContent = "Backend offline";
    }
}

async function loadPersonas(showMessage = false) {
    try {
        const data = await apiRequest("/api/personas");
        personas = normalizeListResponse(data);
        renderAll();

        if (showMessage) showNotice("Persona library refreshed.");
    } catch (error) {
        const message = escapeHTML(error.message);

        if ($("#recentPersonas")) {
            $("#recentPersonas").innerHTML =
                `<div class="empty-state">${message}</div>`;
        }

        if ($("#allPersonas")) {
            $("#allPersonas").innerHTML =
                `<div class="empty-state">${message}</div>`;
        }

        showNotice(error.message, true);
    }
}

/* 7. Navigation */

function openView(viewName) {
    const titles = {
        dashboard: "Dashboard",
        generate: "Generate Persona",
        personas: "All Personas",
        research: "Research Lab"
    };

    document.querySelectorAll(".view").forEach(view => {
        view.classList.add("hidden");
    });

    $(`#${viewName}View`)?.classList.remove("hidden");

    document.querySelectorAll(".nav-item").forEach(button => {
        button.classList.toggle("active", button.dataset.view === viewName);
    });

    if ($("#pageTitle")) {
        $("#pageTitle").textContent = titles[viewName] || "Dashboard";
    }

    if (viewName === "personas") applyPersonaFilters();
    if (viewName === "research") populateResearchPersonas();
}

/* 8. Generate persona */

function renderGeneratedPersona(persona) {
    const container = $("#generatedResult");
    if (!container) return;

    const fields = [
        ["Skills", persona.skills ?? persona.relevant_skills],
        ["Goals", persona.goals],
        ["Preferences", persona.preferences],
        ["Challenges", persona.challenges],
        ["Working style", persona.working_style]
    ];

    container.innerHTML = `
        <article class="result-card">
            <span class="pill">✦ GENERATED PERSONA</span>
            <h2>${escapeHTML(persona.persona_label || persona.role || "New persona")}</h2>
            <p>${escapeHTML(persona.role || "")} · ${escapeHTML(persona.experience_level || "")}</p>

            <div class="result-grid">
                ${fields.map(([label, value]) => `
                    <div class="result-field">
                        <h4>${escapeHTML(label)}</h4>
                        <p>${escapeHTML(displayValue(value) || "Not provided")}</p>
                    </div>
                `).join("")}
            </div>

            <button class="primary-button" id="showLibraryButton" type="button">
                View persona library →
            </button>
        </article>
    `;

    container.classList.remove("hidden");

    $("#showLibraryButton")?.addEventListener("click", async () => {
        openView("personas");
        await loadPersonas();
    });
}

$("#generateForm")?.addEventListener("submit", async event => {
    event.preventDefault();

    const button = $("#generateButton");
    const original = button?.innerHTML || "Generate persona";

    if (button) {
        button.disabled = true;
        button.textContent = "Generating…";
    }

    try {
        const payload = {
            role: $("#role").value.trim(),
            experience: $("#experience").value,
            goal: $("#goal").value.trim()
        };

        const data = await apiRequest("/api/personas/generate", {
            method: "POST",
            body: JSON.stringify(payload)
        });

        lastGenerated = data?.persona || data;
        renderGeneratedPersona(lastGenerated);
        showNotice("Persona generated successfully.");
        await loadPersonas();
    } catch (error) {
        showNotice(error.message, true);
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = original;
        }
    }
});

/* 9. Persona details, editing and archiving */

function findPersona(id) {
    return personas.find(persona => String(getPersonaId(persona)) === String(id));
}

function openDetails(persona) {
    if (!persona) {
        showNotice("Persona not found.", true);
        return;
    }

    $("#dialogTitle").textContent =
        persona.persona_label || persona.archetype || persona.role || "Persona";

    const fields = [
        ["Role", persona.role],
        ["Experience level", persona.experience_level],
        ["Skills", persona.skills ?? persona.relevant_skills],
        ["Goals", persona.goals],
        ["Preferences", persona.preferences],
        ["Challenges", persona.challenges],
        ["Working style", persona.working_style],
        ["Behavioral traits", persona.behavioral_traits],
        ["Usability needs", persona.usability_needs],
        ["Status", getStatus(persona)]
    ];

    $("#dialogBody").innerHTML = fields.map(([label, value]) => `
        <div class="result-field" style="margin-bottom:10px">
            <h4>${escapeHTML(label)}</h4>
            <p>${escapeHTML(displayValue(value) || "Not provided")}</p>
        </div>
    `).join("");

    $("#detailsDialog")?.showModal();
}

function openEdit(persona) {
    if (!persona) return;

    $("#editId").value = getPersonaId(persona) ?? "";
    $("#editRole").value = persona.role || "";
    $("#editExperience").value = persona.experience_level || "";
    $("#editSkills").value = displayValue(persona.skills ?? persona.relevant_skills);
    $("#editGoals").value = displayValue(persona.goals);
    $("#editPreferences").value = displayValue(persona.preferences);
    $("#editChallenges").value = displayValue(persona.challenges);
    $("#editWorkingStyle").value = persona.working_style || "";

    $("#editDialog")?.showModal();
}

async function archivePersona(id) {
    const persona = findPersona(id);
    if (!persona) return showNotice("Persona not found.", true);

    if (!confirm(`Archive "${persona.persona_label || persona.role || "this persona"}"?`)) {
        return;
    }

    try {
        await apiRequest(`/api/personas/${encodeURIComponent(id)}/archive`, {
            method: "PATCH"
        });

        showNotice("Persona archived.");
        await loadPersonas();
    } catch (error) {
        showNotice(error.message, true);
    }
}

async function restorePersona(id) {
    try {
        await apiRequest(`/api/personas/${encodeURIComponent(id)}/restore`, {
            method: "PATCH"
        });

        showNotice("Persona restored.");
        await loadPersonas();
    } catch (error) {
        showNotice(error.message, true);
    }
}

document.addEventListener("click", async event => {
    const button = event.target.closest("[data-action]");
    if (!button) return;

    const id = button.dataset.id;
    const persona = findPersona(id);

    switch (button.dataset.action) {
        case "view":
            openDetails(persona);
            break;
        case "edit":
            if (persona && getStatus(persona) === "archived") {
                showNotice("Restore the persona before editing.", true);
            } else {
                openEdit(persona);
            }
            break;
        case "archive":
            await archivePersona(id);
            break;
        case "restore":
            await restorePersona(id);
            break;
    }
});

$("#editForm")?.addEventListener("submit", async event => {
    event.preventDefault();

    const id = $("#editId").value;

    const payload = {
        role: $("#editRole").value.trim(),
        experience_level: $("#editExperience").value.trim(),
        skills: parseList($("#editSkills").value),
        goals: parseList($("#editGoals").value),
        preferences: parseList($("#editPreferences").value),
        challenges: parseList($("#editChallenges").value),
        working_style: $("#editWorkingStyle").value.trim()
    };

    try {
        await apiRequest(`/api/personas/${encodeURIComponent(id)}`, {
            method: "PATCH",
            body: JSON.stringify(payload)
        });

        $("#editDialog")?.close();
        showNotice("Persona updated.");
        await loadPersonas();
    } catch (error) {
        showNotice(error.message, true);
    }
});

/* 10. Research persona selector */

function populateResearchPersonas() {
    const select = $("#researchPersona");
    if (!select) return;

    const previous = select.value;
    const active = personas.filter(persona => getStatus(persona) !== "archived");

    select.innerHTML = `
        <option value="">Select a persona…</option>
        ${active.map(persona => {
            const id = getPersonaId(persona);
            const label = persona.persona_label || persona.role || `Persona ${id}`;

            return `<option value="${escapeHTML(id)}">${escapeHTML(label)} · #${escapeHTML(id)}</option>`;
        }).join("")}
    `;

    if ([...select.options].some(option => option.value === previous)) {
        select.value = previous;
    }
}

function selectedResearchPersonaId() {
    const value = $("#researchPersona")?.value;

    if (!value) {
        throw new Error("Select a persona before running this research action.");
    }

    return encodeURIComponent(value);
}

/* 11. SINGLE research result renderer — no nested cards */

function renderResearchResult(selector, data) {
    const target = $(selector);
    if (!target) return;

    let result = normalizeObject(data);

    // Unwrap standard API envelopes.
    for (let i = 0; i < 3; i++) {
        if (
            result && !Array.isArray(result) &&
            typeof result === "object" &&
            Object.keys(result).length === 1 &&
            ["data", "result", "report", "profile"].includes(Object.keys(result)[0])
        ) {
            result = result[Object.keys(result)[0]];
        } else {
            break;
        }
    }

    const titles = {
        "#profileResult": ["Psychological Profile", "Behavioral traits and preferences"],
        "#interviewResult": ["Synthetic Interview", "Simulated response from the selected persona"],
        "#surveyResult": ["Survey Results", "Answers generated for your research question"],
        "#reportResult": ["Consistency Report", "Validation findings for this persona"]
    };

    const [title, subtitle] = titles[selector] || ["Research Results", "Structured research output"];

    const isObject = value =>
        value !== null && typeof value === "object" && !Array.isArray(value);

    if (result == null) {
        target.innerHTML = `<div class="empty-state">No research results returned.</div>`;
        return;
    }

    // Flatten nested API objects into one flat list of fields.
    function flatten(value, prefix = "", output = []) {
        if (isObject(value)) {
            for (const [key, child] of Object.entries(value)) {
                if (/^(system_prompt|raw_prompt|debug_info)$/i.test(key)) continue;

                const label = prefix ? `${prefix} · ${humanize(key)}` : humanize(key);

                if (isObject(child)) {
                    flatten(child, label, output);
                } else {
                    output.push([label, child]);
                }
            }
        } else if (Array.isArray(value)) {
            output.push([prefix || "Items", value]);
        } else {
            output.push([prefix || "Result", value]);
        }

        return output;
    }

    function renderField(label, value) {
        const key = label.toLowerCase();

        if (value == null || value === "") {
            return `
                <div class="research-clean-field">
                    <span class="research-clean-label">${escapeHTML(label)}</span>
                    <p class="research-clean-value muted">Not provided</p>
                </div>`;
        }

        if (typeof value === "boolean") {
            return `
                <div class="research-clean-field">
                    <span class="research-clean-label">${escapeHTML(label)}</span>
                    <span class="rr-badge ${value ? "success" : "neutral"}">${value ? "Yes" : "No"}</span>
                </div>`;
        }

        if (Array.isArray(value)) {
            return `
                <div class="research-clean-field research-clean-wide">
                    <span class="research-clean-label">${escapeHTML(label)}</span>
                    ${value.length
                        ? `<ul class="research-clean-list">${value.map(item =>
                            `<li>${escapeHTML(displayValue(item))}</li>`
                          ).join("")}</ul>`
                        : `<p class="research-clean-value muted">No items</p>`}
                </div>`;
        }

        const numeric = Number(value);
        const scoreField = /(score|confidence|openness|patience|tolerance|preference)/i.test(key);
        const isScore = scoreField && String(value).trim() !== "" &&
            Number.isFinite(numeric) && numeric >= 0 && numeric <= 100;

        if (isScore) {
            const score = Math.round(numeric);

            return `
                <div class="research-clean-field">
                    <span class="research-clean-label">${escapeHTML(label)}</span>
                    <div class="research-clean-score">
                        <strong>${score}</strong><span>/ 100</span>
                    </div>
                    <div class="research-clean-progress">
                        <span style="width:${score}%"></span>
                    </div>
                </div>`;
        }

        if (/(status|validation status|overall status|risk level)$/.test(key)) {
            const text = String(value).toLowerCase();
            const type = /inconsistent|failed|error|critical|contradiction/.test(text)
                ? "danger"
                : /consistent|success|passed|valid|complete/.test(text)
                    ? "success"
                    : "neutral";

            return `
                <div class="research-clean-field">
                    <span class="research-clean-label">${escapeHTML(label)}</span>
                    <span class="rr-badge ${type}">${escapeHTML(value)}</span>
                </div>`;
        }

        const text = isObject(value) ? JSON.stringify(value, null, 2) : String(value);
        const wide = text.length > 100 ||
            /response|answer|explanation|recommendation|summary|report/i.test(key);

        return `
            <div class="research-clean-field ${wide ? "research-clean-wide" : ""}">
                <span class="research-clean-label">${escapeHTML(label)}</span>
                <p class="research-clean-value">${escapeHTML(text)}</p>
            </div>`;
    }

    const fields = flatten(result);

    // Prioritize the main answer for interviews and surveys.
    if (selector === "#interviewResult" || selector === "#surveyResult") {
        const priority = /^(response|answer|generated response|generated answer)$/i;

        fields.sort((a, b) =>
            Number(priority.test(b[0])) - Number(priority.test(a[0]))
        );
    }

    const content = fields.length
        ? fields.map(([label, value]) => renderField(label, value)).join("")
        : `<p class="muted">No details available.</p>`;

    target.innerHTML = `
        <article class="rr-result research-clean-result">
            <header class="rr-header">
                <div class="rr-header-icon" aria-hidden="true">✦</div>
                <div class="rr-header-copy">
                    <span class="rr-eyebrow">SYNTHETIC USER RESEARCH</span>
                    <h3>${escapeHTML(title)}</h3>
                    <p>${escapeHTML(subtitle)}</p>
                </div>
            </header>

            <div class="research-clean-grid">${content}</div>

            <footer class="rr-footer">
                <span aria-hidden="true">✦</span>
                Synthetic research output — validate with real users.
            </footer>
        </article>`;
}

/* 12. SINGLE memory renderer */

function renderMemoryResult(data) {
    const target = $("#memoryResult");
    if (!target) return;

    let result = normalizeObject(data);

    for (let i = 0; i < 3; i++) {
        if (
            result && !Array.isArray(result) &&
            typeof result === "object" &&
            result.data !== undefined &&
            (Object.keys(result).length === 1 || result.memories === undefined)
        ) {
            result = normalizeObject(result.data);
        } else {
            break;
        }
    }

    let memories = [];

    if (Array.isArray(result)) {
        memories = result;
    } else if (Array.isArray(result?.memories)) {
        memories = result.memories;
    } else if (Array.isArray(result?.items)) {
        memories = result.items;
    } else if (Array.isArray(result?.results)) {
        memories = result.results;
    } else if (Array.isArray(result?.data)) {
        memories = result.data;
    } else if (result?.content !== undefined || result?.memory_type !== undefined) {
        memories = [result];
    }

    const selected = personas.find(
        persona => String(getPersonaId(persona)) === String($("#researchPersona")?.value)
    );

    const personaId = result?.persona_id ??
        memories[0]?.persona_id ??
        getPersonaId(selected) ??
        "—";

    function parseContent(value) {
        let content = value;

        for (let i = 0; i < 3 && typeof content === "string"; i++) {
            try {
                content = JSON.parse(content);
            } catch {
                return { text: content };
            }
        }

        if (content == null) return {};
        if (Array.isArray(content)) return { items: content };
        if (typeof content !== "object") return { text: String(content) };

        return content;
    }

    function renderMemoryContent(value) {
        const content = parseContent(value);

        const question = content.question ??
            content.interview_question ??
            content.survey_question;

        const answer = content.response ??
            content.answer ??
            content.assistant_response ??
            content.reply ??
            content.text;

        const summary = content.summary;

        const known = new Set([
            "question", "interview_question", "survey_question",
            "response", "answer", "assistant_response", "reply",
            "text", "summary"
        ]);

        const other = Object.entries(content).filter(([key]) => !known.has(key));

        return `
            ${question !== undefined ? `
                <div class="memory-detail">
                    <span class="memory-label">Question</span>
                    <p>${escapeHTML(displayValue(question))}</p>
                </div>` : ""}

            ${answer !== undefined ? `
                <div class="memory-detail memory-response">
                    <span class="memory-label">Response</span>
                    <p>${escapeHTML(displayValue(answer))}</p>
                </div>` : ""}

            ${summary !== undefined ? `
                <div class="memory-detail">
                    <span class="memory-label">Summary</span>
                    <p>${escapeHTML(displayValue(summary))}</p>
                </div>` : ""}

            ${other.map(([key, val]) => `
                <div class="memory-detail">
                    <span class="memory-label">${escapeHTML(humanize(key))}</span>
                    <p>${escapeHTML(displayValue(val))}</p>
                </div>`).join("")}

            ${question === undefined && answer === undefined &&
              summary === undefined && other.length === 0
                ? `<p class="rr-muted">No memory content available.</p>`
                : ""}`;
    }

    target.innerHTML = `
        <article class="rr-result memory-result-card">
            <header class="rr-header">
                <div class="rr-header-icon" aria-hidden="true">✦</div>
                <div class="rr-header-copy">
                    <span class="rr-eyebrow">SYNTHETIC USER RESEARCH</span>
                    <h3>Persona Memories</h3>
                    <p>Information retained from previous interactions</p>
                </div>
                <span class="rr-record-id">
                    ${memories.length} ${memories.length === 1 ? "memory" : "memories"}
                </span>
            </header>

            <div class="rr-content">
                <div class="memory-summary">
                    <div class="memory-summary-item">
                        <span class="memory-label">Persona ID</span>
                        <strong>${escapeHTML(personaId)}</strong>
                    </div>
                    <div class="memory-summary-item">
                        <span class="memory-label">Total memories</span>
                        <strong>${memories.length}</strong>
                    </div>
                </div>

                ${memories.length ? `
                    <div class="memory-list">
                        ${memories.map((memory, index) => {
                            const id = memory.id ?? memory.memory_id ?? index + 1;
                            const type = humanize(memory.memory_type ?? memory.type ?? "Memory");
                            const content = memory.content ??
                                memory.memory_content ??
                                memory.value ??
                                memory.text ??
                                memory;

                            return `
                                <article class="memory-item">
                                    <div class="memory-number">${index + 1}</div>
                                    <div class="memory-item-content">
                                        <div class="memory-item-heading">
                                            <h4>${escapeHTML(type)}</h4>
                                            <span class="memory-id">#${escapeHTML(id)}</span>
                                        </div>
                                        ${renderMemoryContent(content)}
                                    </div>
                                </article>`;
                        }).join("")}
                    </div>
                ` : `
                    <div class="empty-state">
                        <h3>No memories found</h3>
                        <p>Generate an interview or survey response to create stored interactions.</p>
                    </div>`}
            </div>

            <footer class="rr-footer">
                <span aria-hidden="true">✦</span>
                Stored synthetic persona interactions
            </footer>
        </article>`;
}

/* 13. Research action helper */

async function runResearchAction(buttonSelector, action) {
    const button = $(buttonSelector);
    if (!button) return;

    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = "Working…";

    try {
        await action();
    } catch (error) {
        showNotice(error.message || "Something went wrong.", true);
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}

/* 14. Psychological profile */

$("#profileAction")?.addEventListener("click", () =>
    runResearchAction("#profileAction", async () => {
        const id = selectedResearchPersonaId();

        const data = await apiRequest(
            `/api/personas/${id}/psychological-profile`,
            { method: "POST" }
        );

        renderResearchResult("#profileResult", data);
        showNotice("Psychological profile generated.");
    })
);

/* 15. Interview */

$("#interviewAction")?.addEventListener("click", () =>
    runResearchAction("#interviewAction", async () => {
        const id = selectedResearchPersonaId();
        const question = $("#interviewQuestion")?.value.trim();

        if (!question || question.length < 3) {
            throw new Error("Enter an interview question first.");
        }

        const data = await apiRequest(`/api/personas/${id}/interview`, {
            method: "POST",
            body: JSON.stringify({ question })
        });

        renderResearchResult("#interviewResult", data);
        showNotice("Interview response generated.");
    })
);

/* 16. Survey */

$("#surveyAction")?.addEventListener("click", () =>
    runResearchAction("#surveyAction", async () => {
        const id = selectedResearchPersonaId();
        const question = $("#surveyQuestion")?.value.trim();

        if (!question || question.length < 3) {
            throw new Error("Enter a survey question first.");
        }

        const data = await apiRequest(`/api/personas/${id}/survey`, {
            method: "POST",
            body: JSON.stringify({
                questions: [{
                    question,
                    question_type: "text",
                    options: []
                }]
            })
        });

        renderResearchResult("#surveyResult", data);
        showNotice("Survey response generated.");
    })
);

/* 17. Stored memories */

$("#memoryAction")?.addEventListener("click", () =>
    runResearchAction("#memoryAction", async () => {
        const id = selectedResearchPersonaId();

        const data = await apiRequest(
            `/api/personas/${id}/memories?limit=50`
        );

        renderMemoryResult(data);
        showNotice("Stored memories loaded.");
    })
);

/* 18. Consistency report */

$("#reportAction")?.addEventListener("click", () =>
    runResearchAction("#reportAction", async () => {
        const id = selectedResearchPersonaId();

        const data = await apiRequest(
            `/api/personas/${id}/validation-report`
        );

        renderResearchResult("#reportResult", data);
        showNotice("Consistency report loaded.");
    })
);

/* 19. Navigation and controls */

document.querySelectorAll("[data-view]").forEach(button => {
    button.addEventListener("click", () => openView(button.dataset.view));
});

$("#headerGenerate")?.addEventListener("click", () => openView("generate"));
$("#heroGenerate")?.addEventListener("click", () => openView("generate"));

$("#refreshButton")?.addEventListener("click", () => loadPersonas(true));
$("#viewAllButton")?.addEventListener("click", () => openView("personas"));

$("#searchInput")?.addEventListener("input", applyPersonaFilters);
$("#statusFilter")?.addEventListener("change", applyPersonaFilters);

$("#closeDialog")?.addEventListener("click", () => $("#detailsDialog")?.close());
$("#closeEditDialog")?.addEventListener("click", () => $("#editDialog")?.close());

$("#detailsDialog")?.addEventListener("click", event => {
    if (event.target === $("#detailsDialog")) $("#detailsDialog").close();
});

$("#editDialog")?.addEventListener("click", event => {
    if (event.target === $("#editDialog")) $("#editDialog").close();
});

/* 20. Initialize */

async function initializeApp() {
    await checkBackend();
    await loadPersonas();
}

initializeApp();
