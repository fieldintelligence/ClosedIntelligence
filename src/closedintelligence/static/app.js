async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

function values(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  if (data.tags) data.tags = data.tags.split(",").map((x) => x.trim()).filter(Boolean);
  if (data.options) data.options = data.options.split(",").map((x) => x.trim()).filter(Boolean);
  return data;
}

async function refresh() {
  const state = await api("/api/state");
  document.getElementById("employeeCount").textContent = Object.keys(state.employees).length;
  document.getElementById("knowledgeCount").textContent = state.knowledge.length;
  document.getElementById("proposalCount").textContent = Object.keys(state.proposals).length;
  document.getElementById("eventCount").textContent = state.event_count;
  document.getElementById("stateOutput").textContent = JSON.stringify(state, null, 2);
}

function bindForm(id, path) {
  document.getElementById(id).addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api(path, { method: "POST", body: JSON.stringify(values(event.currentTarget)) });
      event.currentTarget.reset();
      await refresh();
    } catch (error) {
      alert(error.message);
    }
  });
}

bindForm("employeeForm", "/api/employee");
bindForm("knowledgeForm", "/api/knowledge");
bindForm("proposalForm", "/api/proposal");
bindForm("voteForm", "/api/vote");
bindForm("taskForm", "/api/task");
bindForm("decisionForm", "/api/decision");

document.getElementById("answerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await api("/api/answer", { method: "POST", body: JSON.stringify(values(event.currentTarget)) });
    document.getElementById("answerOutput").textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    alert(error.message);
  }
});

document.getElementById("downloadBundle").addEventListener("click", async () => {
  const bundle = await api("/api/bundle");
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "closedintelligence-bundle.json";
  link.click();
  URL.revokeObjectURL(link.href);
});

refresh();
