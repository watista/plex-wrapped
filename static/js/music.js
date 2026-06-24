(function (global) {
  const FADE_MS = 900;
  const FADE_STEPS = 24;
  const PLAYBACK_VOLUME = 0.75;

  function slideIdFromElement(slideEl) {
    if (!slideEl?.classList) return null;
    for (const cls of slideEl.classList) {
      if (cls.startsWith("slide--")) {
        return cls.slice("slide--".length);
      }
    }
    return null;
  }

  function createWrappedMusic(options) {
    const music = options.music || { default_pool: [], slides: {} };
    const btnMusic = options.btnMusic || null;
    const reducedMotion = global.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let muted = reducedMotion;
    let currentUrl = null;
    let fadeTimer = null;

    const audioA = new Audio();
    const audioB = new Audio();
    audioA.loop = true;
    audioB.loop = true;
    audioA.preload = "auto";
    audioB.preload = "auto";

    let active = audioA;
    let standby = audioB;

    function updateMuteButton() {
      if (!btnMusic) return;
      const icon = btnMusic.querySelector(".material-symbols-outlined");
      const i18n = global.I18n || { t: (key) => key };
      btnMusic.setAttribute("aria-pressed", muted ? "true" : "false");
      btnMusic.setAttribute(
        "aria-label",
        muted ? i18n.t("wrapped.music_unmute") : i18n.t("wrapped.music_mute")
      );
      if (icon) {
        icon.textContent = muted ? "music_off" : "music_note";
      }
    }

    function setVolume(el, value) {
      el.volume = Math.max(0, Math.min(1, value));
    }

    function stopFade() {
      if (fadeTimer !== null) {
        clearInterval(fadeTimer);
        fadeTimer = null;
      }
    }

    function pauseInactive() {
      const inactive = active === audioA ? audioB : audioA;
      inactive.pause();
      setVolume(inactive, 0);
    }

    function resolveUrl(slideId) {
      if (slideId && music.slides && music.slides[slideId]) {
        return music.slides[slideId];
      }
      return null;
    }

    function playActive() {
      if (muted || reducedMotion || !currentUrl) return;
      active.play().catch(() => {});
    }

    function crossfadeTo(url) {
      if (muted || reducedMotion) {
        currentUrl = url;
        return;
      }
      if (!url) {
        stopFade();
        active.pause();
        standby.pause();
        currentUrl = null;
        return;
      }
      if (url === currentUrl && !active.paused) {
        return;
      }
      currentUrl = url;

      if (!active.src || active.paused) {
        active.src = url;
        setVolume(active, PLAYBACK_VOLUME);
        playActive();
        pauseInactive();
        return;
      }

      stopFade();
      standby.pause();
      standby.src = url;
      standby.currentTime = 0;
      setVolume(standby, 0);

      standby
        .play()
        .then(() => {
          let step = 0;
          fadeTimer = setInterval(() => {
            step += 1;
            const t = step / FADE_STEPS;
            setVolume(active, PLAYBACK_VOLUME * (1 - t));
            setVolume(standby, PLAYBACK_VOLUME * t);
            if (step >= FADE_STEPS) {
              stopFade();
              const previous = active;
              previous.pause();
              setVolume(previous, 0);
              active = standby;
              standby = previous;
              setVolume(active, PLAYBACK_VOLUME);
            }
          }, FADE_MS / FADE_STEPS);
        })
        .catch(() => {});
    }

    function onSlideChange(_index, slideEl) {
      const slideId = slideIdFromElement(slideEl);
      crossfadeTo(resolveUrl(slideId));
    }

    function tryUnlockPlayback() {
      if (muted || reducedMotion || !currentUrl) return;
      playActive();
    }

    function bindUnlock(el) {
      if (!el) return;
      el.addEventListener(
        "pointerdown",
        () => {
          tryUnlockPlayback();
        },
        { once: true }
      );
    }

    function setMuted(nextMuted) {
      muted = Boolean(nextMuted);
      updateMuteButton();
      if (muted) {
        stopFade();
        active.pause();
        standby.pause();
        return;
      }
      if (currentUrl) {
        active.src = currentUrl;
        setVolume(active, PLAYBACK_VOLUME);
        playActive();
      }
    }

    function toggleMuted() {
      setMuted(!muted);
      if (!muted && currentUrl) {
        crossfadeTo(currentUrl);
      }
    }

    function start() {
      updateMuteButton();
      bindUnlock(options.root);
      tryUnlockPlayback();
    }

    if (btnMusic) {
      btnMusic.addEventListener("click", (event) => {
        event.stopPropagation();
        toggleMuted();
      });
    }

    return {
      onSlideChange,
      setMuted,
      toggleMuted,
      isMuted: () => muted,
      start,
    };
  }

  global.createWrappedMusic = createWrappedMusic;
})(typeof window !== "undefined" ? window : globalThis);
