(function () {
  const loading = document.getElementById("loading");
  const slidesEl = document.getElementById("slides");
  const progressBar = document.getElementById("progressBar");
  const btnPrev = document.getElementById("btnPrev");
  const btnNext = document.getElementById("btnNext");
  const btnClose = document.getElementById("btnClose");
  const btnShare = document.getElementById("btnShare");

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
      slideId === "when-you-watch"
        ? '<canvas class="slide-bokeh-canvas" aria-hidden="true"></canvas>'
        : "";
    section.innerHTML = `
      <div class="slide-bg" aria-hidden="true"></div>
      <div class="slide-bg slide-bg--overlay" aria-hidden="true"></div>
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

  function initTotalPlaysIcons(slide) {
    const container = slide.querySelector(".play-icon-explosion");
    if (!container || container.dataset.ready) return;

    const iconTypes = ["play_arrow", "movie", "tv", "theaters", "video_library"];
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

  function buildGenreBars(genres) {
    if (!genres.length) return "";
    const max = Math.max(...genres.map((g) => g.plays), 1);
    let html = '<div class="genre-bars">';
    genres.forEach((g, i) => {
      const pct = Math.round((g.plays / max) * 100);
      const hero = i === 0 ? " genre-row--hero" : "";
      const opacity = i === 0 ? "" : ` style="opacity:${Math.max(0.6, 1 - i * 0.1)}"`;
      html += `<div class="genre-row glass-card${hero}"${opacity}>
        <span class="rank-num">${i + 1}</span>
        <div style="flex:1;min-width:0">
          <h3 style="font-family:var(--font-display);font-size:1rem;color:#fff">${escapeHtml(g.name)}</h3>
          <div class="genre-bar-track" style="margin-top:8px"><div class="genre-bar-fill" style="width:${pct}%"></div></div>
        </div>
        <span class="rank-meta">${g.plays}</span>
      </div>`;
    });
    html += "</div>";
    return html;
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

    const points = counts.map((count, index) => ({
      x: padX + (index / 6) * plotW,
      y: padTop + plotH - (count / max) * plotH,
      count,
      index,
    }));

    const linePath = points
      .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
      .join(" ");

    const areaPath = `${linePath} L ${points[6].x.toFixed(1)} ${(padTop + plotH).toFixed(1)} L ${points[0].x.toFixed(1)} ${(padTop + plotH).toFixed(1)} Z`;

    const dots = points
      .map((point) => {
        const isPeak = point.index === peakIdx;
        const r = isPeak ? 4.5 : 3;
        const label = point.count.toLocaleString("nl-NL");
        return `<g class="${isPeak ? "weekday-line-chart__point--peak" : ""}">
          <circle class="weekday-line-chart__dot" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="${r}"></circle>
          <text class="weekday-line-chart__value" x="${point.x.toFixed(1)}" y="${(point.y - 8).toFixed(1)}" text-anchor="middle">${label}</text>
        </g>`;
      })
      .join("");

    const labels = points
      .map(
        (point) =>
          `<text class="weekday-line-chart__day" x="${point.x.toFixed(1)}" y="${(height - 4).toFixed(1)}" text-anchor="middle">${WEEKDAY_SHORT[point.index]}</text>`
      )
      .join("");

    return `<div class="weekday-line-chart">
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
        <path class="weekday-line-chart__area" d="${areaPath}"></path>
        <path class="weekday-line-chart__line" d="${linePath}"></path>
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
        <div class="when-clock__hand when-clock__hand--hour" style="transform:rotate(${hourAngle}deg)"></div>
        <div class="when-clock__hand when-clock__hand--minute"></div>
        <div class="when-clock__center"></div>
      </div>
    </div>`;
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
                : `<div style="width:12rem;height:12rem;border-radius:50%;background:var(--surface-container-high)"></div>`
            }
          </div>
          <div class="stack-sm">
            <h2 class="headline-lg">Hoi ${escapeHtml(d.display_name)}!</h2>
            <p class="display-lg">Jouw ${year}<br>Plex Wrapped</p>
            <p class="body-md">Laten we kijken naar je jaar in films en series.</p>
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
      const days = d.watch_days ?? Math.floor(hours / 24);

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
        slides.push(
          createSlide(
            slideMain(
              `<div class="device-hero glass-card">
                 <span class="material-symbols-outlined nav-icon-fill">tv</span>
               </div>
               <div class="stack-sm">
                 <p class="label-md label-md--wide">Je favoriete venster</p>
                 <h2 class="display-lg" style="color:#fff;line-height:1.2">Jouw scherm:<br><span class="text-primary">${escapeHtml(d.favorite_device)}</span></h2>
               </div>
               <div class="glass-card device-badge">
                 <span class="material-symbols-outlined" style="color:var(--primary)">tv</span>
                 <p>meest gebruikte player</p>
               </div>`
            ),
            "favorite-device"
          )
        );
      }

      if (d.longest_streak_days > 0) {
        slides.push(
          createSlide(
            slideMain(
              `<div class="streak-glow" aria-hidden="true"></div>
               <div class="streak-ring glass-card">
                 <span class="material-symbols-outlined">calendar_today</span>
                 <span class="display-xl">${d.longest_streak_days}</span>
               </div>
               <h2 class="headline-lg">${d.longest_streak_days} dagen op rij</h2>
               <p class="label-md streak-sub" style="color:var(--on-surface-variant)">Langste streak in ${year}</p>`,
              "bottom-note"
            ),
            "longest-streak"
          )
        );
      }

      if (d.top_movie_genres && d.top_movie_genres.length) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md label-md--wide">Filmgenres</span>
               <h2 class="headline-lg" style="margin-top:0.5rem">Top 5 genres</h2>
               ${buildGenreBars(d.top_movie_genres)}`,
              "top"
            ),
            "movie-genres"
          )
        );
      }

      if (d.top_show_genres && d.top_show_genres.length) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md label-md--wide">Seriesgenres</span>
               <h2 class="headline-lg" style="margin-top:0.5rem">Top 5 genres</h2>
               ${buildGenreBars(d.top_show_genres)}`,
              "top"
            ),
            "show-genres"
          )
        );
      }

      if (d.server && d.server.rank) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md label-md--wide">Op de server</span>
               <p class="rank-medal">#${d.server.rank}</p>
               <p class="body-md" style="margin-top:1rem">tussen kijkers op deze server</p>
               <div class="rank-podium" aria-hidden="true">
                 <span style="height:45%"></span>
                 <span></span>
                 <span style="height:55%"></span>
               </div>`
            ),
            "server-rank"
          )
        );
      }

      const serverTopShow = d.server?.server_top_show || d.server?.server_top_movie;
      const userTopShow = d.user_comparison_show || d.user_comparison_movie;
      if (serverTopShow && userTopShow) {
        const same = serverTopShow.toLowerCase() === userTopShow.toLowerCase();
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md label-md--wide">Server vs jij</span>
               <h2 class="headline-lg" style="margin-top:0.5rem">De grote vergelijking</h2>
               <div class="glass-card versus-card">
                 <div class="versus-row">
                   <div>
                     <p class="versus-label">Server #1</p>
                     <p class="versus-title">${escapeHtml(serverTopShow)}</p>
                   </div>
                   <span class="material-symbols-outlined" style="color:var(--tertiary)">groups</span>
                 </div>
                 <div class="versus-row">
                   <div>
                     <p class="versus-label">Jouw top</p>
                     <p class="versus-title">${escapeHtml(userTopShow)}</p>
                   </div>
                   <span class="material-symbols-outlined" style="color:var(--primary)">person</span>
                 </div>
               </div>
               <p class="match-badge">${same ? "Zelfde smaak" : "Jij koos je eigen pad"}</p>`
            ),
            "server-vs-you"
          )
        );
      }
    }

    if (tgActive) {
      const tg = d.telegram;
      if (tg.film_requests > 0 || tg.serie_requests > 0) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md label-md--wide">Telegram</span>
               <h2 class="headline-lg" style="margin-top:0.5rem">Aanvragen</h2>
               <div class="split-grid req-grid" style="margin-top:1.5rem">
                 <div class="glass-card">
                   <span class="req-num">${tg.film_requests}</span>
                   <span class="label-md" style="color:var(--on-surface-variant)">films</span>
                 </div>
                 <div class="glass-card">
                   <span class="req-num">${tg.serie_requests}</span>
                   <span class="label-md" style="color:var(--on-surface-variant)">series</span>
                 </div>
               </div>`,
              "top"
            ),
            "telegram-requests"
          )
        );
      }

      if (tg.movies_requested > 0 || tg.series_requested > 0) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md label-md--wide">Aanvraag → kijken</span>
               <div class="glass-card versus-card" style="margin-top:1.5rem;text-align:left">
                 <p style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.08)">
                   Films: <strong style="color:#fff">${tg.movies_requested}</strong> aangevraagd · <strong style="color:var(--primary)">${tg.movies_watched}</strong> bekeken
                 </p>
                 <p style="padding:10px 0">
                   Series: <strong style="color:#fff">${tg.series_requested}</strong> aangevraagd · <strong style="color:var(--primary)">${tg.series_watched}</strong> bekeken
                 </p>
               </div>
               <p class="body-md" style="margin-top:1rem">Van aanvraag naar play-knop</p>`
            ),
            "telegram-watched"
          )
        );
      }

      if (tg.login_count > 0) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="material-symbols-outlined bot-icon">smart_toy</span>
               <span class="label-md label-md--wide">Botgebruik</span>
               <h2 class="display-xl" style="margin-top:12px">${tg.login_count}</h2>
               <p class="body-md" style="margin-top:1rem">keer dat je de aanvraagbot gebruikte</p>`
            ),
            "telegram-bot"
          )
        );
      }
    }

    if (d.has_watch_history || tgActive) {
      const personaId = d.persona_id || "dedicated_viewer";
      const art = PERSONA_ART[personaId] || PERSONA_ART.dedicated_viewer;

      slides.push(
        createSlide(
          slideMain(
            `<img class="persona-art" src="${art}" alt="">
             <span class="label-md label-md--wide">Jouw persona</span>
             <h2 class="headline-lg" style="margin-top:8px">Op basis van jouw stats word je gekroond tot</h2>
             <p class="display-lg persona-name" style="margin-top:8px">${escapeHtml(d.persona)}</p>
             <p class="body-md persona-tagline" style="margin-top:12px">${escapeHtml(d.persona_tagline || "")}</p>`
          ),
          "persona"
        )
      );

      const hours = d.watch_hours ?? Math.floor((d.total_watch_seconds || 0) / 3600);
      const days = d.watch_days ?? Math.floor(hours / 24);
      const topMedia =
        d.tv_plays > 0 && d.top_shows && d.top_shows[0]
          ? { title: d.top_shows[0].title, label: "Topserie", thumb: d.top_shows[0].thumb, icon: "tv" }
          : d.top_movies && d.top_movies[0]
            ? { title: d.top_movies[0].title, label: "Topfilm", thumb: d.top_movies[0].thumb, icon: "movie" }
            : null;
      const tg = d.telegram;
      const totalReq = tg
        ? tg.total_requests ?? (tg.film_requests || 0) + (tg.serie_requests || 0)
        : 0;

      let bento = `<div class="summary-header">
        <p class="label-md label-md--wide" style="opacity:0.8">Jouw jaar in review</p>
        <h2 class="headline-lg">${year} samenvatting</h2>
      </div>
      <div class="bento-grid">`;

      if (d.has_watch_history) {
        bento += `<div class="glass-card">
          <span class="material-symbols-outlined">schedule</span>
          <span class="label-md" style="color:var(--on-surface-variant)">Kijktijd</span>
          <span class="bento-value">${hours}u</span>
          <span class="label-md" style="color:var(--on-surface-variant);font-size:0.65rem">${days} dagen</span>
        </div>`;
        bento += `<div class="glass-card">
          <span class="material-symbols-outlined">play_circle</span>
          <span class="label-md" style="color:var(--on-surface-variant)">Totaal gestart</span>
          <span class="bento-value">${d.total_plays}</span>
        </div>`;
      }

      if (topMedia) {
        const thumb = posterUrl(topMedia.thumb);
        const img = thumb
          ? `<img src="${escapeHtml(thumb)}" alt="">`
          : `<div style="width:56px;height:84px;border-radius:8px;background:var(--surface-container-high)"></div>`;
        bento += `<div class="glass-card bento-span-2 bento-media">
          ${img}
          <div>
            <span class="label-md" style="color:var(--on-surface-variant)">${topMedia.label}</span>
            <span class="bento-value">${escapeHtml(topMedia.title)}</span>
          </div>
        </div>`;
      }

      if (d.busiest_month) {
        bento += `<div class="glass-card">
          <span class="material-symbols-outlined">calendar_month</span>
          <span class="label-md" style="color:var(--on-surface-variant)">Drukste maand</span>
          <span class="bento-value">${escapeHtml(d.busiest_month)}</span>
        </div>`;
      }

      if (totalReq > 0) {
        bento += `<div class="glass-card">
          <span class="material-symbols-outlined">send</span>
          <span class="label-md" style="color:var(--on-surface-variant)">Telegram-aanvragen</span>
          <span class="bento-value">${totalReq}</span>
        </div>`;
      }

      bento += `<div class="glass-card bento-span-2 bento-persona">
        <div>
          <span class="label-md" style="color:var(--on-surface-variant)">Persona</span>
          <span class="bento-value">${escapeHtml(d.persona)}</span>
        </div>
        <span class="material-symbols-outlined">workspace_premium</span>
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

      slides.push(createSlide(slideMain(bento, "top"), "summary"));
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
    const children = [...slidesEl.children];
    const mid = window.innerHeight / 2;
    let best = 0;
    let bestDist = Infinity;
    children.forEach((s, i) => {
      const rect = s.getBoundingClientRect();
      const dist = Math.abs(rect.top + rect.height / 2 - mid);
      if (dist < bestDist) {
        bestDist = dist;
        best = i;
      }
    });
    return best;
  }

  function scrollToSlide(index) {
    const target = slidesEl.children[index];
    if (target) target.scrollIntoView({ behavior: "smooth" });
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
    btnShare?.addEventListener("click", (e) => {
      e.stopPropagation();
      shareWrapped();
    });

    btnPrev?.addEventListener("click", (e) => {
      e.stopPropagation();
      const idx = currentSlideIndex();
      if (idx > 0) scrollToSlide(idx - 1);
    });

    btnNext?.addEventListener("click", (e) => {
      e.stopPropagation();
      const idx = currentSlideIndex();
      if (idx < slidesEl.children.length - 1) scrollToSlide(idx + 1);
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
      slides.forEach((s) => slidesEl.appendChild(s));
      slidesEl
        .querySelectorAll(".slide--welcome, .slide--when-you-watch")
        .forEach(initWelcomeBokeh);
      slidesEl.querySelectorAll(".slide--when-you-watch").forEach(initWhenYouWatchWaves);
      slidesEl
        .querySelectorAll(".slide--watch-time, .slide--series-depth")
        .forEach(initWatchTimeBokeh);
      slidesEl.querySelectorAll(".slide--total-plays").forEach(initTotalPlaysIcons);

      loading.classList.add("hidden");
      slidesEl.classList.remove("hidden");

      document.getElementById("btnShareSummary")?.addEventListener("click", (e) => {
        e.stopPropagation();
        shareWrapped();
      });

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const idx = [...slidesEl.children].indexOf(entry.target);
              if (idx >= 0) updateProgress(idx);
            }
          });
        },
        { threshold: 0.55 }
      );
      slides.forEach((s) => observer.observe(s));
      updateProgress(0);

      document.body.addEventListener("click", (e) => {
        if (e.target.closest("button, a, .icon-btn, .nav-btn, .share-btn")) return;
        const idx = currentSlideIndex();
        if (idx < slidesEl.children.length - 1) scrollToSlide(idx + 1);
      });
    } catch (err) {
      loading.querySelector("p").textContent = "Er ging iets mis. Probeer het later opnieuw.";
      console.error(err);
    }
  }

  init();
})();
