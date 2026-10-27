"""Animated listener scene for the "Guess the Mood" game.

One SVG per round, built from a real survey record: the background is the record's listening setting, the sky is its
time of day, the character's head bobs at the genre's real median BPM, and after the guess the character's face shows the
reported effect (smile + sparkles, flat + "...", frown + rain cloud). All motion is CSS (classes in style.css), so it is
rendered with st.markdown and needs no JavaScript.
"""
import html
import random

SKIN = ["#f6d2b8", "#e8b896", "#c98d68", "#a8714e", "#7a4e33", "#5a3825"]
HAIR = ["#2b1d14", "#4a3020", "#7a4a26", "#c8a165", "#1c1c24", "#8a3b2a"]
SHIRT = ["#b44fe0", "#7600bc", "#c3a6e0", "#a000c8", "#4c00b0", "#e2b6f4"]
GENDERS = ["Female", "Male"]
OUTFITS = ["T-shirt", "Hoodie", "Jacket", "Suit", "Sweater", "Dress"]
NAMES = {"Female": ["Maya", "Noor", "Lina", "Zoe", "Mina", "Sara", "Elif", "Hana", "Ivy", "Layla"],
         "Male": ["Leo", "Omar", "Ravi", "Theo", "Yusuf", "Nico", "Dev", "Adam", "Karim"]}

# sky (top, bottom) and whether the sun/moon is up, per time of day
SKY = {"Morning": ("#f4c99a", "#e2b6f4", "sunrise"), "Afternoon": ("#8f4fe8", "#e2b6f4", "sun"),
       "Evening": ("#4c00b0", "#e9a98f", "sunset"), "Late night": ("#0b0320", "#34128a", "moon")}
INDOOR = {"Home / relaxing", "Work / study", "While gaming", "Gym / exercising"}


def character_look(seed):
    rng = random.Random(seed)
    gender = rng.choice(GENDERS)
    outfit = rng.choice([o for o in OUTFITS if o != "Dress"] + (["Dress"] if gender != "Male" else []))
    return dict(name=rng.choice(NAMES[gender]), gender=gender, outfit=outfit, skin=rng.choice(SKIN), hair=rng.choice(HAIR),
                shirt=rng.choice(SHIRT), style=rng.randrange(3))


def _shade(hex_color, k=.72):
    """Darker version of a colour, for lapels, hoods, pockets and stripes."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))


def _sky(uid, time):
    top, bottom, body = SKY.get(time, SKY["Afternoon"])
    out = [f'<defs><linearGradient id="sky{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/>'
           f'</linearGradient></defs><rect width="800" height="360" fill="url(#sky{uid})"/>']
    if body == "moon":
        out.append("".join(f'<circle class="twinkle" style="animation-delay:{i * .37:.2f}s" cx="{x}" cy="{y}" r="{r}" fill="#f6c4fb"/>'
                           for i, (x, y, r) in enumerate([(60, 40, 1.6), (150, 90, 1.2), (240, 30, 1.8), (430, 60, 1.3), (610, 35, 1.7),
                                                          (700, 95, 1.2), (760, 50, 1.5), (520, 110, 1.1), (90, 130, 1.3)])))
        out.append('<circle cx="660" cy="75" r="30" fill="#f6c4fb"/><circle cx="676" cy="66" r="27" fill="#34128a" opacity=".9"/>')
    else:
        x, y, c = {"sunrise": (140, 150, "#ffd8a8"), "sun": (640, 70, "#fff3c4"), "sunset": (712, 160, "#f6b08a")}[body]
        out.append(f'<circle class="glow" cx="{x}" cy="{y}" r="34" fill="{c}"/>')
        out.append('<g class="cloud-drift" opacity=".8"><ellipse cx="300" cy="70" rx="46" ry="14" fill="#f6c4fb"/><ellipse cx="325" cy="60" rx="26" ry="14" fill="#f6c4fb"/></g>')
    return "".join(out)


def _setting(setting):
    """Props behind the character (and a few in front, returned separately)."""
    back, front = [], []
    if setting in INDOOR:
        # wall with a window cut-out: the sky above shows through the window
        back.append('<path fill-rule="evenodd" fill="#25095e" d="M0 0H800V360H0Z M500 40H740V200H500Z"/>'
                    '<rect x="500" y="40" width="240" height="160" fill="none" stroke="#c3a6e0" stroke-width="6"/>'
                    '<path d="M620 40V200M500 120H740" stroke="#c3a6e0" stroke-width="4"/>'
                    '<rect x="0" y="300" width="800" height="60" fill="#1a0845"/>')
    if setting == "Home / relaxing":
        back.append('<rect x="170" y="215" width="320" height="95" rx="26" fill="#4c00b0"/><rect x="150" y="235" width="44" height="80" rx="18" fill="#7600bc"/>'
                    '<rect x="466" y="235" width="44" height="80" rx="18" fill="#7600bc"/>'
                    '<path d="M110 300V160" stroke="#c3a6e0" stroke-width="5"/><path d="M85 165h50l-12-38h-26z" fill="#f6c4fb" class="glow"/>'
                    '<rect x="620" y="250" width="34" height="50" rx="6" fill="#7600bc"/><circle cx="637" cy="236" r="26" fill="#a000c8"/>')
    elif setting == "Work / study":
        front.append('<rect x="180" y="270" width="380" height="16" rx="4" fill="#c3a6e0"/><path d="M200 286V360M540 286V360" stroke="#c3a6e0" stroke-width="10"/>'
                     '<rect x="410" y="214" width="96" height="58" rx="5" fill="#34128a" stroke="#e2b6f4" stroke-width="4"/><rect x="396" y="268" width="124" height="6" rx="3" fill="#e2b6f4"/>'
                     '<rect x="210" y="246" width="70" height="12" fill="#b44fe0"/><rect x="216" y="234" width="62" height="12" fill="#f6c4fb"/><rect x="212" y="222" width="58" height="12" fill="#a000c8"/>')
    elif setting == "While gaming":
        back.append('<rect x="440" y="150" width="200" height="120" rx="8" fill="#0b0320" stroke="#c3a6e0" stroke-width="5"/>'
                    '<rect class="screen" x="450" y="160" width="180" height="100" rx="4" fill="#a000c8"/><path d="M540 270V300" stroke="#c3a6e0" stroke-width="8"/>')
        front.append('<g transform="translate(298 262)"><rect width="64" height="30" rx="14" fill="#140534"/><circle cx="16" cy="15" r="4" fill="#c3a6e0"/>'
                     '<circle cx="48" cy="12" r="3" fill="#ff8ad8"/><circle cx="54" cy="19" r="3" fill="#f6c4fb"/></g>')
    elif setting == "Gym / exercising":
        back.append('<rect x="520" y="230" width="190" height="10" fill="#c3a6e0"/><path d="M540 240V300M690 240V300" stroke="#c3a6e0" stroke-width="8"/>'
                    + "".join(f'<rect x="{548 + k * 34}" y="212" width="22" height="18" rx="4" fill="#a000c8"/>' for k in range(5))
                    + '<rect x="120" y="300" width="300" height="10" rx="5" fill="#7600bc"/>')
        front.append('<g class="lift"><rect x="236" y="196" width="40" height="8" rx="4" fill="#e2b6f4"/><rect x="228" y="186" width="12" height="28" rx="3" fill="#b44fe0"/>'
                     '<rect x="272" y="186" width="12" height="28" rx="3" fill="#b44fe0"/></g>')
    elif setting == "Public / Private Transport":
        back.append('<rect width="800" height="360" fill="#25095e"/>'
                    + "".join(f'<rect x="{30 + k * 190}" y="40" width="160" height="120" rx="14" fill="#e2b6f4" opacity=".22"/>' for k in range(4))
                    + '<g class="pass">' + "".join(f'<g transform="translate({k * 230} 0)"><circle cx="60" cy="120" r="26" fill="#7600bc" opacity=".7"/>'
                                                   f'<rect x="56" y="130" width="8" height="30" fill="#4c00b0" opacity=".7"/></g>' for k in range(8)) + '</g>'
                    + '<path d="M150 0V360" stroke="#c3a6e0" stroke-width="10"/><rect x="0" y="300" width="800" height="60" fill="#1a0845"/>'
                    + '<rect x="200" y="230" width="260" height="80" rx="16" fill="#7600bc"/>')
    elif setting == "Car / commuting":
        back.append('<rect x="0" y="230" width="800" height="130" fill="#34128a"/><path class="road" d="M400 240V360" stroke="#f6c4fb" stroke-width="6" stroke-dasharray="22 22"/>')
        front.append('<path d="M0 285Q400 230 800 285V360H0Z" fill="#0b0320"/><circle cx="210" cy="300" r="46" fill="none" stroke="#c3a6e0" stroke-width="10"/>'
                     '<path d="M164 300H256M210 300V346" stroke="#c3a6e0" stroke-width="6"/>')
    elif setting == "Social / with friends":
        back.append('<rect x="0" y="300" width="800" height="60" fill="#1a0845"/><path d="M0 60Q200 110 400 60T800 60" fill="none" stroke="#c3a6e0" stroke-width="2"/>'
                    + "".join(f'<circle class="twinkle" style="animation-delay:{k * .25:.2f}s" cx="{40 + k * 80}" cy="{70 + (12 if k % 2 else 0)}" r="7" fill="{["#f6c4fb", "#ff8ad8", "#e2b6f4"][k % 3]}"/>' for k in range(10))
                    + "".join(f'<g class="bob" style="animation-delay:-{d}s"><circle cx="{x}" cy="190" r="30" fill="#34128a"/><rect x="{x - 45}" y="225" width="90" height="90" rx="30" fill="#34128a"/></g>'
                              for x, d in ((530, .2), (640, .45))))
    else:  # Anywhere / varies, Other: a park
        back.append('<rect x="0" y="290" width="800" height="70" fill="#4c00b0"/>'
                    + "".join(f'<rect x="{x - 6}" y="210" width="12" height="90" fill="#25095e"/><circle cx="{x}" cy="195" r="{r}" fill="#7600bc"/>' for x, r in ((560, 48), (680, 40), (90, 44)))
                    + '<rect x="180" y="262" width="300" height="12" rx="4" fill="#c3a6e0"/><path d="M200 274V310M460 274V310" stroke="#c3a6e0" stroke-width="8"/>')
    return "".join(back), "".join(front)


def _face(mood):
    if mood == "Improve":
        return ('<path d="M309 150q7-8 14 0M337 150q7-8 14 0" stroke="#140534" stroke-width="4" fill="none" stroke-linecap="round"/>'
                '<path d="M314 168q16 18 32 0" stroke="#140534" stroke-width="4" fill="#fff" stroke-linecap="round"/>'
                '<circle cx="306" cy="163" r="6" fill="#ff7ccb" opacity=".6"/><circle cx="354" cy="163" r="6" fill="#ff7ccb" opacity=".6"/>')
    if mood == "No effect":
        return ('<circle cx="316" cy="150" r="4" fill="#140534"/><circle cx="344" cy="150" r="4" fill="#140534"/>'
                '<path d="M318 172h24" stroke="#140534" stroke-width="4" stroke-linecap="round"/>')
    if mood == "Worsen":
        return ('<path d="M308 140l14 5M352 140l-14 5" stroke="#140534" stroke-width="3" stroke-linecap="round"/>'
                '<circle cx="316" cy="152" r="4" fill="#140534"/><circle cx="344" cy="152" r="4" fill="#140534"/>'
                '<path d="M316 178q14-12 28 0" stroke="#140534" stroke-width="4" fill="none" stroke-linecap="round"/>')
    # still listening: eyes closed, small content smile
    return ('<path d="M309 152q7 6 14 0M337 152q7 6 14 0" stroke="#140534" stroke-width="4" fill="none" stroke-linecap="round"/>'
            '<path d="M320 170q10 6 20 0" stroke="#140534" stroke-width="4" fill="none" stroke-linecap="round"/>')


# torso outline per gender: (left x, width, corner radius)
BODY = {"Female": (272, 116, 46), "Male": (252, 156, 40)}


def _outfit(uid, look):
    """Torso + clothing. Everything is drawn inside the torso outline so every outfit fits every body."""
    x, w, rx = BODY.get(look.get("gender"), BODY["Female"])
    c, dark, light = look["shirt"], _shade(look["shirt"]), "#f6c4fb"
    outfit = look.get("outfit", "T-shirt")
    cx, top, bottom = 330, 200, 340
    if outfit == "Dress":      # flared silhouette instead of the rounded torso
        return (f'<path d="M{x + 12} {top + 8}Q{cx} {top - 6} {x + w - 12} {top + 8}L{x + w + 26} {bottom}H{x - 26}Z" fill="{c}"/>'
                f'<rect x="{x + 8}" y="268" width="{w - 16}" height="9" rx="4" fill="{dark}"/>'
                f'<path d="M318 203q12 12 24 0" stroke="{dark}" stroke-width="4" fill="none"/>')
    out = [f'<clipPath id="torso{uid}"><rect x="{x}" y="{top}" width="{w}" height="{bottom - top}" rx="{rx}"/></clipPath>',
           f'<rect x="{x}" y="{top}" width="{w}" height="{bottom - top}" rx="{rx}" fill="{c}"/>', f'<g clip-path="url(#torso{uid})">']
    if outfit == "T-shirt":
        out.append(f'<path d="M316 201q14 14 28 0" stroke="{dark}" stroke-width="5" fill="none"/>')
    elif outfit == "Hoodie":
        out.append(f'<ellipse cx="{cx}" cy="{top + 4}" rx="44" ry="16" fill="{dark}"/>'
                   f'<path d="M322 212v34M338 212v34" stroke="{light}" stroke-width="3" stroke-linecap="round"/>'
                   f'<rect x="298" y="282" width="64" height="34" rx="12" fill="{dark}"/>')
    elif outfit == "Jacket":
        out.append(f'<rect x="314" y="{top}" width="32" height="{bottom - top}" fill="{light}"/>'
                   f'<path d="M314 {top}L300 250L314 {bottom}M346 {top}L360 250L346 {bottom}" stroke="{dark}" stroke-width="8" fill="none"/>'
                   f'<circle cx="352" cy="282" r="3" fill="{dark}"/><circle cx="352" cy="304" r="3" fill="{dark}"/>')
    elif outfit == "Suit":
        out.append(f'<path d="M312 {top}L{cx} 262L348 {top}Z" fill="#ffffff"/>'
                   f'<path d="M{cx} 206l-7 8 5 44h4l5-44z" fill="#b44fe0"/>'
                   f'<path d="M312 {top}L300 246L{cx} 262M348 {top}L360 246L{cx} 262" stroke="{dark}" stroke-width="7" fill="none"/>')
    elif outfit == "Sweater":
        out.append("".join(f'<rect x="{x}" y="{y}" width="{w}" height="12" fill="{dark}"/>' for y in (232, 262, 292, 322))
                   + f'<rect x="306" y="{top - 2}" width="48" height="12" rx="6" fill="{dark}"/>')
    out.append("</g>")
    return "".join(out)


def _details(gender, mood):
    """Small gender cues on the face: lashes + earrings, or a fuller brow + stubble."""
    if gender == "Female":
        return ('<path d="M305 146l-5-4M355 146l5-4" stroke="#140534" stroke-width="3" stroke-linecap="round"/>'
                '<circle cx="286" cy="176" r="4" fill="#ffd8a8"/><circle cx="374" cy="176" r="4" fill="#ffd8a8"/>')
    if gender == "Male":
        brows = "" if mood == "Worsen" else '<path d="M307 138q9-5 18 0M335 138q9-5 18 0" stroke="#140534" stroke-width="4" fill="none" stroke-linecap="round"/>'
        return brows + '<path d="M300 168q30 32 60 0" stroke="#140534" stroke-width="10" fill="none" opacity=".12" stroke-linecap="round"/>'
    return ""


def _character(uid, look, age, mood):
    hair = "#b8c4cf" if age >= 55 else look["hair"]
    styles = ['<path d="M288 150a42 42 0 0 1 84 0q-12-22-42-22t-42 22z" fill="{h}"/>',                                  # short
              '<path d="M288 150a42 42 0 0 1 84 0q-12-22-42-22t-42 22z" fill="{h}"/><rect x="284" y="140" width="14" height="70" rx="7" fill="{h}"/>'
              '<rect x="362" y="140" width="14" height="70" rx="7" fill="{h}"/>',                                       # long
              '<path d="M288 150a42 42 0 0 1 84 0q-12-22-42-22t-42 22z" fill="{h}"/><circle cx="330" cy="98" r="16" fill="{h}"/>']   # bun
    glasses = ('<g stroke="#140534" stroke-width="3" fill="none"><circle cx="316" cy="151" r="10"/><circle cx="344" cy="151" r="10"/>'
               '<path d="M326 151h8"/></g>') if age >= 45 else ""
    return (f'<g class="bob">' + _outfit(uid, look) +
            f'<rect x="318" y="182" width="24" height="26" fill="{look["skin"]}"/>'
            f'<circle cx="330" cy="150" r="42" fill="{look["skin"]}"/>'
            + styles[look["style"]].format(h=hair) + _face(mood) + _details(look.get("gender"), mood) + glasses +
            '<path d="M286 150a44 44 0 0 1 88 0" stroke="#b44fe0" stroke-width="8" fill="none"/>'
            '<rect x="276" y="136" width="16" height="34" rx="7" fill="#f6c4fb"/><rect x="368" y="136" width="16" height="34" rx="7" fill="#f6c4fb"/>'
            '</g>')


def _mood_fx(mood):
    if mood == "Improve":
        # the animated path sits inside a positioned <g>: a CSS transform would override a transform attribute on the path itself
        return "".join(f'<g transform="translate({x} {y})"><path class="sparkle" style="animation-delay:{i * .3:.1f}s" d="M0-10L3-3 10 0 3 3 0 10-3 3-10 0-3-3Z" fill="#fff3c4"/></g>'
                       for i, (x, y) in enumerate([(250, 110), (410, 100), (240, 190), (425, 180)]))
    if mood == "No effect":
        return ('<g class="think">' + "".join(f'<circle cx="{392 + k * 16}" cy="{108 - k * 10}" r="{4 + k * 2}" fill="#f6c4fb"/>' for k in range(3))
                + '<text x="440" y="70" font-size="26" font-weight="800" fill="#f6c4fb">…</text></g>')
    if mood == "Worsen":
        return ('<g class="raincloud"><ellipse cx="330" cy="70" rx="58" ry="20" fill="#6b5a86"/><ellipse cx="305" cy="58" rx="30" ry="18" fill="#6b5a86"/>'
                '<ellipse cx="352" cy="56" rx="26" ry="16" fill="#6b5a86"/>'
                + "".join(f'<path class="drop" style="animation-delay:{k * .18:.2f}s" d="M{290 + k * 18} 92v12" stroke="#c3a6e0" stroke-width="3" stroke-linecap="round"/>' for k in range(5))
                + '</g>')
    return ""


def scene_html(uid, look, age, setting, time, bpm, mood=None):
    """Full scene. `mood` None = still listening (before the guess); otherwise the reported effect."""
    beat = 60.0 / max(bpm, 40)
    back, front = _setting(setting)
    notes = "".join(f'<text class="note" style="animation-delay:{k * beat * 2:.2f}s" x="{392 + k * 22}" y="150" font-size="{22 + k * 4}" fill="#f6c4fb">♪</text>'
                    for k in range(3))
    svg = (f'<svg viewBox="0 0 800 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(look["name"])} listening to music">'
           f'{_sky(uid, time)}{back}{_character(uid, look, age, mood or "listening")}{front}{notes}{_mood_fx(mood)}</svg>')
    return f'<div class="scene{" revealed" if mood else ""}" style="--beat:{beat:.2f}s">{svg}</div>'
