/**
 * Transform-based story carousel with edge taps and touch drag.
 */
(function (global) {
  function createStoryCarousel(options) {
    const root = options.root;
    if (!root) throw new Error("createStoryCarousel: root element is required");

    const onChange = options.onChange || (() => {});
    const edgeRatio = options.edgeRatio ?? 0.2;
    const edgeMaxPx = options.edgeMaxPx ?? 88;
    const snapThreshold = options.snapThreshold ?? 0.18;
    const rubberBand = options.rubberBand ?? 0.32;

    let trackEl = null;
    let activeIndex = 0;
    let slideCount = 0;
    let suppressClick = false;
    let dragState = null;
    let mounted = false;

    const onPointerDown = (e) => {
      if (!e.isPrimary || !trackEl) return;
      if (e.target.closest("button, a, .icon-btn, .share-btn, .share-icon-btn, input, textarea, select, label")) return;

      dragState = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        startIndex: activeIndex,
        dragging: false,
        width: root.clientWidth,
      };
      root.setPointerCapture(e.pointerId);
    };

    const onPointerMove = (e) => {
      if (!dragState || e.pointerId !== dragState.pointerId) return;

      const dx = e.clientX - dragState.startX;
      const dy = e.clientY - dragState.startY;

      if (!dragState.dragging) {
        if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return;
        if (Math.abs(dy) > Math.abs(dx)) {
          dragState = null;
          root.releasePointerCapture(e.pointerId);
          return;
        }
        dragState.dragging = true;
      }

      const base = -dragState.startIndex * dragState.width;
      let px = base + dx;

      if (dragState.startIndex === 0 && px > 0) px *= rubberBand;
      else if (dragState.startIndex === slideCount - 1) {
        const min = -dragState.startIndex * dragState.width;
        if (px < min) px = min + (px - min) * rubberBand;
      }

      setTrackTranslate(px, true);
    };

    const finishDrag = (e) => {
      if (!dragState || e.pointerId !== dragState.pointerId) return;
      root.releasePointerCapture(e.pointerId);

      const dx = e.clientX - dragState.startX;
      const wasDragging = dragState.dragging;
      const width = dragState.width;
      dragState = null;

      if (wasDragging) suppressClick = true;
      trackEl?.classList.remove("is-dragging");

      if (!wasDragging) return;

      const threshold = width * snapThreshold;
      let next = activeIndex;
      if (dx < -threshold) next += 1;
      else if (dx > threshold) next -= 1;

      goTo(next);
    };

    const onClick = (e) => {
      if (suppressClick) {
        suppressClick = false;
        return;
      }
      if (e.target.closest("button, a, .icon-btn, .share-btn, .share-icon-btn, input, textarea, select, label")) return;

      const rect = root.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const edge = Math.min(rect.width * edgeRatio, edgeMaxPx);

      if (x < edge) prev();
      else if (x > rect.width - edge) next();
    };

    const onResize = () => {
      if (!trackEl) return;
      goTo(activeIndex, { animate: false });
    };

    function setTrackTranslate(px, dragging) {
      if (!trackEl) return;
      trackEl.classList.toggle("is-dragging", dragging);
      trackEl.style.transform = `translate3d(${px}px, 0, 0)`;
    }

    function goTo(index, { animate = true } = {}) {
      if (!trackEl || slideCount === 0) return activeIndex;

      const next = Math.max(0, Math.min(index, slideCount - 1));
      const changed = next !== activeIndex;
      activeIndex = next;

      const reducedMotion = global.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!animate || reducedMotion) {
        trackEl.classList.add("slides-track--instant");
        setTrackTranslate(-next * root.clientWidth, false);
        trackEl.offsetHeight;
        trackEl.classList.remove("slides-track--instant");
      } else {
        setTrackTranslate(-next * root.clientWidth, false);
      }

      if (changed) {
        onChange(next, trackEl.children[next] || null);
      }

      return activeIndex;
    }

    function mount(slides) {
      if (!slides?.length) return;

      trackEl = document.createElement("div");
      trackEl.className = "slides-track";
      slides.forEach((slide) => trackEl.appendChild(slide));
      root.appendChild(trackEl);

      slideCount = slides.length;
      activeIndex = 0;

      root.addEventListener("pointerdown", onPointerDown);
      root.addEventListener("pointermove", onPointerMove);
      root.addEventListener("pointerup", finishDrag);
      root.addEventListener("pointercancel", finishDrag);
      root.addEventListener("click", onClick);
      global.addEventListener("resize", onResize);

      mounted = true;
      goTo(0, { animate: false });
      onChange(0, trackEl.children[0] || null);
    }

    function destroy() {
      root.removeEventListener("pointerdown", onPointerDown);
      root.removeEventListener("pointermove", onPointerMove);
      root.removeEventListener("pointerup", finishDrag);
      root.removeEventListener("pointercancel", finishDrag);
      root.removeEventListener("click", onClick);
      global.removeEventListener("resize", onResize);

      trackEl?.remove();
      trackEl = null;
      slideCount = 0;
      activeIndex = 0;
      dragState = null;
      mounted = false;
    }

    function next() {
      return goTo(activeIndex + 1);
    }

    function prev() {
      return goTo(activeIndex - 1);
    }

    return {
      mount,
      destroy,
      goTo,
      next,
      prev,
      getIndex: () => activeIndex,
      getCount: () => slideCount,
      getTrack: () => trackEl,
    };
  }

  global.createStoryCarousel = createStoryCarousel;
})(typeof window !== "undefined" ? window : globalThis);
