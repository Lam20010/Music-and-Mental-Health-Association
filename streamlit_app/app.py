from pathlib import Path
import json
import random

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.colors import make_colorscale, sample_colorscale
from scipy.stats import chi2_contingency

import scene  # helper script: the animated listener scene for the Guess the Mood game
import player as mp  # helper script: album covers, docked music player, album shelf, track list
import sounds  # helper script: turns every genre into a short synthesised loop at that genre's real median BPM

st.set_page_config(page_title="Music Listening Insights", page_icon=":material/headphones:", layout="wide", initial_sidebar_state="collapsed")

# ============================================================================================ constants (purple palette)
PALETTE = ["#da8ee7", "#be2ed6", "#8a00c2", "#e8bcf0", "#ca5cdd", "#7600bc", "#a000c8", "#b100cd", "#4c00b0"]
EFFECTS = ["Improve", "No effect", "Worsen"]
EFFECT_COLORS = {"Improve": "#e8bcf0", "No effect": "#ca5cdd", "Worsen": "#7600bc"}
TIME_ORDER = ["Morning", "Afternoon", "Evening", "Late night"]
MIN_GROUP = 30
HERE = Path(__file__).parent
DATA_PATH = HERE / "clean_data.csv"
PLOTS_DIR = HERE / "plots"

NICE = {
    "age": "Age", "hours_per_day": "Hours per day", "bpm": "BPM", "music_effects": "Reported music effect",
    "music_genre": "Music genre", "listening_time": "Listening time", "listening_setting": "Listening setting",
    "vibe_reason": "Vibe reason", "primary_streaming_service": "Streaming service",
    "mental_disorder": "Mental-health group", "instrumentalist": "Instrumentalist",
    "composer": "Composer", "exploratory": "Exploratory listener", "foreign_languages": "Foreign-language music",
    "repeats_songs_often": "Repeats songs often", "listening_purpose": "Listening purpose",
}
# every icon is a Material Symbols Rounded name: the same set Streamlit uses for ":material/<name>:" in buttons and tabs
GENRE_ICON = {"Soundtracks": "movie", "Video game music": "sports_esports", "Hip-hop": "mic", "Electronic": "graphic_eq", "Instrumental": "piano",
              "Jazz": "nightlife", "Metal": "bolt", "R&B": "favorite", "Indie": "queue_music", "Ambient": "cloud", "Lofi": "coffee", "EDM": "speaker",
              "Pop": "star", "Rock": "album", "Classical": "library_music", "Country": "landscape", "Blues": "music_note"}
SETTING_ICON = {"Home / relaxing": "home", "Public / Private Transport": "directions_bus", "Work / study": "work", "Gym / exercising": "fitness_center",
                "Social / with friends": "groups", "While gaming": "sports_esports", "Anywhere / varies": "public", "Other": "more_horiz", "Car / commuting": "directions_car"}
TIME_ICON = {"Morning": "wb_twilight", "Afternoon": "light_mode", "Evening": "routine", "Late night": "dark_mode"}
VIBE_ICON = {"Calming/relaxation": "spa", "Emotional connection/mood expression": "favorite", "Rhythm and stimulation": "bolt",
             "Familiarity and emotional comfort": "weekend", "Repetitive/predictable beats": "repeat", "Nostalgia/memories": "history",
             "Enjoyment of sound/rhythm": "music_note"}
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64)
TILES = ["#8e3fd4", "#6a2bbf", "#a95ad9", "#5326a8", "#7d36c9"]          # solid tile colours for thumbnails, avatars and cards

# ============================================================================================ styling (all CSS lives in style.css)
SWATCH_CSS = "".join(f'.st-key-{key} .stButtonGroup button[data-variant="pills"]:nth-of-type({i + 1}) {{ background: {c} !important; }}'
                     for key, colors in (("mr_skin", scene.SKIN), ("mr_hair", scene.HAIR), ("mr_shirt", scene.SHIRT)) for i, c in enumerate(colors))
st.markdown(f"<style>{(HERE / 'style.css').read_text(encoding='utf-8')}{SWATCH_CSS}</style>", unsafe_allow_html=True)


# ============================================================================================ helpers
@st.cache_data
def load_data(path):
    d = pd.read_csv(path)
    for c in d.select_dtypes(include=["object", "string"]).columns:
        d[c] = d[c].astype(str).str.strip()
    return d


def label(c):
    return NICE.get(c, c.replace("_", " ").capitalize())


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def live(markup):
    """HTML that may run JavaScript (the music player and anything that plays through it)."""
    st.html(markup, unsafe_allow_javascript=True)


def icon(name, size=20, fill=False):
    """Inline Material Symbols icon; sizes are restricted to one scale so every icon lines up."""
    assert size in ICON_SIZES, size
    return f'<span class="ms i{size}{" fill" if fill else ""}">{name}</span>'


def playable(genre):
    """Attributes that turn any element into a play button for that genre (handled by the player's click listener)."""
    return f'data-mli-genre="{genre.replace("&", "&amp;")}" role="button" tabindex="0" title="Play {genre}"'


def gicon(genre, size=20, fill=False):
    return icon(GENRE_ICON.get(genre, "music_note"), size, fill)


PLOT_CFG = {"displayModeBar": False}


def show(fig, key=None):
    try:
        st.plotly_chart(fig, width="stretch", key=key, config=PLOT_CFG)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=key, config=PLOT_CFG)


def button(text, **kw):
    try:
        return st.button(text, width="stretch", **kw)
    except TypeError:
        return st.button(text, use_container_width=True, **kw)


def style(fig, height=330, legend=True):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", colorway=PALETTE,
        font=dict(color="#e2b6f4", family="Manrope, Segoe UI, sans-serif"), margin=dict(l=8, r=8, t=18, b=8),
        legend=dict(orientation="h", y=-0.2, title_text="", font=dict(color="#fff")) if legend else dict(),
        hoverlabel=dict(bgcolor="#2b1270", font_color="#fff"),
    )
    fig.update_xaxes(gridcolor="rgba(232,188,240,.12)", zeroline=False, linecolor="rgba(232,188,240,.25)")
    fig.update_yaxes(gridcolor="rgba(232,188,240,.12)", zeroline=False, linecolor="rgba(232,188,240,.25)")
    return equalizer(fig)


EQ_SCALE = make_colorscale(["#5b1ccf", "#7c2be0", "#a03ee6", "#c45de9", "#e08cf0", "#f6c4fb"])   # deep violet -> lavender


def equalizer(fig):
    """Music-equalizer look for bar charts and histograms: every bar is cut into LED blocks by a line pattern, and a
    single-colour bar chart is shaded by value like an equalizer (taller bar = brighter purple). Charts that already
    colour their bars (effect colours) keep those colours and only get the blocks."""
    bars = [t for t in fig.data if t.type in ("bar", "histogram")]
    if not bars:
        return fig
    for t in bars:
        horizontal = t.orientation == "h"
        if len(bars) == 1 and t.type == "bar" and isinstance(t.marker.color, (str, type(None))):
            v = np.abs(np.asarray(t.x if horizontal else t.y, dtype=float))
            t.marker.color = sample_colorscale(EQ_SCALE, list(v / v.max()) if len(v) and v.max() > 0 else [0.5] * len(v))
        # "replace" mode: the pattern lines are the LED blocks, drawn in each bar's own colour, and the gaps between them are
        # transparent so the card shows through. ("overlay" mode with dark gap lines was overridden by plotly.js's automatic
        # grey/white contrast colour whenever bars have per-bar colours.)
        t.marker.pattern = dict(shape="|" if horizontal else "-", fillmode="replace", size=8, solidity=0.7)
        t.marker.line.width = 0
    fig.update_layout(bargap=0.06 if any(t.type == "histogram" for t in bars) else 0.2)
    return fig


def donut(ec):
    """Effect donut: labels stay inside their slice (dark text on the light slice, white on dark ones); slices too thin for a label hide it."""
    fig = px.pie(ec, names="effect", values="records", hole=.6, color="effect", color_discrete_map=EFFECT_COLORS)
    fig.update_traces(textinfo="percent", textposition="inside", sort=False, marker=dict(line=dict(color="#241058", width=2)),
                      textfont=dict(size=13, color=["#140534" if e == "Improve" else "#ffffff" for e in ec.effect]))
    fig.update_layout(uniformtext_minsize=11, uniformtext_mode="hide")
    return fig


def highlight(fig, labels, selected, color="#ff8ad8"):
    """Paint one bar of an equalizer-shaded bar chart pink (the selected genre)."""
    t = fig.data[0]
    t.marker.color = [color if lab == selected else c for lab, c in zip(labels, t.marker.color)]
    return fig


def order_for(col, d):
    vals = list(d[col].unique())
    if col == "listening_time":
        return [t for t in TIME_ORDER if t in vals] + sorted(set(vals) - set(TIME_ORDER))
    if col == "music_effects":
        return [e for e in EFFECTS if e in vals]
    if set(vals) <= {"Yes", "No"}:
        return [v for v in ["Yes", "No"] if v in vals]
    return list(d[col].value_counts().index)


def cramers_v(a, b):
    t = pd.crosstab(a, b)
    if t.shape[0] < 2 or t.shape[1] < 2:
        return np.nan
    chi2 = chi2_contingency(t, correction=False)[0]
    return float(np.sqrt(chi2 / (t.values.sum() * (min(t.shape) - 1))))


def pct_improve(s):
    return float((s == "Improve").mean() * 100)


def group_rates(d, col, minn=MIN_GROUP):
    g = d.groupby(col).music_effects.agg(improve=pct_improve, n="size")
    g["worsen"] = d.groupby(col).music_effects.apply(lambda s: float((s == "Worsen").mean() * 100))
    return g[g.n >= minn]


def card(title, sub=""):
    html(f'<div class="card-h">{title}</div><div class="card-s">{sub}</div>')


def section(title):
    html(f'<div class="sec"><b>{title}</b></div>')


@st.cache_data(show_spinner=False)
def sfx(name):
    return {"win": sounds.win_chime, "miss": sounds.miss_buzz}[name]()


def audio(data, autoplay=False, loop=False):
    kw = {}
    if autoplay:
        kw["autoplay"] = True
    if loop:
        kw["loop"] = True
    try:
        st.audio(data, format="audio/wav", **kw)
    except TypeError:
        st.audio(data, format="audio/wav")


if not DATA_PATH.exists():
    st.error("clean_data.csv was not found. Put it in the same folder as app.py.")
    st.stop()
df = load_data(DATA_PATH)
CAT = [c for c in NICE if c in df.columns and c not in ("age", "hours_per_day", "bpm")]
NUM = [c for c in ("age", "hours_per_day", "bpm") if c in df.columns]
NON_EFFECT = [c for c in CAT if c != "music_effects"]
GENRES = sorted(df.music_genre.unique())
GENRE_BPM = df.groupby("music_genre").bpm.median().to_dict()      # real median tempo of every genre -> used by the synth
TOP_GENRE_ALL = df.music_genre.value_counts().index[0]
LOOPS_DIR = HERE / "static" / "loops"          # served by Streamlit at app/static/loops/ (enableStaticServing in config.toml)


@st.cache_resource(show_spinner="Rendering genre loops (first run only)…")
def ensure_loops():
    """The player streams one WAV per genre from static/loops/. They ship with the app; render any that are missing."""
    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    for g in GENRES:
        path = LOOPS_DIR / f"{mp.slug(g)}.wav"
        if not path.exists():
            path.write_bytes(sounds.render_genre(g, round(GENRE_BPM[g], 1)))


ensure_loops()


@st.cache_resource
def loop_bytes():
    return {mp.slug(g): (LOOPS_DIR / f"{mp.slug(g)}.wav").read_bytes() for g in GENRES}


def play_now(genre, nonce):
    """Start `genre` in the player once. The nonce changes the markup, so Streamlit re-mounts it and the script runs again."""
    live(f'<span hidden data-nonce="{nonce}"></span><script>(function(){{var g={json.dumps(genre)};'
         'if(window.MLI){var i=MLI.idx(g);if(i>=0&&(i!==MLI.i||MLI.audio.paused)){MLI.load(i);MLI.start();}}})();</script>')
# album covers are drawn from the data: each genre's listening-hours distribution (full dataset, so covers never change)
COVER_LEVELS = {g: (h / h.max()).round(3).tolist() for g, h in
                ((g, np.histogram(x.hours_per_day, bins=12, range=(1, 8))[0].astype(float)) for g, x in df.groupby("music_genre"))}


def cover(g, label=True):
    return mp.cover_svg(g, COVER_LEVELS[g], GENRE_BPM[g], GENRES.index(g), label)


TRACKS = [dict(g=g, slug=mp.slug(g), bpm=GENRE_BPM[g], tag=sounds.GENRE_TAGLINE.get(g, ""), cover=cover(g, label=False))
          for g in df.music_genre.value_counts().index]

# ============================================================================================ top bar: brand, about + filters
STEP = 0.25
H_MIN, H_MAX = float(np.floor(df.hours_per_day.min() / STEP) * STEP), float(np.ceil(df.hours_per_day.max() / STEP) * STEP)
B_MIN, B_MAX = float(np.floor(df.bpm.min() / 5) * 5), float(np.ceil(df.bpm.max() / 5) * 5)
A_MIN, A_MAX = int(df.age.min()), int(df.age.max())
DEFAULTS = {
    "f_effects": EFFECTS, "f_age": (A_MIN, A_MAX), "f_hours": (H_MIN, H_MAX), "f_bpm": (B_MIN, B_MAX),
    "f_time": order_for("listening_time", df), "f_setting": "All", "f_group": "All", "f_genre": [],
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
st.session_state.setdefault("genre", TOP_GENRE_ALL)


def reset_filters():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v


def range_slider(col, label, lo, hi, step, name, fmt=None):
    """Two-handle range: left handle = minimum, right handle = maximum, starting at the full range (smallest to largest)."""
    kw = {"format": fmt} if fmt else {}
    col.slider(label, lo, hi, step=step, key=name, **kw)


EFFECT_ICON = {"Improve": "trending_up", "No effect": "trending_flat", "Worsen": "trending_down"}


def with_icon(mapping):
    return lambda v: f":material/{mapping.get(v, 'music_note')}: {v}"


def fsection(col, key, icon_name, title):
    """One labelled card inside the filter bar."""
    box = col.container(key=f"fsec_{key}")
    box.markdown(f'<div class="fsec-h">{icon(icon_name, 20)}{title}</div>', unsafe_allow_html=True)
    return box


top = st.container()          # filled in after the filters so it can show how many records are in view
with st.container(key="filterbar"):
    # sliders sit in the bar itself, not in a popover: Streamlit measures the page to place their value labels,
    # and inside a closed popover those measurements are wrong (that is what put labels over the wrong handle)
    mood, who, how, sound = st.columns([1.25, 1, 1, 1], gap="small")
    with fsection(mood, "mood", "mood", "Mood"):
        st.pills("Reported effect", EFFECTS, selection_mode="multi", format_func=with_icon(EFFECT_ICON), key="f_effects")
        st.pills("Listening time", DEFAULTS["f_time"], selection_mode="multi", format_func=with_icon(TIME_ICON), key="f_time")
    with fsection(who, "who", "person", "Listener"):
        range_slider(st, "Age", A_MIN, A_MAX, 1, "f_age")
        st.selectbox("Mental-health group", ["All"] + sorted(df.mental_disorder.unique()), key="f_group")
    with fsection(how, "how", "headphones", "Listening"):
        range_slider(st, "Hours per day", H_MIN, H_MAX, STEP, "f_hours", "%.2f")
        st.selectbox("Listening setting", ["All"] + sorted(df.listening_setting.unique()), key="f_setting")
    with fsection(sound, "sound", "graphic_eq", "Sound"):
        range_slider(st, "Tempo (BPM)", B_MIN, B_MAX, 5.0, "f_bpm", "%d")
        st.multiselect("Music genre", GENRES, key="f_genre", placeholder="All genres")

s = st.session_state
mask = (
    df.music_effects.isin(s.f_effects)
    & df.age.between(*s.f_age)
    & df.hours_per_day.between(*s.f_hours)
    & df.bpm.between(*s.f_bpm)
    & df.listening_time.isin(s.f_time)
)
if s.f_setting != "All":
    mask &= df.listening_setting == s.f_setting
if s.f_group != "All":
    mask &= df.mental_disorder == s.f_group
if s.f_genre:
    mask &= df.music_genre.isin(s.f_genre)
f = df[mask]
n_active = sum([set(s.f_effects) != set(EFFECTS), set(s.f_time) != set(DEFAULTS["f_time"]), tuple(s.f_age) != DEFAULTS["f_age"],
                tuple(s.f_hours) != DEFAULTS["f_hours"], tuple(s.f_bpm) != DEFAULTS["f_bpm"], s.f_setting != "All", s.f_group != "All", bool(s.f_genre)])

with top:
    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="topstrip"):
        st.markdown(f'<div class="brand"><div class="logo">{icon("graphic_eq", 24)}</div><div>Music Listening Insights</div></div>',
                    unsafe_allow_html=True, width="stretch")
        st.markdown(f'<span class="fchip">{icon("person", 16)} Showing <b>{len(f):,}</b> of {len(df):,}</span>', unsafe_allow_html=True, width="content")
        st.markdown(f'<span class="fchip">{icon("tune", 16)} <b>{n_active}</b> filter{"s" if n_active != 1 else ""} active</span>',
                    unsafe_allow_html=True, width="content")
        st.button("Reset", icon=":material/restart_alt:", on_click=reset_filters, key="reset_btn")
        st.download_button("Export", f.to_csv(index=False).encode(), "filtered_music_data.csv", "text/csv", icon=":material/download:", key="dl_btn")
        about = st.popover("About", icon=":material/info:", width="content", key="pop_about")
    with about:
        html('<div class="about"><b>About this dataset</b><br>1,000 survey-style records about <b>when, where and how people listen to '
             'music</b> (age, hours per day, tempo, genre, setting, time of day) and the effect they report: <i>Improve · No effect · Worsen</i>. '
             'It is based on the MXMH Music &amp; Mental Health survey topic (Kaggle).</div>')

# ============================================================================================ shared numbers
if not f.empty:
    top_time, top_set, top_gen = f.listening_time.value_counts(), f.listening_setting.value_counts(), f.music_genre.value_counts()
    imp_f = pct_improve(f.music_effects)
    r_age_hours = f[["age", "hours_per_day"]].corr().iloc[0, 1] if len(f) > 2 else np.nan
imp_all = pct_improve(df.music_effects)


def delta(a, b, unit="", pct=False):
    d = a - b
    cls = "flat" if abs(d) < 1e-9 else ("up" if d > 0 else "down")
    arrow = icon({"flat": "trending_flat", "up": "arrow_upward", "down": "arrow_downward"}[cls], 16)
    txt = f"{(a / b - 1) * 100:+.1f}%" if pct else f"{d:+.1f}{unit}"
    return f'<span class="{cls}">{arrow}{txt}</span>&nbsp;vs all'


def outlier_counts(d):
    out = {}
    for c in NUM:
        q1, q3 = d[c].quantile([.25, .75])
        iqr = q3 - q1
        out[c] = (int(((d[c] < q1 - 1.5 * iqr) | (d[c] > q3 + 1.5 * iqr)).sum()), float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr))
    return out


def build_insights(d):
    """(icon name, title, text) tuples written from the numbers in the current selection."""
    out = []
    if len(d) < 2:
        return out
    tt, ts, tg = d.listening_time.value_counts(), d.listening_setting.value_counts(), d.music_genre.value_counts()
    out.append(("schedule", "When people listen", f"{tt.index[0]} is the most common listening time ({tt.iloc[0] / len(d) * 100:.0f}% of records)"
                      + (f", followed by {tt.index[1]} ({tt.iloc[1] / len(d) * 100:.0f}%)." if len(tt) > 1 else ".")))
    out.append(("location_on", "Where people listen", f"{ts.index[0]} leads with {ts.iloc[0] / len(d) * 100:.0f}% of records"
                      + (f"; {ts.index[1]} is next ({ts.iloc[1] / len(d) * 100:.0f}%)." if len(ts) > 1 else ".")))
    out.append(("library_music", "Genres", f"{tg.index[0]} is the largest genre ({tg.iloc[0]} records, {tg.iloc[0] / len(d) * 100:.0f}%); "
                      f"{tg.index[-1]} is the smallest ({tg.iloc[-1]} records)."))
    r = d[["age", "hours_per_day"]].corr().iloc[0, 1]
    strength = "strong" if abs(r) >= .6 else "moderate" if abs(r) >= .3 else "weak"
    out.append(("trending_down", "Age and listening hours", f"Pearson r = {r:.2f}, a {strength} {'negative' if r < 0 else 'positive'} linear association: "
                      + ("older respondents report fewer hours per day." if r < 0 else "older respondents report more hours per day.")))
    gg = group_rates(d, "music_genre")
    if len(gg) >= 2:
        gg = gg.sort_values("improve")
        out.append(("sentiment_satisfied", "Genre and reported effect", f"“Improve” is highest for {gg.index[-1]} ({gg.improve.iloc[-1]:.0f}%) and lowest for "
                          f"{gg.index[0]} ({gg.improve.iloc[0]:.0f}%) among genres with at least {MIN_GROUP} records."))
    mg = group_rates(d, "mental_disorder")
    if len(mg) >= 2:
        mg = mg.sort_values("worsen")
        out.append(("psychology", "Mental-health groups", f"{mg.index[-1]} has the highest “Worsen” share ({mg.worsen.iloc[-1]:.0f}%), "
                          f"while {mg.index[0]} has the lowest ({mg.worsen.iloc[0]:.0f}%)."))
    ic = d.groupby("instrumentalist").foreign_languages.apply(lambda s: (s == "Yes").mean() * 100)
    if {"Yes", "No"} <= set(ic.index):
        out.append(("translate", "Instrumentalists and foreign-language music", f"{ic['Yes']:.0f}% of instrumentalists listen to foreign-language music, "
                          f"versus {ic['No']:.0f}% of non-instrumentalists."))
    return out


@st.cache_data
def genre_profile(d, g):
    x = d[d.music_genre == g]
    if x.empty:
        return None
    return dict(n=len(x), improve=pct_improve(x.music_effects), noeff=float((x.music_effects == "No effect").mean() * 100),
                worsen=float((x.music_effects == "Worsen").mean() * 100), hours=float(x.hours_per_day.mean()), bpm=float(x.bpm.median()),
                age=float(x.age.median()), setting=x.listening_setting.value_counts().index[0], time=x.listening_time.value_counts().index[0],
                vibe=x.vibe_reason.value_counts().index[0])


def need_data():
    st.info("No records match the current filters. Widen them or press **Reset** in the filter bar.", icon=":material/filter_alt_off:")


# ============================================================================================ TAB: HOME
def tab_home():
    if len(f) < MIN_GROUP:
        st.warning(f"Only {len(f)} records match, so percentages and patterns may be unreliable.")
    main, rail = st.columns([3.1, 1.15], gap="medium")
    with main:
        waves = ('<svg viewBox="0 0 700 300" preserveAspectRatio="none"><path d="M0 220 C60 120 120 120 180 200 S300 290 360 190 S480 60 540 170 S650 250 700 150 L700 300 L0 300Z" fill="#e2b6f4" opacity=".35"/>'
                 '<path d="M0 250 C70 190 140 180 200 240 S330 300 400 230 S520 120 590 210 S670 270 700 220 L700 300 L0 300Z" fill="#c3a6e0" opacity=".5"/>'
                 '<path d="M0 280 C90 250 160 250 240 285 S400 310 470 270 S600 215 700 270 L700 300 L0 300Z" fill="#4c00b0" opacity=".55"/></svg>')
        hero_title = f"{top_time.index[0]} is when {top_time.iloc[0] / len(f) * 100:.0f}% of people listen"
        hero_sub = (f"{top_set.index[0]} is the most common setting ({top_set.iloc[0] / len(f) * 100:.0f}%), and "
                    f"{imp_f:.0f}% of listeners in this view say music improves how they feel.")
        html(
            f'<div class="hero">{waves}<div class="disc" {playable(top_gen.index[0])}>{gicon(top_gen.index[0], 64, fill=True)}<span class="disc-play">{icon("play_arrow", 32, fill=True)}</span></div><div><div class="hero-eyebrow">Insight of the view · {len(f):,} respondents</div>'
            f'<div class="hero-title">{hero_title}</div><div class="hero-sub">{hero_sub}</div>'
            f'<span class="chip solid">{icon("headphones", 16)} {f.hours_per_day.mean():.1f} h / day</span><span class="chip">{icon("cake", 16)} median age {f.age.median():.0f}</span>'
            f'<span class="chip">{icon("speed", 16)} {f.bpm.median():.0f} BPM</span><span class="chip">{gicon(top_gen.index[0], 16)} {top_gen.index[0]}</span></div></div>'
        )
        kpis = [("Respondents", "group", f"{len(f):,}", f"{len(f) / len(df) * 100:.0f}% of all data"),
                ("Avg hours / day", "headphones", f"{f.hours_per_day.mean():.2f}", delta(f.hours_per_day.mean(), df.hours_per_day.mean(), pct=True)),
                ("Median age", "cake", f"{f.age.median():.0f}", delta(f.age.median(), df.age.median(), " yrs")),
                ("% Improve", "sentiment_satisfied", f"{imp_f:.0f}%", delta(imp_f, imp_all, " pts")),
                ("Median BPM", "speed", f"{f.bpm.median():.0f}", delta(f.bpm.median(), df.bpm.median(), " BPM"))]
        html('<div class="kpis">' + "".join(
            f'<div class="kpi"><div class="top"><div class="l">{l}</div><div class="ic">{icon(ic, 20)}</div></div><div class="v">{v}</div><div class="d">{d}</div></div>'
            for l, ic, v, d in kpis) + '</div>')
        gt = f.groupby("music_genre").agg(n=("age", "size"), improve=("music_effects", pct_improve), hours=("hours_per_day", "mean"), bpm=("bpm", "median"))
        gt = gt.sort_values("n", ascending=False)
        # ---- album shelf: every genre in view is an album, click to play it in the player
        section("Albums")
        live(mp.shelf_html([dict(g=g, cover=cover(g), sub=f"{int(r.n)} records · {r.improve:.0f}% better") for g, r in gt.iterrows()]))
        # ---- top genres as a playable track list
        top6 = gt.head(6)
        section("Top Genres")
        live(mp.tracklist_html([dict(g=g, cover=cover(g, label=False), n=int(r.n), share=r.n / len(f) * 100, improve=r.improve, hours=r.hours,
                                     bpm=r.bpm) for g, r in top6.iterrows()], best=top6.improve.idxmax()))
        # ---- Top settings (circles)
        circ = ""
        for i, (sname, cnt) in enumerate(top_set.head(5).items()):
            tile = TILES[i % len(TILES)]
            circ += (f'<div class="circ"><div class="avatar" style="background:{tile}">{icon(SETTING_ICON.get(sname, "music_note"), 40)}</div>'
                     f'<div class="nm">{sname}</div><div class="sub">{cnt} records · {cnt / len(f) * 100:.0f}%</div></div>')
        section("Top Settings")
        html(f'<div class="g"><div class="circles">{circ}</div></div>')
        # ---- Top vibe reasons (albums)
        alb = ""
        for i, (v, cnt) in enumerate(f.vibe_reason.value_counts().head(5).items()):
            tile = TILES[(i + 2) % len(TILES)]
            alb += (f'<div class="album"><div class="art" style="background:{tile}">{icon(VIBE_ICON.get(v, "music_note"), 48)}</div>'
                    f'<div class="nm">{v}</div><div class="ct">{cnt} records · {cnt / len(f) * 100:.0f}%</div></div>')
        section("Top Vibe Reasons")
        html(f'<div class="g"><div class="albums">{alb}</div></div>')

        section("Charts")
        c1, c2 = st.columns([1.55, 1])
        with c1:
            with st.container(border=True, key="glass_scatter"):
                card("Age vs daily listening hours", "Each dot is a respondent · line = linear trend")
                fig = px.scatter(f, x="age", y="hours_per_day", color="music_effects", opacity=.75, color_discrete_map=EFFECT_COLORS,
                                 category_orders={"music_effects": EFFECTS}, labels=NICE, hover_data=["music_genre", "listening_time"])
                fig.update_traces(marker=dict(size=7))
                if len(f) > 2:
                    m, b = np.polyfit(f.age, f.hours_per_day, 1)
                    xs = np.array([f.age.min(), f.age.max()])
                    fig.add_trace(go.Scatter(x=xs, y=m * xs + b, mode="lines", name=f"Trend (r = {r_age_hours:.2f})", line=dict(color="#fff", width=3, dash="dot")))
                show(style(fig, 340), key="ov_scatter")
        with c2:
            with st.container(border=True, key="glass_donut"):
                card("Reported effect", "Share of respondents in view")
                ec = f.music_effects.value_counts().reindex(EFFECTS).dropna().rename_axis("effect").reset_index(name="records")
                show(style(donut(ec), 340), key="ov_donut")
        c3, c4 = st.columns(2)
        with c3:
            with st.container(border=True, key="glass_time"):
                card("Listening time by reported effect", "Number of respondents")
                ct = pd.crosstab(f.listening_time, f.music_effects).reindex(index=order_for("listening_time", f), columns=EFFECTS, fill_value=0).reset_index()
                fig = px.bar(ct.melt(id_vars="listening_time", var_name="Effect", value_name="Records"), x="listening_time", y="Records", color="Effect",
                             barmode="stack", color_discrete_map=EFFECT_COLORS, category_orders={"Effect": EFFECTS}, labels=NICE)
                fig.update_xaxes(title_text=None)
                show(style(fig, 320), key="ov_time")
        with c4:
            with st.container(border=True, key="glass_setting"):
                card("Where people listen", "Records by listening setting")
                sc = f.listening_setting.value_counts().rename_axis("setting").reset_index(name="records")
                fig = px.bar(sc, x="records", y="setting", orientation="h", text="records", labels={"setting": "", "records": "Records"})
                fig.update_traces(marker_color="#c3a6e0", textposition="outside", textfont=dict(color="#fff"), cliponaxis=False)
                fig.update_layout(yaxis=dict(autorange="reversed"))
                show(style(fig, 320, legend=False).update_layout(margin=dict(l=8, r=44, t=18, b=8)), key="ov_setting")
        c5, c6 = st.columns(2)
        with c5:
            with st.container(border=True, key="glass_genre_eff"):
                card("Reported effect within each genre", "100% stacked · share of records")
                ct = pd.crosstab(f.music_genre, f.music_effects).reindex(columns=EFFECTS, fill_value=0)
                pc = (ct.div(ct.sum(axis=1), axis=0) * 100).sort_values("Improve")
                long = pc.reset_index().melt(id_vars="music_genre", var_name="Effect", value_name="Percent")
                fig = px.bar(long, x="Percent", y="music_genre", color="Effect", orientation="h", color_discrete_map=EFFECT_COLORS,
                             category_orders={"Effect": EFFECTS}, labels={"music_genre": "", "Percent": "% of records"})
                show(style(fig, 440), key="ov_genre_eff")
        with c6:
            with st.container(border=True, key="glass_group_eff"):
                card("Effect by mental-health group", "100% stacked · small groups are noisy")
                ct = pd.crosstab(f.mental_disorder, f.music_effects).reindex(columns=EFFECTS, fill_value=0)
                nn = ct.sum(axis=1)
                pc = (ct.div(nn, axis=0) * 100).sort_values("Improve")
                pc.index = [f"{i} (n={nn[i]})" for i in pc.index]
                long = pc.reset_index().melt(id_vars="index", var_name="Effect", value_name="Percent")
                fig = px.bar(long, x="Percent", y="index", color="Effect", orientation="h", color_discrete_map=EFFECT_COLORS,
                             category_orders={"Effect": EFFECTS}, labels={"index": "", "Percent": "% of records"})
                show(style(fig, 440), key="ov_group_eff")

    with rail:
        tags = "".join(f'<span class="tag" {playable(g)}><i>{gicon(g, 16)}</i>{g}</span>' for g in top_gen.head(6).index)
        html(f'<div class="g"><div class="sec"><b>Tags</b></div>{tags}</div>')
        items = ""
        for i, (tname, cnt) in enumerate(top_time.items()):
            tile = TILES[i % len(TILES)]
            imp = pct_improve(f.loc[f.listening_time == tname, "music_effects"])
            items += (f'<div class="li"><div class="th" style="background:{tile}">{icon(TIME_ICON.get(tname, "schedule"), 24)}</div>'
                      f'<div><div class="t">{tname}</div><div class="s">{cnt} records · {cnt / len(f) * 100:.0f}%</div></div>'
                      f'<div class="r">{imp:.0f}%<small>improve</small></div></div>')
        html(f'<div class="g"><div class="sec"><b>Played</b></div>{items}</div>')
        g0 = top_gen.index[0]
        html(f'<div class="feat" {playable(g0)}><div class="art">{cover(g0)}</div><div class="ft"><div class="t">Top genre in view: {g0}</div>'
             f'<div class="s">{GENRE_BPM[g0]:.0f} BPM median tempo · {top_gen.iloc[0]} records</div></div></div>')
        live(mp.play_button_html(g0, f"Play {g0}"))
        share = len(f) / len(df) * 100
        html(f'<div class="g" style="margin-top:12px"><div class="card-h">Now showing</div><div class="card-s">{share:.0f}% of the dataset · {n_active} filter{"s" if n_active != 1 else ""} active</div>'
             f'<div class="mini" style="width:100%"><i style="width:{share:.1f}%"></i></div></div>')


# ============================================================================================ TAB: TOP CHARTS (explore)
def tab_charts():
    section("Top Charts")
    kind = st.radio("Chart type", ["Histogram", "Counts", "Box plot", "Scatter", "Heatmap (row %)", "Grouped bars (% within group)", "Correlation"],
                    horizontal=True, label_visibility="collapsed", key="ex_kind")
    with st.container(border=True, key="glass_explore"):
        if kind == "Histogram":
            c1, c2 = st.columns(2)
            x = c1.selectbox("Numeric variable", NUM, 1, format_func=label, key="ex_hx")
            hue = c2.selectbox("Colour by", ["none"] + CAT, CAT.index("music_effects") + 1, format_func=lambda c: "None" if c == "none" else label(c), key="ex_hh")
            fig = px.histogram(f, x=x, color=None if hue == "none" else hue, nbins=30, barmode="stack", labels=NICE, color_discrete_sequence=PALETTE,
                               color_discrete_map=EFFECT_COLORS if hue == "music_effects" else None, marginal="box")
            show(style(fig, 480), key="ex_hist")
        elif kind == "Scatter":
            c1, c2, c3 = st.columns(3)
            x = c1.selectbox("X axis", NUM, 0, format_func=label, key="ex_sx")
            y = c2.selectbox("Y axis", NUM, 1, format_func=label, key="ex_sy")
            hue = c3.selectbox("Colour by", ["none"] + CAT, CAT.index("music_effects") + 1, format_func=lambda c: "None" if c == "none" else label(c), key="ex_sh")
            fig = px.scatter(f, x=x, y=y, color=None if hue == "none" else hue, opacity=.75, labels=NICE, color_discrete_sequence=PALETTE,
                             color_discrete_map=EFFECT_COLORS if hue == "music_effects" else None, hover_data=["music_genre", "listening_setting"])
            if len(f) > 2 and st.checkbox("Show trend line", True, key="ex_trend"):
                m, b = np.polyfit(f[x], f[y], 1)
                xs = np.array([f[x].min(), f[x].max()])
                fig.add_trace(go.Scatter(x=xs, y=m * xs + b, mode="lines", name=f"Trend (r = {f[x].corr(f[y]):.2f})", line=dict(color="#fff", width=3, dash="dot")))
            show(style(fig, 480), key="ex_scatter")
        elif kind == "Box plot":
            c1, c2 = st.columns(2)
            y = c1.selectbox("Numeric variable", NUM, 1, format_func=label, key="ex_by")
            x = c2.selectbox("Group by", NON_EFFECT + ["music_effects"], NON_EFFECT.index("mental_disorder"), format_func=label, key="ex_bx")
            od = list(f.groupby(x)[y].median().sort_values().index)
            fig = px.box(f, x=x, y=y, color=x, category_orders={x: od}, color_discrete_sequence=PALETTE, labels=NICE, points="outliers")
            fig.update_layout(showlegend=False)
            fig.update_xaxes(tickangle=-30)
            show(style(fig, 480, legend=False), key="ex_box")
        elif kind == "Counts":
            c1, c2 = st.columns(2)
            x = c1.selectbox("Category", CAT, CAT.index("music_genre"), format_func=label, key="ex_cx")
            sp = c2.selectbox("Split by", ["none"] + CAT, CAT.index("music_effects") + 1, format_func=lambda c: "None" if c == "none" else label(c), key="ex_cs")
            if sp == "none":
                cnt = f[x].value_counts().rename_axis(x).reset_index(name="Records")
                fig = px.bar(cnt, x=x, y="Records", text="Records", labels=NICE, color_discrete_sequence=["#c3a6e0"])
                fig.update_traces(textposition="outside", textfont=dict(color="#fff"), cliponaxis=False)
            else:
                cnt = f.groupby([x, sp]).size().reset_index(name="Records")
                fig = px.bar(cnt, x=x, y="Records", color=sp, barmode="group", labels=NICE, color_discrete_sequence=PALETTE,
                             color_discrete_map=EFFECT_COLORS if sp == "music_effects" else None)
            fig.update_xaxes(tickangle=-30)
            show(style(fig, 480, legend=sp != "none"), key="ex_counts")
        elif kind == "Heatmap (row %)":
            c1, c2 = st.columns(2)
            r_ = c1.selectbox("Rows", NON_EFFECT, NON_EFFECT.index("mental_disorder"), format_func=label, key="ex_hr")
            c_ = c2.selectbox("Columns", [c for c in CAT if c != r_], [c for c in CAT if c != r_].index("music_genre"), format_func=label, key="ex_hc")
            ct = pd.crosstab(f[r_], f[c_]).reindex(index=order_for(r_, f), columns=order_for(c_, f))
            pc = ct.div(ct.sum(axis=1), axis=0) * 100
            pc.index = [f"{i} (n={ct.loc[i].sum()})" for i in pc.index]
            fig = px.imshow(pc, text_auto=".0f", aspect="auto", color_continuous_scale=[[0, "#26085f"], [.5, "#8a00c2"], [1, "#da8ee7"]],
                            labels=dict(x=label(c_), y=label(r_), color="% of row"))
            fig.update_xaxes(tickangle=-35)
            show(style(fig, 520, legend=False), key="ex_heat")
        elif kind == "Grouped bars (% within group)":
            c1, c2 = st.columns(2)
            g_ = c1.selectbox("Group (x axis)", NON_EFFECT, NON_EFFECT.index("mental_disorder"), format_func=label, key="ex_gg")
            h_ = c2.selectbox("Compare", [c for c in CAT if c != g_], [c for c in CAT if c != g_].index("music_effects"), format_func=label, key="ex_gh")
            ct = pd.crosstab(f[g_], f[h_]).reindex(index=order_for(g_, f), columns=order_for(h_, f), fill_value=0)
            pc = ct.div(ct.sum(axis=1), axis=0) * 100
            long = pc.reset_index().melt(id_vars=g_, var_name=h_, value_name="Percent")
            fig = px.bar(long, x=g_, y="Percent", color=h_, barmode="group", labels=NICE, color_discrete_sequence=PALETTE,
                         color_discrete_map=EFFECT_COLORS if h_ == "music_effects" else None)
            fig.update_xaxes(tickangle=-30)
            fig.update_yaxes(ticksuffix="%")
            show(style(fig, 480), key="ex_grouped")
            small = ct.sum(axis=1)[ct.sum(axis=1) < MIN_GROUP]
            if len(small):
                st.caption(":material/warning: Small groups (< 30 records): " + ", ".join(f"{i} (n={v})" for i, v in small.items()))
        else:
            corr = f[NUM].corr().round(2)
            fig = px.imshow(corr, text_auto=True, zmin=-1, zmax=1, color_continuous_scale=[[0, "#4c00b0"], [.5, "#e8bcf0"], [1, "#be2ed6"]],
                            x=[label(c) for c in corr.columns], y=[label(c) for c in corr.index])
            fig.update_traces(textfont=dict(color="#140534", size=16))
            show(style(fig, 440, legend=False), key="ex_corr")
            st.caption("Pearson correlation of the numeric variables in the current selection.")

    with st.container(border=True, key="glass_assoc"):
        card("Which variables are most associated with the reported effect?",
             "Cramér’s V for the current selection · 0 = none, 1 = perfect · association is not causation")
        v = pd.DataFrame({"Variable": [label(c) for c in NON_EFFECT], "V": [cramers_v(f[c], f.music_effects) for c in NON_EFFECT]}).dropna().sort_values("V")
        fig = px.bar(v, x="V", y="Variable", orientation="h", color_discrete_sequence=["#b44fe0"], labels={"V": "Cramér's V"})
        show(style(fig, 420, legend=False), key="ex_cramer")


# ============================================================================================ TAB: GENRE JUKEBOX
def pick_genre(g):
    st.session_state.genre = g
    st.session_state.jb_play = st.session_state.get("jb_play", 0) + 1     # new value -> the play script below re-mounts and runs once


def tab_jukebox():
    section("Genre Jukebox")
    cols = st.columns(6)
    for i, g in enumerate(GENRES):
        sel = g == st.session_state.genre
        with cols[i % 6]:
            button(g, key=f"{'tilesel' if sel else 'tile'}_{g}", on_click=pick_genre, args=(g,), icon=f":material/{GENRE_ICON.get(g, 'music_note')}:")
    g = st.session_state.genre
    if st.session_state.get("jb_play"):     # a tile was clicked: play that genre (the click counts as the user gesture browsers require)
        play_now(g, st.session_state.jb_play)
    bpm = GENRE_BPM[g]
    prof = genre_profile(f, g)
    left, right = st.columns([1.1, 1.4], gap="medium")
    with left:
        html(f'<div class="gcard"><div class="gcard-art" {playable(g)}>{cover(g)}</div><div><div class="gn">{g}</div>'
             f'<div class="tg">{sounds.GENRE_TAGLINE.get(g, "")} · {bpm:.0f} BPM</div></div></div>')
        live(mp.play_button_html(g, f"Play {g} loop"))
        st.caption("The loop is generated by code (see sounds.py): same recipe every time, tempo taken from the data. It is an original sketch, not a real recording.")
    with right:
        if prof is None:
            st.info(f"No **{g}** records match the current filters, so there are no stats to show. The loop still plays.")
        else:
            html(
                '<div class="statrow">'
                f'<div class="stat"><div class="l">Records</div><div class="v">{prof["n"]}</div></div>'
                f'<div class="stat"><div class="l">% Improve</div><div class="v">{prof["improve"]:.0f}%</div></div>'
                f'<div class="stat"><div class="l">% Worsen</div><div class="v">{prof["worsen"]:.0f}%</div></div>'
                f'<div class="stat"><div class="l">Avg hours</div><div class="v">{prof["hours"]:.1f}</div></div></div>'
                f'<div class="insight" style="margin-top:12px"><div class="ic">{icon("lightbulb", 20)}</div><div><div class="t">What the data says about ' + g + ' listeners</div><div class="p">'
                f'Median age {prof["age"]:.0f}; most often listened to <b>{prof["time"].lower()}</b> in a <b>{prof["setting"]}</b> setting; top reason: <i>{prof["vibe"]}</i>. '
                f'{prof["improve"]:.0f}% say it improves how they feel, {prof["noeff"]:.0f}% no effect, {prof["worsen"]:.0f}% worsen'
                + (f' (only {prof["n"]} records, so treat this cautiously).' if prof["n"] < MIN_GROUP else '.') + '</div></div></div>')
            c1, c2 = st.columns(2)
            with c1:
                x = f[f.music_genre == g]
                ec = x.music_effects.value_counts().reindex(EFFECTS).dropna().rename_axis("effect").reset_index(name="records")
                show(style(donut(ec), 250), key="jb_donut")
            with c2:
                sc = f[f.music_genre == g].listening_setting.value_counts().head(5).rename_axis("setting").reset_index(name="records")
                fig = px.bar(sc, x="records", y="setting", orientation="h", labels={"setting": "", "records": "Records"})
                fig.update_traces(marker_color="#c3a6e0")
                fig.update_layout(yaxis=dict(autorange="reversed"))
                show(style(fig, 250, legend=False), key="jb_settings")
    c1, c2 = st.columns(2)
    gstats = f.groupby("music_genre").agg(n=("age", "size"), improve=("music_effects", pct_improve)).reset_index()
    with c1:
        with st.container(border=True, key="glass_jb_bpm"):
            card("Tempo of each genre (median BPM in the data)", "This is the tempo the synthesised loops use")
            b = pd.DataFrame({"genre": list(GENRE_BPM), "bpm": list(GENRE_BPM.values())}).sort_values("bpm")
            fig = px.bar(b, x="bpm", y="genre", orientation="h", labels={"bpm": "Median BPM", "genre": ""})
            show(highlight(style(fig, 430, legend=False), b.genre, g), key="jb_bpm")
    with c2:
        with st.container(border=True, key="glass_jb_imp"):
            card("% of listeners who say it improves how they feel", "Current filters · pink = selected genre · genres with few records are noisy")
            gs = gstats.sort_values("improve")
            fig = px.bar(gs, x="improve", y="music_genre", orientation="h", hover_data=["n"], labels={"improve": "% Improve", "music_genre": ""})
            show(highlight(style(fig, 430, legend=False), gs.music_genre, g), key="jb_imp")


# ============================================================================================ TAB: GAME ZONE
# ---- Guess the Mood: an animated listener built from a real survey record; the player guesses the reported effect
GUESS_ROUNDS = 8
MOOD_ICON = {"Improve": "sentiment_very_satisfied", "No effect": "sentiment_neutral", "Worsen": "sentiment_dissatisfied"}
MOOD_LINE = {"Improve": "music improves {n}'s mood", "No effect": "music has no effect on {n}'s mood", "Worsen": "music makes {n} feel worse"}
MOOD_LINE_YOU = {"Improve": "music improves your mood", "No effect": "music has no effect on your mood", "Worsen": "music makes you feel worse"}
CLUES = [("schedule", lambda r: f"Listens <b>{r.hours_per_day:.1f} h</b> a day"),
         ("favorite", lambda r: f"Listens for <b>{r.vibe_reason.lower()}</b>"),
         ("psychology", lambda r: f"Mental-health group: <b>{r.mental_disorder}</b>"),
         ("explore", lambda r: "<b>Explores</b> new artists" if r.exploratory == "Yes" else "Sticks to <b>familiar</b> music")]


def new_round(gm):
    rng = random.Random()
    effect = rng.choice(EFFECTS)          # each effect equally likely, so always answering "Improve" is not a winning strategy
    gm.update(rec=int(rng.choice(list(df.index[df.music_effects == effect]))), seed=rng.randrange(10 ** 9), hints=0, answer=None, pts=0)


def start_guess():
    st.session_state.gm = dict(round=1, score=0, streak=0, best=0, history=[])
    new_round(st.session_state.gm)


def ask_clue():
    st.session_state.gm["hints"] += 1


def submit_guess(choice):
    gm = st.session_state.gm
    r = df.loc[gm["rec"]]
    ok = choice == r.music_effects
    pts = max(1, 3 - gm["hints"]) if ok else 0
    gm.update(answer=choice, pts=pts, score=gm["score"] + pts, streak=gm["streak"] + 1 if ok else 0)
    gm["best"] = max(gm["best"], gm["streak"])
    gm["history"].append(dict(name=scene.character_look(gm["seed"])["name"], genre=r.music_genre, guess=choice, truth=r.music_effects, pts=pts))


def next_round():
    gm = st.session_state.gm
    gm["round"] += 1
    if gm["round"] <= GUESS_ROUNDS:
        new_round(gm)


def hud(gm):
    dots = "".join(f'<i class="{"done" if j < gm["round"] else "now" if j == gm["round"] else ""}"></i>' for j in range(1, GUESS_ROUNDS + 1))
    html(f'<div class="hud"><div><div class="dots">{dots}</div><div class="qhead">Listener {min(gm["round"], GUESS_ROUNDS)} of {GUESS_ROUNDS}</div></div>'
         f'<div class="hud-chips"><span class="fchip">{icon("star", 16)} <b>{gm["score"]}</b> pts</span>'
         f'<span class="fchip{" hot" if gm["streak"] >= 2 else ""}">{icon("local_fire_department", 16)} streak <b>{gm["streak"]}</b></span></div></div>')


def game_guess():
    gm = st.session_state.get("gm")
    if gm is None:
        html(f'<div class="qtitle">{icon("theater_comedy", 32)}<span>Guess the Mood</span></div>'
             '<div class="qsub">Meet real listeners from the survey. Each one is listening to music somewhere, at some time of day. '
             'Read the scene, ask questions if you need them, and guess: does the music <b>improve</b> their mood, have <b>no effect</b>, or make it <b>worse</b>?</div>'
             '<div class="howto">'
             f'<div>{icon("visibility", 24)}<b>Read the scene</b><span>Setting, time of day, the genre playing and how fast they bob to the beat.</span></div>'
             f'<div>{icon("forum", 24)}<b>Ask questions</b><span>Each question reveals a clue but lowers the points for that round.</span></div>'
             f'<div>{icon("star", 24)}<b>Score</b><span>Up to 3 points per listener. Build a streak with correct guesses in a row.</span></div></div>')
        demo = scene.character_look(7)
        html(scene.scene_html("demo", demo, 21, "Home / relaxing", "Late night", GENRE_BPM.get("Lofi", 80)))
        button(f"Start the game · {GUESS_ROUNDS} listeners", key="cta_gm_start", on_click=start_guess, icon=":material/play_arrow:")
        return
    hud(gm)
    if gm["round"] > GUESS_ROUNDS:
        top = GUESS_ROUNDS * 3
        rank, ic = (("Mood Whisperer", "auto_awesome") if gm["score"] >= .7 * top else ("Good Listener", "headphones") if gm["score"] >= .45 * top
                    else ("Still Tuning In", "tune"))
        rows = "".join(f'<div class="hist-row"><span>{h["name"]}</span><span class="m">{h["genre"]}</span><span>{icon(MOOD_ICON[h["guess"]], 20)} {h["guess"]}</span>'
                       f'<span>{icon(MOOD_ICON[h["truth"]], 20)} {h["truth"]}</span><b class="{"ok" if h["pts"] else "no"}">{"+" + str(h["pts"]) if h["pts"] else "0"}</b></div>'
                       for h in gm["history"])
        html(f'<div class="reveal nail"><div class="eyebrow">FINAL SCORE</div><div class="scorebig">{gm["score"]} / {top}</div>'
             f'<div class="badge">{icon(ic, 16)} {rank}</div><div style="margin-top:10px">Best streak: <b>{gm["best"]}</b> in a row</div></div>'
             f'<div class="hist"><div class="hist-row head"><span>Listener</span><span>Genre</span><span>Your guess</span><span>Answer</span><span>Pts</span></div>{rows}</div>')
        if gm["score"] >= .7 * top and not gm.get("celebrated"):
            gm["celebrated"] = True
            st.balloons()
        button("Play again", key="cta_gm_again", on_click=start_guess, icon=":material/replay:")
        return

    r = df.loc[gm["rec"]]
    look = scene.character_look(gm["seed"])
    name, bpm = look["name"], GENRE_BPM[r.music_genre]
    answered = gm["answer"] is not None
    if not answered:   # start this listener's music in the player (re-runs only when a new listener appears)
        play_now(r.music_genre, gm["seed"])
    left, right = st.columns([1.7, 1], gap="medium")
    with left:
        html(scene.scene_html(gm["seed"], look, int(r.age), r.listening_setting, r.listening_time, bpm, r.music_effects if answered else None))
    with right:
        clues = "".join(f'<div class="clue">{icon(ic, 20)}<span>{fn(r)}</span></div>' for ic, fn in CLUES[:gm["hints"]])
        html(f'<div class="who"><div class="who-n">{name}<small>{int(r.age)} years old</small></div>'
             f'<div class="who-song"><span class="tl-cover">{cover(r.music_genre, label=False)}</span><div><small>Listening to</small><b>{r.music_genre}</b>'
             f'<small>{bpm:.0f} BPM</small></div></div>'
             f'<div class="clue">{icon(SETTING_ICON.get(r.listening_setting, "place"), 20)}<span>{r.listening_setting}</span></div>'
             f'<div class="clue">{icon(TIME_ICON.get(r.listening_time, "schedule"), 20)}<span>{r.listening_time}</span></div>{clues}</div>')
        live(mp.play_button_html(r.music_genre, f"Hear what {name} hears"))
        if gm["hints"] < len(CLUES) and not answered:
            button(f"Ask {name} a question  (−1 pt)", key="gm_ask", on_click=ask_clue, icon=":material/forum:")
    if not answered:
        html(f'<div class="ask"><span class="ask-q">How does this music affect <b>{name}</b>?</span>'
             f'<span class="ask-pts">{icon("star", 16)} {max(1, 3 - gm["hints"])} pts if you are right</span></div>')
        cols = st.columns(3)
        for col, eff in zip(cols, EFFECTS):
            with col:
                button(eff, key=f"guess_{eff.replace(' ', '_')}", on_click=submit_guess, args=(eff,), icon=f":material/{MOOD_ICON[eff]}:")
        return
    truth = r.music_effects
    same = df[(df.music_genre == r.music_genre) & (df.listening_time == r.listening_time)]
    share = (same.music_effects == truth).mean() * 100 if len(same) else 0
    ok = gm["pts"] > 0
    html(f'<div class="reveal {"nail" if ok else "shock"}"><div class="badge">{icon("check_circle" if ok else "cancel", 16)} '
         f'{"Spot on!  +" + str(gm["pts"]) if ok else "Not this time"}</div>'
         f'<div class="qtitle" style="margin-top:8px">{icon(MOOD_ICON[truth], 32)}<span>{MOOD_LINE[truth].format(n=name)}</span></div>'
         f'<div class="qsub" style="margin:0">In the data, <b>{share:.0f}%</b> of {r.music_genre} listeners who listen '
         f'{"late at night" if r.listening_time == "Late night" else "in the " + r.listening_time.lower()} '
         f'report the same ({len(same)} records).</div></div>')
    with st.container(key="sfx_box"):
        audio(sfx("win" if ok else "miss"), autoplay=True)
    last = gm["round"] >= GUESS_ROUNDS
    button("See my final score" if last else "Next listener", key="cta_gm_next", on_click=next_round,
           icon=":material/flag:" if last else ":material/arrow_forward:")


# ---- optional predictive model: categorical naive Bayes written in numpy/pandas (no extra libraries)
MODEL_FEATS = ["age_bin", "hours_bin", "music_genre", "listening_time", "listening_setting"]


def with_bins(d):
    d = d.copy()
    d["age_bin"] = pd.cut(d.age, [0, 17, 20, 24, 30, 45, 120], labels=["≤17", "18–20", "21–24", "25–30", "31–45", "46+"]).astype(str)
    d["hours_bin"] = pd.cut(d.hours_per_day, [0, 3, 4, 5, 6, 7, 24], labels=["≤3", "3–4", "4–5", "5–6", "6–7", "7+"]).astype(str)
    return d


@st.cache_resource
def train_model(data):
    d = with_bins(data)
    idx = np.random.default_rng(42).permutation(len(d))
    cut = int(.8 * len(d))
    tr, te = d.iloc[idx[:cut]], d.iloc[idx[cut:]]

    def fit(t):
        prior = t.music_effects.value_counts(normalize=True).reindex(EFFECTS).fillna(1e-6)
        like = {}
        for c in MODEL_FEATS:
            ct = pd.crosstab(t[c], t.music_effects).reindex(columns=EFFECTS, fill_value=0) + 1.0
            like[c] = ct.div(ct.sum(axis=0), axis=1)
        return prior, like

    def proba(model, row):
        prior, like = model
        lp = np.log(prior.values.astype(float))
        for c in MODEL_FEATS:
            tab = like[c]
            lp = lp + (np.log(tab.loc[row[c]].values) if row[c] in tab.index else 0)
        p = np.exp(lp - lp.max())
        return dict(zip(EFFECTS, p / p.sum()))

    model = fit(tr)
    pred = [max(proba(model, r), key=proba(model, r).get) for _, r in te.iterrows()]
    acc = float(np.mean(np.array(pred) == te.music_effects.values))
    base = float((te.music_effects == te.music_effects.mode().iloc[0]).mean())
    return fit(d), acc, base, proba, len(te)


# ---- Mind Reader: build your own listener, the scene updates live, then the model guesses what music does for them
MR_STYLES = ["Short", "Long", "Bun"]
MR_DEFAULTS = dict(mr_name="You", mr_age=21, mr_gender="Female", mr_skin=1, mr_hair=0, mr_style=0, mr_outfit="Hoodie", mr_shirt=0,
                   mr_genre="Lofi", mr_setting="Home / relaxing", mr_time="Late night", mr_hours=4.0)
GENDER_ICON = {"Female": "female", "Male": "male"}
MR_INPUTS = ["mr_age", "mr_hours", "mr_genre", "mr_time", "mr_setting"]          # what the model sees (the look is just for fun)


def mr_surprise():
    rng = random.Random()
    st.session_state.update(mr_age=rng.randint(A_MIN, 60), mr_gender=rng.choice(scene.GENDERS), mr_outfit=rng.choice(scene.OUTFITS),
                            mr_skin=rng.randrange(len(scene.SKIN)), mr_hair=rng.randrange(len(scene.HAIR)),
                            mr_style=rng.randrange(3), mr_shirt=rng.randrange(len(scene.SHIRT)), mr_genre=rng.choice(GENRES),
                            mr_setting=rng.choice(sorted(df.listening_setting.unique())), mr_time=rng.choice(order_for("listening_time", df)),
                            mr_hours=float(rng.choice(list(np.arange(H_MIN, H_MAX + STEP, STEP)))))
    mr_genre_changed()


def mr_genre_changed():
    st.session_state.mr_play = st.session_state.get("mr_play", 0) + 1      # new genre -> start it in the player


def mr_read():
    st.session_state.mr_result = {k: st.session_state[k] for k in MR_INPUTS}


SWATCH_NAMES = {"mr_skin": ["Light", "Fair", "Medium", "Tan", "Brown", "Deep"],
                "mr_hair": ["Dark brown", "Brown", "Chestnut", "Blonde", "Black", "Auburn"],
                "mr_shirt": ["Orchid", "Violet", "Lavender", "Magenta", "Indigo", "Pink"]}


def swatches(label, key, colors):
    """Colour picker: single-choice pills painted with the colours (the colours come from SWATCH_CSS, the selected one gets a ring).
    Each option needs its own label: Streamlit matches a clicked pill to its option by label, so identical blank labels made
    every click select the same swatch. The names are hidden by CSS but still read out by screen readers."""
    names = SWATCH_NAMES[key]
    st.pills(label, list(range(len(colors))), key=key, selection_mode="single", required=True, format_func=lambda i: names[i])


def mr_group(key, icon_name, title):
    """One labelled card inside the creator panel."""
    box = st.container(key=f"mrg_{key}")
    box.markdown(f'<div class="mr-group-h">{icon(icon_name, 20)}{title}</div>', unsafe_allow_html=True)
    return box


def game_mind():
    for k, v in MR_DEFAULTS.items():
        st.session_state.setdefault(k, v)
    if st.session_state.mr_gender not in scene.GENDERS:         # a session saved with an option that no longer exists
        st.session_state.mr_gender = MR_DEFAULTS["mr_gender"]
    s = st.session_state
    model, acc, base, proba, n_te = train_model(df)
    html(f'<div class="qtitle">{icon("auto_awesome", 32)}<span>The Mind Reader</span></div><div class="qsub">Create your listener, set the scene, and a '
         'small model trained on this survey (naive Bayes) will guess what music does for them. The scene changes as you go.</div>')
    # always render this slot (empty until a genre is picked): inserting it later shifts the layout and Streamlit then
    # rebuilds the tabs below, which jumped the panel back to "Your character"
    if s.get("mr_play"):
        play_now(s.mr_genre, s.mr_play)
    else:
        live('<span hidden></span>')
    look = dict(name=s.mr_name.strip() or "You", gender=s.mr_gender, outfit=s.mr_outfit, skin=scene.SKIN[s.mr_skin], hair=scene.HAIR[s.mr_hair],
                shirt=scene.SHIRT[s.mr_shirt], style=s.mr_style)
    res = s.get("mr_result")
    fresh = res is not None and all(res[k] == s[k] for k in MR_INPUTS)
    pr = None
    if fresh:
        row = with_bins(pd.DataFrame([dict(age=s.mr_age, hours_per_day=s.mr_hours, music_genre=s.mr_genre, listening_time=s.mr_time,
                                           listening_setting=s.mr_setting)])).iloc[0]
        pr = proba(model, row)
    best = max(pr, key=pr.get) if pr else None

    stage, panel = st.columns([1.6, 1], gap="medium")
    with stage:
        html(scene.scene_html("mr", look, int(s.mr_age), s.mr_setting, s.mr_time, GENRE_BPM[s.mr_genre], best))
        html(f'<div class="mr-caption"><b>{look["name"]}</b>, {s.mr_age} · listening to <b>{s.mr_genre}</b> ({GENRE_BPM[s.mr_genre]:.0f} BPM) · '
             f'{s.mr_setting.lower()} · {s.mr_time.lower()} · {s.mr_hours:g} h a day</div>')
        if res is not None and not fresh:
            html(f'<div class="mr-stale">{icon("refresh", 20)} You changed the listening details since the last reading. Read again to update it.</div>')
        button(f"Read {look['name']}'s mind" if look["name"] != "You" else "Read my mind", key="cta_mr_go", on_click=mr_read, icon=":material/auto_awesome:")
    with panel:
        look_tab, listen_tab = st.tabs([":material/face: Your character", ":material/headphones: Your listening"])
        with look_tab:
            with mr_group("who", "badge", "Who you are"):
                c1, c2 = st.columns([1.5, 1], vertical_alignment="bottom")
                c1.text_input("Name", key="mr_name", max_chars=14)
                c2.button("Surprise me", key="mr_surprise", on_click=mr_surprise, icon=":material/casino:", width="stretch")
                st.slider("Age", A_MIN, A_MAX, key="mr_age")
                st.pills("Gender", scene.GENDERS, key="mr_gender", selection_mode="single", required=True, format_func=with_icon(GENDER_ICON))
            with mr_group("look", "face", "Look"):
                swatches("Skin tone", "mr_skin", scene.SKIN)
                swatches("Hair colour", "mr_hair", scene.HAIR)
                st.pills("Hairstyle", list(range(3)), key="mr_style", selection_mode="single", required=True, format_func=lambda i: MR_STYLES[i])
            with mr_group("outfit", "checkroom", "Outfit"):
                st.pills("Clothing style", scene.OUTFITS, key="mr_outfit", selection_mode="single", required=True)
                swatches("Colour", "mr_shirt", scene.SHIRT)
        with listen_tab:
            with mr_group("music", "music_note", "Music"):
                st.selectbox("Favourite genre (it plays as you pick)", GENRES, key="mr_genre", on_change=mr_genre_changed)
                st.slider("Hours of music per day", H_MIN, H_MAX, step=STEP, key="mr_hours", format="%.2f")
            with mr_group("moment", "schedule", "Moment"):
                st.pills("When do you listen most?", order_for("listening_time", df), key="mr_time", selection_mode="single", required=True,
                         format_func=with_icon(TIME_ICON))
                st.selectbox("Where?", sorted(df.listening_setting.unique()), key="mr_setting")
    if not fresh:
        return

    like = df[(df.music_genre == s.mr_genre) & (df.age.between(s.mr_age - 5, s.mr_age + 5))]
    gp = genre_profile(df, s.mr_genre)
    twist = (f"{icon('bolt', 16)} Plot twist: only <b>{gp['improve']:.0f}%</b> of {s.mr_genre} listeners in this dataset say it improves how they feel."
             if gp and gp["improve"] < 30 else "")
    html(f'<div class="reveal {"shock" if best != "Improve" else "nail"}"><div class="eyebrow">I THINK MUSIC WILL…</div>'
         f'<div class="qtitle" style="justify-content:center">{icon(MOOD_ICON[best], 32)}<span>{MOOD_LINE_YOU[best] if look["name"] == "You" else MOOD_LINE[best].format(n=look["name"])}</span></div>'
         f'<div class="badge">{pr[best] * 100:.0f}% confident</div><div style="margin-top:10px">{twist}</div></div>')
    fig = px.bar(pd.DataFrame({"effect": list(pr), "p": [v * 100 for v in pr.values()]}), x="p", y="effect", orientation="h", color="effect",
                 color_discrete_map=EFFECT_COLORS, labels={"p": "Probability (%)", "effect": ""}, category_orders={"effect": EFFECTS})
    show(style(fig, 220, legend=False), key="mr_bar")
    if len(like) >= 5:
        st.caption(f"People like {look['name'] if look['name'] != 'You' else 'you'} ({s.mr_genre}, age {s.mr_age - 5}–{s.mr_age + 5}): {len(like)} records, "
                   f"{pct_improve(like.music_effects):.0f}% say it improves how they feel.")
    else:
        st.caption(f"Only {len(like)} {s.mr_genre} listeners are within 5 years of that age in the data, so there is no solid ‘people like you’ group.")
    verdict = ("It barely beats a lazy guess" if acc - base < 0.03 else "It beats a lazy guess")
    html(f'<div class="insight warn"><div class="ic">{icon("science", 20)}</div><div><div class="t">How good is this model, honestly?</div><div class="p">On {n_te} held-out records it is right '
         f'<b>{acc * 100:.0f}%</b> of the time; always answering “{EFFECTS[0]}” would be right <b>{base * 100:.0f}%</b>. {verdict}. '
         'It is a classroom demo, not advice.</div></div></div>')


def tab_game():
    section("Game Zone")
    games = {":material/theater_comedy: Guess the Mood": game_guess, ":material/auto_awesome: Mind Reader": game_mind}
    mode = st.radio("Pick a game", list(games), horizontal=True, key="game_mode", label_visibility="collapsed")
    with st.container(border=True, key="glass_game"):
        games[mode]()


# ============================================================================================ TAB: PLOT GALLERY (static plots exported from the notebook)
@st.cache_data
def load_manifest():
    p = PLOTS_DIR / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def tab_gallery():
    man = load_manifest()
    section("Plot Gallery")
    if not man:
        st.info("Copy the notebook's `plots/` folder (with manifest.json) next to app.py to see the static EDA plots here.")
        return
    c1, c2 = st.columns([1, 2])
    sec = c1.radio("Section", ["All", "Univariate", "Bivariate"], horizontal=True, key="gal_sec")
    pool = [m for m in man if sec == "All" or m["section"] == sec]
    groups = ["All plots"] + list(dict.fromkeys(m["group"] for m in pool))
    grp = c2.selectbox("Variable / relationship", groups, key="gal_grp")
    if grp != "All plots":
        pool = [m for m in pool if m["group"] == grp]
    per = 6
    pages = max(1, -(-len(pool) // per))
    page = st.columns([1, 4])[0].number_input("Page", 1, pages, 1, key="gal_page") if pages > 1 else 1
    st.caption(f"{len(pool)} plots · page {page} of {pages}")
    chunk = pool[(page - 1) * per: page * per]
    for i in range(0, len(chunk), 2):
        cols = st.columns(2)
        for col, m in zip(cols, chunk[i:i + 2]):
            with col, st.container(border=True, key=f"glass_gal_{m['file']}"):
                title = m["what"].split(". ")[0].replace("Feature: ", "").replace("Relationship: ", "") if m["what"] else m["title"]
                card(title, m["group"])
                st.image(str(PLOTS_DIR / m["file"]))
                with st.expander("Read the insight"):
                    st.markdown(f"**Observation.** {m['observation']}\n\n**Interpretation.** {m['interpretation']}")


# ============================================================================================ TAB: DATA
DICTIONARY = {
    "age": "Respondent age in years", "primary_streaming_service": "Main streaming service used", "hours_per_day": "Hours of music per day",
    "listening_time": "Time of day listened most", "listening_setting": "Where the person usually listens", "instrumentalist": "Plays an instrument (Yes/No)",
    "composer": "Composes music (Yes/No)", "exploratory": "Explores new artists/genres (Yes/No)", "foreign_languages": "Listens to foreign-language music (Yes/No)",
    "bpm": "Tempo of favourite music (beats per minute)", "music_effects": "Reported effect: Improve / No effect / Worsen",
    "mental_disorder": "Mental-health group label", "music_genre": "Favourite genre", "vibe_reason": "Main reason for the music",
    "repeats_songs_often": "Repeats songs often (Yes/No)",
}


def tab_data():
    section("Data preview")
    try:
        st.dataframe(f.head(100), width="stretch", hide_index=True)
    except TypeError:
        st.dataframe(f.head(100), use_container_width=True, hide_index=True)
    section("Summary statistics")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Numeric variables**")
        st.dataframe(f[NUM].describe().T.round(2))
    with c2:
        st.markdown("**Categorical variables**")
        cs = pd.DataFrame({"unique values": f[CAT].nunique(), "most common": f[CAT].agg(lambda x: x.mode().iloc[0]),
                           "share of top value": f[CAT].agg(lambda x: f"{x.value_counts(normalize=True).iloc[0]:.0%}")})
        cs.index = [label(i) for i in cs.index]
        st.dataframe(cs)
    section("Data dictionary")
    dd = pd.DataFrame({"column": df.columns, "type": [str(t) for t in df.dtypes], "meaning": [DICTIONARY.get(c, "") for c in df.columns],
                       "example": [str(df[c].iloc[0]) for c in df.columns]})
    try:
        st.dataframe(dd, width="stretch", hide_index=True)
    except TypeError:
        st.dataframe(dd, use_container_width=True, hide_index=True)


# ============================================================================================ TAB: INSIGHTS
def tab_insights():
    section("Insights for the current selection")
    cols = st.columns(2)
    for i, (ic, t, p) in enumerate(build_insights(f)):
        with cols[i % 2]:
            html(f'<div class="insight"><div class="ic">{icon(ic, 20)}</div><div><div class="t">{t}</div><div class="p">{p}</div></div></div>')
    oc = outlier_counts(f)
    parts = ", ".join(f"<b>{label(c)}</b>: {v[0]} (fences {v[1]:.1f} to {v[2]:.1f})" for c, v in oc.items())
    html(f'<div class="insight"><div class="ic">{icon("search", 20)}</div><div><div class="t">Outliers (IQR rule)</div><div class="p">{parts}. '
         'Flagged values are unusual for this sample, not automatically wrong: the sample is young, so older ages show up as outliers.</div></div></div>')

    section("How to read these patterns")
    html(
        f'<div class="insight"><div class="ic">{icon("balance", 20)}</div><div><div class="t">Limitations</div><div class="p">Reported effects are self-reported and descriptive (association, not causation). '
        'The sample skews young (median age 21) and several groups are small (fewer than 30 records), so their percentages are unstable.</div></div></div>'
        f'<div class="insight"><div class="ic">{icon("rocket_launch", 20)}</div><div><div class="t">Recommendations for future analysis</div><div class="p">Repeat the analysis on the original, fully documented survey data; '
        'collect more responses for small genres and groups; and if a predictive model is needed, use stratified cross-validation and report per-class metrics.</div></div></div>'
    )


# ============================================================================================ layout: player dock + tabs
# the dock is drawn before the tabs and its HTML never changes, so Streamlit keeps it (and the audio) alive across reruns
with st.container(key="loopbank"):      # hidden: gives the player a second URL per loop (see M.backup in player.py)
    for slug, data in loop_bytes().items():
        with st.container(key=f"loop_{slug}"):
            st.audio(data, format="audio/wav")
live(mp.dock_html(TRACKS))


tabs = st.tabs([":material/home: Home", ":material/bar_chart: Top Charts", ":material/album: Genre Jukebox", ":material/sports_esports: Game Zone",
                ":material/photo_library: Plot Gallery", ":material/table_chart: Data", ":material/lightbulb: Insights"])
for tab, render, needs_rows in zip(tabs, (tab_home, tab_charts, tab_jukebox, tab_game, tab_gallery, tab_data, tab_insights),
                                   (True, True, True, False, False, True, True)):
    with tab:                      # a plain if-statement: a bare `a() if x else b()` expression gets echoed as "None" by Streamlit magic
        if needs_rows and f.empty:
            need_data()
        else:
            render()
