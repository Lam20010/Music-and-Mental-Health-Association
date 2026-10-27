"""Music-player pieces for the dashboard: album covers, the docked player, the album shelf, the track list and play buttons.

Everything is plain HTML rendered with st.html(..., unsafe_allow_javascript=True), so it lives in the page itself (no iframes).
st.html still sanitises with DOMPurify, so: no inline event handlers (one delegated listener instead), covers are <img> data
URIs, and the engine script escapes "<" in its data.
One audio engine, window.MLI, is created by the dock and survives reruns; every other piece just calls MLI.play(genre).
Anything carrying a data-mli-genre attribute is marked .is-current / .is-playing by the engine, which drives the
equalizer animations and play/pause icons. The loops themselves are WAV files served from static/loops/ (see app.py).
"""
import base64
import html
import json
import re
import textwrap

# (background, bar colour, disc colour) per cover - all from the dashboard's purple range
COVER_THEMES = [("#3b1489", "#f3c4ff", "#d8a7ef"), ("#55139a", "#ffd1f6", "#ff9ad5"), ("#2a0f6e", "#d9b8ff", "#b44fe0"),
                ("#4a1fb0", "#f6c4fb", "#e08cf0"), ("#61208f", "#ecd4ff", "#a98bff"), ("#25095e", "#e8bcf0", "#8f4fe8")]


def slug(genre):
    return re.sub(r"[^a-z0-9]+", "-", genre.lower()).strip("-")


def cover_svg(genre, levels, bpm, theme, label=True):
    """Album cover drawn from the data: the LED bars are that genre's listening-hours distribution (1 to 8 h/day).
    Returned as an <img> with an SVG data URI: st.html sanitises with DOMPurify's HTML profile, which removes inline <svg>."""
    bg, bar, disc = COVER_THEMES[theme % len(COVER_THEMES)]
    n = len(levels)
    w = 84 / n
    bars = "".join(f'<rect x="{8 + i * w:.1f}" y="{92 - (6 + 46 * h):.1f}" width="{w * .72:.1f}" height="{6 + 46 * h:.1f}" rx=".8" '
                   f'fill="{bar}" opacity="{.45 + .55 * h:.2f}"/>' for i, h in enumerate(levels))
    gaps = "".join(f"M6 {y:.1f}H94" for y in [91 - k * 3.4 for k in range(16)])
    out = [f'<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(genre)} cover">',
           f'<rect width="100" height="100" rx="6" fill="{bg}"/>',
           f'<circle cx="80" cy="24" r="15" fill="{disc}"/><circle cx="80" cy="24" r="5.5" fill="{bg}"/><circle cx="80" cy="24" r="1.8" fill="{disc}"/>',
           bars, f'<path d="{gaps}" stroke="{bg}" stroke-width="1.2"/>']
    if label:
        lines = textwrap.wrap(genre, 10, break_long_words=False) or [genre]
        size = min(10.0, 100 / max(len(t) for t in lines))          # a long single word ("Instrumental") shrinks instead of breaking
        out += [f'<text x="8" y="{17 + 11 * k}" font-size="{size:.1f}" font-weight="800" fill="#fff" font-family="Manrope, Segoe UI, sans-serif">'
                f'{html.escape(t)}</text>' for k, t in enumerate(lines)]
        out.append(f'<text x="8" y="{17 + 11 * len(lines) - 2}" font-size="6" font-weight="700" fill="#fff" opacity=".75" '
                   f'font-family="Manrope, Segoe UI, sans-serif">{bpm:.0f} BPM</text>')
    out.append("</svg>")
    b64 = base64.b64encode("".join(out).encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" alt="{html.escape(genre)} album cover">'


def _attr(genre):
    return f'data-mli-genre="{html.escape(genre)}"'


PLAY_PAUSE = '<span class="ms fill i24 ic-play">play_arrow</span><span class="ms fill i24 ic-pause">pause</span>'
EQ_BARS = '<span class="mli-eq"><i></i><i></i><i></i><i></i></span>'


def dock_html(tracks):
    """Fixed player bar + the audio engine. `tracks`: dicts with g (genre), slug, bpm, tag, cover (small svg).
    Its HTML never depends on the filters, so Streamlit keeps it mounted across reruns and playback is not interrupted."""
    # the covers are <img> markup: DOMPurify deletes a <script> whose text looks like it holds tags, so escape "<"
    tracks_json = json.dumps(tracks).replace("<", "\\u003c")
    return f"""
<div id="mli-dock" class="mli-dock">
  <div class="mli-now"><div id="mli-cover" class="mli-cover"></div>
    <div class="mli-meta"><div id="mli-title" class="mli-title"></div><div id="mli-sub" class="mli-sub"></div>
      <div id="mli-msg" class="mli-msg" role="status" aria-live="polite"></div></div>{EQ_BARS}</div>
  <div class="mli-center">
    <div class="mli-ctl">
      <button id="mli-shuffle" class="mli-btn" title="Shuffle" data-mli-act="toggleShuffle"><span class="ms i20">shuffle</span></button>
      <button class="mli-btn" title="Previous" data-mli-act="prev"><span class="ms fill i24">skip_previous</span></button>
      <button id="mli-play" class="mli-play" title="Play / pause" data-mli-act="toggle">{PLAY_PAUSE}</button>
      <button class="mli-btn" title="Next" data-mli-act="next"><span class="ms fill i24">skip_next</span></button>
      <button id="mli-repeat" class="mli-btn" title="Repeat this loop" data-mli-act="toggleRepeat"><span class="ms i20">repeat</span></button>
    </div>
    <div class="mli-prog"><span id="mli-cur">0:00</span>
      <input id="mli-seek" class="mli-range" type="range" min="0" max="1000" value="0" aria-label="Seek">
      <span id="mli-dur">0:00</span></div>
  </div>
  <div class="mli-right">
    <button class="mli-btn" title="Mute" data-mli-act="mute"><span id="mli-volicon" class="ms i20">volume_up</span></button>
    <input id="mli-vol" class="mli-range mli-vol" type="range" min="0" max="100" value="80" aria-label="Volume">
  </div>
</div>
<script>
(function () {{
  const M = window.MLI = window.MLI || {{}};
  M.tracks = {tracks_json};
  if (!M.audio) {{                                   // created once per browser tab, so playback survives Streamlit reruns
    M.audio = new Audio(); M.audio.preload = "auto"; M.i = 0; M.shuffle = false; M.repeat = false; M.volume = .8;
    M.audio.volume = M.volume;
    M.audio.addEventListener("ended", () => M.next());
    M.audio.addEventListener("error", () => M.recover());        // file could not be fetched/decoded: try the backup source
    M.audio.addEventListener("playing", () => M.notice(""));
    ["timeupdate", "play", "pause", "loadedmetadata", "volumechange"].forEach(e => M.audio.addEventListener(e, () => M.paint()));
    setInterval(() => M.sync(), 400);               // keeps cards rendered after a rerun in step with the player
    // one delegated listener for every player control and every playable card (inline handlers are stripped by st.html)
    document.addEventListener("click", e => {{
      const act = e.target.closest("[data-mli-act]");
      if (act) {{ M[act.dataset.mliAct](); return; }}
      const card = e.target.closest("[data-mli-genre]");
      if (card) M.play(card.dataset.mliGenre);
    }});
    document.addEventListener("keydown", e => {{
      const card = e.target.closest && e.target.closest("[data-mli-genre][role=button]");
      if (card && (e.key === "Enter" || e.key === " ")) {{ e.preventDefault(); M.play(card.dataset.mliGenre); }}
    }});
    document.addEventListener("input", e => {{
      if (e.target.id === "mli-seek") {{ M.dragging = true; e.target.style.setProperty("--p", e.target.value / 10 + "%"); }}
      if (e.target.id === "mli-vol") M.setVol(e.target.value);
    }});
    document.addEventListener("change", e => {{ if (e.target.id === "mli-seek") M.seek(e.target.value); }});
  }}
  const fmt = s => isFinite(s) ? Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0") : "0:00";
  M.idx = g => M.tracks.findIndex(t => t.g === g);
  // two sources per loop: the static file (fast, cacheable) and the same WAV registered with Streamlit's media server by a
  // hidden st.audio in app.py (works even if static serving is unavailable). The engine falls back to the second on error.
  M.backup = slug => {{ const a = document.querySelector(".st-key-loop_" + slug + " audio"); return a && a.src ? a.src : null; }};
  M.load = i => {{
    M.i = (i + M.tracks.length) % M.tracks.length; M.fellBack = false;
    M.audio.src = "app/static/loops/" + M.tracks[M.i].slug + ".wav"; M.audio.loop = M.repeat;
  }};
  M.recover = () => {{
    const b = M.backup(M.tracks[M.i].slug);
    if (!M.fellBack && b) {{ M.fellBack = true; M.audio.src = b; M.audio.loop = M.repeat; M.start(); return; }}
    M.notice("Could not load this loop. Try another genre.");
  }};
  M.notice = msg => {{
    const el = document.getElementById("mli-msg"), dock = document.getElementById("mli-dock");
    if (el) {{ el.textContent = msg; el.classList.toggle("show", !!msg); }}
    if (dock) dock.classList.toggle("needs-tap", /press/i.test(msg));
  }};
  M.start = () => M.audio.play().then(() => M.notice("")).catch(err => {{
    // NotAllowedError = the browser blocked sound until the page is clicked; anything else is a loading problem
    if (err && err.name === "NotAllowedError") M.notice("Your browser blocked autoplay: press play to start the music.");
    else if (err && err.name !== "AbortError") M.recover();
    M.paint();
  }});
  M.play = g => {{                                   // click on a card/row: start that genre, or pause/resume it if it is current
    const i = M.idx(g); if (i < 0) return;
    if (i === M.i && M.audio.src) {{ M.audio.paused ? M.start() : M.audio.pause(); }} else {{ M.load(i); M.start(); }}
  }};
  M.toggle = () => {{ if (!M.audio.src) M.load(M.i); M.audio.paused ? M.start() : M.audio.pause(); }};
  M.next = () => {{
    let i = M.i + 1;
    if (M.shuffle && M.tracks.length > 1) do {{ i = Math.floor(Math.random() * M.tracks.length); }} while (i === M.i);
    M.load(i); M.start();
  }};
  M.prev = () => {{ if (M.audio.currentTime > 3) {{ M.audio.currentTime = 0; return; }} M.load(M.i - 1); M.start(); }};
  M.seek = v => {{ M.dragging = false; if (M.audio.duration) M.audio.currentTime = v / 1000 * M.audio.duration; }};
  M.setVol = v => {{ M.volume = v / 100; M.audio.volume = M.volume; M.audio.muted = false; }};
  M.mute = () => {{ M.audio.muted = !M.audio.muted; }};
  M.toggleShuffle = () => {{ M.shuffle = !M.shuffle; M.paint(); }};
  M.toggleRepeat = () => {{ M.repeat = !M.repeat; M.audio.loop = M.repeat; M.paint(); }};
  M.sync = () => {{
    const g = M.tracks[M.i].g, on = !M.audio.paused;
    document.querySelectorAll("[data-mli-genre]").forEach(el => {{
      const me = el.dataset.mliGenre === g; el.classList.toggle("is-current", me); el.classList.toggle("is-playing", me && on);
    }});
  }};
  M.paint = () => {{
    const $ = id => document.getElementById(id), t = M.tracks[M.i], a = M.audio;
    if (!$("mli-dock")) return;
    $("mli-title").textContent = t.g; $("mli-sub").textContent = t.tag + " · " + Math.round(t.bpm) + " BPM";
    if ($("mli-cover").dataset.g !== t.g) {{ $("mli-cover").innerHTML = t.cover; $("mli-cover").dataset.g = t.g; }}
    $("mli-dock").classList.toggle("is-playing", !a.paused);
    $("mli-shuffle").classList.toggle("on", M.shuffle); $("mli-repeat").classList.toggle("on", M.repeat);
    const d = a.duration || 0, c = a.currentTime || 0, seek = $("mli-seek"), vol = $("mli-vol");
    $("mli-cur").textContent = fmt(c); $("mli-dur").textContent = fmt(d);
    if (!M.dragging) {{ seek.value = d ? c / d * 1000 : 0; seek.style.setProperty("--p", (d ? c / d * 100 : 0) + "%"); }}
    const v = a.muted ? 0 : M.volume * 100; vol.value = v; vol.style.setProperty("--p", v + "%");
    $("mli-volicon").textContent = v === 0 ? "volume_off" : v < 50 ? "volume_down" : "volume_up";
    if ("mediaSession" in navigator) navigator.mediaSession.metadata = new MediaMetadata({{ title: t.g, artist: "Music Listening Insights", album: t.tag }});
    M.sync();
  }};
  if ("mediaSession" in navigator) {{
    navigator.mediaSession.setActionHandler("play", () => M.toggle()); navigator.mediaSession.setActionHandler("pause", () => M.toggle());
    navigator.mediaSession.setActionHandler("nexttrack", () => M.next()); navigator.mediaSession.setActionHandler("previoustrack", () => M.prev());
  }}
  M.paint();
}})();
</script>"""


def shelf_html(albums):
    """Horizontal album shelf. `albums`: dicts with g, sub, cover (labelled svg)."""
    cards = "".join(f'<div class="lp" role="button" tabindex="0" {_attr(a["g"])}><div class="lp-art">{a["cover"]}'
                    f'<span class="lp-btn">{PLAY_PAUSE}</span></div><div class="lp-t">{html.escape(a["g"])}{EQ_BARS}</div>'
                    f'<div class="lp-s">{html.escape(a["sub"])}</div></div>' for a in albums)
    return f'<div class="shelf">{cards}</div>'


def tracklist_html(rows, best):
    """Spotify-style track list. `rows`: dicts with g, cover (small svg), n, share, improve, hours, bpm. `best` gets highlighted."""
    head = ('<div class="tl-row tl-head"><span>#</span><span>Genre</span><span>Records</span><span>% Improve</span>'
            '<span>Avg hours</span><span>BPM</span></div>')
    body = "".join(
        f'<div class="tl-row{" hl" if r["g"] == best else ""}" role="button" tabindex="0" {_attr(r["g"])}>'
        f'<span class="tl-n"><b>{k + 1:02d}</b><span class="ms fill i20 ic-play">play_arrow</span><span class="ms fill i20 ic-pause">pause</span>{EQ_BARS}</span>'
        f'<span class="tl-g"><span class="tl-cover">{r["cover"]}</span><span><b>{html.escape(r["g"])}</b>'
        f'{"<small>highest “Improve” share</small>" if r["g"] == best else ""}</span></span>'
        f'<span class="m">{r["n"]} <em>({r["share"]:.0f}%)</em></span>'
        f'<span>{r["improve"]:.0f}%<span class="mini"><i style="width:{r["improve"]:.0f}%"></i></span></span>'
        f'<span class="m">{r["hours"]:.2f} h</span><span class="m">{r["bpm"]:.0f}</span></div>' for k, r in enumerate(rows))
    return f'<div class="tracklist">{head}{body}</div>'


def play_button_html(genre, label):
    return (f'<button class="mli-cta" {_attr(genre)}>{PLAY_PAUSE}<span>{html.escape(label)}</span>{EQ_BARS}</button>')
