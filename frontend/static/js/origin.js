/* ================================================================
   FighterSim -- Origin Selection Logic
   3-step flow: select card -> name promotion -> text crawl -> begin
   ================================================================ */

// ---------------------------------------------------------------------------
// Narrative text per origin (second-person cinematic voice)
// ---------------------------------------------------------------------------

const NARRATIVES = {
  "The Heir": [
    "The call came on a Tuesday. Gerald Rawlings \u2014 your mentor, your father\u2019s best friend, the man who built this promotion from a warehouse show into a regional powerhouse \u2014 was gone. Heart attack at 63. The board wanted to sell. The networks wanted to renegotiate. Everyone had an opinion about what happens next.",
    "You stare at the empty arena. Eighteen thousand seats, a cage that\u2019s hosted legends, and a legacy that doesn\u2019t belong to you yet. The Rawlings name opened doors. Yours will have to keep them open. You have the roster, you have the budget, but respect? That\u2019s earned fight by fight."
  ],
  "The Matchmaker": [
    "Ten years. Ten years of building fight cards for UCC, turning unknowns into contenders, engineering the kind of matchups that make crowds forget to breathe. You made their champions. You filled their arenas. And when you asked for a seat at the table, they laughed.",
    "So you walked. Took your rolodex, your eye for talent, and every lesson learned from a decade inside the machine. Your promotion doesn\u2019t have the budget or the broadcast deal. What it has is you \u2014 the person who knows exactly which fights the world wants to see. Now you just need to prove it\u2019s not the logo on the cage that matters. It\u2019s who\u2019s booking the fights."
  ],
  "The Comeback": [
    "They remember your last fight. Everybody does. Third-round stoppage, flat on the canvas, the referee waving it off while the crowd went quiet. That was three years ago. The gym closed. The sponsors vanished. Your name became a punchline on MMA forums.",
    "But fighters don\u2019t quit. You scraped together every dollar, called in every favor, and signed six hungry kids who remind you of yourself \u2014 back when you still believed you could be somebody. The warehouse smells like sweat and ambition. The budget wouldn\u2019t cover one UCC undercard. Nobody in the industry gives you six months. Good. You\u2019ve been counted out before."
  ]
};

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let selectedOrigin = null;
let seedComplete = false;
let crawlComplete = false;

// ---------------------------------------------------------------------------
// Init: fetch origin configs and render cards
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  fetch("/api/origins")
    .then(res => res.json())
    .then(origins => {
      const container = document.getElementById("cards-container");
      origins.forEach(origin => {
        const card = document.createElement("div");
        card.className = "origin-card";
        card.dataset.key = origin.key;
        card.innerHTML = `
          <div class="card-label">${origin.label}</div>
          <p class="card-tagline">${origin.tagline}</p>
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-value">${formatBudget(origin.budget)}</span>
              <span class="stat-label">Budget</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${origin.prestige}</span>
              <span class="stat-label">Prestige</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${origin.roster_target}</span>
              <span class="stat-label">Fighters</span>
            </div>
          </div>
        `;
        card.addEventListener("click", () => selectCard(origin.key));
        container.appendChild(card);
      });
    })
    .catch(err => showError("Failed to load origins: " + err.message));
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatBudget(amount) {
  if (amount >= 1_000_000) {
    return "$" + (amount / 1_000_000).toFixed(1) + "M";
  }
  return "$" + (amount / 1_000).toFixed(0) + "K";
}

function showError(msg) {
  const overlay = document.getElementById("error-overlay");
  overlay.textContent = msg;
  overlay.classList.add("visible");
  setTimeout(() => overlay.classList.remove("visible"), 4000);
}

function showNameError(msg) {
  document.getElementById("name-error").textContent = msg;
}

// ---------------------------------------------------------------------------
// Step 1: Card selection
// ---------------------------------------------------------------------------

function selectCard(key) {
  selectedOrigin = key;

  // Highlight selected card
  document.querySelectorAll(".origin-card").forEach(card => {
    card.classList.toggle("selected", card.dataset.key === key);
  });

  // Show name input
  const stepName = document.getElementById("step-name");
  if (!stepName.classList.contains("active")) {
    stepName.classList.add("active");
    document.getElementById("promotion-name").focus();
  }
}

// ---------------------------------------------------------------------------
// Step 2: Confirm origin + name
// ---------------------------------------------------------------------------

function confirmOrigin() {
  const nameInput = document.getElementById("promotion-name");
  const name = nameInput.value.trim();

  // Client-side validation
  if (!selectedOrigin) {
    showNameError("Please select an origin first.");
    return;
  }
  if (name.length < 2) {
    showNameError("Name must be at least 2 characters.");
    return;
  }
  if (name.length > 50) {
    showNameError("Name must be 50 characters or fewer.");
    return;
  }
  if (!/^[A-Za-z0-9 '\.\-]+$/.test(name)) {
    showNameError("Only letters, numbers, spaces, hyphens, periods, and apostrophes allowed.");
    return;
  }

  showNameError("");

  // Disable confirm button to prevent double-submit
  const btn = document.getElementById("btn-confirm");
  btn.disabled = true;
  btn.textContent = "Starting...";

  // POST to backend
  fetch("/api/origin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      origin_type: selectedOrigin,
      promotion_name: name
    })
  })
    .then(res => res.json().then(data => ({ ok: res.ok, data })))
    .then(({ ok, data }) => {
      if (!ok) {
        showNameError(data.error || "Something went wrong.");
        btn.disabled = false;
        btn.textContent = "Confirm";
        return;
      }

      // Success: show text crawl and start polling
      showTextCrawl(selectedOrigin);
      pollSeedTask(data.task_id);
    })
    .catch(err => {
      showNameError("Network error: " + err.message);
      btn.disabled = false;
      btn.textContent = "Confirm";
    });
}

// ---------------------------------------------------------------------------
// Step 3: Text crawl
// ---------------------------------------------------------------------------

function showTextCrawl(originType) {
  // Hide steps 1 and 2
  document.getElementById("step-cards").classList.remove("active");
  document.getElementById("step-name").classList.remove("active");

  // Show step 3
  const stepCrawl = document.getElementById("step-crawl");
  stepCrawl.classList.add("active");

  // Insert narrative paragraphs
  const paragraphs = NARRATIVES[originType] || NARRATIVES["The Heir"];
  document.getElementById("crawl-p1").textContent = paragraphs[0];
  document.getElementById("crawl-p2").textContent = paragraphs[1];

  // Trigger CSS animations
  document.getElementById("crawl-p1").classList.add("crawl-reveal", "crawl-p1");
  document.getElementById("crawl-p2").classList.add("crawl-reveal", "crawl-p2");
  document.getElementById("btn-begin").classList.add("crawl-reveal");

  // Text crawl animation total: last element at 4.5s + 1.2s duration = 5.7s
  // Use 5700ms as the crawl gate
  setTimeout(() => {
    crawlComplete = true;
    checkBeginReady();
  }, 5700);
}

// ---------------------------------------------------------------------------
// Seed task polling
// ---------------------------------------------------------------------------

function pollSeedTask(taskId) {
  const interval = setInterval(() => {
    fetch("/api/tasks/" + taskId)
      .then(res => res.json())
      .then(data => {
        if (data.status === "done") {
          clearInterval(interval);
          seedComplete = true;
          checkBeginReady();
        } else if (data.status === "error") {
          clearInterval(interval);
          showError("Seeding failed: " + (data.error || "unknown error"));
        }
      })
      .catch(() => {
        // Retry on network hiccup
      });
  }, 500);
}

// ---------------------------------------------------------------------------
// Dual gate: both seed complete AND crawl animation done
// ---------------------------------------------------------------------------

function checkBeginReady() {
  if (seedComplete && crawlComplete) {
    const btn = document.getElementById("btn-begin");
    btn.disabled = false;
    btn.addEventListener("click", () => {
      window.location.href = "/";
    });
  }
}

// Allow Enter key to submit name form
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const nameStep = document.getElementById("step-name");
    if (nameStep.classList.contains("active") && document.activeElement.id === "promotion-name") {
      confirmOrigin();
    }
  }
});
