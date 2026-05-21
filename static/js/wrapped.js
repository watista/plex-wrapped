(function () {
  const loading = document.getElementById("loading");
  const slidesEl = document.getElementById("slides");
  const progressBar = document.getElementById("progressBar");
  const btnPrev = document.getElementById("btnPrev");
  const btnNext = document.getElementById("btnNext");
  const btnClose = document.getElementById("btnClose");
  const btnShare = document.getElementById("btnShare");

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

  /** Unified slide shell: same height, mesh, padded main area */
  function createSlide(innerHtml, variant) {
    const meshClass =
      variant === "cool" ? "slide-mesh slide-mesh--cool" : variant === "warm" ? "slide-mesh slide-mesh--warm" : "slide-mesh";
    const section = document.createElement("section");
    section.className = "slide";
    section.innerHTML = `<div class="${meshClass}"></div>${innerHtml}`;
    return section;
  }

  function slideMain(html, layout) {
    const cls = layout ? `slide-main slide-main--${layout}` : "slide-main";
    return `<main class="${cls}">${html}</main>`;
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
      html += `<div class="rank-item glass-card${hero}"${opacity}>
        <span class="rank-num">${i + 1}</span>
        ${img}
        <div class="rank-body">
          <h3>${escapeHtml(item.title)}</h3>
          <p class="rank-meta">${item.plays} ${playsLabel}</p>
        </div>
        ${verified}
      </div>`;
    });
    html += "</div>";
    return html;
  }

  function buildDonutChart(moviePlays, tvPlays) {
    const total = moviePlays + tvPlays || 1;
    const tvPct = tvPlays / total;
    const moviePct = moviePlays / total;
    const r = 40;
    const c = 2 * Math.PI * r;
    const tvLen = c * tvPct;
    const movieLen = c * moviePct;
    const ratio =
      moviePlays > 0 ? `${moviePlays}:${tvPlays}` : tvPlays > 0 ? `0:${tvPlays}` : "—";
    return `
      <div class="chart-wrap">
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <circle cx="50" cy="50" r="${r}" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="8"/>
          <circle cx="50" cy="50" r="${r}" fill="none" stroke="#ffbd49" stroke-width="8"
            stroke-dasharray="${tvLen} ${c}" stroke-linecap="round"/>
          <circle cx="50" cy="50" r="${r}" fill="none" stroke="#96ceff" stroke-width="8"
            stroke-dasharray="${movieLen} ${c}" stroke-dashoffset="-${tvLen}" stroke-linecap="round"/>
        </svg>
        <div class="chart-center">
          <span class="display-lg">${ratio}</span>
          <span class="label-md" style="color:var(--on-surface-variant)">verhouding</span>
        </div>
      </div>`;
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
        "warm"
      )
    );

    if (!d.has_watch_history && !tgActive) {
      slides.push(
        createSlide(
          slideMain(
            `<h2 class="headline-lg">Geen activiteit in ${year}</h2>
             <p class="body-md" style="margin-top:1rem">Begin met kijken of aanvragen om volgend jaar stats te zien.</p>`
          )
        )
      );
      return slides;
    }

    if (d.has_watch_history) {
      const hours = d.watch_hours ?? Math.floor((d.total_watch_seconds || 0) / 3600);
      const days = d.watch_days ?? Math.floor(hours / 24);

      slides.push(
        createSlide(
          slideMain(
            `<span class="label-md">Kijktijd</span>
             <h2 class="display-xl" style="margin-top:12px">${hours} uur</h2>
             <div class="glass-card glass-card--inline">
               <p class="body-md">Dat is <strong>${days} dagen</strong> kijkplezier</p>
             </div>`,
            "bottom-note"
          ) +
            `<p class="slide-footnote label-md" style="color:rgba(226,226,226,0.6)">gestreamd in ${year}</p>`
        )
      );

      slides.push(
        createSlide(
          slideMain(
            `<span class="label-md">Totaal gestart</span>
             <h2 class="display-xl" style="margin-top:12px">${d.total_plays}</h2>
             <p class="body-md" style="margin-top:1rem">keer op play gedrukt voor films & series</p>`
          )
        )
      );

      slides.push(
        createSlide(
          slideMain(
            `<span class="label-md">De grote balans</span>
             <h2 class="headline-lg" style="margin-bottom:8px">Films vs series</h2>
             ${buildDonutChart(d.movie_plays, d.tv_plays)}
             <div class="split-grid">
               <div class="glass-card">
                 <span class="material-symbols-outlined nav-icon-fill" style="font-size:22px;color:var(--primary)">live_tv</span>
                 <span class="stat-num">${d.tv_plays}</span>
                 <span class="label-md" style="color:var(--on-surface-variant)">afleveringen</span>
               </div>
               <div class="glass-card">
                 <span class="material-symbols-outlined nav-icon-fill" style="font-size:22px;color:var(--tertiary)">movie</span>
                 <span class="stat-num stat-num--tertiary">${d.movie_plays}</span>
                 <span class="label-md" style="color:var(--on-surface-variant)">films</span>
               </div>
             </div>`,
            "top"
          )
        )
      );

      if (d.top_movies && d.top_movies.length) {
        slides.push(
          createSlide(
            slideMain(
              `<h2 class="headline-lg" style="text-align:left;width:100%;max-width:360px;margin-bottom:1rem">
                 Jouw <span class="text-primary">top 5</span> films
               </h2>
               ${buildRankList(d.top_movies, "keer bekeken", true)}`,
              "top"
            )
          )
        );
      }

      if (d.top_shows && d.top_shows.length) {
        slides.push(
          createSlide(
            slideMain(
              `<h2 class="headline-lg" style="text-align:left;width:100%;max-width:360px;margin-bottom:1rem">
                 Jouw <span class="text-primary">top 5</span> series
               </h2>
               ${buildRankList(d.top_shows, "afleveringen", true)}`,
              "top"
            )
          )
        );
      }

      if (d.unique_series > 0 || d.unique_seasons > 0 || d.unique_episodes > 0) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md">Jouw seriesreis</span>
               <div class="depth-stats" style="margin-top:1.5rem">
                 <p><strong>${d.unique_series}</strong> series</p>
                 <p><strong>${d.unique_seasons}</strong> seizoenen</p>
                 <p><strong>${d.unique_episodes}</strong> afleveringen</p>
               </div>`
            )
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
              `<span class="label-md">Wanneer kijk je</span>
               <div class="stat-rows" style="margin-top:1.5rem">
                 <p>Drukste maand: <strong>${escapeHtml(d.busiest_month || "—")}</strong></p>
                 <p>Drukste dag: <strong>${escapeHtml(d.peak_day || "—")}</strong></p>
                 <p>Piekuur: <strong>${hour}</strong></p>
               </div>`
            )
          )
        );
      }

      if (d.favorite_device) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md">Jouw scherm</span>
               <h2 class="display-lg" style="margin-top:1rem;color:#fff">${escapeHtml(d.favorite_device)}</h2>
               <p class="body-md" style="margin-top:0.75rem">meest gebruikte player</p>`
            )
          )
        );
      }

      if (d.longest_streak_days > 0) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md">Langste streak</span>
               <h2 class="display-xl" style="margin-top:12px">${d.longest_streak_days} dagen op rij</h2>
               <p class="body-md" style="margin-top:1rem">jouw langste kijkstreak in ${year}</p>`
            )
          )
        );
      }

      if (d.top_movie_genres && d.top_movie_genres.length) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md">Filmgenres</span>
               ${buildRankList(
                 d.top_movie_genres.map((g) => ({ title: g.name, plays: g.plays })),
                 "keer",
                 false
               )}`,
              "top"
            )
          )
        );
      }

      if (d.top_show_genres && d.top_show_genres.length) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md">Seriesgenres</span>
               ${buildRankList(
                 d.top_show_genres.map((g) => ({ title: g.name, plays: g.plays })),
                 "keer",
                 false
               )}`,
              "top"
            )
          )
        );
      }

      if (d.server && d.server.rank) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md">Op de server</span>
               <h2 class="display-xl" style="margin-top:12px">#${d.server.rank}</h2>
               <p class="body-md" style="margin-top:1rem">tussen kijkers op deze server</p>`
            )
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
              `<span class="label-md">Server vs jij</span>
               <div class="stat-rows glass-card" style="margin-top:1.5rem;padding:1.25rem;border-radius:12px">
                 <p>Server #1 serie: <strong>${escapeHtml(serverTopShow)}</strong></p>
                 <p>Jouw serie: <strong>${escapeHtml(userTopShow)}</strong></p>
               </div>
               <p class="body-md" style="margin-top:1rem">${same ? "Zelfde smaak?" : "Jij koos je eigen pad"}</p>`
            )
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
              `<span class="label-md">Aanvragen</span>
               <div class="split-grid" style="margin-top:1.5rem">
                 <div class="glass-card">
                   <span class="stat-num">${tg.film_requests}</span>
                   <span class="label-md" style="color:var(--on-surface-variant)">films</span>
                 </div>
                 <div class="glass-card">
                   <span class="stat-num">${tg.serie_requests}</span>
                   <span class="label-md" style="color:var(--on-surface-variant)">series</span>
                 </div>
               </div>`
            )
          )
        );
      }

      if (tg.movies_requested > 0 || tg.series_requested > 0) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md">Aanvraag → kijken</span>
               <div class="stat-rows glass-card" style="margin-top:1.5rem;padding:1.25rem;border-radius:12px">
                 <p>Films: <strong>${tg.movies_requested}</strong> aangevraagd · <strong>${tg.movies_watched}</strong> bekeken</p>
                 <p>Series: <strong>${tg.series_requested}</strong> aangevraagd · <strong>${tg.series_watched}</strong> bekeken</p>
               </div>`
            )
          )
        );
      }

      if (tg.login_count > 0) {
        slides.push(
          createSlide(
            slideMain(
              `<span class="label-md">Botgebruik</span>
               <h2 class="display-xl" style="margin-top:12px">${tg.login_count}</h2>
               <p class="body-md" style="margin-top:1rem">keer dat je de aanvraagbot gebruikte</p>`
            )
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
             <span class="label-md" style="margin-top:1rem">Jouw persona</span>
             <h2 class="headline-lg" style="margin-top:8px">Op basis van jouw stats word je gekroond tot</h2>
             <p class="display-lg" style="margin-top:8px">${escapeHtml(d.persona)}</p>
             <p class="body-md" style="margin-top:12px">${escapeHtml(d.persona_tagline || "")}</p>`
          ),
          "cool"
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

      let bento = `<div class="stack-sm" style="width:100%;max-width:360px;margin-bottom:1rem">
        <p class="label-md">Jouw jaar in review</p>
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
            <span class="bento-value" style="font-size:1.1rem">${escapeHtml(topMedia.title)}</span>
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
        <button type="button" class="share-btn" id="btnShareSummary">
          <span class="material-symbols-outlined" style="font-size:20px">share</span>
          Deel je jaar
        </button>`;

      slides.push(
        createSlide(slideMain(bento, "top"), "warm")
      );
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
