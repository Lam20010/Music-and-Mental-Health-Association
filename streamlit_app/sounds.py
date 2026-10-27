"""Tiny numpy synthesiser used by the Streamlit dashboard.

Every music genre in the dataset gets a short, original loop. The TEMPO of each loop is the real median BPM of that
genre in the project data, so the sound is connected to the analysis. No audio files are needed: the loops are rendered
on the fly (and cached by Streamlit) as 16-bit mono WAV bytes.
"""
import io
import wave

import numpy as np
from scipy.signal import lfilter

SR = 22050
_RNG_SEED = 7

# ----------------------------------------------------------------------------------------------------- building blocks
CHORDS = {
    "maj": [0, 4, 7], "min": [0, 3, 7], "maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10], "dom7": [0, 4, 7, 10],
    "min9": [0, 3, 7, 10, 14], "maj9": [0, 4, 7, 11, 14], "pow": [0, 7, 12], "sus": [0, 5, 7], "dim": [0, 3, 6],
}
SCALES = {
    "minor": [0, 3, 5, 7, 10, 12, 15, 17, 19, 22], "major": [0, 2, 4, 7, 9, 12, 14, 16, 19, 21],
    "blues": [0, 3, 5, 6, 7, 10, 12, 15, 17, 18], "dorian": [0, 2, 3, 7, 9, 12, 14, 15, 19, 21],
}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def _t(n):
    return np.arange(n) / SR


def _adsr(n, a=0.005, tau=0.3, r=0.03):
    t = _t(n)
    env = np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t / max(tau, 1e-3))
    rl = int(r * SR)
    if 0 < rl < n:
        env[-rl:] *= np.linspace(1, 0, rl)
    return env


def _additive(f, n, amps, detune=0.0):
    t = _t(n)
    out = np.zeros(n)
    for k, a in enumerate(amps, start=1):
        if f * k * (1 + detune) < SR / 2 - 500:
            out += a * np.sin(2 * np.pi * f * k * (1 + detune) * t)
    return out


def pluck(f, dur, tau=0.35, bright=1.0):
    n = int(dur * SR)
    amps = [1.0, 0.6 * bright, 0.4 * bright, 0.25 * bright, 0.15 * bright, 0.1 * bright]
    return _additive(f, n, amps) * _adsr(n, 0.003, tau)


def piano(f, dur):
    n = int(dur * SR)
    t = _t(n)
    out = np.zeros(n)
    for k, a in enumerate([1.0, 0.55, 0.3, 0.2, 0.12, 0.07], start=1):
        if f * k < SR / 2 - 500:
            out += a * np.sin(2 * np.pi * f * k * t) * np.exp(-t / (0.9 / (0.6 + 0.5 * k)))
    out *= np.minimum(1, t / 0.004)
    rl = int(0.05 * SR)
    if rl < n:
        out[-rl:] *= np.linspace(1, 0, rl)
    return out


def rhodes(f, dur):
    n = int(dur * SR)
    t = _t(n)
    bell = 0.25 * np.sin(2 * np.pi * f * 7 * t) * np.exp(-t / 0.05)
    body = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t)
    trem = 1 + 0.12 * np.sin(2 * np.pi * 5 * t)
    return (body * np.exp(-t / 0.9) + bell) * trem * np.minimum(1, t / 0.004)


def saw(f, dur, harmonics=14, tau=None, a=0.01, r=0.04):
    n = int(dur * SR)
    out = _additive(f, n, [1.0 / k for k in range(1, harmonics + 1)])
    env = _adsr(n, a, tau if tau else 1e6, r)
    return out * env


def square(f, dur, tau=None):
    n = int(dur * SR)
    amps = [1.0 / k if k % 2 else 0 for k in range(1, 16)]
    return _additive(f, n, amps) * _adsr(n, 0.004, tau if tau else 1e6, 0.02)


def pad(f, dur, a=0.35, r=0.5):
    n = int(dur * SR)
    t = _t(n)
    vib = 1 + 0.002 * np.sin(2 * np.pi * 4.5 * t)
    sig = np.zeros(n)
    for d in (-0.006, 0.0, 0.006):
        sig += _additive(f * 1.0, n, [1.0 / k ** 1.2 for k in range(1, 9)], detune=d) * vib
    env = np.minimum(1, t / a)
    rl = int(r * SR)
    if rl < n:
        env[-rl:] *= np.linspace(1, 0, rl)
    return sig * env / 3


def strings(f, dur):
    return pad(f, dur, a=0.25, r=0.35) * 1.3 + pad(f * 2, dur, a=0.4, r=0.35) * 0.5


def bass(f, dur, tau=0.35):
    n = int(dur * SR)
    t = _t(n)
    sig = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2 * t)
    return np.tanh(sig * 1.4) * _adsr(n, 0.004, tau, 0.03)


def sub808(f, dur):
    n = int(dur * SR)
    t = _t(n)
    sweep = f * (1 + 1.2 * np.exp(-t / 0.04))
    ph = 2 * np.pi * np.cumsum(sweep) / SR
    return np.tanh(np.sin(ph) * 1.6) * np.exp(-t / (dur * 0.6 + 0.05)) * np.minimum(1, t / 0.003)


def dist_chord(freqs, dur, drive=6.0, mute=False):
    n = int(dur * SR)
    sig = np.zeros(n)
    for f in freqs:
        sig += _additive(f, n, [1.0 / k for k in range(1, 10)])
    sig = np.tanh(sig * drive / max(1, len(freqs)))
    env = _adsr(n, 0.003, 0.09 if mute else 0.6, 0.02)
    return sig * env


def kick(depth=1.0):
    n = int(0.35 * SR)
    t = _t(n)
    f = 45 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.12) * depth + 0.25 * np.exp(-t / 0.004) * np.sin(2 * np.pi * 1800 * t)


def snare(rng, tone=190, amount=1.0):
    n = int(0.25 * SR)
    t = _t(n)
    noise = rng.standard_normal(n)
    noise = lfilter([1, -0.6], [1], noise)
    return amount * (0.7 * noise * np.exp(-t / 0.07) + 0.5 * np.sin(2 * np.pi * tone * t) * np.exp(-t / 0.05))


def clap(rng):
    n = int(0.25 * SR)
    t = _t(n)
    noise = lfilter([1, -0.5], [1], rng.standard_normal(n))
    env = np.exp(-t / 0.08)
    for k in (0.0, 0.012, 0.024):
        env += 0.8 * np.exp(-np.clip(t - k, 0, None) / 0.012) * (t >= k)
    return noise * env * 0.4


def hat(rng, open_=False, amount=0.4):
    n = int((0.22 if open_ else 0.06) * SR)
    t = _t(n)
    noise = np.diff(rng.standard_normal(n + 1))
    return amount * noise * np.exp(-t / (0.09 if open_ else 0.018))


def tom(f=80, depth=1.0):
    n = int(0.9 * SR)
    t = _t(n)
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.5 * np.exp(-t / 0.08))) / SR
    return np.sin(ph) * np.exp(-t / 0.35) * depth


def _place(buf, sig, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf) or i < 0:
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def _reverb(x, mix=0.25):
    out = x.copy()
    for d, g in ((0.0297, 0.70), (0.0371, 0.68), (0.0411, 0.66), (0.0437, 0.64)):
        dl = int(d * SR)
        a = np.zeros(dl + 1)
        a[0] = 1
        a[dl] = -g
        out += lfilter([1.0], a, x) * mix * 0.35
    return out


def _delay(x, secs, fb=0.35, mix=0.3):
    dl = max(1, int(secs * SR))
    a = np.zeros(dl + 1)
    a[0] = 1
    a[dl] = -fb
    return x + mix * lfilter([1.0], a, np.concatenate([np.zeros(dl), x[:-dl]]))


def _lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x)


# ----------------------------------------------------------------------------------------------------- drum patterns
# 16-step grid per bar -> list of step numbers for every drum.
DRUMS = {
    "four": dict(kick=[0, 4, 8, 12], clap=[4, 12], hat=[2, 6, 10, 14]),
    "pop": dict(kick=[0, 6, 8, 14], clap=[4, 12], hat=list(range(0, 16, 2))),
    "boombap": dict(kick=[0, 7, 10], snare=[4, 12], hat=list(range(0, 16, 2))),
    "trap": dict(kick=[0, 7, 10], clap=[8], hat=list(range(0, 16, 2)) + [13, 15]),
    "rock": dict(kick=[0, 6, 8, 10], snare=[4, 12], hat=list(range(0, 16, 2))),
    "metal": dict(kick=[0, 1, 3, 4, 6, 8, 9, 11, 12, 14], snare=[4, 12], hat=[0, 8]),
    "lofi": dict(kick=[0, 9], snare=[4, 12], hat=list(range(0, 16, 2))),
    "shuffle": dict(kick=[0, 8], snare=[4, 12], hat=[0, 2, 4, 6, 8, 10, 12, 14]),
    "swing": dict(kick=[0, 4, 8, 12], hat=[4, 12], ride=[0, 4, 6, 8, 12, 14]),
    "half": dict(kick=[0, 10], snare=[8], hat=list(range(0, 16, 2))),
    "country": dict(kick=[0, 8], snare=[4, 12], hat=[0, 4, 8, 12]),
    "chip": dict(kick=[0, 8], snare=[4, 12], hat=list(range(0, 16, 2))),
    "cinema": dict(tom=[0, 8, 14]),
    "indie": dict(kick=[0, 8, 10], snare=[4, 12], hat=list(range(0, 16, 2))),
    "none": dict(),
}

# ----------------------------------------------------------------------------------------------------- genre recipes
# prog: (semitone offset from the key root, chord type) per bar.  comp: how the chords are played.
RECIPES = {
    "Ambient": dict(root=57, scale="major", prog=[(0, "maj9"), (5, "maj7"), (7, "sus"), (3, "maj7")], chord="pad", comp="whole",
                    bass="drone", drums="none", melody=("sine", 0.35), reverb=0.9, delay=0.5, vol=0.9),
    "Classical": dict(root=60, scale="major", prog=[(0, "maj"), (7, "maj"), (9, "min"), (5, "maj")], chord="piano", comp="arp8",
                      bass="root2", drums="none", melody=("piano", 0.7), reverb=0.6, strings=True, vol=0.9),
    "Lofi": dict(root=57, scale="dorian", prog=[(0, "min9"), (5, "maj9"), (3, "maj7"), (7, "dom7")], chord="rhodes", comp="stabs",
                 bass="root8", drums="lofi", swing16=0.22, melody=("rhodes", 0.5), vinyl=True, reverb=0.35, lowpass=3200, vol=0.95),
    "Pop": dict(root=60, scale="major", prog=[(0, "maj"), (7, "maj"), (9, "min"), (5, "maj")], chord="saw", comp="stabs",
                bass="root8", drums="pop", melody=("saw", 0.8), reverb=0.2, vol=0.9),
    "Instrumental": dict(root=57, scale="major", prog=[(0, "maj7"), (4, "min7"), (5, "maj7"), (7, "dom7")], chord="pluck", comp="arp8",
                         bass="root2", drums="none", melody=("pluck", 0.6), reverb=0.4, strings=True, vol=0.9),
    "Rock": dict(root=52, scale="minor", prog=[(0, "pow"), (8, "pow"), (10, "pow"), (7, "pow")], chord="dist", comp="power8",
                 bass="root8", drums="rock", melody=("dist", 0.5), reverb=0.15, vol=0.85),
    "EDM": dict(root=57, scale="minor", prog=[(0, "min7"), (8, "maj7"), (3, "maj7"), (10, "dom7")], chord="saw", comp="sidechain",
                bass="root8", drums="four", melody=("saw", 0.9), reverb=0.2, sidechain=True, vol=0.9),
    "Hip-hop": dict(root=53, scale="minor", prog=[(0, "min7"), (0, "min7"), (8, "maj7"), (7, "dom7")], chord="rhodes", comp="stabs",
                    bass="808", drums="boombap", swing16=0.12, melody=("pluck", 0.35), reverb=0.2, vol=0.95),
    "Indie": dict(root=55, scale="major", prog=[(0, "maj"), (5, "maj"), (9, "min"), (7, "maj")], chord="pluck", comp="arp8",
                  bass="root4", drums="indie", melody=("pluck", 0.55), reverb=0.3, vol=0.9),
    "Blues": dict(root=52, scale="blues", prog=[(0, "dom7"), (0, "dom7"), (5, "dom7"), (0, "dom7")], chord="pluck", comp="stabs",
                  bass="walk", drums="shuffle", swing8=0.33, melody=("pluck", 0.7), reverb=0.25, vol=0.95),
    "Electronic": dict(root=57, scale="minor", prog=[(0, "min"), (8, "maj"), (3, "maj"), (10, "maj")], chord="saw", comp="arp16",
                       bass="root8", drums="four", melody=("none", 0), reverb=0.25, delay=0.25, vol=0.85),
    "Video game music": dict(root=60, scale="major", prog=[(0, "maj"), (9, "min"), (5, "maj"), (7, "maj")], chord="square", comp="arp16",
                             bass="chipbass", drums="chip", melody=("square", 0.9), reverb=0.05, vol=0.8),
    "Metal": dict(root=40, scale="minor", prog=[(0, "pow"), (0, "pow"), (1, "pow"), (0, "pow")], chord="dist", comp="gallop",
                  bass="root8", drums="metal", melody=("dist", 0.45), reverb=0.12, vol=0.85),
    "Jazz": dict(root=55, scale="dorian", prog=[(2, "min7"), (7, "dom7"), (0, "maj7"), (9, "dom7")], chord="rhodes", comp="comp",
                 bass="walk", drums="swing", swing8=0.3, melody=("pluck", 0.55), reverb=0.3, vol=0.95),
    "Soundtracks": dict(root=50, scale="minor", prog=[(0, "min"), (8, "maj"), (5, "min"), (7, "dom7")], chord="strings", comp="whole",
                        bass="drone", drums="cinema", melody=("piano", 0.4), reverb=0.7, vol=0.9),
    "Country": dict(root=55, scale="major", prog=[(0, "maj"), (5, "maj"), (0, "maj"), (7, "dom7")], chord="pluck", comp="strum",
                    bass="boomchick", drums="country", melody=("pluck", 0.6), reverb=0.2, vol=0.9),
    "R&B": dict(root=54, scale="dorian", prog=[(0, "min9"), (5, "maj9"), (3, "maj7"), (7, "dom7")], chord="rhodes", comp="whole",
                bass="808", drums="half", swing16=0.1, melody=("rhodes", 0.5), reverb=0.4, vol=0.95),
}
DEFAULT = RECIPES["Pop"]
GENRE_TAGLINE = {
    "Ambient": "slow pads, long echoes, no drums", "Classical": "piano arpeggios over warm strings", "Lofi": "dusty swing, soft keys, vinyl hiss",
    "Pop": "bright chords, four-bar hook", "Instrumental": "plucked guitar-style arpeggios", "Rock": "power chords and a driving kit",
    "EDM": "four-on-the-floor with side-chained synths", "Hip-hop": "boom-bap drums and an 808 bass", "Indie": "jangly plucks, loose drums",
    "Blues": "12/8 shuffle with a bluesy riff", "Electronic": "16th-note synth sequence", "Video game music": "8-bit square-wave arcade loop",
    "Metal": "palm-muted gallop and double kick", "Jazz": "swing ride, walking bass, 7th chords", "Soundtracks": "cinematic strings and timpani",
    "Country": "boom-chick bass and twangy strum", "R&B": "smooth 9th chords and a slow groove",
}


def _chord_notes(root, off, kind, octave=0):
    return [root + off + s + 12 * octave for s in CHORDS[kind]]


def render_genre(genre, bpm, bars=None, seed=_RNG_SEED):
    """Return WAV bytes (16-bit mono) for one original loop in the style of `genre` at `bpm`."""
    rc = RECIPES.get(genre, DEFAULT)
    rng = np.random.default_rng(seed + sum(map(ord, genre)))
    bpm = float(np.clip(bpm, 55, 175))
    beat = 60.0 / bpm
    step = beat / 4.0
    bar_len = beat * 4
    if bars is None:
        bars = 8 if bpm >= 125 else 4
    total = bars * bar_len + 1.0
    n = int(total * SR)
    mix = {k: np.zeros(n) for k in ("chords", "bass", "lead", "drums", "extra")}
    sw16, sw8 = rc.get("swing16", 0.0), rc.get("swing8", 0.0)

    def when(bar, s):
        t0 = bar * bar_len + s * step
        if s % 2 == 1:
            t0 += sw16 * step
        if sw8 and s % 4 == 2:
            t0 += sw8 * step * 2 * 0.5
        return t0

    prog = rc["prog"]
    root = rc["root"]
    scale = [root + s for s in SCALES[rc["scale"]]]
    voice = {"pad": lambda f, d: pad(f, d), "piano": piano, "rhodes": rhodes, "saw": lambda f, d: saw(f, d, tau=d * 0.8, a=0.01),
             "pluck": lambda f, d: pluck(f, d, 0.45), "square": lambda f, d: square(f, d, tau=0.18), "strings": strings,
             "dist": lambda f, d: saw(f, d)}[rc["chord"] if rc["chord"] != "dist" else "dist"]

    # --- chords --------------------------------------------------------------------------------------------------
    for b in range(bars):
        off, kind = prog[b % len(prog)]
        notes = _chord_notes(root, off, kind)
        comp = rc["comp"]
        if comp == "whole":
            for m in notes:
                _place(mix["chords"], voice(hz(m), bar_len * 1.02), when(b, 0), 0.22)
        elif comp == "arp8":
            seq = notes + notes[::-1][1:-1]
            for i in range(8):
                m = seq[i % len(seq)] + (12 if rc["chord"] in ("pluck",) and i % 4 == 3 else 0)
                _place(mix["chords"], voice(hz(m), beat * 1.2), when(b, i * 2), 0.28)
            if rc.get("strings"):
                for m in notes:
                    _place(mix["extra"], pad(hz(m), bar_len * 1.05), when(b, 0), 0.12)
        elif comp == "arp16":
            seq = notes + [notes[1] + 12, notes[2] + 12]
            for i in range(16):
                m = seq[i % len(seq)] + (12 if i % 8 >= 4 else 0)
                _place(mix["chords"], voice(hz(m), step * 1.6), when(b, i), 0.2 * (1.0 if i % 4 == 0 else 0.7))
        elif comp == "stabs":
            hits = [0, 6, 10] if rc["drums"] != "pop" else [0, 3, 6, 10, 12]
            for s_ in hits:
                for m in notes:
                    _place(mix["chords"], voice(hz(m), step * 3.2), when(b, s_), 0.18)
        elif comp == "sidechain":
            for m in notes:
                _place(mix["chords"], voice(hz(m), bar_len * 1.02), when(b, 0), 0.2)
        elif comp == "power8":
            fr = [hz(m) for m in notes]
            for i in range(8):
                _place(mix["chords"], dist_chord(fr, beat * 0.55, 5.0), when(b, i * 2), 0.32 if i % 2 == 0 else 0.26)
        elif comp == "gallop":
            fr = [hz(m) for m in notes]
            for i in range(16):
                if i % 4 == 2:
                    continue
                _place(mix["chords"], dist_chord(fr, step * 0.9, 9.0, mute=True), when(b, i), 0.3)
        elif comp == "strum":
            for s_ in (0, 4, 8, 12):
                for k, m in enumerate(notes + [notes[0] + 12]):
                    _place(mix["chords"], voice(hz(m), beat * 0.9), when(b, s_) + k * 0.018, 0.22)
        elif comp == "comp":
            for s_ in (0, 6, 10) if b % 2 == 0 else (2, 8, 14):
                for m in notes:
                    _place(mix["chords"], voice(hz(m), step * 3), when(b, s_), 0.17)

    # --- bass ----------------------------------------------------------------------------------------------------
    bs = rc["bass"]
    for b in range(bars):
        off, kind = prog[b % len(prog)]
        r = root + off - 24
        fifth = r + 7
        if bs == "drone":
            _place(mix["bass"], bass(hz(r), bar_len * 1.0, tau=3), when(b, 0), 0.5)
        elif bs == "root2":
            for s_ in (0, 8):
                _place(mix["bass"], bass(hz(r), beat * 2, tau=1.2), when(b, s_), 0.45)
        elif bs == "root4":
            for s_ in (0, 4, 8, 12):
                _place(mix["bass"], bass(hz(r + (7 if s_ == 8 else 0)), beat * 0.9), when(b, s_), 0.5)
        elif bs == "root8":
            pat = [0, 0, 12, 0, 7, 0, 12, 0]
            for i in range(8):
                _place(mix["bass"], bass(hz(r + pat[i]), beat * 0.45), when(b, i * 2), 0.5)
        elif bs == "walk":
            ch = CHORDS[kind]
            walk = [r, r + ch[1], r + ch[2], r + ch[1] + 2]
            for i in range(4):
                _place(mix["bass"], bass(hz(walk[i]), beat * 0.95, tau=0.5), when(b, i * 4), 0.55)
        elif bs == "808":
            for s_, d_ in ((0, 6), (7, 3), (10, 5)):
                _place(mix["bass"], sub808(hz(r), step * d_ + 0.2), when(b, s_), 0.75)
        elif bs == "boomchick":
            for i, s_ in enumerate((0, 4, 8, 12)):
                _place(mix["bass"], bass(hz(r if i % 2 == 0 else fifth), beat * 0.8, tau=0.3), when(b, s_), 0.5)
        elif bs == "chipbass":
            for i in range(8):
                _place(mix["bass"], square(hz(r + 12), beat * 0.4, tau=0.12), when(b, i * 2), 0.18)

    # --- melody --------------------------------------------------------------------------------------------------
    mv, mdens = rc["melody"]
    if mv != "none":
        mvoice = {"sine": lambda f, d: pad(f, d, a=0.2, r=0.4), "piano": piano, "rhodes": rhodes, "pluck": lambda f, d: pluck(f, d, 0.4),
                  "saw": lambda f, d: saw(f, d, tau=d * 0.9, a=0.01), "square": lambda f, d: square(f, d, tau=0.25),
                  "dist": lambda f, d: np.tanh(2.5 * saw(f, d, tau=d * 0.9, a=0.01))}[mv]
        mrng = np.random.default_rng(11 + sum(map(ord, genre)))
        motif = []
        pos = 4
        for s_ in range(0, 32, 2):
            if mrng.random() < mdens or s_ % 8 == 0:
                pos = int(np.clip(pos + mrng.integers(-2, 3), 1, len(scale) - 2))
                motif.append((s_, scale[pos] + 12, 2 if mrng.random() < 0.7 else 4))
        for b in range(bars):
            half = (b % 2) * 16
            for s_, m, ln in motif:
                if s_ < half or s_ >= half + 16:
                    continue
                if b % 4 == 3 and s_ - half > 8:
                    m -= 2 if mrng.random() < 0.5 else 0
                gain = 0.28 if mv not in ("sine",) else 0.22
                _place(mix["lead"], mvoice(hz(m), step * ln * 1.1), when(b, s_ - half), gain)

    # --- drums ---------------------------------------------------------------------------------------------------
    pat = DRUMS[rc["drums"]]
    kk, sn = kick(), None
    for b in range(bars):
        for s_ in pat.get("kick", []):
            _place(mix["drums"], kk, when(b, s_), 0.95 if s_ % 4 == 0 else 0.75)
        for s_ in pat.get("snare", []):
            _place(mix["drums"], snare(rng, amount=0.85 if rc["drums"] != "lofi" else 0.55), when(b, s_), 0.75)
        for s_ in pat.get("clap", []):
            _place(mix["drums"], clap(rng), when(b, s_), 0.9)
        for s_ in pat.get("hat", []):
            if rc["drums"] == "metal":
                _place(mix["drums"], hat(rng, True, 0.6), when(b, s_), 0.6)
            elif rc["drums"] == "four" and s_ % 4 == 2:
                _place(mix["drums"], hat(rng, True, 0.35), when(b, s_), 0.8)
            else:
                _place(mix["drums"], hat(rng, False, 0.5 if s_ % 4 == 0 else 0.3), when(b, s_), 0.7)
        for s_ in pat.get("ride", []):
            _place(mix["drums"], hat(rng, True, 0.28), when(b, s_), 0.8)
        for s_ in pat.get("tom", []):
            _place(mix["drums"], tom(70 if s_ != 14 else 95), when(b, s_), 0.8)

    # --- processing ----------------------------------------------------------------------------------------------
    if rc.get("sidechain"):
        env = np.ones(n)
        for b in range(bars):
            for q in range(4):
                i = int((b * bar_len + q * beat) * SR)
                L = int(beat * SR)
                curve = 1 - 0.85 * np.exp(-np.arange(min(L, n - i)) / (0.11 * SR))
                env[i:i + len(curve)] = np.minimum(env[i:i + len(curve)], curve)
        mix["chords"] *= env
        mix["extra"] *= env
    chords = mix["chords"] + mix["extra"]
    cutoff = rc.get("lowpass", 4800)          # keep synth layers soft; drums stay bright
    chords = _lowpass(_lowpass(chords, cutoff), cutoff * 1.6)
    mix["lead"] = _lowpass(_lowpass(mix["lead"], cutoff), cutoff * 1.6)
    if rc.get("delay"):
        chords = _delay(chords, beat * 0.75, 0.45, rc["delay"])
        mix["lead"] = _delay(mix["lead"], beat * 0.75, 0.4, rc["delay"])
    else:
        mix["lead"] = _delay(mix["lead"], beat * 0.75, 0.25, 0.15)
    wet = _reverb(chords + mix["lead"], rc.get("reverb", 0.2))
    out = wet + mix["bass"] + mix["drums"]
    if rc.get("vinyl"):
        crackle = (rng.random(n) > 0.9993) * rng.standard_normal(n) * 0.25
        hiss = _lowpass(rng.standard_normal(n), 6000) * 0.012
        out += crackle + hiss
    out = out[: int((bars * bar_len + 0.6) * SR)]
    fade = int(0.35 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out[:200] *= np.linspace(0, 1, 200)
    out = np.tanh(out * 1.1)
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.88 * rc.get("vol", 0.9)
    return _to_wav(out)


# ----------------------------------------------------------------------------------------------------- sound effects
def _to_wav(x):
    x = np.nan_to_num(np.clip(x, -1, 1))
    pcm = (x * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def shock_sting():
    """A short dramatic 'dun-dun!' used when the game reveals a surprising number."""
    rng = np.random.default_rng(3)
    n = int(2.2 * SR)
    out = np.zeros(n)
    t = _t(n)
    boom = np.sin(2 * np.pi * np.cumsum(55 * (1 + 2 * np.exp(-t / 0.05))) / SR) * np.exp(-t / 0.7)
    _place(out, boom, 0, 1.0)
    for f_ in (hz(48), hz(54), hz(60), hz(66)):          # tense, dissonant cluster
        _place(out, saw(f_, 1.6, harmonics=10, tau=0.9, a=0.01), 0.0, 0.18)
    _place(out, np.diff(rng.standard_normal(int(0.5 * SR) + 1)) * np.exp(-_t(int(0.5 * SR)) / 0.15), 0, 0.5)
    for f_ in (hz(72), hz(78)):
        _place(out, saw(f_, 0.9, harmonics=8, tau=0.5, a=0.01), 0.55, 0.15)
    out = _reverb(out, 0.4)
    return _to_wav(np.tanh(out * 1.2) * 0.9)


def win_chime():
    out = np.zeros(int(1.4 * SR))
    for i, m in enumerate((72, 76, 79, 84)):
        _place(out, piano(hz(m), 0.9), i * 0.11, 0.5)
    return _to_wav(_reverb(out, 0.3) * 0.9)


def miss_buzz():
    out = np.zeros(int(0.9 * SR))
    for i, m in enumerate((55, 52)):
        _place(out, square(hz(m), 0.4, tau=0.4), i * 0.22, 0.4)
    return _to_wav(out)
