(function () {
  const loading = document.getElementById("loading");
  const slidesEl = document.getElementById("slides");
  const progressBar = document.getElementById("progressBar");
  const btnClose = document.getElementById("btnClose");
  let carousel = null;

  const TOP_MOVIES_BG = [
    "/static/designs/top_movies_bg_1.png",
    "/static/designs/top_movies_bg_2.png",
    "/static/designs/top_movies_bg_3.png",
    "/static/designs/top_movies_bg_4.png",
    "/static/designs/top_movies_bg_5.png",
    "/static/designs/top_movies_bg_6.png",
  ];

  const TOP_SHOWS_BG = [
    "/static/designs/top_shows_bg_1.png",
    "/static/designs/top_shows_bg_2.png",
    "/static/designs/top_shows_bg_3.png",
    "/static/designs/top_shows_bg_4.png",
    "/static/designs/top_shows_bg_5.png",
    "/static/designs/top_shows_bg_6.png",
  ];

  const PERSONA_ART = {
    curator: "/static/designs/personas/curator.png",
    series_devourer: "/static/designs/personas/series_devourer.png",
    film_buff: "/static/designs/personas/film_buff.png",
    marathon_runner: "/static/designs/personas/marathon_runner.png",
    binge_royalty: "/static/designs/personas/binge_royalty.png",
    night_owl: "/static/designs/personas/night_owl.png",
    early_bird: "/static/designs/personas/early_bird.png",
    completionist: "/static/designs/personas/completionist.png",
    genre_explorer: "/static/designs/personas/genre_explorer.png",
    weekend_warrior: "/static/designs/personas/weekend_warrior.png",
    loyal_rewatcher: "/static/designs/personas/loyal_rewatcher.png",
    dedicated_viewer: "/static/designs/personas/dedicated_viewer.png",
  };

  function formatStreakDate(isoDate) {
    if (!isoDate) return "—";
    const parsed = new Date(`${isoDate}T12:00:00`);
    if (Number.isNaN(parsed.getTime())) return isoDate;
    return parsed.toLocaleDateString("nl-NL", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function posterUrl(thumb) {
    if (!thumb) return null;
    if (thumb.startsWith("http")) return thumb;
    return `/api/poster?path=${encodeURIComponent(thumb)}`;
  }

  function hasTelegramActivity(tg) {
    if (!tg) return false;
    return (
      (tg.film_requests || 0) > 0 ||
      (tg.serie_requests || 0) > 0 ||
      (tg.login_count || 0) > 0
    );
  }

  function createSlide(innerHtml, slideId) {
    const section = document.createElement("section");
    section.className = `slide slide--${slideId}`;
    const bokehCanvas =
      slideId === "welcome" ||
      slideId === "watch-time" ||
      slideId === "series-depth" ||
      slideId === "when-you-watch" ||
      slideId === "longest-streak" ||
      slideId === "server-rank"
        ? '<canvas class="slide-bokeh-canvas" aria-hidden="true"></canvas>'
        : "";
    const summaryDots =
      slideId === "summary"
        ? '<div class="slide-bg slide-bg--dots" aria-hidden="true"></div>'
        : "";
    section.innerHTML = `
      <div class="slide-bg" aria-hidden="true"></div>
      <div class="slide-bg slide-bg--overlay" aria-hidden="true"></div>
      ${summaryDots}
      ${bokehCanvas}
      ${innerHtml}`;
    return section;
  }

  function initWelcomeBokeh(slide) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const canvas = slide.querySelector(".slide-bokeh-canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let particles = [];
    let viewWidth = 0;
    let viewHeight = 0;

    function resize() {
      const w = slide.clientWidth;
      const h = slide.clientHeight;
      if (!w || !h) return false;

      const dpr = window.devicePixelRatio || 1;
      viewWidth = w;
      viewHeight = h;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      return true;
    }

    function createParticle() {
      return {
        x: Math.random() * viewWidth,
        y: Math.random() * viewHeight,
        size: Math.random() * 3 + 1,
        speedX: (Math.random() - 0.5) * 0.2,
        speedY: (Math.random() - 0.5) * 0.2,
        opacity: Math.random() * 0.45 + 0.15,
      };
    }

    function resetParticle(p) {
      Object.assign(p, createParticle());
    }

    function initParticles(count) {
      particles = Array.from({ length: count }, createParticle);
    }

    function animate() {
      if (viewWidth && viewHeight) {
        ctx.clearRect(0, 0, viewWidth, viewHeight);
        particles.forEach((p) => {
          p.x += p.speedX;
          p.y += p.speedY;
          if (p.x < 0 || p.x > viewWidth || p.y < 0 || p.y > viewHeight) {
            resetParticle(p);
          }
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(229, 160, 13, ${p.opacity})`;
          ctx.fill();
        });
      }
      requestAnimationFrame(animate);
    }

    function start() {
      if (!resize()) {
        requestAnimationFrame(start);
        return;
      }
      initParticles(40);
      animate();
    }

    const resizeObserver = new ResizeObserver(() => {
      if (resize()) {
        particles.forEach(resetParticle);
      }
    });
    resizeObserver.observe(slide);
    start();
  }

  function initWatchTimeBokeh(slide) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const canvas = slide.querySelector(".slide-bokeh-canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let particles = [];
    let viewWidth = 0;
    let viewHeight = 0;
    let started = false;

    function resize() {
      const w = slide.clientWidth;
      const h = slide.clientHeight;
      if (!w || !h) return false;

      const dpr = window.devicePixelRatio || 1;
      viewWidth = w;
      viewHeight = h;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      return true;
    }

    function createParticle(yRange) {
      const yMax = yRange ?? viewHeight;
      return {
        x: Math.random() * viewWidth,
        y: Math.random() * yMax,
        size: Math.random() * 2 + 0.5,
        speedY: Math.random() * -0.5 - 0.2,
        opacity: Math.random() * 0.5,
      };
    }

    function recycleParticle(p) {
      Object.assign(p, createParticle());
      p.y = viewHeight + Math.random() * 20;
    }

    function fillParticles(count) {
      particles = Array.from({ length: count }, () => createParticle());
    }

    function animate() {
      if (viewWidth && viewHeight) {
        ctx.clearRect(0, 0, viewWidth, viewHeight);
        particles.forEach((p) => {
          p.y += p.speedY;
          if (p.y < -10) recycleParticle(p);
          ctx.fillStyle = `rgba(255, 189, 73, ${p.opacity})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fill();
        });
      }
      requestAnimationFrame(animate);
    }

    function start() {
      if (started) return;
      if (!resize()) {
        requestAnimationFrame(start);
        return;
      }
      started = true;
      fillParticles(40);
      animate();
    }

    const resizeObserver = new ResizeObserver(() => {
      if (!started || !resize()) return;
      particles.forEach((p) => Object.assign(p, createParticle()));
    });
    resizeObserver.observe(slide);

    const visibilityObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) start();
      },
      { threshold: 0.35 }
    );
    visibilityObserver.observe(slide);
  }

  function initIconExplosion(slide, selector, iconTypes) {
    const container = slide.querySelector(selector);
    if (!container || container.dataset.ready) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function populate() {
      if (container.dataset.ready) return;
      container.dataset.ready = "1";

      for (let i = 0; i < 40; i++) {
        const span = document.createElement("span");
        span.className = "material-symbols-outlined";
        span.textContent = iconTypes[Math.floor(Math.random() * iconTypes.length)];

        const rotation = Math.random() * 360;
        span.style.left = `${Math.random() * 100}%`;
        span.style.top = `${Math.random() * 100}%`;
        span.style.fontSize = `${20 + Math.random() * 60}px`;
        span.style.transform = `rotate(${rotation}deg)`;
        span.style.opacity = String(0.05 + Math.random() * 0.15);

        if (!reducedMotion) {
          span.animate(
            [
              { transform: `rotate(${rotation}deg) translateY(0px)` },
              { transform: `rotate(${rotation + 20}deg) translateY(-40px)` },
              { transform: `rotate(${rotation}deg) translateY(0px)` },
            ],
            {
              duration: 5000 + Math.random() * 10000,
              iterations: Infinity,
              delay: Math.random() * 5000,
              easing: "linear",
            }
          );
        }

        container.appendChild(span);
      }
    }

    const visibilityObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) populate();
      },
      { threshold: 0.35 }
    );
    visibilityObserver.observe(slide);
  }

  const SUMMARY_DOT_DRIFTS = [
    "summary-dot--drift-a",
    "summary-dot--drift-b",
    "summary-dot--drift-c",
    "summary-dot--drift-d",
    "summary-dot--drift-e",
    "summary-dot--drift-f",
    "summary-dot--drift-g",
    "summary-dot--drift-h",
  ];

  function initSummaryDots(slide) {
    const container = slide.querySelector(".slide-bg--dots");
    if (!container || container.childElementCount > 0) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const spacing = 24;

    const w = slide.offsetWidth;
    const h = slide.offsetHeight;
    if (w < 1 || h < 1) return;

    const cols = Math.ceil(w / spacing) + 1;
    const rows = Math.ceil(h / spacing) + 1;
    const fragment = document.createDocumentFragment();

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const dot = document.createElement("span");
        dot.className = "summary-dot";
        dot.style.left = `${col * spacing}px`;
        dot.style.top = `${row * spacing}px`;

        if (!reducedMotion) {
          dot.classList.add(
            SUMMARY_DOT_DRIFTS[Math.floor(Math.random() * SUMMARY_DOT_DRIFTS.length)]
          );
          const duration = 1100 + Math.random() * 900;
          dot.style.animationDuration = `${duration}ms`;
          dot.style.animationDelay = `${Math.random() * duration}ms`;
        }

        fragment.appendChild(dot);
      }
    }

    container.appendChild(fragment);
  }

  function setupSummaryDots(slide) {
    const container = slide.querySelector(".slide-bg--dots");
    if (!container || slide.dataset.summaryDotsWatching) return;
    slide.dataset.summaryDotsWatching = "1";

    const tryInit = () => initSummaryDots(slide);
    tryInit();

    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(tryInit);
      observer.observe(slide);
    }

  }

  function ensureSummaryDots() {
    slidesEl.querySelectorAll(".slide--summary").forEach(setupSummaryDots);
  }

  function initTotalPlaysIcons(slide) {
    initIconExplosion(slide, ".play-icon-explosion", [
      "play_arrow",
      "movie",
      "tv",
      "theaters",
      "video_library",
    ]);
  }

  function initTelegramDeco(slide) {
    const container = slide.querySelector(".tg-deco");
    if (!container || container.dataset.ready) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const positions = [
      { top: "8%", left: "12%", delay: "0s", size: "5.5rem", opacity: 0.12 },
      { top: "18%", left: "72%", delay: "-1.5s", size: "4.5rem", opacity: 0.18 },
      { top: "32%", left: "38%", delay: "-3s", size: "6.5rem", opacity: 0.1 },
      { top: "48%", left: "8%", delay: "-4.5s", size: "5rem", opacity: 0.16 },
      { top: "55%", left: "82%", delay: "-2s", size: "7rem", opacity: 0.14 },
      { top: "68%", left: "28%", delay: "-5.5s", size: "4rem", opacity: 0.2 },
      { top: "74%", left: "58%", delay: "-1s", size: "5.5rem", opacity: 0.11 },
      { top: "85%", left: "14%", delay: "-3.5s", size: "6rem", opacity: 0.15 },
      { top: "88%", left: "78%", delay: "-6s", size: "4.5rem", opacity: 0.17 },
      { top: "22%", left: "52%", delay: "-2.5s", size: "3.5rem", opacity: 0.09 },
      { top: "42%", left: "92%", delay: "-4s", size: "3rem", opacity: 0.13 },
      { top: "62%", left: "48%", delay: "-0.5s", size: "8rem", opacity: 0.08 },
    ];

    function populate() {
      if (container.dataset.ready) return;
      container.dataset.ready = "1";

      positions.forEach((pos) => {
        const wrap = document.createElement("span");
        wrap.className = "tg-deco__icon-wrap";
        wrap.style.top = pos.top;
        wrap.style.left = pos.left;

        const span = document.createElement("span");
        span.className = "material-symbols-outlined tg-deco__icon";
        span.textContent = "send";
        span.style.fontSize = pos.size;
        span.style.opacity = String(pos.opacity);

        if (!reducedMotion) {
          wrap.style.animationDelay = pos.delay;
          span.style.animationDelay = pos.delay;
        } else {
          wrap.style.animation = "none";
          span.style.animation = "none";
        }

        wrap.appendChild(span);
        container.appendChild(wrap);
      });
    }

    const visibilityObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) populate();
      },
      { threshold: 0.35 }
    );
    visibilityObserver.observe(slide);
  }

  function initTelegramProgressBar(slide) {
    const fill = slide.querySelector(".tg-completion__fill");
    if (!fill) return;

    const target = Number(fill.dataset.target) || 0;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function reset() {
      fill.style.transition = "none";
      fill.style.width = "0%";
    }

    function animate() {
      if (reducedMotion) {
        fill.style.transition = "none";
        fill.style.width = `${target}%`;
        return;
      }
      fill.style.transition = "none";
      fill.style.width = "0%";
      void fill.offsetWidth;
      fill.style.transition = "";
      requestAnimationFrame(() => {
        fill.style.width = `${target}%`;
      });
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) animate();
          else reset();
        });
      },
      { threshold: 0.35 }
    );
    observer.observe(slide);
  }

  function initPersonaConfetti(slide) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const colors = ["#ffbd49", "#e5a00d", "#96ceff", "#ff6b8a", "#fff8e7", "#49b5ff"];
    let activeLayer = null;
    let cleanupTimer = null;

    function clearConfetti() {
      if (cleanupTimer) {
        window.clearTimeout(cleanupTimer);
        cleanupTimer = null;
      }
      activeLayer?.remove();
      activeLayer = null;
    }

    function burst() {
      clearConfetti();

      const layer = document.createElement("div");
      layer.className = "persona-confetti";
      layer.setAttribute("aria-hidden", "true");
      slide.appendChild(layer);
      activeLayer = layer;

      for (let i = 0; i < 48; i++) {
        const piece = document.createElement("span");
        piece.className = "persona-confetti__piece";
        const size = 6 + Math.random() * 8;
        const startX = 20 + Math.random() * 60;
        const drift = (Math.random() - 0.5) * 120;
        const delay = Math.random() * 400;
        const duration = 1800 + Math.random() * 1200;
        piece.style.left = `${startX}%`;
        piece.style.top = "-12px";
        piece.style.width = `${size}px`;
        piece.style.height = `${Math.random() > 0.5 ? size : size * 0.45}px`;
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.borderRadius = Math.random() > 0.6 ? "50%" : "2px";
        piece.style.setProperty("--drift", `${drift}px`);
        piece.style.animation = `persona-confetti-fall ${duration}ms ease-out ${delay}ms forwards`;
        layer.appendChild(piece);
      }

      cleanupTimer = window.setTimeout(clearConfetti, 3500);
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) burst();
          else clearConfetti();
        });
      },
      { threshold: 0.35 }
    );
    observer.observe(slide);
  }

  function initTopListMotion(slide) {
    const images = slide.querySelectorAll(".poster-stack img");
    if (!images.length || slide.dataset.posterMotionReady) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function start() {
      if (slide.dataset.posterMotionReady) return;
      slide.dataset.posterMotionReady = "1";

      images.forEach((img, index) => {
        if (reducedMotion) return;

        const drift = 8 + Math.random() * 12;
        const tilt = (Math.random() - 0.5) * 6;
        img.animate(
          [
            { transform: `translateY(0px) rotate(${tilt}deg)` },
            { transform: `translateY(-${drift}px) rotate(${-tilt}deg)` },
            { transform: `translateY(0px) rotate(${tilt}deg)` },
          ],
          {
            duration: 4500 + Math.random() * 4000,
            iterations: Infinity,
            delay: index * 350 + Math.random() * 1200,
            easing: "ease-in-out",
          }
        );
      });
    }

    const visibilityObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) start();
      },
      { threshold: 0.35 }
    );
    visibilityObserver.observe(slide);
  }

  function slideMain(html, layout) {
    const cls = layout ? `slide-main slide-main--${layout}` : "slide-main";
    return `<main class="${cls}">${html}</main>`;
  }

  function buildPosterStack(items) {
    const thumbs = (items || [])
      .slice(0, 6)
      .map((item) => posterUrl(item.thumb))
      .filter(Boolean);
    if (!thumbs.length) return "";
    return `<div class="poster-stack" aria-hidden="true">${thumbs
      .map((src) => `<img src="${escapeHtml(src)}" alt="" loading="lazy">`)
      .join("")}</div>`;
  }

  function buildTopMoviesPosterBg() {
    return `<div class="poster-stack poster-stack--top-movies" aria-hidden="true">${TOP_MOVIES_BG.map(
      (src) => `<img src="${src}" alt="" loading="lazy">`
    ).join("")}</div>`;
  }

  function buildTopShowsPosterBg() {
    return `<div class="poster-stack poster-stack--top-shows" aria-hidden="true">${TOP_SHOWS_BG.map(
      (src) => `<img src="${src}" alt="" loading="lazy">`
    ).join("")}</div>`;
  }

  function buildServerVsPosterBg(serverThumb, userThumb) {
    const thumbs = [serverThumb, userThumb]
      .map((thumb) => posterUrl(thumb))
      .filter(Boolean);
    const sources = thumbs.length
      ? Array.from({ length: 6 }, (_, i) => thumbs[i % thumbs.length])
      : TOP_SHOWS_BG;
    return `<div class="poster-stack poster-stack--server-vs" aria-hidden="true">${sources
      .map((src) => `<img src="${escapeHtml(src)}" alt="" loading="lazy">`)
      .join("")}</div>`;
  }

  function buildRankList(items, playsLabel, withPoster) {
    if (!items.length) return "";
    let html = '<div class="rank-list">';
    items.forEach((item, i) => {
      const hero = i === 0 ? " rank-item--hero" : "";
      const opacity = i === 0 ? "" : ` style="opacity:${Math.max(0.55, 1 - i * 0.12)}"`;
      const thumb = withPoster && posterUrl(item.thumb);
      const img = thumb
        ? `<img src="${escapeHtml(thumb)}" alt="" loading="lazy">`
        : `<div style="width:48px;height:72px;border-radius:8px;background:var(--surface-container-high)"></div>`;
      const verified =
        i === 0
          ? '<span class="material-symbols-outlined" style="color:var(--primary);font-variation-settings:\'FILL\' 1">verified</span>'
          : "";
      const metaStyle = i === 0 ? "color:var(--primary)" : "color:var(--on-surface-variant)";
      html += `<div class="rank-item glass-card${hero}"${opacity}>
        <span class="rank-num">${i + 1}</span>
        ${img}
        <div class="rank-body">
          <h3>${escapeHtml(item.title)}</h3>
          <p class="rank-meta" style="${metaStyle}">${item.plays} ${playsLabel.toUpperCase()}</p>
        </div>
        ${verified}
      </div>`;
    });
    html += "</div>";
    return html;
  }

  const GENRE_ICONS = {
    action: "bolt",
    adventure: "explore",
    animation: "animation",
    comedy: "sentiment_very_satisfied",
    crime: "policy",
    documentary: "menu_book",
    drama: "theater_comedy",
    family: "family_rest",
    fantasy: "auto_awesome",
    history: "history_edu",
    horror: "skull",
    music: "music_note",
    mystery: "help",
    romance: "favorite",
    "science fiction": "rocket_launch",
    "sci-fi": "rocket_launch",
    scifi: "rocket_launch",
    thriller: "visibility",
    war: "military_tech",
    western: "landscape",
    biography: "person",
    sport: "sports",
    sports: "sports",
    superhero: "shield",
    suspense: "visibility",
    "tv movie": "live_tv",
    news: "newspaper",
    reality: "videocam",
    soap: "soap",
    talk: "mic",
    "film-noir": "dark_mode",
    kids: "child_care",
    children: "child_care",
  };

  const GENRE_ICON_POOL = [...new Set(Object.values(GENRE_ICONS))];

  function initGenreIconExplosion(slide) {
    initIconExplosion(slide, ".genre-icon-explosion", GENRE_ICON_POOL);
  }

  function genreIcon(name) {
    const key = (name || "").toLowerCase().trim();
    if (GENRE_ICONS[key]) return GENRE_ICONS[key];
    if (key.includes("sci")) return "rocket_launch";
    if (key.includes("romance") || key.includes("romant")) return "favorite";
    if (key.includes("horror")) return "skull";
    if (key.includes("comedy") || key.includes("komedie")) return "sentiment_very_satisfied";
    if (key.includes("drama")) return "theater_comedy";
    if (key.includes("action") || key.includes("actie")) return "bolt";
    if (key.includes("document")) return "menu_book";
    if (key.includes("thriller")) return "visibility";
    if (key.includes("crime") || key.includes("misdaad")) return "policy";
    if (key.includes("fantasy")) return "auto_awesome";
    if (key.includes("anim")) return "animation";
    if (key.includes("war") || key.includes("oorlog")) return "military_tech";
    if (key.includes("music") || key.includes("muziek")) return "music_note";
    if (key.includes("family") || key.includes("familie")) return "family_rest";
    return "movie";
  }

  function genreToneClass(rankIndex) {
    return rankIndex % 2 === 0 ? "genre-tone--odd" : "genre-tone--even";
  }

  function buildGenreLayout(genres, statLabel, compactLabel) {
    const top = genres.slice(0, 5);
    if (!top.length) return "";

    let html = '<div class="genre-layout">';

    const hero = top[0];
    const heroIcon = genreIcon(hero.name);
    html += `<div class="genre-card genre-card--hero glass-card ${genreToneClass(0)}">
      <div class="genre-card__main">
        <div class="genre-icon genre-icon--lg">
          <span class="material-symbols-outlined nav-icon-fill">${heroIcon}</span>
        </div>
        <div class="genre-card__copy">
          <p class="genre-rank-label">#1 Genre</p>
          <h3 class="genre-name">${escapeHtml(hero.name)}</h3>
        </div>
      </div>
      <div class="genre-card__stat">
        <span class="genre-count">${hero.plays.toLocaleString("nl-NL")}</span>
        <span class="genre-count-label">${escapeHtml(statLabel)}</span>
      </div>
    </div>`;

    for (let i = 1; i < 3 && i < top.length; i += 1) {
      const g = top[i];
      const icon = genreIcon(g.name);
      const opacity = i === 1 ? 0.9 : 0.8;
      html += `<div class="genre-card genre-card--row glass-card ${genreToneClass(i)}" style="opacity:${opacity}">
        <div class="genre-card__main">
          <div class="genre-icon genre-icon--md">
            <span class="material-symbols-outlined">${icon}</span>
          </div>
          <h3 class="genre-name">${escapeHtml(g.name)}</h3>
        </div>
        <div class="genre-card__stat">
          <span class="genre-count">${g.plays.toLocaleString("nl-NL")}</span>
          <span class="genre-count-label">${escapeHtml(statLabel)}</span>
        </div>
      </div>`;
    }

    if (top.length > 3) {
      html += '<div class="genre-grid">';
      for (let i = 3; i < top.length; i += 1) {
        const g = top[i];
        const icon = genreIcon(g.name);
        const opacity = i === 3 ? 0.7 : 0.6;
        html += `<div class="genre-card genre-card--compact glass-card ${genreToneClass(i)}" style="opacity:${opacity}">
          <div class="genre-icon genre-icon--sm">
            <span class="material-symbols-outlined">${icon}</span>
          </div>
          <h4 class="genre-name-compact">${escapeHtml(g.name)}</h4>
          <p class="genre-meta-compact">${g.plays.toLocaleString("nl-NL")} ${escapeHtml(compactLabel)}</p>
        </div>`;
      }
      html += "</div>";
    }

    html += "</div>";
    return html;
  }

  function formatRankHours(hours) {
    return `${Number(hours).toLocaleString("nl-NL")} u`;
  }

  function buildComparisonCaption(d, serverTitle, userTitle, same) {
    if (d.comparison_caption) return d.comparison_caption;
    if (same) {
      return `Iedereen op de server draaide ${serverTitle} — jij inclusief. Great minds think alike.`;
    }
    if (d.user_comparison_reason === "first_played") {
      return `Terwijl de server massaal naar ${serverTitle} keek, startte jij het jaar met ${userTitle}.`;
    }
    return `Terwijl de server naar ${serverTitle} keek, was ${userTitle} jouw nummer één.`;
  }

  function buildComparisonHeadline(d, same) {
    if (same) {
      return 'Je bent <span class="text-primary">perfect in sync</span> met de server.';
    }
    const accent = d.comparison_headline_accent || "eigenzinnige";
    return `Je hebt een <span class="text-primary">${escapeHtml(accent)}</span> smaak.`;
  }

  function buildVsPosterCard(side, title, thumb, badge) {
    const url = posterUrl(thumb);
    const img = url
      ? `<img src="${escapeHtml(url)}" alt="" loading="lazy">`
      : `<div class="vs-poster__placeholder"><span class="material-symbols-outlined">tv</span></div>`;
    const sideClass = side === "user" ? " vs-poster-card--user" : " vs-poster-card--server";
    const badgeClass =
      side === "user" ? " vs-poster-card__badge--user" : " vs-poster-card__badge--server";
    return `<div class="vs-poster-card${sideClass}">
      <div class="vs-poster-card__frame">
        <span class="vs-poster-card__badge${badgeClass}">${escapeHtml(badge)}</span>
        <div class="vs-poster-card__poster glass-card">${img}</div>
      </div>
      <p class="vs-poster-card__title">${escapeHtml(title)}</p>
    </div>`;
  }

  function buildTelegramCompletionNote(percent) {
    if (percent >= 80) return "Je houdt je wachtrij goed bij!";
    if (percent >= 50) return "Meer dan de helft van je aanvragen heb je al bekeken.";
    if (percent > 0) return "Er staat nog genoeg op je lijst.";
    return "Tijd om je aanvragen af te werken.";
  }

  function buildTelegramSlide(tg) {
    const films = tg.film_requests || 0;
    const series = tg.serie_requests || 0;
    const logins = tg.login_count || 0;
    const requested = (tg.movies_requested || 0) + (tg.series_requested || 0);
    const watched = (tg.movies_watched || 0) + (tg.series_watched || 0);
    const percent = requested > 0 ? Math.round((watched / requested) * 100) : 0;
    const completionBlock =
      requested > 0
        ? `<div class="tg-completion glass-card">
                <div class="tg-completion__head">
                  <span class="tg-completion__pct">${percent}%</span>
                  <span class="tg-completion__label">voltooid</span>
                </div>
                <div class="tg-completion__track">
                  <div class="tg-completion__fill" data-target="${percent}"></div>
                </div>
                <p class="tg-completion__note">${escapeHtml(buildTelegramCompletionNote(percent))}</p>
              </div>`
        : "";

    return `<div class="tg-deco" aria-hidden="true"></div>
            <div class="tg-layout">
              <div class="tg-header stack-sm">
                <span class="label-md label-md--wide tg-header__label">Community vragen</span>
                <h2 class="tg-title">Telegram bot</h2>
              </div>
              <div class="tg-row tg-row--types">
                <div class="tg-stat-card glass-card">
                  <span class="material-symbols-outlined tg-stat-card__icon tg-stat-card__icon--primary">movie</span>
                  <h3 class="tg-stat-card__type">Films</h3>
                  <p class="tg-stat-card__num">${films.toLocaleString("nl-NL")}</p>
                  <p class="tg-stat-card__meta">aanvragen</p>
                </div>
                <div class="tg-stat-card glass-card">
                  <span class="material-symbols-outlined tg-stat-card__icon tg-stat-card__icon--tertiary">tv</span>
                  <h3 class="tg-stat-card__type">Series</h3>
                  <p class="tg-stat-card__num">${series.toLocaleString("nl-NL")}</p>
                  <p class="tg-stat-card__meta">aanvragen</p>
                </div>
              </div>
              <div class="tg-row tg-row--conv">
                <div class="tg-conv-card glass-card">
                  <span class="material-symbols-outlined tg-conv-card__icon tg-conv-card__icon--tertiary">send_and_archive</span>
                  <p class="tg-conv-card__num">${logins.toLocaleString("nl-NL")}</p>
                  <p class="tg-conv-card__meta">logins</p>
                </div>
                <div class="tg-conv-card glass-card">
                  <span class="material-symbols-outlined tg-conv-card__icon tg-conv-card__icon--primary">visibility</span>
                  <p class="tg-conv-card__num">${watched.toLocaleString("nl-NL")}</p>
                  <p class="tg-conv-card__meta">bekeken</p>
                </div>
              </div>
              ${completionBlock}
            </div>`;
  }

  function buildRankContextRows(entries) {
    if (!entries || !entries.length) return "";

    return entries
      .map((entry) => {
        const youClass = entry.is_you ? " rank-row--you" : "";
        const edgeClass = entry.is_you
          ? ""
          : entry.position_label === "Eén plek hoger"
            ? " rank-row--above"
            : " rank-row--below";
        return `<div class="rank-row glass-card${youClass}${edgeClass}">
          <div class="rank-row__main">
            <span class="rank-row__num">#${entry.rank}</span>
            <span class="rank-row__avatar" aria-hidden="true">
              <span class="material-symbols-outlined">${entry.is_you ? "account_circle" : "person"}</span>
            </span>
            <span class="rank-row__label">${escapeHtml(entry.position_label)}</span>
          </div>
          <span class="rank-row__hours">${formatRankHours(entry.watch_hours)}</span>
        </div>`;
      })
      .join("");
  }

  function formatMoviesTvRatio(moviePlays, tvPlays) {
    const movies = Math.max(0, moviePlays);
    const episodes = Math.max(0, tvPlays);
    if (movies === 0 && episodes === 0) return "—";
    if (movies === 0) return "0:1";
    if (episodes === 0) return "1:0";
    if (movies >= episodes) {
      return `${Math.ceil(movies / episodes)}:1`;
    }
    return `1:${Math.ceil(episodes / movies)}`;
  }

  function buildDonutChart(moviePlays, tvPlays) {
    const total = moviePlays + tvPlays || 1;
    const tvPct = tvPlays / total;
    const moviePct = moviePlays / total;
    const r = 40;
    const c = 2 * Math.PI * r;
    const tvLen = c * tvPct;
    const movieLen = c * moviePct;
    const ratio = formatMoviesTvRatio(moviePlays, tvPlays);
    return `
      <div class="chart-wrap">
        <div class="chart-mesh" aria-hidden="true"></div>
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <circle cx="50" cy="50" r="${r}" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="8"/>
          <circle cx="50" cy="50" r="${r}" fill="none" stroke="#ffbd49" stroke-width="8"
            stroke-dasharray="${tvLen} ${c}" stroke-linecap="round"/>
          <circle cx="50" cy="50" r="${r}" fill="none" stroke="#96ceff" stroke-width="8"
            stroke-dasharray="${movieLen} ${c}" stroke-dashoffset="-${tvLen}" stroke-linecap="round"/>
        </svg>
        <div class="chart-center">
          <span class="chart-ratio">${ratio}</span>
          <span class="chart-ratio-label">Statistieken</span>
        </div>
      </div>`;
  }

  const WEEKDAY_ORDER = [
    "maandag",
    "dinsdag",
    "woensdag",
    "donderdag",
    "vrijdag",
    "zaterdag",
    "zondag",
  ];

  function daysInMonth(year, monthIndex) {
    return new Date(year, monthIndex, 0).getDate();
  }

  function normalizeDailyPlays(raw) {
    if (!Array.isArray(raw)) return [];
    return raw.map((value) => {
      if (typeof value === "boolean") return value ? 1 : 0;
      const count = Number(value);
      return Number.isFinite(count) && count > 0 ? Math.floor(count) : 0;
    });
  }

  function playCountToLevel(count, maxCount) {
    if (!count || count <= 0) return 1;
    if (maxCount <= 1) return 5;
    const ratio = count / maxCount;
    if (ratio <= 0.25) return 2;
    if (ratio <= 0.5) return 3;
    if (ratio <= 0.75) return 4;
    return 5;
  }

  function buildHeatmapGrid(dailyPlays, firstWeekday, monthIndex, year) {
    let plays = normalizeDailyPlays(dailyPlays);
    const offset = Number.isFinite(Number(firstWeekday)) ? Number(firstWeekday) : 0;

    if (!plays.length && monthIndex) {
      const length = daysInMonth(year, monthIndex);
      plays = Array.from({ length }, () => 0);
    }

    if (!plays.length) {
      return "";
    }

    const maxPlays = Math.max(...plays, 0);
    const cells = [];
    for (let i = 0; i < offset; i += 1) {
      cells.push('<div class="heat-dot heat-dot--empty" aria-hidden="true"></div>');
    }

    plays.forEach((count) => {
      const level = playCountToLevel(count, maxPlays);
      const title = count > 0 ? ` title="${count} keer"` : "";
      cells.push(`<div class="heat-dot heat-dot--${level}"${title}></div>`);
    });

    return cells.join("");
  }

  const WEEKDAY_SHORT = ["ma", "di", "wo", "do", "vr", "za", "zo"];

  const DUTCH_MONTH_TO_INDEX = {
    januari: 1,
    februari: 2,
    maart: 3,
    april: 4,
    mei: 5,
    juni: 6,
    juli: 7,
    augustus: 8,
    september: 9,
    oktober: 10,
    november: 11,
    december: 12,
  };

  function resolveBusiestMonthIndex(monthName, monthIndex) {
    if (Number.isFinite(Number(monthIndex))) {
      return Number(monthIndex);
    }
    if (!monthName) return null;
    return DUTCH_MONTH_TO_INDEX[monthName.toLowerCase()] || null;
  }

  function normalizeWeekdayCounts(playsByWeekday) {
    const raw = Array.isArray(playsByWeekday) ? playsByWeekday : [];
    return Array.from({ length: 7 }, (_, index) => {
      const value = Number(raw[index]);
      return Number.isFinite(value) ? value : 0;
    });
  }

  function buildWeekdayChart(playsByWeekday, peakDay) {
    const counts = normalizeWeekdayCounts(playsByWeekday);
    const max = Math.max(...counts, 1);
    const peakIdx = WEEKDAY_ORDER.indexOf((peakDay || "").toLowerCase());

    const width = 320;
    const height = 88;
    const padX = 14;
    const padTop = 18;
    const padBottom = 22;
    const plotW = width - padX * 2;
    const plotH = height - padTop - padBottom;

    const bottomY = padTop + plotH;
    const points = counts.map((count, index) => ({
      x: padX + (index / 6) * plotW,
      y: padTop + plotH - (count / max) * plotH,
      count,
      index,
    }));

    const flatLinePath = points
      .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${bottomY.toFixed(1)}`)
      .join(" ");
    const flatAreaPath = `${flatLinePath} L ${points[6].x.toFixed(1)} ${bottomY.toFixed(1)} L ${points[0].x.toFixed(1)} ${bottomY.toFixed(1)} Z`;

    const pointPayload = points.map((point) => ({
      x: point.x,
      y: point.y,
      count: point.count,
      index: point.index,
    }));

    const dots = points
      .map((point) => {
        const isPeak = point.index === peakIdx;
        const r = isPeak ? 4.5 : 3;
        const label = point.count.toLocaleString("nl-NL");
        return `<g class="${isPeak ? "weekday-line-chart__point--peak" : ""}">
          <circle class="weekday-line-chart__dot" cx="${point.x.toFixed(1)}" cy="${bottomY.toFixed(1)}" data-target-y="${point.y.toFixed(1)}" r="${r}"></circle>
          <text class="weekday-line-chart__value" x="${point.x.toFixed(1)}" y="${(bottomY - 8).toFixed(1)}" data-target-y="${(point.y - 8).toFixed(1)}" text-anchor="middle" opacity="0">${label}</text>
        </g>`;
      })
      .join("");

    const labels = points
      .map(
        (point) =>
          `<text class="weekday-line-chart__day" x="${point.x.toFixed(1)}" y="${(height - 4).toFixed(1)}" text-anchor="middle">${WEEKDAY_SHORT[point.index]}</text>`
      )
      .join("");

    return `<div class="weekday-line-chart" data-bottom-y="${bottomY}" data-points="${escapeHtml(JSON.stringify(pointPayload))}">
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
        <path class="weekday-line-chart__area" d="${flatAreaPath}"></path>
        <path class="weekday-line-chart__line" d="${flatLinePath}"></path>
        ${dots}
        ${labels}
      </svg>
    </div>`;
  }

  function buildPeakClock(peakHour, inline) {
    if (peakHour === null || peakHour === undefined) {
      return "";
    }
    const hourAngle = (peakHour % 12) * 30;
    const clockClass = inline ? "when-clock when-clock--inline" : "when-clock";
    return `<div class="${clockClass}">
      <div class="when-clock__face">
        <div class="when-clock__hand when-clock__hand--hour" style="--start-angle:${hourAngle}deg"></div>
        <div class="when-clock__hand when-clock__hand--minute"></div>
        <div class="when-clock__center"></div>
      </div>
    </div>`;
  }

  function applyWeekdayChartProgress(chart, progress) {
    const bottomY = Number(chart.dataset.bottomY);
    const points = JSON.parse(chart.getAttribute("data-points") || "[]");
    if (!points.length || !Number.isFinite(bottomY)) return;

    const eased = 1 - Math.pow(1 - Math.min(1, Math.max(0, progress)), 3);
    const line = chart.querySelector(".weekday-line-chart__line");
    const area = chart.querySelector(".weekday-line-chart__area");
    const dots = chart.querySelectorAll(".weekday-line-chart__dot");
    const values = chart.querySelectorAll(".weekday-line-chart__value");

    const current = points.map((point) => ({
      x: point.x,
      y: bottomY + (point.y - bottomY) * eased,
    }));

    dots.forEach((dot, index) => {
      dot.setAttribute("cy", current[index].y.toFixed(1));
    });
    values.forEach((text, index) => {
      const targetY = Number(text.dataset.targetY);
      const startY = bottomY - 8;
      const y = startY + (targetY - startY) * eased;
      text.setAttribute("y", y.toFixed(1));
      text.setAttribute("opacity", String(eased));
    });

    const linePath = current
      .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
      .join(" ");
    line?.setAttribute("d", linePath);
    area?.setAttribute(
      "d",
      `${linePath} L ${points[6].x.toFixed(1)} ${bottomY.toFixed(1)} L ${points[0].x.toFixed(1)} ${bottomY.toFixed(1)} Z`
    );
  }

  function initWeekdayChart(slide) {
    const chart = slide.querySelector(".weekday-line-chart");
    if (!chart) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const duration = 1400;
    let animFrame = null;
    let animStart = 0;

    function cancelAnim() {
      if (animFrame) {
        cancelAnimationFrame(animFrame);
        animFrame = null;
      }
    }

    function reset() {
      cancelAnim();
      applyWeekdayChartProgress(chart, 0);
    }

    function play() {
      if (reducedMotion) {
        applyWeekdayChartProgress(chart, 1);
        return;
      }
      cancelAnim();
      applyWeekdayChartProgress(chart, 0);
      animStart = performance.now();

      function frame(now) {
        const progress = Math.min(1, (now - animStart) / duration);
        applyWeekdayChartProgress(chart, progress);
        if (progress < 1) {
          animFrame = requestAnimationFrame(frame);
        } else {
          animFrame = null;
        }
      }

      animFrame = requestAnimationFrame(frame);
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) play();
          else reset();
        });
      },
      { threshold: 0.35 }
    );
    observer.observe(slide);
  }

  function initWhenYouWatchWaves(slide) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const paths = slide.querySelectorAll(".when-waves path");
    if (!paths.length) return;

    let offset = 0;
    let running = false;

    function animate() {
      if (!running) return;
      offset += 0.05;
      paths.forEach((path, index) => {
        const shift = Math.sin(offset + index) * 5;
        path.setAttribute("transform", `translate(0, ${shift})`);
      });
      requestAnimationFrame(animate);
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.some((entry) => entry.isIntersecting);
        if (visible && !running) {
          running = true;
          animate();
        } else if (!visible) {
          running = false;
        }
      },
      { threshold: 0.35 }
    );
    observer.observe(slide);
  }

  function bingeNarrative(moviePlays, tvPlays) {
    const LOW_THRESHOLD = 5;

    if (tvPlays === 0 && moviePlays > 0) {
      return "Pure filmmodus: geen series, alleen films.";
    }
    if (moviePlays === 0 && tvPlays > 0) {
      return "Pure seriesmodus: geen films, alleen afleveringen.";
    }
    if (moviePlays > tvPlays) {
      if (tvPlays > 0 && tvPlays < LOW_THRESHOLD) {
        return "Pure filmmodus: (bijna) geen series, alleen films.";
      }
      const ratio = Math.round(moviePlays / tvPlays);
      return `Films stonden centraal — ${ratio} films voor elke aflevering.`;
    }
    if (tvPlays > moviePlays) {
      if (moviePlays > 0 && moviePlays < LOW_THRESHOLD) {
        return "Pure seriesmodus: (bijna) geen films, alleen afleveringen.";
      }
      const ratio = Math.round(tvPlays / moviePlays);
      return `Je bent een echte serie-bingewatcher. Voor elke film keek je maar liefst ${ratio} afleveringen.`;
    }
    return "Een gebalanceerde mix van films en series.";
  }

  function buildSlides(d) {
    const slides = [];
    const year = d.year;
    const tgActive = hasTelegramActivity(d.telegram);

    slides.push(
      createSlide(
        slideMain(`
          <div class="avatar-wrap">
            <div class="avatar-ring"></div>
            ${
              d.avatar_url
                ? `<img src="${escapeHtml(d.avatar_url)}" alt="${escapeHtml(d.display_name)}">`
                : `<img class="avatar-default" src="/static/images/default-avatar.svg" alt="">`
            }
          </div>
          <div class="stack-sm welcome-copy">
            <h2 class="headline-lg welcome-greeting">Hoi ${escapeHtml(d.display_name)}!</h2>
            <p class="display-lg welcome-title">Jouw ${year}<br>Plex Wrapped</p>
            <p class="body-md">Laten we kijken naar jouw jaar in films en series.</p>
          </div>
        `),
        "welcome"
      )
    );

    if (!d.has_watch_history && !tgActive) {
      slides.push(
        createSlide(
          slideMain(
            `<h2 class="headline-lg">Geen activiteit in ${year}</h2>
             <p class="body-md" style="margin-top:1rem">Begin met kijken of aanvragen om volgend jaar stats te zien.</p>`
          ),
          "welcome"
        )
      );
      return slides;
    }

    if (d.has_watch_history) {
      const hours = d.watch_hours ?? Math.floor((d.total_watch_seconds || 0) / 3600);
      const days = d.watch_days ?? Math.ceil(hours / 24);

      slides.push(
        createSlide(
          `<div class="floating-clock" aria-hidden="true">
             <img src="/static/designs/watch_time_clock.png" alt="">
           </div>` +
            slideMain(
              `<div class="hero-pop watch-hero">
                 <span class="watch-label">Totale Kijktijd</span>
                 <h2 class="watch-hours">${hours.toLocaleString("nl-NL")} uur</h2>
                 <div class="glass-card glass-card--days watch-days-card">
                   <p class="watch-days-text">Dat is <span class="text-primary">${days} dagen</span> kijkplezier</p>
                 </div>
               </div>
               <div class="slide-footnote watch-footnote">
                 <div class="footnote-divider"></div>
                 <p class="watch-footnote-label">gestreamd in ${year}</p>
               </div>`,
              "bottom-note"
            ),
          "watch-time"
        )
      );

      slides.push(
        createSlide(
          `<div class="play-icon-explosion" aria-hidden="true"></div>` +
            slideMain(
              `<div class="plays-hero-card glass-card">
                 <span class="material-symbols-outlined nav-icon-fill plays-icon">play_circle</span>
                 <h2 class="plays-count">${d.total_plays.toLocaleString("nl-NL")}</h2>
                 <p class="plays-subtitle">keer op de play-knop gedrukt</p>
                 <div class="plays-divider"></div>
               </div>
               <p class="plays-tagline">Je bent een echte binge-watcher</p>`
            ),
          "total-plays"
        )
      );

      slides.push(
        createSlide(
          `<div class="movies-vs-tv-photo" aria-hidden="true">
             <img src="/static/designs/movies_vs_tv_theater.png" alt="">
           </div>` +
            slideMain(
              `<div class="mvt-header">
                 <span class="mvt-label">De grote balans</span>
                 <h2 class="mvt-title">Films vs series</h2>
               </div>
               ${buildDonutChart(d.movie_plays, d.tv_plays)}
               <div class="split-grid mvt-stats">
                 <div class="glass-card">
                   <span class="material-symbols-outlined nav-icon-fill mvt-stat-icon mvt-stat-icon--movie">movie</span>
                   <span class="stat-num stat-num--tertiary">${d.movie_plays.toLocaleString("nl-NL")}</span>
                   <span class="mvt-stat-label">Films</span>
                 </div>
                 <div class="glass-card">
                   <span class="material-symbols-outlined nav-icon-fill mvt-stat-icon mvt-stat-icon--tv">live_tv</span>
                   <span class="stat-num">${d.tv_plays.toLocaleString("nl-NL")}</span>
                   <span class="mvt-stat-label">Afleveringen</span>
                 </div>
               </div>
               <p class="mvt-narrative">${escapeHtml(bingeNarrative(d.movie_plays, d.tv_plays))}</p>`,
              "movies-vs-tv"
            ),
          "movies-vs-tv"
        )
      );

      if (d.top_movies && d.top_movies.length) {
        slides.push(
          createSlide(
            buildTopMoviesPosterBg() +
              slideMain(
                `<h2 class="slide-title">Jouw <span class="text-primary">top 5</span> films</h2>
                 ${buildRankList(d.top_movies, "keer bekeken", true)}`,
                "top-movies"
              ),
            "top-movies"
          )
        );
      }

      if (d.top_shows && d.top_shows.length) {
        slides.push(
          createSlide(
            buildTopShowsPosterBg() +
              `<div class="top-shows-glow" aria-hidden="true"></div>` +
              slideMain(
                `<h2 class="slide-title">Jouw <span class="text-primary">top 5</span> series</h2>
                 ${buildRankList(d.top_shows, "afleveringen", true)}`,
                "top-shows"
              ),
            "top-shows"
          )
        );
      }

      if (d.unique_series > 0 || d.unique_seasons > 0 || d.unique_episodes > 0) {
        slides.push(
          createSlide(
            slideMain(
              `<div class="series-depth-content">
                 <div class="series-depth-header stack-sm">
                   <span class="label-md label-md--wide">Diepe duik</span>
                   <h2 class="headline-lg">Serie diepte</h2>
                 </div>
                 <div class="staircase">
                   <div class="stair-step glass-card">
                     <span class="headline-lg">${d.unique_series.toLocaleString("nl-NL")}</span>
                     <span class="stair-label">series</span>
                   </div>
                   <div class="stair-step glass-card">
                     <span class="display-lg">${d.unique_seasons.toLocaleString("nl-NL")}</span>
                     <span class="stair-label">seizoenen</span>
                   </div>
                   <div class="stair-step glass-card">
                     <span class="display-xl">${d.unique_episodes.toLocaleString("nl-NL")}</span>
                     <span class="stair-label">afleveringen</span>
                   </div>
                 </div>
                 <p class="stair-quote">"Je hebt genoeg content verslonden om een heel decennium te vullen."</p>
               </div>`
            ),
            "series-depth"
          )
        );
      }

      if (d.busiest_month || d.peak_day || d.peak_hour !== null) {
        const hour =
          d.peak_hour !== null && d.peak_hour !== undefined
            ? `${String(d.peak_hour).padStart(2, "0")}:00`
            : "—";
        slides.push(
          createSlide(
            slideMain(
              `<div class="when-content">
                 <div class="when-header stack-sm">
                   <span class="label-md label-md--wide">Jouw ritme</span>
                   <h2 class="headline-lg">Wanneer kijk je</h2>
                 </div>
                 <div class="when-stack">
                   <div class="glass-card when-card when-card--month-heatmap">
                     <p class="label-md when-label">Drukste maand</p>
                     <div class="when-card__row when-card__row--title">
                       <p class="headline-md when-value">${escapeHtml(d.busiest_month || "—")}</p>
                       <div class="when-icon-circle">
                         <span class="material-symbols-outlined nav-icon-fill">calendar_month</span>
                       </div>
                     </div>
                     <div class="heatmap-grid">${buildHeatmapGrid(
                       d.busiest_month_daily_plays ?? d.busiest_month_active_days,
                       d.busiest_month_first_weekday,
                       resolveBusiestMonthIndex(d.busiest_month, d.busiest_month_index),
                       year
                     )}</div>
                   </div>
                   <div class="glass-card when-card when-card--weekday">
                     <p class="label-md when-label">Drukste dag</p>
                     <p class="headline-md when-day-value">${escapeHtml(d.peak_day || "—")}</p>
                     ${buildWeekdayChart(d.plays_by_weekday, d.peak_day)}
                   </div>
                   <div class="glass-card when-card when-card--hour">
                     <div class="when-card__row when-card__row--hour">
                       <div class="when-hour-text">
                         <p class="label-md when-label">Drukste uur</p>
                         <p class="headline-md when-hour-value">${hour}</p>
                       </div>
                       ${buildPeakClock(d.peak_hour, true)}
                     </div>
                   </div>
                 </div>
               </div>
               <div class="when-waves" aria-hidden="true">
                 <svg viewBox="0 0 400 100" preserveAspectRatio="none">
                   <path class="when-wave when-wave--primary" d="M0,50 Q50,0 100,50 T200,50 T300,50 T400,50" fill="none" stroke="#ffbd49" stroke-width="2"></path>
                   <path class="when-wave when-wave--tertiary" d="M0,50 Q50,20 100,50 T200,50 T300,50 T400,50" fill="none" stroke="#96ceff" stroke-width="1"></path>
                 </svg>
               </div>`,
              "when-you-watch"
            ),
            "when-you-watch"
          )
        );
      }

      if (d.favorite_device) {
        const devicePercent =
          d.favorite_device_watch_percent !== null &&
          d.favorite_device_watch_percent !== undefined
            ? d.favorite_device_watch_percent
            : null;
        const deviceBadgeText =
          devicePercent !== null
            ? `${devicePercent}% van je kijktijd`
            : "—% van je kijktijd";
        slides.push(
          createSlide(
            `<div class="device-silhouettes" aria-hidden="true">
               <div class="tv-silhouette tv-silhouette--1"></div>
               <div class="tv-silhouette tv-silhouette--2"></div>
             </div>` +
              slideMain(
                `<div class="device-hero-block">
                   <div class="device-hero glass-card">
                     <span class="material-symbols-outlined nav-icon-fill">tv</span>
                   </div>
                   <div class="device-copy stack-sm">
                     <p class="label-md label-md--wide">Je favoriete venster</p>
                     <h2 class="device-title">Jouw scherm:<br><span class="text-primary">${escapeHtml(d.favorite_device)}</span></h2>
                   </div>
                 </div>
                 <div class="glass-card device-badge">
                   <span class="material-symbols-outlined nav-icon-fill" style="color:var(--primary)">tv</span>
                   <p>${escapeHtml(deviceBadgeText)}</p>
                 </div>`,
                "favorite-device"
              ),
            "favorite-device"
          )
        );
      }

      if (d.longest_streak_days > 0) {
        const streakStart = formatStreakDate(d.longest_streak_start);
        const streakEnd = formatStreakDate(d.longest_streak_end);
        slides.push(
          createSlide(
            slideMain(
              `<div class="streak-content">
                 <div class="streak-glow" aria-hidden="true"></div>
                 <div class="streak-ring glass-card">
                   <span class="material-symbols-outlined nav-icon-fill">calendar_today</span>
                   <span class="display-xl">${d.longest_streak_days}</span>
                 </div>
                 <h2 class="device-title">Langste streak<br><span class="text-primary">${d.longest_streak_days} dagen op rij</span></h2>
               </div>
               <div class="streak-dates">
                 <div class="glass-card streak-date-card">
                   <p class="label-md streak-date-label">Start</p>
                   <p class="headline-md streak-date-value">${escapeHtml(streakStart)}</p>
                 </div>
                 <div class="glass-card streak-date-card">
                   <p class="label-md streak-date-label">Einde</p>
                   <p class="headline-md streak-date-value">${escapeHtml(streakEnd)}</p>
                 </div>
               </div>`,
              "longest-streak"
            ),
            "longest-streak"
          )
        );
      }

      if (d.top_movie_genres && d.top_movie_genres.length) {
        slides.push(
          createSlide(
            `<div class="genre-icon-explosion" aria-hidden="true"></div>` +
              slideMain(
                `<div class="genre-header stack-sm">
                   <span class="label-md label-md--wide">Jouw vibe</span>
                   <h2 class="genre-title">Top film <span class="text-primary-container">genres</span></h2>
                 </div>
                 ${buildGenreLayout(d.top_movie_genres, "Films", "films")}`,
                "movie-genres"
              ),
            "movie-genres"
          )
        );
      }

      if (d.top_show_genres && d.top_show_genres.length) {
        slides.push(
          createSlide(
            `<div class="genre-icon-explosion" aria-hidden="true"></div>` +
              slideMain(
                `<div class="genre-header stack-sm">
                   <span class="label-md label-md--wide">Jouw vibe</span>
                   <h2 class="genre-title">Top series <span class="text-primary-container">genres</span></h2>
                 </div>
                 ${buildGenreLayout(d.top_show_genres, "Episodes", "episodes")}`,
                "show-genres"
              ),
            "show-genres"
          )
        );
      }

      if (d.server && d.server.rank) {
        const activePct = d.server.more_active_than_percent;
        const activityBadge =
          activePct != null
            ? `<div class="rank-activity-badge glass-card">
                 <p class="rank-activity-badge__text">
                   Je bent actiever dan <strong>${activePct}%</strong> van de gebruikers
                 </p>
               </div>`
            : "";
        const contextRows = buildRankContextRows(d.server.rank_context);

        slides.push(
          createSlide(
            slideMain(
              `<div class="server-rank-layout">
                 <div class="server-rank-header stack-sm">
                   ${
                     d.server.server_name
                       ? `<div class="server-rank-badge glass-card">
                            <span class="material-symbols-outlined nav-icon-fill server-rank-badge__icon">dns</span>
                            <span class="server-rank-badge__name">${escapeHtml(d.server.server_name)}</span>
                          </div>`
                       : ""
                   }
                   <h2 class="headline-lg">Jouw plek op de server</h2>
                 </div>
                 <div class="rank-circle glass-card">
                   <span class="rank-circle__label">Rank</span>
                   <span class="rank-circle__num">#${d.server.rank}</span>
                 </div>
                 ${activityBadge}
                 ${contextRows ? `<div class="rank-context">${contextRows}</div>` : ""}
               </div>`,
              "server-rank"
            ),
            "server-rank"
          )
        );
      }

      const serverTopShow = d.server?.server_top_show || d.server?.server_top_movie;
      const userTopShow = d.user_comparison_show || d.user_comparison_movie;
      if (serverTopShow && userTopShow) {
        const same =
          d.comparison_same_show != null
            ? d.comparison_same_show
            : serverTopShow.toLowerCase() === userTopShow.toLowerCase();
        const serverThumb = d.server?.server_top_show_thumb;
        const userThumb = d.user_comparison_show_thumb;
        const caption = buildComparisonCaption(d, serverTopShow, userTopShow, same);

        slides.push(
          createSlide(
            buildServerVsPosterBg(serverThumb, userThumb) +
              `<div class="top-shows-glow" aria-hidden="true"></div>` +
              slideMain(
              `<div class="server-vs-layout">
                 <h2 class="server-vs-headline">${buildComparisonHeadline(d, same)}</h2>
                 <div class="server-vs-posters">
                   ${buildVsPosterCard("server", serverTopShow, serverThumb, "Server #1")}
                   <div class="server-vs-badge" aria-hidden="true">VS</div>
                   ${buildVsPosterCard("user", userTopShow, userThumb, "Jouw #1")}
                 </div>
                 <div class="server-vs-caption glass-card">
                   <p class="server-vs-caption__text">"${escapeHtml(caption)}"</p>
                 </div>
               </div>`,
              "server-vs-you"
            ),
            "server-vs-you"
          )
        );
      }
    }

    if (tgActive) {
      const tg = d.telegram;
      const hasTelegramSlide =
        (tg.film_requests || 0) > 0 ||
        (tg.serie_requests || 0) > 0 ||
        (tg.movies_requested || 0) > 0 ||
        (tg.series_requested || 0) > 0 ||
        (tg.login_count || 0) > 0;

      if (hasTelegramSlide) {
        slides.push(
          createSlide(slideMain(buildTelegramSlide(tg), "telegram-requests"), "telegram-requests")
        );
      }
    }

    if (d.has_watch_history || tgActive) {
      const personaId = d.persona_id || "dedicated_viewer";
      const art = PERSONA_ART[personaId] || PERSONA_ART.dedicated_viewer;

      slides.push(
        createSlide(
          slideMain(
            `<div class="persona-layout">
               <div class="persona-hero">
                 <div class="persona-art-glow">
                   <img class="persona-art" src="${art}" alt="">
                 </div>
               </div>
               <div class="persona-copy">
                 <span class="persona-label">Jouw persona</span>
                 <h2 class="persona-title">Jouw kroon:<br><span class="persona-title__name">${escapeHtml(d.persona)}</span></h2>
                 <p class="persona-tagline">${escapeHtml(d.persona_tagline || "")}</p>
               </div>
             </div>`,
            "persona"
          ),
          "persona"
        )
      );

      const hours = d.watch_hours ?? Math.floor((d.total_watch_seconds || 0) / 3600);
      const topMedia =
        d.tv_plays > 0 && d.top_shows && d.top_shows[0]
          ? {
              title: d.top_shows[0].title,
              label: "Topserie",
              mostWatched: "Meest bekeken serie",
              thumb: d.top_shows[0].thumb,
              icon: "tv",
            }
          : d.top_movies && d.top_movies[0]
            ? {
                title: d.top_movies[0].title,
                label: "Topfilm",
                mostWatched: "Meest bekeken film",
                thumb: d.top_movies[0].thumb,
                icon: "movie",
              }
            : null;
      const tg = d.telegram;
      const totalReq = tg
        ? tg.total_requests ?? (tg.film_requests || 0) + (tg.serie_requests || 0)
        : 0;

      let bento = `<div class="summary-header">
        <p class="summary-eyebrow">Jouw jaar in review</p>
        <h2 class="summary-title">${year} Samenvatting</h2>
      </div>
      <div class="bento-grid">`;

      if (d.has_watch_history) {
        bento += `<div class="glass-card bento-card">
          <span class="material-symbols-outlined bento-card__icon">schedule</span>
          <p class="bento-card__label">Kijktijd</p>
          <p class="bento-card__value">${hours}u</p>
        </div>`;
        bento += `<div class="glass-card bento-card">
          <span class="material-symbols-outlined bento-card__icon">play_circle</span>
          <p class="bento-card__label">Totaal gestart</p>
          <p class="bento-card__value">${d.total_plays}</p>
        </div>`;
      }

      if (topMedia) {
        const thumb = posterUrl(topMedia.thumb);
        const img = thumb
          ? `<img src="${escapeHtml(thumb)}" alt="">`
          : `<div class="bento-media__placeholder" aria-hidden="true"></div>`;
        bento += `<div class="glass-card bento-span-2 bento-media">
          ${img}
          <div class="bento-media__copy">
            <p class="bento-card__label">${topMedia.label}</p>
            <p class="bento-card__value bento-card__value--md">${escapeHtml(topMedia.title)}</p>
            <p class="bento-media__badge">
              <span class="material-symbols-outlined bento-media__star">star</span>
              <span class="bento-media__badge-text">${topMedia.mostWatched}</span>
            </p>
          </div>
        </div>`;
      }

      if (d.busiest_month) {
        bento += `<div class="glass-card bento-card">
          <span class="material-symbols-outlined bento-card__icon">calendar_month</span>
          <p class="bento-card__label">Drukste maand</p>
          <p class="bento-card__value">${escapeHtml(d.busiest_month)}</p>
        </div>`;
      }

      if (totalReq > 0) {
        bento += `<div class="glass-card bento-card">
          <span class="material-symbols-outlined bento-card__icon">send</span>
          <p class="bento-card__label">Telegram-aanvragen</p>
          <p class="bento-card__value">${totalReq}</p>
        </div>`;
      }

      bento += `<div class="glass-card bento-span-2 bento-persona">
        <div class="bento-persona__copy">
          <p class="bento-card__label">Jouw Persona</p>
          <p class="bento-card__value">${escapeHtml(d.persona)}</p>
        </div>
        <span class="material-symbols-outlined bento-persona__icon">workspace_premium</span>
      </div>`;

      bento += `</div>
        <div class="share-actions">
          <button type="button" class="share-btn" id="btnShareSummary">
            <span class="material-symbols-outlined" style="font-size:20px">share</span>
            Deel je jaar
          </button>
          <div class="share-secondary" aria-hidden="true">
            <span class="material-symbols-outlined">download</span>
            <span class="material-symbols-outlined">bookmark</span>
            <span class="material-symbols-outlined">favorite</span>
          </div>
        </div>`;

      slides.push(createSlide(slideMain(bento, "summary"), "summary"));
    }

    return slides;
  }

  function setupProgress(count) {
    progressBar.innerHTML = "";
    for (let i = 0; i < count; i++) {
      const seg = document.createElement("div");
      seg.className = "progress-segment";
      progressBar.appendChild(seg);
    }
  }

  function updateProgress(index) {
    progressBar.querySelectorAll(".progress-segment").forEach((seg, i) => {
      seg.classList.toggle("active", i <= index);
    });
  }

  function currentSlideIndex() {
    return carousel?.getIndex() ?? 0;
  }

  async function shareWrapped() {
    const url = window.location.href;
    const title = `Plex Wrapped ${document.body.dataset.year || ""}`;
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
      } catch (e) {
        if (e.name !== "AbortError") console.warn(e);
      }
    } else if (navigator.clipboard) {
      await navigator.clipboard.writeText(url);
      alert("Link gekopieerd naar klembord.");
    }
  }

  async function init() {
    btnClose?.addEventListener("click", () => {
      window.location.href = "/auth/logout";
    });

    try {
      const res = await fetch("/api/wrapped");
      if (!res.ok) {
        if (res.status === 401) {
          window.location.href = "/";
          return;
        }
        if (res.status === 503) {
          const err = await res.json().catch(() => ({}));
          const msg =
            err.detail?.message ||
            "Wrapped is nog niet gegenereerd. Vraag de beheerder om compute_wrapped.py te draaien.";
          loading.querySelector("p").textContent = msg;
          return;
        }
        throw new Error("Failed to load wrapped data");
      }
      const data = await res.json();
      const slides = buildSlides(data);

      setupProgress(slides.length);
      carousel = createStoryCarousel({
        root: slidesEl,
        onChange: (index, slide) => {
          updateProgress(index);
          if (slide?.classList.contains("slide--summary")) ensureSummaryDots();
        },
      });
      carousel.mount(slides);
      slidesEl
        .querySelectorAll(".slide--welcome, .slide--when-you-watch, .slide--server-rank")
        .forEach(initWelcomeBokeh);
      slidesEl.querySelectorAll(".slide--when-you-watch").forEach((slide) => {
        initWhenYouWatchWaves(slide);
        initWeekdayChart(slide);
      });
      slidesEl
        .querySelectorAll(".slide--watch-time, .slide--series-depth, .slide--longest-streak")
        .forEach(initWatchTimeBokeh);
      slidesEl.querySelectorAll(".slide--total-plays").forEach(initTotalPlaysIcons);
      slidesEl
        .querySelectorAll(".slide--movie-genres, .slide--show-genres")
        .forEach(initGenreIconExplosion);
      slidesEl
        .querySelectorAll(".slide--top-movies, .slide--top-shows")
        .forEach(initTopListMotion);
      slidesEl.querySelectorAll(".slide--telegram-requests").forEach((slide) => {
        initTelegramDeco(slide);
        initTelegramProgressBar(slide);
      });
      slidesEl.querySelectorAll(".slide--persona").forEach(initPersonaConfetti);

      loading.classList.add("hidden");
      slidesEl.classList.remove("hidden");

      requestAnimationFrame(() => {
        requestAnimationFrame(ensureSummaryDots);
      });
      window.setTimeout(ensureSummaryDots, 120);

      document.getElementById("btnShareSummary")?.addEventListener("click", (e) => {
        e.stopPropagation();
        shareWrapped();
      });

    } catch (err) {
      loading.querySelector("p").textContent = "Er ging iets mis. Probeer het later opnieuw.";
      console.error(err);
    }
  }

  init();
})();
