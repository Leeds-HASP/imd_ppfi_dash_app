// MapLibre + PMTiles choropleth, configured at runtime by Dash stores.
//
// Each mount is <div class="pmtiles-map" id="..."> with two data attributes:
//   data-palette    initial palette name (ppfi | imd | mismatch)
//   data-drilldown  "1" to enable LAD-click drilldown
//
// Server callbacks push state via window.pmtilesPush(mountId, patch). Patch
// keys: lookup, filter, geography, palette, selected. LAD clicks and the
// Clear button mutate selected_lad_store + geography_selector via set_props.
(function () {
  // ---------------------------------------------------------------- config ----
  // window.PMTILES_URL is injected by app.py (Dash index_string) from the
  // PMTILES_URL env var. Falls back to the local dev tile server.
  const TILE_URL = (typeof window !== "undefined" && window.PMTILES_URL)
                 || "http://localhost:8080/england.pmtiles";

  const PALETTES = {
    ppfi: ["#00214d","#003366","#004c8c","#0066a1","#3386b2",
           "#66a6c4","#99c6d7","#cce6e9","#e6f1f4","#ffffff"],
    imd:  ["#002d12","#00441b","#006d2c","#238b45","#41ab5d",
           "#74c476","#a1d99b","#c7e9c0","#edf8e9","#ffffff"],
    mismatch: ["#ffffcc","#ffeda0","#fed976","#feb24c","#fd8d3c",
               "#fc4e2a","#e31a1c","#bd0026","#800026","#4a0014"],
  };
  const DECILE_BINS = [1,2,3,4,5,6,7,8,9,10];

  const BASEMAP_TILES = [
    "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
    "https://cartodb-basemaps-b.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
    "https://cartodb-basemaps-c.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
    "https://cartodb-basemaps-d.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
  ];
  const BASEMAP_ATTRIB =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

  // ----------------------------------------------------------------- deps -----
  const CDN = [
    "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js",
    "https://unpkg.com/pmtiles@3.2.1/dist/pmtiles.js",
  ];
  let depsReady = null;
  function loadDeps() {
    if (depsReady) return depsReady;
    depsReady = (async () => {
      for (const src of CDN) {
        await new Promise((ok, fail) => {
          const s = document.createElement("script");
          s.src = src; s.onload = ok; s.onerror = fail;
          document.head.appendChild(s);
        });
      }
      const proto = new pmtiles.Protocol();
      maplibregl.addProtocol("pmtiles", proto.tile);
    })();
    return depsReady;
  }

  // ----------------------------------------------------- color interpolation --
  function hexToRgb(hex) {
    const h = hex.replace("#", "");
    return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)];
  }
  function rgbToHex(r,g,b) {
    const h = (n) => Math.round(n).toString(16).padStart(2,"0");
    return "#" + h(r) + h(g) + h(b);
  }
  function lerpColor(a, b, t) {
    const A = hexToRgb(a), B = hexToRgb(b);
    return rgbToHex(A[0]+(B[0]-A[0])*t, A[1]+(B[1]-A[1])*t, A[2]+(B[2]-A[2])*t);
  }
  function interpolate(palette, t) {
    if (t <= 0) return palette[0];
    if (t >= 1) return palette[palette.length-1];
    const x = t * (palette.length - 1);
    const lo = Math.floor(x);
    return lerpColor(palette[lo], palette[lo+1], x - lo);
  }
  function classify(values, level, paletteName) {
    if (!values.length) return null;
    let vmin = Infinity, vmax = -Infinity;
    for (const v of values) { if (v < vmin) vmin = v; if (v > vmax) vmax = v; }
    if (paletteName === "mismatch") return {mode: "diff",  vmin: 0, vmax: Math.max(9, vmax)};
    if (level === "lad")            return {mode: "rank",  vmin: 1, vmax: Math.max(vmax, vmin + 1)};
    return {mode: "decile", vmin: 1, vmax: 10};
  }

  // ============================ legend overlay ==============================
  function buildLegend(host) {
    const el = document.createElement("div");
    el.className = "pmtiles-legend";
    el.innerHTML = `
      <div class="pmtiles-legend__title"></div>
      <div class="pmtiles-legend__bar"></div>
      <div class="pmtiles-legend__labels">
        <span class="pmtiles-legend__lo"></span>
        <span class="pmtiles-legend__hi"></span>
      </div>
    `;
    host.appendChild(el);
    return el;
  }
  function updateLegend(el, cls, palette) {
    if (!cls) { el.style.display = "none"; return; }
    el.style.display = "block";
    const title = cls.mode === "decile" ? "Decile (1 = most deprived)"
                : cls.mode === "rank"   ? "Rank (1 = most deprived)"
                : "Absolute decile difference";
    el.querySelector(".pmtiles-legend__title").textContent = title;
    const stops = palette.map((c,i) => `${c} ${(i/(palette.length-1))*100}%`).join(", ");
    el.querySelector(".pmtiles-legend__bar").style.background = `linear-gradient(to right, ${stops})`;
    el.querySelector(".pmtiles-legend__lo").textContent = Math.round(cls.vmin);
    el.querySelector(".pmtiles-legend__hi").textContent = Math.round(cls.vmax);
  }

  // ============================ title pill ==================================
  function buildTitle(host) {
    const el = document.createElement("div");
    el.className = "pmtiles-title";
    el.style.display = "none";
    host.appendChild(el);
    return el;
  }
  function updateTitle(el, text) {
    if (!text) { el.style.display = "none"; return; }
    el.style.display = "block";
    el.textContent = text;
  }

  // ============================ selection chip ==============================
  function buildSelectionChip(host, onClear) {
    const el = document.createElement("div");
    el.className = "pmtiles-chip";
    el.style.display = "none";
    el.innerHTML = `<span class="pmtiles-chip__label"></span><button class="pmtiles-chip__btn">✕ Clear</button>`;
    el.querySelector("button").addEventListener("click", onClear);
    host.appendChild(el);
    return el;
  }
  function updateChip(el, selected) {
    if (!selected.length) { el.style.display = "none"; return; }
    el.style.display = "flex";
    const label = el.querySelector(".pmtiles-chip__label");
    if (selected.length === 1) label.textContent = `${selected[0].lad_name || selected[0].lad_id}`;
    else label.textContent = `${selected.length} LADs selected`;
  }

  // -------------------------- registry for Dash bridge --------------------------
  window.pmtilesMaps = window.pmtilesMaps || {};
  window.__pmtilesPending = window.__pmtilesPending || {};
  window.pmtilesPush = function (mountId, patch) {
    const fn = window.pmtilesMaps[mountId];
    if (typeof fn === "function") { fn(patch); return; }
    const cur = window.__pmtilesPending[mountId] || {};
    window.__pmtilesPending[mountId] = Object.assign(cur, patch);
  };

  // ----------------------------------------------------- per-mount lifecycle --
  function createMap(el) {
    let paletteName = el.dataset.palette || "ppfi";
    let palette = PALETTES[paletteName] || PALETTES.ppfi;
    const drilldown = el.dataset.drilldown === "1";

    let lookup    = {lsoa: {}, lad: {}};
    let filter    = {lsoa: null, lad: null};
    let geography = "lsoa";
    let selected  = [];                       // [{lad_id, lad_name}, ...]
    let activeClass = null;

    const map = new maplibregl.Map({
      container: el,
      style: {
        version: 8,
        sources: {
          basemap: { type: "raster", tiles: BASEMAP_TILES, tileSize: 256,
                     attribution: BASEMAP_ATTRIB },
          tiles:   { type: "vector", url: "pmtiles://" + TILE_URL },
        },
        layers: [
          { id: "basemap",          type: "raster", source: "basemap" },
          // LAD fill is always present so clicks land on it. Opacity switches
          // between "choropleth" and "ghost" depending on mode.
          { id: "lad-fill",         type: "fill", source: "tiles", "source-layer": "lad",
            paint: {"fill-color":"#cccccc","fill-opacity":0.85} },
          { id: "lad-line",         type: "line", source: "tiles", "source-layer": "lad",
            paint: {"line-color":"#000","line-width":0.5} },
          // LSOA layers — visibility toggled by mode
          { id: "lsoa-fill",        type: "fill", source: "tiles", "source-layer": "lsoa",
            paint: {"fill-color":"#cccccc","fill-opacity":0.9}, layout: {visibility:"none"} },
          { id: "lsoa-line",        type: "line", source: "tiles", "source-layer": "lsoa",
            paint: {"line-color":"#ffffff","line-width":0.2}, layout: {visibility:"none"} },
          // Thick highlight around selected LADs — drawn last so it sits on top
          { id: "lad-selected-line",type: "line", source: "tiles", "source-layer": "lad",
            paint: {"line-color":"#000","line-width":2.5}, filter: ["in", ["get","id"], ["literal", []]] },
        ],
      },
      center: [-1.5, 53.0], zoom: 6,
    });

    const titleEl = buildTitle(el);
    const legendEl = buildLegend(el);
    const chipEl = buildSelectionChip(el, () => clearSelection());

    // ------------------------- popup --------------------------------------
    const popup = new maplibregl.Popup({closeButton:false, closeOnClick:false, maxWidth:"280px"});
    let lastHoverKey = null;
    function pushHover(level, feature) {
      const sp = window.dash_clientside && window.dash_clientside.set_props;
      if (!sp) return;
      if (!feature) {
        if (lastHoverKey === null) return;
        lastHoverKey = null;
        sp("hovered_feature", {data: null});
        return;
      }
      const id = feature.properties.id;
      const key = level + ":" + id;
      if (key === lastHoverKey) return;
      lastHoverKey = key;
      sp("hovered_feature", {data: {level, id, name: feature.properties.name || ""}});
    }
    function fmt(v) { return v == null ? "—" : (Number.isInteger(v) ? String(v) : v.toFixed(2)); }
    function tip(e, level) {
      const f = e.features[0]; if (!f) return;
      const id = f.properties.id;
      const name = f.properties.name || "";
      const v = lookup[level] && lookup[level][id];
      let phrase = "";
      if (activeClass) {
        if (activeClass.mode === "decile") phrase = v != null ? `Decile <b>${fmt(v)}</b> of 10` : "";
        else if (activeClass.mode === "rank") phrase = v != null ? `Rank <b>${fmt(v)}</b> of ${activeClass.vmax}` : "";
        else if (activeClass.mode === "diff") {
          const label = level === "lad" ? "Mean LSOA decile gap" : "Decile gap";
          phrase = v != null ? `${label} <b>${fmt(v)}</b>` : "";
        }
      }
      const header = level === "lad"
        ? `<div class="pmtiles-tip__title">${name || id}</div><div class="pmtiles-tip__sub">${id}</div>`
        : `<div class="pmtiles-tip__title">${id}</div>${name ? `<div class="pmtiles-tip__sub">${name}</div>` : ""}`;
      const body = phrase ? `<div class="pmtiles-tip__val">${phrase}</div>` : "";
      let hint = "";
      if (drilldown && level === "lad") {
        const isSel = selected.some(s => s.lad_id === id);
        hint = `<div class="pmtiles-tip__hint">Click to ${isSel ? "deselect" : "select"}</div>`;
      }
      popup.setLngLat(e.lngLat).setHTML(`<div class="pmtiles-tip">${header}${body}${hint}</div>`).addTo(map);
    }
    // Hover priority: LSOA tip wins when LSOAs are the primary layer; LAD tip
    // when LADs are. Both layers' handlers fire on overlap, but the second-
    // dispatched one's setHTML overwrites the first.
    map.on("mousemove", "lad-fill",  (e) => {
      if (isLadPrimary())      { map.getCanvas().style.cursor = drilldown ? "pointer" : ""; tip(e, "lad"); pushHover("lad", e.features[0]); }
      else if (drilldown)      { map.getCanvas().style.cursor = "pointer"; }
    });
    map.on("mousemove", "lsoa-fill", (e) => {
      if (!isLadPrimary()) { tip(e, "lsoa"); pushHover("lsoa", e.features[0]); }
    });
    map.on("mouseleave", "lad-fill",  () => { map.getCanvas().style.cursor = ""; if (isLadPrimary()) { popup.remove(); pushHover(null, null); } });
    map.on("mouseleave", "lsoa-fill", () => { if (!isLadPrimary()) { popup.remove(); pushHover(null, null); } });

    // ------------------------- click → toggle selection -------------------
    if (drilldown) {
      map.on("click", "lad-fill", (e) => {
        const f = e.features[0]; if (!f) return;
        const lad_id = f.properties.id, lad_name = f.properties.name || lad_id;
        const cur = (window.__pmtilesSelectedLads || []).slice();
        const idx = cur.findIndex((s) => s.lad_id === lad_id);
        const next = idx >= 0 ? cur.filter((s) => s.lad_id !== lad_id)
                              : cur.concat([{lad_id, lad_name}]);
        pushSelection(next);
      });
    }
    function clearSelection() { pushSelection([]); }
    function pushSelection(next) {
      const sp = window.dash_clientside && window.dash_clientside.set_props;
      if (!sp) return;
      window.__pmtilesSelectedLads = next;
      sp("selected_lad_store", {data: next});
      sp("geography_selector",  {value: next.length ? "lsoa" : "lad"});
    }

    // ------------------------- paint / filter / visibility -----------------
    function isLadPrimary() { return geography === "lad" && selected.length === 0; }

    function paintExpr(level, primary) {
      const table = lookup[level] || {};
      const values = [];
      for (const k in table) if (table[k] != null) values.push(table[k]);
      const cls = classify(values, level, paletteName);
      if (primary) activeClass = cls;
      if (!cls) return "#cccccc";
      const pairs = [];
      const useDiscrete = cls.mode === "decile";
      for (const k in table) {
        const v = table[k];
        if (v == null) continue;
        let color;
        if (useDiscrete) {
          const idx = Math.max(0, Math.min(DECILE_BINS.length - 1, Math.round(v) - 1));
          color = palette[idx];
        } else {
          const t = (v - cls.vmin) / (cls.vmax - cls.vmin || 1);
          color = interpolate(palette, t);
        }
        pairs.push(k, color);
      }
      return pairs.length ? ["match", ["get","id"], ...pairs, "#cccccc"] : "#cccccc";
    }

    function applyVisibility() {
      const ladPrimary = isLadPrimary();
      // LSOA layers visible whenever LADs are NOT the primary view
      map.setLayoutProperty("lsoa-fill", "visibility", ladPrimary ? "none" : "visible");
      map.setLayoutProperty("lsoa-line", "visibility", ladPrimary ? "none" : "visible");
      // Selected-LAD highlight
      const selIds = selected.map(s => s.lad_id);
      map.setFilter("lad-selected-line", ["in", ["get","id"], ["literal", selIds]]);
    }
    function applyPaint() {
      activeClass = null;
      const ladPrimary = isLadPrimary();
      // LAD fill: choropleth when primary, ghost (clickable but invisible) otherwise
      if (ladPrimary) {
        map.setPaintProperty("lad-fill", "fill-color", paintExpr("lad", true));
        map.setPaintProperty("lad-fill", "fill-opacity", 0.85);
      } else {
        map.setPaintProperty("lad-fill", "fill-color", "#ffffff");
        map.setPaintProperty("lad-fill", "fill-opacity", 0.01);   // ~invisible, still clickable
      }
      // LSOA fill: always paint (cheap if no values); shown when not lad-primary
      map.setPaintProperty("lsoa-fill", "fill-color", paintExpr("lsoa", !ladPrimary));
      updateLegend(legendEl, activeClass, palette);
      updateChip(chipEl, selected);
      updateTitle(titleEl, lookup && lookup._title);
    }
    function applyFilter() {
      const lsoaIds = filter.lsoa;
      const ladIds  = filter.lad;
      map.setFilter("lsoa-fill", lsoaIds == null ? null : ["in", ["get","id"], ["literal", lsoaIds]]);
      map.setFilter("lsoa-line", lsoaIds == null ? null : ["in", ["get","id"], ["literal", lsoaIds]]);
      // lad-fill is always clickable across all LADs — only lad-line follows
      // the rank-percentile filter so user keeps an accurate visual cue.
      map.setFilter("lad-line", ladIds == null ? null : ["in", ["get","id"], ["literal", ladIds]]);
    }
    function applyAll() { applyVisibility(); applyPaint(); applyFilter(); }

    let styleReady = false;
    map.on("load", () => {
      styleReady = true;
      const pending = window.__pmtilesPending[el.id];
      if (pending) {
        if (pending.lookup)    lookup    = pending.lookup;
        if (pending.filter)    filter    = pending.filter;
        if (typeof pending.geography === "string") geography = pending.geography;
        if (typeof pending.palette === "string" && PALETTES[pending.palette]) {
          paletteName = pending.palette; palette = PALETTES[paletteName];
        }
        if (Array.isArray(pending.selected)) selected = pending.selected;
        delete window.__pmtilesPending[el.id];
      }
      applyAll();
    });

    window.pmtilesMaps[el.id] = function (patch) {
      if (!patch) return;
      if (patch.lookup)    lookup    = patch.lookup;
      if (patch.filter)    filter    = patch.filter;
      if (typeof patch.geography === "string") geography = patch.geography;
      if (typeof patch.palette === "string" && PALETTES[patch.palette]) {
        paletteName = patch.palette; palette = PALETTES[paletteName];
      }
      if (Array.isArray(patch.selected)) selected = patch.selected;
      if (styleReady) applyAll();
    };

    new ResizeObserver(() => map.resize()).observe(el);
  }

  // ---------------------------- mount discovery -----------------------------
  const seen = new WeakSet();
  setInterval(async () => {
    const mounts = document.querySelectorAll(".pmtiles-map");
    if (!mounts.length) return;
    await loadDeps();
    mounts.forEach((el) => {
      if (seen.has(el)) return;
      if (!el.clientWidth || !el.clientHeight) return;
      seen.add(el);
      try { createMap(el); }
      catch (e) { console.error("pmtiles map init failed", e); seen.delete(el); }
    });
  }, 300);
})();
