import * as THREE from 'three';

// ---- BASIC SCENE SETUP ----
// A scene is like an empty stage. A camera is your eye looking at it.
// A renderer actually draws it onto the screen.
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0e1a);

const camera = new THREE.PerspectiveCamera(
  60,
  window.innerWidth / window.innerHeight,
  0.1,
  1000
);
camera.position.set(15, 12, 15);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// ---- LIGHTING ----
// Without light, 3D shapes look flat and black. We add two lights:
// one soft overall glow, one directional like sunlight.
scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const sunLight = new THREE.DirectionalLight(0xffffff, 0.8);
sunLight.position.set(10, 20, 10);
scene.add(sunLight);

// ---- THE SHIP DECK ----
// A simple flat gray box to represent the ship's deck.
const deckGeometry = new THREE.BoxGeometry(12, 0.5, 6);
const deckMaterial = new THREE.MeshStandardMaterial({ color: 0x444455 });
const deck = new THREE.Mesh(deckGeometry, deckMaterial);
deck.position.set(0, -0.25, 0);
scene.add(deck);



let containerMeshes = [];

function clearContainerMeshes() {
  for (const mesh of containerMeshes) {
    scene.remove(mesh);
  }
  containerMeshes = [];
}

function colorForIndex(i) {
  const palette = [0xff4d4d, 0x4d79ff, 0x4dff88, 0xffd24d, 0xb84dff, 0x4dfff2];
  return palette[i % palette.length];
}



function updateLegend(containersData) {
  const legend = document.getElementById('legend');
  let html = '<strong>Containers</strong><br>';
  containersData.forEach((c, i) => {
    const color = colorForIndex(i);
    const hex = '#' + color.toString(16).padStart(6, '0');
    html += `<span style="display:inline-block;width:10px;height:10px;background:${hex};margin-right:6px;"></span>${c.container_id} — ${c.weight}kg<br>`;
  });
  legend.innerHTML = html;
}
const PORT_ORDER = ["COLOMBO", "SINGAPORE", "DUBAI"];

function buildUnloadPlan(containers) {
  const groups = {};
  containers.forEach((c) => {
    const port = (c.destination_port || "").trim().toUpperCase() || "NO PORT";
    if (!groups[port]) groups[port] = [];
    groups[port].push(c);
  });

  const rank = (p) => (PORT_ORDER.indexOf(p) === -1 ? 999 : PORT_ORDER.indexOf(p));
  const ports = Object.keys(groups).sort((a, b) => rank(a) - rank(b));

  let html = "<strong>Unload plan</strong><br>";
  ports.forEach((port) => {
    // top tier first, then by section, then by row
    const list = groups[port].sort(
      (a, b) => b.tier - a.tier || a.bay_number - b.bay_number || a.row - b.row
    );
    html += `<span style="color:#9ca3af">${escapeForHtml(port)}</span><br>`;
    list.forEach((c, n) => {
      html += `${n + 1}. ${escapeForHtml(c.container_id)} (section ${c.bay_number}, tier ${c.tier})<br>`;
    });
  });
  return html;
}

const methodResults = {};

function updateReport(data) {
  const report = document.getElementById('report');
  const e = data.emissions;
  const s = data.stability;
  const v = data.violations || [];
  methodResults[data.method] = { score: data.score, time: data.time_seconds };
  const compareHtml = ['GA', 'RL'].map((m) => {
    const r = methodResults[m];
    return r ? `${m}: score ${r.score.toFixed(2)}, ${r.time}s` : `${m}: not run yet`;
  }).join('<br>');

  const violationsHtml = v.length === 0
    ? '<span style="color:#80ff9f">All rules satisfied</span>'
    : '<span style="color:#ff8080">' + v.map((x) => '• ' + escapeForHtml(x)).join('<br>') + '</span>';

  report.innerHTML = `
    <strong>Voyage report</strong><br>
    Optimizer: ${data.method}<br>
    <br>
    <strong>Optimizer scores</strong><br>
    ${compareHtml}<br>
    Distance: ${e.voyage_distance_nm} nm<br>
    Cargo: ${e.total_cargo_tons.toFixed(1)} tons<br>
    Fuel: ${e.fuel_kg.toFixed(2)} kg<br>
    CO2: ${e.co2_kg.toFixed(2)} kg<br>
    CII grade: ${e.cii_grade}<br>
    <br>
    <strong>Stability</strong><br>
    Imbalance: ${s.imbalance_percent.toFixed(2)}%<br>
    Balanced: ${s.is_balanced ? 'Yes' : 'No'}<br>
    Center of gravity: ${s.center_of_gravity_height_m.toFixed(2)} m<br>
    <br>
    <strong>Rule check</strong><br>
    ${violationsHtml}
    <br><br>
    ${buildUnloadPlan(data.containers)}
  `;
}
function createInfoLabel(c) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 96;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "rgba(0,0,0,0.6)";
  ctx.fillRect(0, 0, 256, 96);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  ctx.font = "bold 30px sans-serif";
  ctx.fillStyle = "white";
  ctx.fillText(c.container_id, 128, 24);

  ctx.font = "bold 22px sans-serif";
  ctx.fillStyle = "#9ca3af";
  ctx.fillText(c.destination_port || "-", 128, 52);

  const flags = [];
  if (c.is_hazardous) flags.push("HAZ");
  if (c.is_fragile) flags.push("FRAGILE");
  ctx.fillStyle = c.is_hazardous ? "#ff6b6b" : "#ffd24d";
  ctx.fillText(flags.join(" + "), 128, 78);

  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(2.4, 0.9, 1);
  sprite.renderOrder = 999;
  return sprite;
}
async function runOptimization() {
  const button = document.getElementById("optimize-button");
  button.disabled = true;
  button.textContent = "Optimizing...";

  try {
    const distance = document.getElementById("voyage-select").value;
    const method = document.getElementById("method-select").value;
    const response = await fetch(`http://127.0.0.1:8000/optimize?distance_nm=${distance}&method=${method}`, { method: "POST" });
    const data = await response.json();
        if (!response.ok) {
      alert(data.detail || "The optimizer could not run.");
      return;
    }

    clearContainerMeshes();

    const SCALE = 0.4;            // 1 metre = 0.4 units in the 3D scene
    const SLOT_HEIGHT = 1.04;     // height of one tier (2.6 m)
    const SECTION_SPACING = 1.2;  // gap between sections, front to back
    const sections = data.sections || 1;

        data.containers.forEach((c, i) => {
      const length = c.length * SCALE;
      const width = c.width * SCALE;
      const height = c.height * SCALE;
      const color = colorForIndex(i);

      const geometry = new THREE.BoxGeometry(length, height, width);
      const material = new THREE.MeshStandardMaterial({ color });
      const mesh = new THREE.Mesh(geometry, material);

      const x = (c.row - 1.5) * 7;
      const y = (c.tier - 1) * SLOT_HEIGHT + height / 2;
      const z = (c.bay_number - (sections + 1) / 2) * SECTION_SPACING;
      mesh.position.set(x, y, z);

      scene.add(mesh);
      containerMeshes.push(mesh);

      const label = createInfoLabel(c);
      label.position.set(x, y + height / 2 + 0.7, z);
      scene.add(label);
      containerMeshes.push(label);
    });

    updateLegend(data.containers);
    updateReport(data);

    console.log("Optimization result:", data);
  } catch (error) {
    console.error("Failed to fetch optimization result:", error);
    alert("Could not reach the backend. Is uvicorn still running?");
  } finally {
    button.disabled = false;
    button.textContent = "Optimize";
  }
}

document.getElementById("optimize-button").addEventListener("click", runOptimization);



// ---- LET THE USER ROTATE THE VIEW WITH THEIR MOUSE ----
// (Three.js doesn't include mouse controls by default, so we write a small
// manual version: click and drag to rotate the camera around the ship.)
let isDragging = false;
let previousMouseX = 0;
let previousMouseY = 0;
let cameraAngleX = 0.6;
let cameraAngleY = 0.7;
let cameraDistance = 22;

function updateCameraPosition() {
  camera.position.x = cameraDistance * Math.sin(cameraAngleY) * Math.cos(cameraAngleX);
  camera.position.y = cameraDistance * Math.sin(cameraAngleX);
  camera.position.z = cameraDistance * Math.cos(cameraAngleY) * Math.cos(cameraAngleX);
  camera.lookAt(0, 1, 0);
}
updateCameraPosition();

renderer.domElement.addEventListener('mousedown', (event) => {
  isDragging = true;
  previousMouseX = event.clientX;
  previousMouseY = event.clientY;
});
window.addEventListener('mouseup', () => { isDragging = false; });
window.addEventListener('mousemove', (event) => {
  if (!isDragging) return;
  const deltaX = event.clientX - previousMouseX;
  const deltaY = event.clientY - previousMouseY;
  cameraAngleY += deltaX * 0.01;
  cameraAngleX = Math.max(0.1, Math.min(1.4, cameraAngleX + deltaY * 0.01));
  previousMouseX = event.clientX;
  previousMouseY = event.clientY;
  updateCameraPosition();
});
renderer.domElement.addEventListener('wheel', (event) => {
  cameraDistance = Math.max(8, Math.min(40, cameraDistance + event.deltaY * 0.02));
  updateCameraPosition();
});

// ---- THE ANIMATION LOOP ----
// This function runs about 60 times per second, redrawing the scene.
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();

// Keep things sized correctly if the browser window is resized
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// ===== Stage 9b: manage containers from the browser =====
const CONTAINER_API = "http://127.0.0.1:8000";
let editingContainerId = null;   // null = adding a new one; otherwise the ID being edited
let loadedContainers = [];

function showPanelMessage(text, isError) {
  const box = document.getElementById("panel-message");
  box.textContent = text;
  box.style.color = isError ? "#ff8080" : "#80ff9f";
}

function escapeForHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function explainError(data) {
  if (data && typeof data.detail === "string") {
    return data.detail;
  }
  return "Limits: weight up to 30000 kg, length up to 12.2 m, width up to 3 m, height up to 2.6 m.";
}

function readContainerForm() {
  return {
    container_id: document.getElementById("f-container-id").value.trim(),
    weight: Number(document.getElementById("f-weight").value),
    length: Number(document.getElementById("f-length").value),
    width: Number(document.getElementById("f-width").value),
    height: Number(document.getElementById("f-height").value),
    is_fragile: document.getElementById("f-fragile").checked,
    is_hazardous: document.getElementById("f-hazardous").checked,
    destination_port: document.getElementById("f-port").value.trim(),
  };
}

function resetContainerForm() {
  editingContainerId = null;
  const idInput = document.getElementById("f-container-id");
  idInput.value = "";
  idInput.disabled = false;
  document.getElementById("f-weight").value = 10000;
  document.getElementById("f-length").value = 6.06;
  document.getElementById("f-width").value = 2.44;
  document.getElementById("f-height").value = 2.59;
  document.getElementById("f-fragile").checked = false;
  document.getElementById("f-hazardous").checked = false;
  document.getElementById("f-port").value = "";
  document.getElementById("save-button").textContent = "Add container";
  document.getElementById("cancel-button").style.display = "none";
}

function renderContainerList() {
  const list = document.getElementById("container-list");
  if (loadedContainers.length === 0) {
    list.textContent = "No containers yet.";
    return;
  }
  let html = "";
  loadedContainers.forEach((c) => {
    const id = escapeForHtml(c.container_id);
    html += `
      <div class="container-card">
        <div>
          <div class="card-id">${id}</div>
          <div class="card-weight">${c.weight} kg</div>
        </div>
        <div class="card-actions">
          <button class="btn-small edit-btn" data-id="${id}">Edit</button>
          <button class="btn-small btn-danger delete-btn" data-id="${id}">Delete</button>
        </div>
      </div>`;
  });
  list.innerHTML = html;
}

async function loadContainerList() {
  try {
    const response = await fetch(`${CONTAINER_API}/containers`);
    loadedContainers = await response.json();
    renderContainerList();
    renderCapacity();
  } catch (error) {
    console.error("Failed to load containers:", error);
    showPanelMessage("Could not reach the backend. Is uvicorn running?", true);
  }
}

async function saveContainer() {
  const data = readContainerForm();
  if (editingContainerId === null && data.container_id === "") {
    showPanelMessage("Please type a Container ID first.", true);
    return;
  }

  const saveButton = document.getElementById("save-button");
  saveButton.disabled = true;
  try {
    let response;
    if (editingContainerId === null) {
      response = await fetch(`${CONTAINER_API}/containers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
    } else {
      response = await fetch(
        `${CONTAINER_API}/containers/${encodeURIComponent(editingContainerId)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        }
      );
    }

    const result = await response.json();
    if (!response.ok) {
      showPanelMessage(explainError(result), true);
      return;
    }
    showPanelMessage(result.message, false);
    resetContainerForm();
    await loadContainerList();
    autoRedraw();
  } catch (error) {
    console.error("Failed to save container:", error);
    showPanelMessage("Could not reach the backend. Is uvicorn running?", true);
  } finally {
    saveButton.disabled = false;
  }
}

function startEditing(containerId) {
  const c = loadedContainers.find((x) => x.container_id === containerId);
  if (!c) return;

  editingContainerId = containerId;
  const idInput = document.getElementById("f-container-id");
  idInput.value = c.container_id;
  idInput.disabled = true;   // the ID can't be changed while editing
  document.getElementById("f-weight").value = c.weight;
  document.getElementById("f-length").value = c.length;
  document.getElementById("f-width").value = c.width;
  document.getElementById("f-height").value = c.height;
  document.getElementById("f-fragile").checked = c.is_fragile;
  document.getElementById("f-hazardous").checked = c.is_hazardous;
  document.getElementById("f-port").value = c.destination_port;
  document.getElementById("save-button").textContent = "Save changes";
  document.getElementById("cancel-button").style.display = "inline-block";
  showPanelMessage(`Editing ${containerId}`, false);
}

async function deleteContainer(containerId) {
  if (!confirm(`Remove ${containerId} from the database?`)) return;
  try {
    const response = await fetch(
      `${CONTAINER_API}/containers/${encodeURIComponent(containerId)}`,
      { method: "DELETE" }
    );
    const result = await response.json();
    if (!response.ok) {
      showPanelMessage(explainError(result), true);
      return;
    }
    if (editingContainerId === containerId) {
      resetContainerForm();
    }
    showPanelMessage(result.message, false);
    await loadContainerList();
    autoRedraw();
  } catch (error) {
    console.error("Failed to delete container:", error);
    showPanelMessage("Could not reach the backend. Is uvicorn running?", true);
  }
}

document.getElementById("save-button").addEventListener("click", saveContainer);
document.getElementById("cancel-button").addEventListener("click", () => {
  resetContainerForm();
  showPanelMessage("", false);
});

// One listener for every Edit/Delete button in the list
document.getElementById("container-list").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const containerId = button.dataset.id;
  if (button.classList.contains("edit-btn")) {
    startEditing(containerId);
  } else if (button.classList.contains("delete-btn")) {
    deleteContainer(containerId);
  }
});

loadContainerList();

// ===== Stage 15: re-run Optimize after drawer changes =====
function autoRedraw() {
  const button = document.getElementById("optimize-button");
  if (button.disabled) return;                                   // already running
  if (loadedContainers.length === 0) return;                     // nothing to place
  if (loadedContainers.length > baySummary.total_bays) return;   // capacity line already warns
  runOptimization();
}
// ===== Drawer open/close =====
const containerDrawer = document.getElementById("container-drawer");

document.getElementById("drawer-tab").addEventListener("click", () => {
  containerDrawer.classList.toggle("open");
});

// Stop the drawer from spinning or zooming the 3D ship underneath it
containerDrawer.addEventListener("wheel", (event) => event.stopPropagation());
containerDrawer.addEventListener("mousedown", (event) => event.stopPropagation());

// ===== Ship capacity (bay sections) =====
let baySummary = { sections: 0, total_bays: 0 };

function renderCapacity() {
  const box = document.getElementById("capacity-text");
  const containerCount = loadedContainers.length;
  let text = `${containerCount} containers · ${baySummary.total_bays} bays (${baySummary.sections} sections)`;
  if (containerCount > baySummary.total_bays) {
    text += " — not enough bays, add a section!";
    box.style.color = "#ff8080";
  } else {
    box.style.color = "#e5e7eb";
  }
  box.textContent = text;
}

async function loadBaySummary() {
  try {
    const response = await fetch(`${CONTAINER_API}/bays`);
    baySummary = await response.json();
    renderCapacity();
  } catch (error) {
    console.error("Failed to load bay summary:", error);
  }
}

async function changeSection(method) {
  try {
    const response = await fetch(`${CONTAINER_API}/bays/section`, { method });
    const result = await response.json();
    if (!response.ok) {
      showPanelMessage(explainError(result), true);
      return;
    }
    showPanelMessage(result.message, false);
    await loadBaySummary();
    autoRedraw();
  } catch (error) {
    console.error("Failed to change bay sections:", error);
    showPanelMessage("Could not reach the backend. Is uvicorn running?", true);
  }
}

document.getElementById("add-section-button").addEventListener("click", () => changeSection("POST"));
document.getElementById("remove-section-button").addEventListener("click", () => changeSection("DELETE"));

loadBaySummary();


// ===== Stage 25: Download Report (PDF) =====
function captureViews() {
  const saved = { x: cameraAngleX, y: cameraAngleY, d: cameraDistance };
  const W = 900, H = 600;
  renderer.setSize(W, H, false);
  camera.aspect = W / H;
  camera.updateProjectionMatrix();

  const views = [
    { title: "Isometric view", x: 0.6, y: 0.7, d: 22 },
    { title: "Top view", x: 1.5, y: 0, d: 14 },
    { title: "Starboard side view", x: 0.05, y: Math.PI / 2, d: 14 },
    { title: "Port side view", x: 0.05, y: -Math.PI / 2, d: 14 },
    { title: "End view (last section side)", x: 0.05, y: 0, d: 14 },
    { title: "End view (section 1 side)", x: 0.05, y: Math.PI, d: 14 },
  ];

  const shots = [];
  for (const v of views) {
    cameraAngleX = v.x;
    cameraAngleY = v.y;
    cameraDistance = v.d;
    updateCameraPosition();
    renderer.render(scene, camera);
    shots.push({ title: v.title, image: renderer.domElement.toDataURL("image/png") });
  }

  cameraAngleX = saved.x;
  cameraAngleY = saved.y;
  cameraDistance = saved.d;
  updateCameraPosition();
  renderer.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  return shots;
}
async function downloadReport() {
  if (containerMeshes.length === 0) {
    alert("Click Optimize first, so the 3D view has something to show.");
    return;
  }

  const button = document.getElementById("report-button");
  button.disabled = true;
  button.textContent = "Preparing report...";

  try {
    // draw once, then read the canvas in the same step so the picture is not blank
    const screenshots = captureViews();

    const voyageSelect = document.getElementById("voyage-select");
    const response = await fetch(`${CONTAINER_API}/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        distance_nm: Number(voyageSelect.value),
        voyage_name: voyageSelect.selectedOptions[0].text,
        screenshots: screenshots,
      }),
    });

    if (!response.ok) {
      let message = "The report could not be created.";
      try {
        const err = await response.json();
        if (typeof err.detail === "string") message = err.detail;
      } catch (e) {}
      alert(message);
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "Voyage report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Failed to download report:", error);
    alert("Could not reach the backend. Is uvicorn still running?");
  } finally {
    button.disabled = false;
    button.textContent = "Download Report";
  }
}

document.getElementById("report-button").addEventListener("click", downloadReport);