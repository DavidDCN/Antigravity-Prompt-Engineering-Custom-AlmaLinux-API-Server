"""Interactive Web GUI for the ATTRial Image Server.

Served at GET / and GET /ui so users visiting http://<alma-ip>/ in a browser get
an intuitive visual dashboard with:
- An unobstructed Open Background Frame to view backgrounds clearly (never hidden behind header text)
- A horizontally scrollable Database Image Options Carousel showing all images from metadata.db
- Scrollable Galleries for Server Backgrounds (/api/backgrounds) and User Uploads (/api/uploads)
- A SQLite Database & File Explorer (/api/database) showing exact disk paths and direct file URLs
"""
from __future__ import annotations

WEB_GUI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ATTRial Image Server — Visual Web GUI</title>
  <style>
    :root {
      color-scheme: light dark;
      --brand-color: #2563eb;
      --brand-hover: #1d4ed8;
      --bg-page: #f8fafc;
      --bg-card: #ffffff;
      --bg-subtle: #f1f5f9;
      --text-main: #0f172a;
      --text-muted: #475569;
      --border-color: #cbd5e1;
      --border-strong: #64748b;
      --success-bg: #dcfce7;
      --success-text: #166534;
      --error-bg: #fee2e2;
      --error-text: #991b1b;
      --badge-bg: #dbeafe;
      --badge-text: #1e40af;
      --gold-bg: #fef3c7;
      --gold-text: #92400e;
      --shadow: 0 4px 16px rgba(15, 23, 42, 0.07);
      --radius: 12px;
    }

    @media (prefers-color-scheme: dark) {
      :root {
        --brand-color: #60a5fa;
        --brand-hover: #93c5fd;
        --bg-page: #0b0f19;
        --bg-card: #111827;
        --bg-subtle: #1e293b;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --border-color: #334155;
        --border-strong: #94a3b8;
        --success-bg: #064e3b;
        --success-text: #a7f3d0;
        --error-bg: #7f1d1d;
        --error-text: #fecaca;
        --badge-bg: #1e3a8a;
        --badge-text: #bfdbfe;
        --gold-bg: #78350f;
        --gold-text: #fde68a;
        --shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
      }
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
      background-color: var(--bg-page);
      color: var(--text-main);
      accent-color: var(--brand-color);
    }

    .visually-hidden {
      position: absolute !important;
      clip-path: inset(50%) !important;
      overflow: hidden !important;
      width: 1px !important;
      height: 1px !important;
      margin: -1px !important;
      padding: 0 !important;
      border: 0 !important;
      white-space: nowrap !important;
    }

    /* Clean top header — never puts background images behind the title text */
    .top-header {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #ffffff;
      padding: 1.25rem 1.5rem;
      border-block-end: 1px solid var(--border-color);
    }

    .header-inner {
      max-width: 1320px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: center;
      justify-content: space-between;
    }

    .header-title h1 {
      margin: 0 0 0.25rem 0;
      font-size: 1.5rem;
    }

    .header-title p {
      margin: 0;
      color: #cbd5e1;
      font-size: 0.92rem;
    }

    .status-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 0.6rem;
      align-items: center;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.4rem 0.85rem;
      border-radius: 999px;
      font-size: 0.85rem;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.14);
      color: #f8fafc;
      text-decoration: none;
    }

    .pill.ok {
      background: #065f46;
      color: #d1fae5;
    }

    .container {
      max-width: 1320px;
      margin: 0 auto;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .panel {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius);
      padding: 1.35rem 1.5rem;
      box-shadow: var(--shadow);
    }

    .panel-header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      margin-block-end: 1rem;
      padding-block-end: 0.75rem;
      border-block-end: 1px solid var(--border-color);
    }

    .panel-header h2 {
      margin: 0;
      font-size: 1.2rem;
    }

    /* Dedicated Open Background Frame (unobstructed viewing space) */
    .open-frame-stage {
      position: relative;
      width: 100%;
      height: 360px;
      border-radius: 10px;
      border: 2px solid var(--border-strong);
      background:
        repeating-conic-gradient(rgba(148, 163, 184, 0.12) 0% 25%, transparent 0% 50%)
        50% / 24px 24px,
        #090d16;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      margin-block-end: 0.85rem;
    }

    .open-frame-stage img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      cursor: zoom-in;
      transition: object-fit 0.15s ease;
    }

    .open-frame-stage.cover-mode img {
      object-fit: cover;
    }

    .frame-placeholder {
      color: #94a3b8;
      text-align: center;
      padding: 1.5rem;
      font-size: 0.95rem;
    }

    .frame-info-bar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      padding: 0.65rem 0.9rem;
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      margin-block-end: 1rem;
      font-size: 0.88rem;
    }

    /* Horizontally Scrollable Options Carousel (Modern Web Guidance carousel pattern) */
    .options-carousel {
      display: flex;
      flex-direction: column;
      gap: 0.65rem;
    }

    .carousel-toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
    }

    .filter-tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
    }

    .filter-tab {
      min-height: 36px;
      padding: 0.3rem 0.75rem;
      font-size: 0.84rem;
      border-radius: 999px;
      background: var(--bg-subtle);
      color: var(--text-main);
      border: 1px solid var(--border-color);
    }

    .filter-tab[aria-pressed="true"] {
      background: var(--brand-color);
      color: #ffffff;
      border-color: var(--brand-color);
    }

    @media (prefers-color-scheme: dark) {
      .filter-tab[aria-pressed="true"] {
        color: #0b0f19;
      }
    }

    .carousel-track {
      display: flex;
      gap: 0.85rem;
      overflow-x: auto;
      scroll-snap-type: x mandatory;
      padding: 0.4rem 0.25rem 0.75rem 0.25rem;
      touch-action: manipulation;
      scrollbar-width: thin;
    }

    @media (prefers-reduced-motion: no-preference) {
      .carousel-track {
        scroll-behavior: smooth;
      }
    }

    .option-slide {
      flex: 0 0 185px;
      scroll-snap-align: start;
      background: var(--bg-subtle);
      border: 2px solid var(--border-color);
      border-radius: 10px;
      overflow: hidden;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      transition: border-color 0.15s ease, transform 0.15s ease;
    }

    .option-slide:hover {
      border-color: var(--brand-color);
    }

    .option-slide.active {
      border-color: var(--brand-color);
      box-shadow: 0 0 0 2px var(--brand-color);
    }

    .option-slide-thumb {
      width: 100%;
      height: 105px;
      background: #0f172a;
      overflow: hidden;
      position: relative;
    }

    .option-slide-thumb img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    .option-slide-meta {
      padding: 0.5rem 0.6rem;
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      min-inline-size: 0;
    }

    /* Main 2-column layout: Upload Form + Galleries */
    .workspace-grid {
      display: grid;
      grid-template-columns: minmax(320px, 400px) 1fr;
      gap: 1.5rem;
      align-items: start;
    }

    @media (max-width: 920px) {
      .workspace-grid {
        grid-template-columns: 1fr;
      }
    }

    /* Scrollable vertical containers with scrollability affordance shadows */
    .scrollable-gallery {
       --surface: var(--bg-card);
      max-height: 420px;
      overflow-y: auto;
      container-type: scroll-state;
      padding-inline-end: 0.25rem;
    }

    .scrollable-gallery::before,
    .scrollable-gallery::after {
      content: "";
      display: block;
      position: sticky;
      block-size: 0.75rem;
      z-index: 2;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s;
    }

    .scrollable-gallery::before {
      inset-block-start: 0;
      margin-block-end: -0.75rem;
      background: radial-gradient(farthest-side at 50% 0, rgb(0 0 0 / 0.22), transparent);
    }

    .scrollable-gallery::after {
      inset-block-end: 0;
      margin-block-start: -0.75rem;
      background: radial-gradient(farthest-side at 50% 100%, rgb(0 0 0 / 0.22), transparent);
    }

    @container scroll-state(scrollable: block-start) {
      .scrollable-gallery::before {
        opacity: 1;
      }
    }

    @container scroll-state(scrollable: block-end) {
      .scrollable-gallery::after {
        opacity: 1;
      }
    }

    @supports not (container-type: scroll-state) {
      .scrollable-gallery::before,
      .scrollable-gallery::after {
        animation: show-scroll-shadow linear both;
        animation-timeline: scroll();
      }
      .scrollable-gallery::before {
        animation-range: 0 2rem;
      }
      .scrollable-gallery::after {
        animation-direction: reverse;
        animation-range: calc(100% - 2rem) 100%;
      }
    }

    @keyframes show-scroll-shadow {
      to {
        opacity: 1;
      }
    }

    @supports not ((container-type: scroll-state) or (animation-timeline: scroll())) {
      .scrollable-gallery {
        background:
          linear-gradient(var(--surface) 30%, transparent) top / 100% 2rem no-repeat local,
          linear-gradient(transparent, var(--surface) 70%) bottom / 100% 2rem no-repeat local,
          radial-gradient(farthest-side at 50% 0, rgb(0 0 0 / 0.18), transparent) top / 100% 0.75rem no-repeat,
          radial-gradient(farthest-side at 50% 100%, rgb(0 0 0 / 0.18), transparent) bottom / 100% 0.75rem no-repeat,
          var(--surface);
      }
    }

    /* Forms */
    .field {
      display: flex;
      flex-direction: column;
      align-items: stretch;
      gap: 0.3rem;
      margin-block-end: 1.15rem;
    }

    .field label {
      font-weight: 600;
      font-size: 0.94rem;
    }

    .hint {
      font-size: 0.82rem;
      color: var(--text-muted);
    }

    input[type="text"],
    input[type="password"],
    input[type="file"],
    textarea {
      font: inherit;
      font-size: max(1rem, 1em);
      padding: 0.6rem 0.75rem;
      min-height: 46px;
      border: 1.5px solid var(--border-strong);
      border-radius: 8px;
      background: var(--bg-page);
      color: var(--text-main);
      box-sizing: border-box;
      width: 100%;
    }

    textarea {
      min-height: 95px;
      resize: vertical;
    }

    input:focus-visible,
    textarea:focus-visible,
    button:focus-visible,
    a:focus-visible,
    .option-slide:focus-visible {
      outline: 3px solid var(--brand-color);
      outline-offset: 2px;
    }

    .checkbox-row {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      margin-block-end: 1.15rem;
      padding: 0.6rem 0.75rem;
      background: var(--bg-subtle);
      border-radius: 8px;
    }

    .checkbox-row input[type="checkbox"] {
      width: 1.2rem;
      height: 1.2rem;
      margin: 0;
      cursor: pointer;
    }

    .checkbox-row label {
      cursor: pointer;
      font-weight: 500;
    }

    .preview-box {
      border: 1.5px dashed var(--border-strong);
      border-radius: 8px;
      background: var(--bg-subtle);
      min-height: 130px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 0.75rem;
      text-align: center;
      color: var(--text-muted);
      margin-block-end: 1.15rem;
      overflow: hidden;
    }

    .preview-box img {
      max-width: 100%;
      max-height: 180px;
      border-radius: 6px;
      object-fit: contain;
    }

    .btn-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      align-items: center;
    }

    button,
    a.btn-link {
      font: inherit;
      font-size: 0.92rem;
      font-weight: 600;
      min-height: 44px;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      border: 1px solid transparent;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.35rem;
      background: var(--brand-color);
      color: #ffffff;
      text-decoration: none;
      touch-action: manipulation;
      transition: background-color 0.15s ease, opacity 0.15s ease;
    }

    @media (prefers-color-scheme: dark) {
      button,
      a.btn-link {
        color: #0b0f19;
      }
    }

    button:hover:not(:disabled),
    a.btn-link:hover {
      background: var(--brand-hover);
    }

    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    button.secondary,
    a.btn-link.secondary {
      background: var(--bg-subtle);
      color: var(--text-main);
      border-color: var(--border-color);
    }

    button.secondary:hover:not(:disabled),
    a.btn-link.secondary:hover {
      background: var(--border-color);
    }

    button.small,
    a.btn-link.small {
      min-height: 36px;
      padding: 0.3rem 0.7rem;
      font-size: 0.82rem;
    }

    .status-banner {
      padding: 0.7rem 0.95rem;
      border-radius: 8px;
      font-size: 0.88rem;
      font-weight: 500;
      margin-block-end: 1rem;
      display: none;
    }

    .status-banner.visible {
      display: block;
    }

    .status-banner.ok {
      background: var(--success-bg);
      color: var(--success-text);
    }

    .status-banner.err {
      background: var(--error-bg);
      color: var(--error-text);
    }

    /* Galleries */
    .gallery-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
      gap: 0.9rem;
    }

    .media-card {
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .media-thumb {
      width: 100%;
      height: 145px;
      background: #0f172a;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      position: relative;
    }

    .media-thumb img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      cursor: pointer;
    }

    .media-body {
      padding: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      flex: 1;
      min-inline-size: 0;
    }

    .filename {
      display: flex;
      white-space: nowrap;
      font-weight: 600;
      font-size: 0.88rem;
      min-inline-size: 0;
    }

    .filename > span {
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .badge {
      display: inline-block;
      padding: 0.15rem 0.5rem;
      border-radius: 999px;
      font-size: 0.73rem;
      font-weight: 600;
      background: var(--badge-bg);
      color: var(--badge-text);
      width: fit-content;
    }

    .badge.gold {
      background: var(--gold-bg);
      color: var(--gold-text);
    }

    .meta-line {
      font-size: 0.78rem;
      color: var(--text-muted);
      word-break: break-all;
    }

    .upload-text {
      margin: 0;
      font-size: 0.88rem;
      background: var(--bg-card);
      padding: 0.5rem 0.6rem;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      white-space: pre-wrap;
      word-break: break-word;
    }

    .empty-state {
      padding: 1.75rem;
      text-align: center;
      color: var(--text-muted);
      background: var(--bg-subtle);
      border-radius: 8px;
    }

    /* Database Table Explorer */
    .db-table-wrap {
      max-height: 320px;
      overflow: auto;
      border: 1px solid var(--border-color);
      border-radius: 8px;
    }

    table.db-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.83rem;
      text-align: left;
    }

    table.db-table th,
    table.db-table td {
      padding: 0.55rem 0.75rem;
      border-block-end: 1px solid var(--border-color);
      vertical-align: middle;
    }

    table.db-table th {
      position: sticky;
      top: 0;
      background: var(--bg-subtle);
      font-weight: 600;
      z-index: 1;
    }

    .cli-box {
      margin-block-start: 0.85rem;
      padding: 0.75rem 1rem;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 8px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.8rem;
      overflow-x: auto;
    }

    .log-list {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.8rem;
      background: #0f172a;
      color: #e2e8f0;
      padding: 0.75rem;
      border-radius: 8px;
      max-height: 160px;
      overflow-y: auto;
      margin: 0;
      list-style: none;
    }

    .log-list li {
      padding: 0.2rem 0;
      border-block-end: 1px solid rgba(255, 255, 255, 0.08);
    }

    dialog {
      border: 1px solid var(--border-color);
      border-radius: var(--radius);
      background: var(--bg-card);
      color: var(--text-main);
      max-width: min(92vw, 960px);
      max-height: 90vh;
      padding: 1.25rem;
      box-shadow: var(--shadow);
    }

    dialog:modal {
      overscroll-behavior: contain;
    }

    dialog::backdrop {
      background: rgba(15, 23, 42, 0.75);
    }

    .dialog-img-wrap {
      text-align: center;
      margin: 1rem 0;
    }

    .dialog-img-wrap img {
      max-width: 100%;
      max-height: 68vh;
      border-radius: 8px;
      object-fit: contain;
    }
  </style>
</head>
<body>
  <header class="top-header">
    <div class="header-inner">
      <div class="header-title">
        <h1>ATTRial AlmaLinux Image &amp; Text Server</h1>
        <p>Open Background Viewer &amp; SQLite Database Browser (<code>/srv/imgserver/data/metadata.db</code>)</p>
      </div>
      <div class="status-pills">
        <span class="pill ok" id="health-pill">Connecting to Alma Server…</span>
        <button type="button" class="small secondary" id="btn-sync-db">↻ Sync Database &amp; Files</button>
        <a class="pill" href="/api/database" target="_blank" rel="noopener">Raw DB JSON (/api/database) ↗</a>
        <a class="pill" href="/docs" target="_blank" rel="noopener">Swagger API (/docs) ↗</a>
      </div>
    </div>
  </header>

  <main class="container">
    <!-- Dedicated Open Space Frame for Viewing the Active Background & Scrolling All Database Options -->
    <section class="panel" aria-labelledby="open-frame-title">
      <div class="panel-header">
        <div>
          <h2 id="open-frame-title">Open Background Viewer Frame &amp; Scrollable Database Options</h2>
          <span class="hint">Images are displayed inside this dedicated open frame (never hidden behind header text). Scroll the strip below to pick any image in your database.</span>
        </div>
        <div class="btn-row">
          <button type="button" class="secondary small" id="btn-toggle-fit">📐 Mode: Fit Whole Image</button>
          <button type="button" class="secondary small" id="btn-test-random">🎲 Random Server Background</button>
          <button type="button" class="secondary small" id="btn-open-fullscreen" disabled>🔍 Fullscreen</button>
          <a class="btn-link secondary small" id="link-raw-file" href="#" target="_blank" rel="noopener" aria-disabled="true" style="pointer-events: none; opacity: 0.5;">⬇ Open Raw File</a>
        </div>
      </div>

      <!-- The Open Space Frame -->
      <div class="open-frame-stage" id="open-frame-stage">
        <div class="frame-placeholder" id="frame-placeholder">
          Select any image from the scrollable database options strip below (or upload a new image) to view it in this open frame.
        </div>
        <img id="frame-active-img" src="" alt="Selected database image in open frame" width="960" height="540" style="display: none;">
      </div>

      <!-- Metadata bar for the image currently shown in the open frame -->
      <div class="frame-info-bar" id="frame-info-bar">
        <div id="frame-meta-text">
          <strong>Currently Viewing:</strong> None selected yet
        </div>
        <div class="btn-row" id="frame-extra-actions"></div>
      </div>

      <!-- Scrollable Carousel of All Options in Database -->
      <section class="options-carousel" aria-roledescription="carousel" aria-label="Database image options">
        <div class="carousel-toolbar">
          <div class="filter-tabs" role="group" aria-label="Filter database image options">
            <button type="button" class="filter-tab" data-filter="all" aria-pressed="true" id="tab-all">All Database Images (0)</button>
            <button type="button" class="filter-tab" data-filter="backgrounds" aria-pressed="false" id="tab-bg">Server Backgrounds Only (0)</button>
            <button type="button" class="filter-tab" data-filter="uploads" aria-pressed="false" id="tab-up">Upload-Only Images (0)</button>
          </div>
          <div class="btn-row">
            <button type="button" class="secondary small" id="btn-carousel-prev" aria-label="Previous image option">◀ Prev</button>
            <button type="button" class="secondary small" id="btn-carousel-next" aria-label="Next image option">Next ▶</button>
          </div>
        </div>

        <div class="carousel-track" id="options-track" tabindex="0" role="group" aria-label="Scrollable image options">
          <div class="empty-state" style="width: 100%;">Loading images from database…</div>
        </div>

        <p class="visually-hidden" id="carousel-status" role="status" aria-live="polite"></p>
      </section>
    </section>

    <div class="workspace-grid">
      <!-- Left Column: Upload Form + Admin Key -->
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <section class="panel" aria-labelledby="upload-form-title">
          <div class="panel-header">
            <h2 id="upload-form-title">Upload Image or Text</h2>
            <span class="badge">POST /api/uploads</span>
          </div>

          <div id="upload-status" class="status-banner" role="status" aria-live="polite"></div>

          <form id="upload-form" action="/api/uploads" method="POST" enctype="multipart/form-data" aria-labelledby="upload-form-title" novalidate>
            <div class="field">
              <label for="upload-text">Text Message / Note (optional)</label>
              <textarea id="upload-text" name="text" maxlength="5000" aria-describedby="text-help" placeholder="Write a message or note to store on the AlmaLinux server…"></textarea>
              <span id="text-help" class="hint">0 / 5,000 characters. You can upload text alone, an image alone, or both together.</span>
            </div>

            <div class="field">
              <label for="upload-image">Image File (optional — JPEG, PNG, WebP)</label>
              <input type="file" id="upload-image" name="image" accept="image/jpeg,image/png,image/webp" aria-describedby="image-help">
              <span id="image-help" class="hint">Max 10 MB. Stored in <code>/srv/imgserver/data/uploads/</code> and indexed in <code>metadata.db</code>.</span>
            </div>

            <div class="preview-box" id="upload-preview-box">
              <span>No image selected yet</span>
            </div>

            <div class="checkbox-row">
              <input type="checkbox" id="add-as-bg" name="add_as_background" value="true" disabled>
              <label for="add-as-bg"><span>Also add to Alma Server Backgrounds rotation</span></label>
            </div>

            <div class="btn-row">
              <button type="submit" id="btn-submit-upload">⬆ Upload to Alma Server</button>
              <button type="button" class="secondary" id="btn-clear-form">Clear</button>
            </div>
          </form>
        </section>

        <section class="panel" aria-labelledby="admin-form-title">
          <div class="panel-header">
            <h2 id="admin-form-title">Admin Key (Optional)</h2>
            <span class="badge">X-API-Key</span>
          </div>
          <div class="field" style="margin-block-end: 0;">
            <label for="admin-api-key">Admin API Key (for deleting items)</label>
            <input type="password" id="admin-api-key" name="admin_api_key" autocomplete="current-password" autocorrect="off" autocapitalize="none" spellcheck="false" aria-describedby="admin-key-help" placeholder="Paste key from /etc/imgserver/imgserver.env">
            <span id="admin-key-help" class="hint">Needed only if you click Delete on a background or upload.</span>
          </div>
        </section>
      </div>

      <!-- Right Column: Scrollable Galleries + SQLite Database Explorer -->
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <!-- 1. Server Backgrounds Gallery -->
        <section class="panel" aria-labelledby="bg-gallery-title">
          <div class="panel-header">
            <div>
              <h2 id="bg-gallery-title">1. Alma Server Backgrounds Gallery</h2>
              <span class="hint">Scrollable list of <code>backgrounds</code> table in <code>/srv/imgserver/data/backgrounds/</code> (<code>GET /api/backgrounds</code>)</span>
            </div>
            <div class="btn-row">
              <button type="button" class="secondary small" id="btn-refresh-bg">↻ Refresh</button>
            </div>
          </div>
          <div class="scrollable-gallery">
            <div id="backgrounds-grid" class="gallery-grid" aria-live="polite">
              <div class="empty-state">Loading server backgrounds…</div>
            </div>
          </div>
        </section>

        <!-- 2. User Uploads Gallery -->
        <section class="panel" aria-labelledby="uploads-gallery-title">
          <div class="panel-header">
            <div>
              <h2 id="uploads-gallery-title">2. User Uploads Feed (All Uploaded Images &amp; Text Notes)</h2>
              <span class="hint">Scrollable list of <code>uploads</code> table in <code>/srv/imgserver/data/uploads/</code> (<code>GET /api/uploads</code>)</span>
            </div>
            <div class="btn-row">
              <button type="button" class="secondary small" id="btn-refresh-uploads">↻ Refresh</button>
            </div>
          </div>
          <div class="scrollable-gallery">
            <div id="uploads-grid" class="gallery-grid" aria-live="polite">
              <div class="empty-state">Loading user uploads…</div>
            </div>
          </div>
        </section>

        <!-- 3. Direct Database & File Explorer -->
        <section class="panel" aria-labelledby="db-explorer-title">
          <div class="panel-header">
            <div>
              <h2 id="db-explorer-title">3. SQLite Database &amp; Disk Files Explorer (<code>metadata.db</code>)</h2>
              <span class="hint" id="db-paths-hint">Inspect every file stored inside your database and open or preview it directly</span>
            </div>
          </div>

          <div class="db-table-wrap">
            <table class="db-table">
              <thead>
                <tr>
                  <th>Table</th>
                  <th>Original Name / Note</th>
                  <th>Disk File in <code>/srv/imgserver/data/</code></th>
                  <th>Type</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody id="db-table-body">
                <tr><td colspan="5">Loading database records…</td></tr>
              </tbody>
            </table>
          </div>

          <div class="cli-box">
            <strong>How to inspect files on the AlmaLinux VM via SSH:</strong><br>
            <code>ls -lh /srv/imgserver/data/backgrounds /srv/imgserver/data/uploads</code><br>
            <code>sqlite3 -header -column /srv/imgserver/data/metadata.db "SELECT id, name, filename, source, created_at FROM backgrounds;"</code><br>
            <code>sqlite3 -header -column /srv/imgserver/data/metadata.db "SELECT id, original_name, filename, text, created_at FROM uploads;"</code>
          </div>
        </section>

        <!-- 4. Live Network Log -->
        <section class="panel" aria-labelledby="inspector-title">
          <div class="panel-header">
            <div>
              <h2 id="inspector-title">4. Live HTTP Request Log (Browser ↔ AlmaLinux)</h2>
              <span class="hint">Every API call to Nginx (:80) → FastAPI (:8000)</span>
            </div>
          </div>
          <ul class="log-list" id="network-log" aria-label="Live HTTP request log">
            <li>[Ready] Waiting for requests…</li>
          </ul>
        </section>
      </div>
    </div>
  </main>

  <!-- Native Modal Lightbox Dialog -->
  <dialog id="image-lightbox" closedby="any" aria-labelledby="lightbox-title">
    <div class="panel-header" style="margin-block-end: 0.5rem;">
      <h2 id="lightbox-title" style="font-size: 1.1rem;">Image Preview</h2>
      <form method="dialog">
        <button value="close" class="secondary small" autofocus>Close (Esc)</button>
      </form>
    </div>
    <div class="dialog-img-wrap">
      <img id="lightbox-img" src="" alt="Full size server image preview" width="960" height="540">
    </div>
    <p id="lightbox-meta" class="hint" style="margin: 0; text-align: center;"></p>
  </dialog>

  <script type="module">
    // Fallback for <dialog closedby="any"> in browsers without native closedBy support
    if (!('closedBy' in HTMLDialogElement.prototype)) {
      const outside = (e, dialog) => {
        const r = dialog.getBoundingClientRect();
        return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      };
      for (const dialog of document.querySelectorAll('dialog[closedby="any"]')) {
        let pressedOutside = false;
        dialog.addEventListener('pointerdown', (e) => { pressedOutside = outside(e, dialog); });
        dialog.addEventListener('pointerup', (e) => { if (pressedOutside && outside(e, dialog)) dialog.close(); });
      }
    }

    const logEl = document.getElementById('network-log');
    function logNetwork(method, url, status, ms, note = '') {
      const li = document.createElement('li');
      const time = new Date().toLocaleTimeString();
      li.textContent = `[${time}] ${method} ${url} → HTTP ${status} (${ms} ms) ${note}`;
      if (logEl.firstElementChild && logEl.firstElementChild.textContent.startsWith('[Ready]')) {
        logEl.innerHTML = '';
      }
      logEl.prepend(li);
    }

    async function apiFetch(url, options = {}) {
      const method = options.method || 'GET';
      const t0 = performance.now();
      const res = await fetch(url, options);
      const ms = Math.round(performance.now() - t0);
      const bgId = res.headers.get('X-Background-Id');
      logNetwork(method, url, res.status, ms, bgId ? `[X-Background-Id: ${bgId.slice(0, 8)}…]` : '');
      return res;
    }

    function splitFilename(name) {
      const safe = name || 'unnamed';
      const dot = safe.lastIndexOf('.');
      if (dot <= 0) return { base: safe, ext: '' };
      return { base: safe.slice(0, dot), ext: safe.slice(dot) };
    }

    function formatTime(iso) {
      try {
        return new Date(iso).toLocaleString();
      } catch {
        return iso;
      }
    }

    // Lightbox modal
    const lightbox = document.getElementById('image-lightbox');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxTitle = document.getElementById('lightbox-title');
    const lightboxMeta = document.getElementById('lightbox-meta');

    function openLightbox(url, title, metaText) {
      lightboxImg.src = url;
      lightboxTitle.textContent = title || 'Image Preview';
      lightboxMeta.textContent = metaText || '';
      lightbox.showModal();
    }

    // State for Open Background Frame & Scrollable Options Carousel
    let allOptions = [];
    let currentFilter = 'all';
    let selectedOptionId = null;
    let coverMode = false;

    const frameStage = document.getElementById('open-frame-stage');
    const frameImg = document.getElementById('frame-active-img');
    const framePlaceholder = document.getElementById('frame-placeholder');
    const frameMetaText = document.getElementById('frame-meta-text');
    const frameExtraActions = document.getElementById('frame-extra-actions');
    const btnToggleFit = document.getElementById('btn-toggle-fit');
    const btnFullscreen = document.getElementById('btn-open-fullscreen');
    const linkRawFile = document.getElementById('link-raw-file');
    const optionsTrack = document.getElementById('options-track');
    const carouselStatus = document.getElementById('carousel-status');

    btnToggleFit.addEventListener('click', () => {
      coverMode = !coverMode;
      frameStage.classList.toggle('cover-mode', coverMode);
      btnToggleFit.textContent = coverMode ? '📐 Mode: Fill Frame (Cover)' : '📐 Mode: Fit Whole Image';
    });

    function getFilteredOptions() {
      if (currentFilter === 'backgrounds') {
        return allOptions.filter((o) => o.table === 'backgrounds');
      }
      if (currentFilter === 'uploads') {
        return allOptions.filter((o) => o.table === 'uploads');
      }
      return allOptions;
    }

    function showInOpenFrame(opt, announce = false) {
      if (!opt) {
        frameImg.style.display = 'none';
        framePlaceholder.style.display = 'block';
        frameMetaText.innerHTML = '<strong>Currently Viewing:</strong> No image available in this filter.';
        frameExtraActions.innerHTML = '';
        btnFullscreen.disabled = true;
        linkRawFile.style.pointerEvents = 'none';
        linkRawFile.style.opacity = '0.5';
        return;
      }

      selectedOptionId = opt.option_id;
      framePlaceholder.style.display = 'none';
      frameImg.style.display = 'block';
      frameImg.src = opt.url;
      frameImg.alt = opt.name || 'Selected database image';

      const sourceLabel = opt.table === 'backgrounds'
        ? `backgrounds table (${opt.source === 'admin' ? 'Server/Admin' : 'Promoted Upload'})`
        : 'uploads table (Upload-Only Image)';

      frameMetaText.innerHTML = '';
      const strong = document.createElement('strong');
      strong.textContent = `Viewing in Frame: ${opt.name || opt.id} `;
      const details = document.createElement('span');
      details.className = 'hint';
      details.textContent = `· Table: ${sourceLabel} · Disk file: /srv/imgserver/data/${opt.storage_path || opt.filename || ''} · URL: ${opt.url}`;
      frameMetaText.append(strong, details);

      frameExtraActions.innerHTML = '';
      if (!opt.is_background && opt.upload_id) {
        const btnPromote = document.createElement('button');
        btnPromote.type = 'button';
        btnPromote.className = 'small';
        btnPromote.textContent = '★ Promote to Server Background';
        btnPromote.addEventListener('click', () => promoteUpload(opt.upload_id, btnPromote));
        frameExtraActions.appendChild(btnPromote);
      }

      btnFullscreen.disabled = false;
      btnFullscreen.onclick = () => openLightbox(
        opt.url,
        opt.name || 'Database Image',
        `Disk path: /srv/imgserver/data/${opt.storage_path || ''} · URL: ${opt.url}`
      );
      frameImg.onclick = btnFullscreen.onclick;

      linkRawFile.href = opt.url;
      linkRawFile.style.pointerEvents = 'auto';
      linkRawFile.style.opacity = '1';

      // Highlight active slide in scrollable strip
      const slides = optionsTrack.querySelectorAll('.option-slide');
      slides.forEach((slide, idx) => {
        const isCurrent = slide.dataset.optionId === selectedOptionId;
        slide.classList.toggle('active', isCurrent);
        slide.setAttribute('aria-current', isCurrent ? 'true' : 'false');
        if (isCurrent && announce) {
          carouselStatus.textContent = `Viewing option ${idx + 1} of ${slides.length}: ${opt.name || opt.id}`;
        }
      });
    }

    function renderOptionsCarousel() {
      const filtered = getFilteredOptions();
      const bgCount = allOptions.filter((o) => o.table === 'backgrounds').length;
      const upCount = allOptions.filter((o) => o.table === 'uploads').length;

      document.getElementById('tab-all').textContent = `All Database Images (${allOptions.length})`;
      document.getElementById('tab-bg').textContent = `Server Backgrounds Only (${bgCount})`;
      document.getElementById('tab-up').textContent = `Upload-Only Images (${upCount})`;

      if (!filtered.length) {
        optionsTrack.innerHTML = '<div class="empty-state" style="width: 100%;">No images in this category yet. Upload an image on the left!</div>';
        showInOpenFrame(null);
        return;
      }

      optionsTrack.innerHTML = '';
      filtered.forEach((opt, index) => {
        const slide = document.createElement('div');
        slide.className = 'option-slide';
        slide.tabIndex = 0;
        slide.setAttribute('role', 'group');
        slide.setAttribute('aria-roledescription', 'slide');
        slide.setAttribute('aria-label', `${index + 1} of ${filtered.length}: ${opt.name || opt.id}`);
        slide.dataset.optionId = opt.option_id;

        const thumb = document.createElement('div');
        thumb.className = 'option-slide-thumb';
        const img = document.createElement('img');
        img.src = opt.url;
        img.alt = opt.name || 'Database image thumbnail';
        img.width = 185;
        img.height = 105;
        img.loading = 'lazy';
        thumb.appendChild(img);

        const meta = document.createElement('div');
        meta.className = 'option-slide-meta';

        const parts = splitFilename(opt.name || opt.id);
        const titleDiv = document.createElement('div');
        titleDiv.className = 'filename';
        const baseSpan = document.createElement('span');
        baseSpan.textContent = parts.base;
        titleDiv.appendChild(baseSpan);
        titleDiv.append(parts.ext);

        const badge = document.createElement('span');
        badge.className = opt.is_background ? 'badge gold' : 'badge';
        badge.textContent = opt.is_background ? '★ Background' : 'Upload Only';

        meta.append(titleDiv, badge);
        slide.append(thumb, meta);

        slide.addEventListener('click', () => showInOpenFrame(opt, true));
        slide.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            showInOpenFrame(opt, true);
          }
        });

        optionsTrack.appendChild(slide);
      });

      const currentStillExists = filtered.find((o) => o.option_id === selectedOptionId);
      showInOpenFrame(currentStillExists || filtered[0], false);
    }

    // Filter tabs
    for (const tabBtn of document.querySelectorAll('.filter-tab')) {
      tabBtn.addEventListener('click', () => {
        currentFilter = tabBtn.dataset.filter;
        for (const b of document.querySelectorAll('.filter-tab')) {
          b.setAttribute('aria-pressed', b === tabBtn ? 'true' : 'false');
        }
        renderOptionsCarousel();
      });
    }

    // Prev / Next buttons for scrolling through all options and updating the Open Frame
    function stepOption(delta) {
      const filtered = getFilteredOptions();
      if (!filtered.length) return;
      const idx = filtered.findIndex((o) => o.option_id === selectedOptionId);
      const nextIdx = idx < 0 ? 0 : (idx + delta + filtered.length) % filtered.length;
      const targetOpt = filtered[nextIdx];
      showInOpenFrame(targetOpt, true);

      const slideEl = optionsTrack.querySelector(`[data-option-id="${CSS.escape(targetOpt.option_id)}"]`);
      if (slideEl) {
        const offset = slideEl.offsetLeft - optionsTrack.offsetLeft - (optionsTrack.clientWidth - slideEl.clientWidth) / 2;
        optionsTrack.scrollTo({ left: Math.max(0, offset), behavior: 'smooth' });
      }
    }

    document.getElementById('btn-carousel-prev').addEventListener('click', () => stepOption(-1));
    document.getElementById('btn-carousel-next').addEventListener('click', () => stepOption(1));

    // Settled scroll status update using scrollend with debounced fallback
    function onCarouselScrollSettled() {
      const slides = Array.from(optionsTrack.querySelectorAll('.option-slide'));
      if (!slides.length) return;
      const trackCenter = optionsTrack.scrollLeft + optionsTrack.clientWidth / 2;
      let closestIdx = 0;
      let minDiff = Infinity;
      slides.forEach((s, i) => {
        const center = s.offsetLeft - optionsTrack.offsetLeft + s.clientWidth / 2;
        const diff = Math.abs(center - trackCenter);
        if (diff < minDiff) {
          minDiff = diff;
          closestIdx = i;
        }
      });
      carouselStatus.textContent = `Scrolled to option ${closestIdx + 1} of ${slides.length}`;
    }

    if ('onscrollend' in window) {
      optionsTrack.addEventListener('scrollend', onCarouselScrollSettled);
    } else {
      let scrollTimer = null;
      optionsTrack.addEventListener('scroll', () => {
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(onCarouselScrollSettled, 150);
      });
    }

    async function loadHealth() {
      const pill = document.getElementById('health-pill');
      try {
        const res = await apiFetch('/api/health');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const upTotal = data.uploads !== undefined ? ` · ${data.uploads} uploads` : '';
        pill.textContent = `● Connected (v${data.version} · ${data.backgrounds} backgrounds${upTotal})`;
        pill.classList.add('ok');
      } catch (err) {
        pill.textContent = `⚠ Server Unreachable (${err.message})`;
        pill.classList.remove('ok');
      }
    }

    async function loadRandomIntoOpenFrame() {
      try {
        const res = await apiFetch('/api/backgrounds/random');
        if (!res.ok) return;
        const bgId = res.headers.get('X-Background-Id') || '';
        const match = allOptions.find((o) => o.table === 'backgrounds' && o.id === bgId);
        if (match) {
          showInOpenFrame(match, true);
          const slideEl = optionsTrack.querySelector(`[data-option-id="${CSS.escape(match.option_id)}"]`);
          if (slideEl) {
            const offset = slideEl.offsetLeft - optionsTrack.offsetLeft - (optionsTrack.clientWidth - slideEl.clientWidth) / 2;
            optionsTrack.scrollTo({ left: Math.max(0, offset), behavior: 'smooth' });
          }
        } else {
          const blob = await res.blob();
          const objectUrl = URL.createObjectURL(blob);
          framePlaceholder.style.display = 'none';
          frameImg.style.display = 'block';
          frameImg.src = objectUrl;
          frameMetaText.innerHTML = `<strong>Viewing Random Background ID:</strong> ${bgId} (from <code>GET /api/backgrounds/random</code>)`;
        }
      } catch {
        // Ignore if no backgrounds exist
      }
    }

    async function loadDatabaseExplorer() {
      const tbody = document.getElementById('db-table-body');
      const hintEl = document.getElementById('db-paths-hint');
      try {
        const res = await apiFetch('/api/database');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const dbData = await res.json();

        allOptions = dbData.all_images || [];
        renderOptionsCarousel();

        hintEl.innerHTML = `SQLite DB: <code>${dbData.db_file}</code> · Total Images: <strong>${dbData.counts.total_images}</strong> (${dbData.counts.backgrounds} in <code>backgrounds</code>, ${dbData.counts.uploads} in <code>uploads</code>)`;

        tbody.innerHTML = '';
        const rows = [];
        for (const b of dbData.backgrounds || []) {
          rows.push({
            table: 'backgrounds',
            label: b.name || b.id.slice(0, 10),
            diskPath: b.storage_path || `backgrounds/${b.filename || ''}`,
            ctype: b.content_type || 'image/*',
            url: b.url,
            optionId: `bg:${b.id}`,
          });
        }
        for (const u of dbData.uploads || []) {
          rows.push({
            table: 'uploads',
            label: u.original_name || (u.text ? u.text.slice(0, 40) : u.id.slice(0, 10)),
            diskPath: u.storage_path || '(text-only row in metadata.db)',
            ctype: u.content_type || 'text/plain',
            url: u.image_url,
            optionId: u.has_image ? (u.is_background ? `bg:${u.background_id}` : `up:${u.id}`) : null,
          });
        }

        if (!rows.length) {
          tbody.innerHTML = '<tr><td colspan="5">Database is empty. Upload an image or text note!</td></tr>';
          return;
        }

        for (const r of rows) {
          const tr = document.createElement('tr');

          const tdTable = document.createElement('td');
          const badge = document.createElement('span');
          badge.className = r.table === 'backgrounds' ? 'badge gold' : 'badge';
          badge.textContent = r.table;
          tdTable.appendChild(badge);

          const tdLabel = document.createElement('td');
          tdLabel.textContent = r.label;

          const tdPath = document.createElement('td');
          const code = document.createElement('code');
          code.textContent = r.diskPath;
          tdPath.appendChild(code);

          const tdType = document.createElement('td');
          tdType.textContent = r.ctype;

          const tdAct = document.createElement('td');
          const actRow = document.createElement('div');
          actRow.className = 'btn-row';
          if (r.url) {
            const btnView = document.createElement('button');
            btnView.type = 'button';
            btnView.className = 'secondary small';
            btnView.textContent = 'View in Frame';
            btnView.addEventListener('click', () => {
              const found = allOptions.find((o) => o.option_id === r.optionId) || {
                option_id: r.optionId || r.url,
                id: r.label,
                table: r.table,
                name: r.label,
                storage_path: r.diskPath,
                is_background: r.table === 'backgrounds',
                url: r.url,
              };
              showInOpenFrame(found, true);
              document.getElementById('open-frame-stage').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            });
            actRow.appendChild(btnView);

            const rawLink = document.createElement('a');
            rawLink.className = 'btn-link secondary small';
            rawLink.href = r.url;
            rawLink.target = '_blank';
            rawLink.rel = 'noopener';
            rawLink.textContent = 'Raw File ↗';
            actRow.appendChild(rawLink);
          } else {
            actRow.textContent = 'Text Record';
          }
          tdAct.appendChild(actRow);

          tr.append(tdTable, tdLabel, tdPath, tdType, tdAct);
          tbody.appendChild(tr);
        }
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5">Failed to load database explorer: ${err.message}</td></tr>`;
      }
    }

    async function loadBackgrounds() {
      const grid = document.getElementById('backgrounds-grid');
      try {
        const res = await apiFetch('/api/backgrounds');
        const items = await res.json();
        if (!items.length) {
          grid.innerHTML = '<div class="empty-state">No background images on the server yet. Upload an image and tick "Also add to Alma Server Backgrounds"!</div>';
          return;
        }
        grid.innerHTML = '';
        for (const item of items) {
          const card = document.createElement('article');
          card.className = 'media-card';

          const thumb = document.createElement('div');
          thumb.className = 'media-thumb';
          const img = document.createElement('img');
          img.src = item.url;
          img.alt = item.name || 'Server background image';
          img.width = 220;
          img.height = 145;
          img.loading = 'lazy';
          img.addEventListener('click', () => {
            const opt = allOptions.find((o) => o.option_id === `bg:${item.id}`) || {
              option_id: `bg:${item.id}`,
              id: item.id,
              table: 'backgrounds',
              name: item.name || item.filename,
              storage_path: item.storage_path,
              source: item.source,
              is_background: true,
              url: item.url,
            };
            showInOpenFrame(opt, true);
            document.getElementById('open-frame-stage').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          });
          thumb.appendChild(img);

          const body = document.createElement('div');
          body.className = 'media-body';

          const parts = splitFilename(item.name || item.id);
          const titleDiv = document.createElement('div');
          titleDiv.className = 'filename';
          const baseSpan = document.createElement('span');
          baseSpan.textContent = parts.base;
          titleDiv.appendChild(baseSpan);
          titleDiv.append(parts.ext);

          const badge = document.createElement('span');
          badge.className = item.source === 'admin' ? 'badge' : 'badge gold';
          badge.textContent = item.source === 'admin' ? 'Server / Admin Background' : '★ Promoted User Upload';

          const meta = document.createElement('div');
          meta.className = 'meta-line';
          meta.textContent = `${item.storage_path || ''} · ${formatTime(item.created_at)}`;

          const actions = document.createElement('div');
          actions.className = 'btn-row';
          actions.style.marginTop = 'auto';

          const btnShowInFrame = document.createElement('button');
          btnShowInFrame.type = 'button';
          btnShowInFrame.className = 'secondary small';
          btnShowInFrame.textContent = '🖼 View in Frame';
          btnShowInFrame.addEventListener('click', () => {
            const opt = allOptions.find((o) => o.option_id === `bg:${item.id}`) || {
              option_id: `bg:${item.id}`,
              id: item.id,
              table: 'backgrounds',
              name: item.name || item.filename,
              storage_path: item.storage_path,
              source: item.source,
              is_background: true,
              url: item.url,
            };
            showInOpenFrame(opt, true);
            document.getElementById('open-frame-stage').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          });
          actions.appendChild(btnShowInFrame);

          const btnDelete = document.createElement('button');
          btnDelete.type = 'button';
          btnDelete.className = 'secondary small';
          btnDelete.textContent = 'Delete';
          btnDelete.addEventListener('click', () => deleteBackground(item.id));
          actions.appendChild(btnDelete);

          body.append(titleDiv, badge, meta, actions);
          card.append(thumb, body);
          grid.appendChild(card);
        }
      } catch (err) {
        grid.innerHTML = `<div class="empty-state">Failed to load backgrounds: ${err.message}</div>`;
      }
    }

    async function loadUploads() {
      const grid = document.getElementById('uploads-grid');
      try {
        const res = await apiFetch('/api/uploads?limit=100');
        const items = await res.json();
        if (!items.length) {
          grid.innerHTML = '<div class="empty-state">No uploads yet. Use the form on the left to upload your first image or text note!</div>';
          return;
        }
        grid.innerHTML = '';
        for (const item of items) {
          const card = document.createElement('article');
          card.className = 'media-card';

          if (item.has_image && item.image_url) {
            const thumb = document.createElement('div');
            thumb.className = 'media-thumb';
            const img = document.createElement('img');
            img.src = item.image_url;
            img.alt = item.original_name || 'Uploaded image';
            img.width = 220;
            img.height = 145;
            img.loading = 'lazy';
            img.addEventListener('click', () => {
              showInOpenFrame({
                option_id: item.is_background ? `bg:${item.background_id}` : `up:${item.id}`,
                id: item.id,
                table: item.is_background ? 'backgrounds' : 'uploads',
                name: item.original_name || item.filename,
                storage_path: item.storage_path,
                is_background: item.is_background,
                upload_id: item.id,
                url: item.image_url,
              }, true);
              document.getElementById('open-frame-stage').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            });
            thumb.appendChild(img);
            card.appendChild(thumb);
          }

          const body = document.createElement('div');
          body.className = 'media-body';

          if (item.original_name) {
            const parts = splitFilename(item.original_name);
            const titleDiv = document.createElement('div');
            titleDiv.className = 'filename';
            const baseSpan = document.createElement('span');
            baseSpan.textContent = parts.base;
            titleDiv.appendChild(baseSpan);
            titleDiv.append(parts.ext);
            body.appendChild(titleDiv);
          }

          const badge = document.createElement('span');
          badge.className = item.is_background ? 'badge gold' : 'badge';
          badge.textContent = item.is_background ? '★ In Backgrounds + Uploads' : (item.has_image ? 'Upload-Only Image' : 'Text-Only Note');
          body.appendChild(badge);

          if (item.text) {
            const p = document.createElement('p');
            p.className = 'upload-text';
            p.textContent = item.text;
            body.appendChild(p);
          }

          const meta = document.createElement('div');
          meta.className = 'meta-line';
          meta.textContent = `${item.storage_path || 'metadata.db'} · ${formatTime(item.created_at)}`;
          body.appendChild(meta);

          const actions = document.createElement('div');
          actions.className = 'btn-row';
          actions.style.marginTop = 'auto';

          if (item.has_image && item.image_url) {
            const btnViewFrame = document.createElement('button');
            btnViewFrame.type = 'button';
            btnViewFrame.className = 'secondary small';
            btnViewFrame.textContent = '🖼 View in Frame';
            btnViewFrame.addEventListener('click', () => {
              showInOpenFrame({
                option_id: item.is_background ? `bg:${item.background_id}` : `up:${item.id}`,
                id: item.id,
                table: item.is_background ? 'backgrounds' : 'uploads',
                name: item.original_name || item.filename,
                storage_path: item.storage_path,
                is_background: item.is_background,
                upload_id: item.id,
                url: item.image_url,
              }, true);
              document.getElementById('open-frame-stage').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            });
            actions.appendChild(btnViewFrame);
          }

          if (item.has_image && !item.is_background) {
            const btnPromote = document.createElement('button');
            btnPromote.type = 'button';
            btnPromote.className = 'small';
            btnPromote.textContent = '★ Promote to Background';
            btnPromote.addEventListener('click', () => promoteUpload(item.id, btnPromote));
            actions.appendChild(btnPromote);
          }

          const btnDel = document.createElement('button');
          btnDel.type = 'button';
          btnDel.className = 'secondary small';
          btnDel.textContent = 'Delete';
          btnDel.addEventListener('click', () => deleteUpload(item.id));
          actions.appendChild(btnDel);

          body.appendChild(actions);
          card.appendChild(body);
          grid.appendChild(card);
        }
      } catch (err) {
        grid.innerHTML = `<div class="empty-state">Failed to load uploads: ${err.message}</div>`;
      }
    }

    async function refreshAll() {
      await Promise.all([loadHealth(), loadDatabaseExplorer(), loadBackgrounds(), loadUploads()]);
    }

    async function promoteUpload(uploadId, btn) {
      btn.disabled = true;
      try {
        const res = await apiFetch(`/api/uploads/${uploadId}/promote`, { method: 'POST' });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        showStatus('✔ Image promoted to Alma Server backgrounds!', false);
        await refreshAll();
      } catch (err) {
        showStatus(`⚠ Could not promote: ${err.message}`, true);
        btn.disabled = false;
      }
    }

    async function deleteBackground(bgId) {
      const key = document.getElementById('admin-api-key').value.trim();
      if (!key) {
        showStatus('⚠ Enter the Admin API Key in the left panel before deleting a background.', true);
        document.getElementById('admin-api-key').focus();
        return;
      }
      try {
        const res = await apiFetch(`/api/backgrounds/${bgId}`, {
          method: 'DELETE',
          headers: { 'X-API-Key': key }
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        showStatus('✔ Background deleted from server.', false);
        await refreshAll();
      } catch (err) {
        showStatus(`⚠ Delete failed: ${err.message}`, true);
      }
    }

    async function deleteUpload(uploadId) {
      const key = document.getElementById('admin-api-key').value.trim();
      if (!key) {
        showStatus('⚠ Enter the Admin API Key in the left panel before deleting an upload.', true);
        document.getElementById('admin-api-key').focus();
        return;
      }
      try {
        const res = await apiFetch(`/api/uploads/${uploadId}`, {
          method: 'DELETE',
          headers: { 'X-API-Key': key }
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        showStatus('✔ Upload deleted from server.', false);
        await refreshAll();
      } catch (err) {
        showStatus(`⚠ Delete failed: ${err.message}`, true);
      }
    }

    const statusEl = document.getElementById('upload-status');
    function showStatus(msg, isError) {
      statusEl.textContent = msg;
      statusEl.className = `status-banner visible ${isError ? 'err' : 'ok'}`;
    }

    const textInput = document.getElementById('upload-text');
    const textHelp = document.getElementById('text-help');
    const fileInput = document.getElementById('upload-image');
    const addAsBgCheck = document.getElementById('add-as-bg');
    const previewBox = document.getElementById('upload-preview-box');
    const uploadForm = document.getElementById('upload-form');
    const submitBtn = document.getElementById('btn-submit-upload');

    textInput.addEventListener('input', () => {
      textInput.removeAttribute('aria-invalid');
      const len = textInput.value.length;
      textHelp.textContent = `${len.toLocaleString()} / 5,000 characters. You can upload text alone, an image alone, or both together.`;
    });

    fileInput.addEventListener('change', () => {
      fileInput.removeAttribute('aria-invalid');
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        previewBox.innerHTML = '<span>No image selected yet</span>';
        addAsBgCheck.checked = false;
        addAsBgCheck.disabled = true;
        return;
      }
      addAsBgCheck.disabled = false;
      const url = URL.createObjectURL(file);
      previewBox.innerHTML = '';
      const img = document.createElement('img');
      img.src = url;
      img.alt = 'Selected file preview';
      img.width = 240;
      img.height = 160;
      const cap = document.createElement('span');
      cap.className = 'hint';
      cap.style.marginTop = '0.4rem';
      cap.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      previewBox.append(img, cap);
    });

    function clearForm() {
      uploadForm.reset();
      previewBox.innerHTML = '<span>No image selected yet</span>';
      addAsBgCheck.checked = false;
      addAsBgCheck.disabled = true;
      textInput.removeAttribute('aria-invalid');
      fileInput.removeAttribute('aria-invalid');
      textHelp.textContent = '0 / 5,000 characters. You can upload text alone, an image alone, or both together.';
    }

    document.getElementById('btn-clear-form').addEventListener('click', clearForm);

    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const textVal = textInput.value.trim();
      const file = fileInput.files && fileInput.files[0];

      if (!textVal && !file) {
        textInput.setAttribute('aria-invalid', 'true');
        showStatus('⚠ Please enter a text note, choose an image file, or both before uploading.', true);
        textInput.focus();
        return;
      }

      submitBtn.disabled = true;
      showStatus('Uploading to AlmaLinux server…', false);

      const formData = new FormData();
      if (textVal) formData.append('text', textVal);
      if (file) formData.append('image', file);
      formData.append('add_as_background', addAsBgCheck.checked ? 'true' : 'false');

      try {
        const res = await apiFetch('/api/uploads', {
          method: 'POST',
          body: formData
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `Server returned HTTP ${res.status}`);
        }
        const saved = await res.json();
        clearForm();
        const bgNote = saved.is_background ? ' and added to Alma Server backgrounds!' : ' (stored in uploads table)!';
        showStatus(`✔ Successfully uploaded to Alma Server${bgNote}`, false);
        selectedOptionId = saved.is_background ? `bg:${saved.background_id}` : (saved.has_image ? `up:${saved.id}` : selectedOptionId);
        await refreshAll();
      } catch (err) {
        showStatus(`⚠ Upload failed: ${err.message}`, true);
      } finally {
        submitBtn.disabled = false;
      }
    });

    document.getElementById('btn-refresh-bg').addEventListener('click', refreshAll);
    document.getElementById('btn-refresh-uploads').addEventListener('click', refreshAll);
    document.getElementById('btn-sync-db').addEventListener('click', refreshAll);
    document.getElementById('btn-test-random').addEventListener('click', loadRandomIntoOpenFrame);

    // Initial load
    refreshAll();
  </script>
</body>
</html>
"""
