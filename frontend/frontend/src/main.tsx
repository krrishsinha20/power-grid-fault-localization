import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import "leaflet/dist/leaflet.css";

// NOTE: intentionally not wrapping in <React.StrictMode>. StrictMode's
// deliberate double-invoke of mount effects in development is known to
// conflict with react-leaflet, which does direct, imperative DOM
// manipulation (creating a Leaflet map instance on the container div)
// that isn't idempotent across a mount -> unmount -> remount cycle.
// The visible symptom was a broken/duplicated map render (a blank gray
// box alongside a stray low-zoom world view) that reproduced on every
// dev run, independent of caching or stale processes. Production
// builds don't double-invoke effects, so this was a dev-only bug --
// but removing StrictMode avoids it outright rather than working
// around react-leaflet's imperative lifecycle. Documented in
// DECISIONS.md.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <App />
);