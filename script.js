// ── CONFIG ────────────────────────────────────────────
// This is the address of your Flask backend server.
// When you run app.py, it starts at http://localhost:5000
const API = "http://localhost:5000";


// ── LOAD STREETS INTO DROPDOWN ────────────────────────
// Called immediately when the page loads.
// Fetches the list of streets from the backend and fills the <select>.
async function loadStreets() {
  const res = await fetch(`${API}/streets`);  // calls GET /streets
  const streets = await res.json();           // converts response to JS array

  const select = document.getElementById("streetSelect");
  select.innerHTML = '<option value="">-- Choose a street --</option>';

  // Create one <option> per street
  streets.forEach(street => {
    const option = document.createElement("option");
    option.value = street;
    option.textContent = street;
    select.appendChild(option);
  });
}


// ── CHECK RISK FOR SELECTED STREET ───────────────────
// Called when user clicks "Check Risk" button.
// Sends the street name to the backend and shows the result.
async function checkRisk() {
  const street = document.getElementById("streetSelect").value;

  if (!street) {
    alert("Please select a street first.");
    return;
  }

  // Show loading, hide old result
  document.getElementById("loading").classList.remove("hidden");
  document.getElementById("result").classList.add("hidden");

  // Fetch from backend — ?street=Observer+Highway
  const res = await fetch(`${API}/risk?street=${encodeURIComponent(street)}`);
  const data = await res.json();

  // Hide loading
  document.getElementById("loading").classList.add("hidden");

  // ── POPULATE RESULT CARD ─────────────────────────
  const circle = document.getElementById("scoreCircle");
  circle.className = `risk-score-circle risk-${data.risk_level}`;

  document.getElementById("scoreNumber").textContent = data.risk_score;
  document.getElementById("streetName").textContent  = data.street;

  const badge = document.getElementById("riskBadge");
  badge.textContent  = data.risk_level + " RISK";
  badge.className    = `badge badge-${data.risk_level}`;

  document.getElementById("advice").textContent     = data.advice;
  document.getElementById("temp").textContent       = data.weather.temp_f;
  document.getElementById("rain").textContent       = data.weather.rain_inch;
  document.getElementById("wind").textContent       = data.weather.wind_mph;
  document.getElementById("elevation").textContent  = data.elevation_ft;

  // Show result card
  document.getElementById("result").classList.remove("hidden");
}


// ── LOAD ALL STREETS TABLE ────────────────────────────
// Fetches risk for every street and builds an HTML table.
async function loadAllRisks() {
  const res = await fetch(`${API}/all-risks`);
  const streets = await res.json();

  const tbody = document.getElementById("tableBody");
  tbody.innerHTML = ""; // clear old rows

  streets.forEach(s => {
    const row = document.createElement("tr");

    // Color-code the risk score cell
    const color = s.risk_level === "HIGH"     ? "#fca5a5" :
                  s.risk_level === "MODERATE"  ? "#fcd34d" : "#86efac";

    row.innerHTML = `
      <td>${s.street}</td>
      <td style="color:${color}; font-weight:700">${s.risk_score}/100</td>
      <td>${s.risk_level}</td>
      <td>${s.elevation_ft} ft</td>
    `;
    tbody.appendChild(row);
  });

  document.getElementById("allRisksTable").classList.remove("hidden");
}


// ── RUN ON PAGE LOAD ──────────────────────────────────
// As soon as the page opens, load the street dropdown
loadStreets();

// ── LOAD SCENARIO BUTTONS ──────────────────────────────
// Fetches all scenarios and creates a button for each one
async function loadScenarios() {
  const res = await fetch(`${API}/scenarios`);
  const scenarios = await res.json();

  const container = document.getElementById("scenarioButtons");

  scenarios.forEach(s => {
    const btn = document.createElement("button");
    btn.textContent = s.label;
    btn.title = s.description;
    btn.style.fontSize = "0.85rem";
    btn.style.padding = "0.5rem 1rem";
    btn.onclick = () => runSimulation(s.key, btn);
    container.appendChild(btn);
  });
}


// ── RUN A SIMULATION ───────────────────────────────────
// Sends the scenario key to the backend and renders results
async function runSimulation(scenarioKey, clickedBtn) {

  // Highlight the selected button
  document.querySelectorAll("#scenarioButtons button")
    .forEach(b => b.style.background = "#0284c7");
  clickedBtn.style.background = "#7c3aed";  // purple = active

  document.getElementById("simLoading").classList.remove("hidden");
  document.getElementById("simResult").classList.add("hidden");

  const res  = await fetch(`${API}/simulate?scenario=${scenarioKey}`);
  const data = await res.json();

  document.getElementById("simLoading").classList.add("hidden");

  // ── RENDER HEADER ────────────────────────────────
  document.getElementById("simHeader").innerHTML = `
    <h3 style="color:#38bdf8; margin-bottom:0.5rem">${data.label}</h3>
    <p style="color:#94a3b8; font-size:0.9rem; margin-bottom:0.75rem">${data.description}</p>
    <div style="display:flex; gap:1.5rem; font-size:0.85rem; color:#94a3b8">
      <span>🌧️ Rainfall: ${data.conditions.rainfall_mm} mm/hr</span>
      <span>💨 Wind: ${data.conditions.wind_mph} mph</span>
      <span>🌊 Tide: ${data.conditions.tide_ft} ft</span>
    </div>
  `;

  // ── RENDER TABLE ─────────────────────────────────
  const tbody = document.getElementById("simTableBody");
  tbody.innerHTML = "";

  data.streets.forEach(s => {
    const color = s.risk_level === "HIGH"     ? "#fca5a5" :
                  s.risk_level === "MODERATE"  ? "#fcd34d" : "#86efac";

    const bar = `
      <div style="background:#1e293b; border-radius:4px; height:6px; margin-top:4px; width:100%">
        <div style="background:${color}; width:${s.risk_score}%; height:6px; border-radius:4px"></div>
      </div>`;

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${s.street}</td>
      <td style="color:${color}; font-weight:700">
        ${s.risk_score}/100 ${bar}
      </td>
      <td style="color:${color}">${s.risk_level}</td>
      <td>${s.elevation_ft} ft</td>
    `;
    tbody.appendChild(row);
  });

  document.getElementById("simResult").classList.remove("hidden");
}


// Load scenarios when page loads
loadScenarios();
