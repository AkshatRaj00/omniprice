/* ==========================================================================
   OmniPrice Application Logic & Particle Engine
   ========================================================================== */

let activeProductPayload = null;

// Official Branding Registry
const STORE_THEMES = {
  "Flipkart": { color: "#2874f0", bg: "rgba(40,116,240,0.15)", icon: "fa-bolt" },
  "Amazon": { color: "#ff9900", bg: "rgba(255,153,0,0.15)", icon: "fa-box-open" },
  "Myntra": { color: "#ff3f6c", bg: "rgba(255,63,108,0.15)", icon: "fa-bag-shopping" },
  "Ajio": { color: "#2c4152", bg: "rgba(44,65,82,0.25)", icon: "fa-shirt" },
  "Tata CLiQ": { color: "#e2e8f0", bg: "rgba(255,255,255,0.1)", icon: "fa-gem" },
  "Nykaa": { color: "#fc2779", bg: "rgba(252,39,121,0.15)", icon: "fa-wand-magic-sparkles" },
  "Snapdeal": { color: "#e40046", bg: "rgba(228,0,70,0.15)", icon: "fa-tag" },
  "JioMart": { color: "#0078ad", bg: "rgba(0,120,173,0.15)", icon: "fa-basket-shopping" }
};

/* --------------------------------------------------------------------------
   Interactive Canvas Particle Background
   Ensures the UI stays dynamic even if local MP4 fails to autoplay
   -------------------------------------------------------------------------- */
class ParticleMatrix {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.particles = [];
    this.resize();
    this.init();
    window.addEventListener("resize", () => this.resize());
  }

  resize() {
    this.width = this.canvas.width = window.innerWidth;
    this.height = this.canvas.height = window.innerHeight;
  }

  init() {
    const count = Math.min(Math.floor((this.width * this.height) / 22000), 55);
    this.particles = [];
    for (let i = 0; i < count; i++) {
      this.particles.push({
        x: Math.random() * this.width,
        y: Math.random() * this.height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 1.5 + 0.5,
        alpha: Math.random() * 0.5 + 0.15
      });
    }
    this.animate();
  }

  animate() {
    this.ctx.clearRect(0, 0, this.width, this.height);

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < 0) p.x = this.width;
      if (p.x > this.width) p.x = 0;
      if (p.y < 0) p.y = this.height;
      if (p.y > this.height) p.y = 0;

      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = `rgba(129, 140, 248, ${p.alpha})`;
      this.ctx.fill();

      // Connect proximal nodes
      for (let j = i + 1; j < this.particles.length; j++) {
        const p2 = this.particles[j];
        const dx = p.x - p2.x;
        const dy = p.y - p2.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 110) {
          this.ctx.beginPath();
          this.ctx.moveTo(p.x, p.y);
          this.ctx.lineTo(p2.x, p2.y);
          this.ctx.strokeStyle = `rgba(99, 102, 241, ${0.12 * (1 - dist / 110)})`;
          this.ctx.lineWidth = 0.6;
          this.ctx.stroke();
        }
      }
    }
    requestAnimationFrame(() => this.animate());
  }
}

// Dom Initialization & Video Auto-unblock
document.addEventListener("DOMContentLoaded", () => {
  new ParticleMatrix("particleCanvas");

  const v = document.getElementById("bgVideo");
  if (v) {
    v.muted = true;
    const playPromise = v.play();
    if (playPromise !== undefined) {
      playPromise.catch(() => {
        const forcePlay = () => {
          v.play();
          window.removeEventListener("click", forcePlay);
        };
        window.addEventListener("click", forcePlay, { once: true });
      });
    }
  }

  // Connect Main Form
  const compareForm = document.getElementById("compareForm");
  if (compareForm) {
    compareForm.addEventListener("submit", (e) => {
      e.preventDefault();
      compareNow();
    });
  }

  // Connect Alert Form
  const alertForm = document.getElementById("alertForm");
  if (alertForm) {
    alertForm.addEventListener("submit", (e) => {
      e.preventDefault();
      setAlert();
    });
  }
});

/* --------------------------------------------------------------------------
   Counter Price Animation
   -------------------------------------------------------------------------- */
function animateValue(element, target) {
  if (!target || isNaN(target)) {
    element.textContent = "N/A";
    return;
  }
  const duration = 650;
  const startTime = performance.now();

  function step(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const current = Math.floor(ease * target);
    element.textContent = `₹${current.toLocaleString()}`;
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      element.textContent = `₹${target.toLocaleString()}`;
    }
  }
  requestAnimationFrame(step);
}

/* --------------------------------------------------------------------------
   Core Dispatcher: Scan & Compare Catalogs
   -------------------------------------------------------------------------- */
async function compareNow() {
  const urlInput = document.getElementById("productUrl");
  const loader = document.getElementById("loader");
  const results = document.getElementById("results");
  const btn = document.getElementById("searchBtn");
  const btnText = document.getElementById("btnText");
  const btnIcon = document.getElementById("btnIcon");
  const storesGrid = document.getElementById("storesGrid");

  const url = urlInput.value.trim();
  if (!url) {
    urlInput.focus();
    return;
  }

  // Loading State
  btn.disabled = true;
  btn.style.opacity = "0.7";
  btnText.textContent = "Scanning...";
  btnIcon.className = "fa-solid fa-circle-notch fa-spin";

  loader.classList.remove("hidden");
  results.classList.add("hidden");
  storesGrid.innerHTML = "";

  try {
    const res = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url })
    });

    if (!res.ok) throw new Error("Crawl failure from backend engine.");

    const data = await res.json();
    activeProductPayload = data;

    // 1. Populate Target Showcase Card
    document.getElementById("targetTitle").textContent = data.title || "Matched Entity";
    document.getElementById("targetVariant").textContent = data.variant ? data.variant.toUpperCase() : "STANDARD SKU";
    document.getElementById("targetQuery").textContent = data.query_used || "Auto Vector";

    const targetImgEl = document.getElementById("targetImg");
    targetImgEl.src = data.image_url || "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&q=80";

    const bestPriceEl = document.getElementById("targetBestPrice");
    animateValue(bestPriceEl, data.best_price);

    // 2. Populate Predictive Intelligence Radar
    if (data.prediction) {
      document.getElementById("predDropProb").textContent = data.prediction.drop_probability || "Analyzing Cycle";
      document.getElementById("predBestDay").textContent = data.prediction.best_day_to_buy || "Weekends";
      document.getElementById("predLowestEver").textContent = `₹${(data.prediction.lowest_ever || data.best_price || 0).toLocaleString()}`;
      document.getElementById("predVerdict").textContent = data.prediction.verdict || "Price steady across market.";
    }

    // 3. Render Stores Matrix
    document.getElementById("storeCountBadge").textContent = `${data.stores.length} NODES RESPONDED`;

    data.stores.forEach((store) => {
      const isCheapest = store.is_cheapest;
      const theme = STORE_THEMES[store.platform] || { color: "#818cf8", bg: "rgba(129,140,248,0.15)", icon: "fa-store" };
      const card = document.createElement("div");
      card.className = `store-card ${isCheapest ? 'is-cheapest' : ''}`;

      // Interactive 3D Perspective Tilt on Hover
      card.addEventListener("mousemove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `perspective(600px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg) translateY(-2px)`;
      });
      card.addEventListener("mouseleave", () => {
        card.style.transform = "perspective(600px) rotateY(0deg) rotateX(0deg) translateY(0px)";
      });

      const priceHtml = store.price 
        ? `<div class="card-price-pod">
             <span class="price-sub">OFFER PRICE</span>
             <span class="price-num">₹${store.price.toLocaleString()}</span>
           </div>`
        : `<span class="price-sub">OUT OF STOCK</span>`;

      const bestBadge = isCheapest 
        ? `<span class="cheapest-badge"><i class="fa-solid fa-crown"></i> LOWEST</span>` 
        : "";

      const storeImg = store.image_url || "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&q=80";

      card.innerHTML = `
        <div class="card-top">
          <div class="card-img-wrap">
            <img src="${storeImg}" alt="${store.platform}" class="card-img" onerror="this.src='https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&q=80'">
          </div>
          <div class="card-body">
            <div class="card-header-line">
              <span class="platform-name">
                <span class="store-icon-badge" style="background:${theme.bg}">
                  <i class="fa-solid ${theme.icon}" style="color:${theme.color}"></i>
                </span>
                ${store.platform}
              </span>
              ${bestBadge}
            </div>
            <p class="card-product-title">${store.title || 'Official Catalog Item'}</p>
          </div>
        </div>

        <div class="card-bottom">
          ${priceHtml}
          ${store.url ? `
            <a href="${store.url}" target="_blank" rel="noopener noreferrer" class="deal-btn">
              <span>View Deal</span>
              <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </a>` : ''}
        </div>
      `;
      storesGrid.appendChild(card);
    });

    results.classList.remove("hidden");
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    alert("Crawl error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.style.opacity = "1";
    btnText.textContent = "Scan Catalogs";
    btnIcon.className = "fa-solid fa-arrow-right-long";
    loader.classList.add("hidden");
  }
}

/* --------------------------------------------------------------------------
   WhatsApp Autonomous Price Watch Dispatcher
   -------------------------------------------------------------------------- */
async function setAlert() {
  const targetPriceInput = document.getElementById("targetPriceInput");
  const phoneInput = document.getElementById("phoneInput");
  const alertFeedback = document.getElementById("alertFeedback");
  const alertBtn = document.getElementById("alertSubmitBtn");

  const targetPrice = parseInt(targetPriceInput.value);
  const phone = phoneInput.value.trim();

  if (!targetPrice || targetPrice <= 0) {
    alert("Please enter a valid target price.");
    targetPriceInput.focus();
    return;
  }

  if (!phone || phone.length < 10) {
    alert("Please enter a valid 10-digit WhatsApp phone number.");
    phoneInput.focus();
    return;
  }

  if (!activeProductPayload) {
    alert("Scan a product link first.");
    return;
  }

  alertBtn.disabled = true;
  alertBtn.style.opacity = "0.6";
  alertFeedback.className = "terminal-feedback";
  alertFeedback.textContent = "Registering alert on autonomous background daemon...";
  alertFeedback.classList.remove("hidden");

  try {
    const payload = {
      title: activeProductPayload.title,
      query_used: activeProductPayload.query_used,
      target_price: targetPrice,
      phone_number: phone,
      source_url: document.getElementById("productUrl").value.trim()
    };

    const res = await fetch("/api/track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Registration failed.");

    alertFeedback.className = "terminal-feedback success";
    alertFeedback.textContent = `✓ Watch active: When price hits ₹${targetPrice.toLocaleString()}, you will receive an automated WhatsApp ping.`;
    targetPriceInput.value = "";
    phoneInput.value = "";

  } catch (err) {
    alertFeedback.className = "terminal-feedback error";
    alertFeedback.textContent = "✕ Error: " + err.message;
  } finally {
    alertBtn.disabled = false;
    alertBtn.style.opacity = "1";
  }
}