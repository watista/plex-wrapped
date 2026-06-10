(function (global) {
  const sessionStart = Date.now();
  let slideCount = 0;
  let lastSlideId = null;
  let wrappedLoaded = false;
  let sessionEnded = false;

  function gtagEvent(name, params) {
    if (typeof global.gtag === "function") {
      global.gtag("event", name, params || {});
    }
  }

  function sendActivity(payload) {
    const body = JSON.stringify({
      ...payload,
      metadata: {
        ...(payload.metadata || {}),
        path: global.location?.pathname || "",
        share_mode: document.body?.dataset?.shareMode === "true",
      },
    });

    if (global.navigator?.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      global.navigator.sendBeacon("/api/activity", blob);
      return;
    }

    global
      .fetch("/api/activity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      })
      .catch(() => {});
  }

  function track(event, data) {
    const payload = { event, ...data };
    gtagEvent(event, data || {});
    sendActivity(payload);
  }

  function slideIdFromElement(slideEl, index) {
    if (!slideEl?.classList) return `slide-${index}`;
    for (const cls of slideEl.classList) {
      if (cls.startsWith("slide--")) return cls.slice("slide--".length);
    }
    return `slide-${index}`;
  }

  function trackSlideView(index, slideEl) {
    const slideId = slideIdFromElement(slideEl, index);
    if (slideId === lastSlideId) return;
    lastSlideId = slideId;

    const payload = {
      slide_id: slideId,
      slide_index: index,
      slide_count: slideCount,
    };
    track("slide_view", payload);

    if (slideCount > 0 && index === slideCount - 1) {
      track("summary_reached", payload);
    }
  }

  function trackWrappedLoaded(count, persona) {
    if (wrappedLoaded) return;
    wrappedLoaded = true;
    slideCount = count;
    track("wrapped_loaded", {
      slide_count: count,
      metadata: { persona: persona || null },
    });
  }

  function trackButtonClick(button) {
    track("summary_button_click", { button, slide_id: lastSlideId || "summary" });
  }

  function trackSessionEnd(reason) {
    if (sessionEnded) return;
    sessionEnded = true;
    track("session_end", {
      duration_ms: Date.now() - sessionStart,
      slide_id: lastSlideId,
      slide_count: slideCount,
      metadata: { reason: reason || "unload" },
    });
  }

  function bindLifecycle() {
    global.addEventListener("pagehide", () => trackSessionEnd("pagehide"));
    global.addEventListener("beforeunload", () => trackSessionEnd("beforeunload"));
  }

  bindLifecycle();

  global.WrappedAnalytics = {
    track,
    trackSlideView,
    trackWrappedLoaded,
    trackButtonClick,
    trackSessionEnd,
    setSlideCount(count) {
      slideCount = count;
    },
  };
})(typeof window !== "undefined" ? window : globalThis);
