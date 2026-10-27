# Music Listening Habits and Reported Music Effects

An interactive data science project exploring associations between music preferences, listening habits, and mental health
indicators through exploratory data analysis, statistical insights, and visualizations.

**Unit 3 Final Project — Data Exploration & Dashboard Development**
Lama Mansour Aldhalaan

This project explores how people listen to music (when, where, how many hours a day and which genres) and how that relates
to whether they say music **improves** their mood, has **no effect**, or makes it **worse**. It covers the full workflow:
loading and cleaning the data, exploratory data analysis, an insights summary, an interactive Streamlit dashboard, and a
presentation.

---

## Contents of this repository

| Path | What it is |
|---|---|
| `Music_Mental_Health_Eda.ipynb` | Jupyter notebook: data loading, cleaning, EDA (univariate and bivariate), insights and final summary |
| `Music_Mental_Health.csv` | The dataset used in the notebook (1,000 rows, 15 columns) |
| `streamlit_app/` | The Streamlit dashboard (see [Dashboard](#dashboard)) |
| `streamlit_app/clean_data.csv` | The cleaned dataset produced by the notebook and used by the dashboard |
| `presentation/music_listening_presentation.html` | The interactive 7-slide presentation (open it in any browser) |
| `requirements.txt` | Python packages for the notebook and the dashboard |

---

## Dataset

**Music & Mental Health Survey (MXMH)** by Catherine Rasgaitis —
[Kaggle](https://www.kaggle.com/datasets/catherinerasgaitis/mxmh-survey-results) ·
[creator's project page](https://crasgaitis.github.io/mental_music/)

The survey covers listening habits, music preferences and the effect people feel music has on them. The version used here was
extended with supplementary survey responses and two research papers:

- *Music Therapy Practices and Perspectives Regarding the Mental Health Needs of People With Intellectual Disabilities* (2026) — https://doi.org/10.1093/mtp/miag005
- *Clinical Implications of College Students’ Music Listening Habits and Perceptions of Personal Impact* (2025) — https://doi.org/10.1093/mtp/miaf008

**Variables (15):** `age`, `primary_streaming_service`, `hours_per_day`, `listening_time`, `listening_setting`,
`instrumentalist`, `composer`, `exploratory`, `foreign_languages`, `bpm`, `music_effects` (the outcome), `mental_disorder`,
`music_genre`, `vibe_reason`, `repeats_songs_often`.

## Questions explored

1. What do the distributions of age, daily listening hours and BPM look like?
2. Which genres, listening times and settings are most common?
3. Do reported effects differ by genre, listening time or mental-health group?
4. Is age related to how long people listen each day?
5. Which numeric variables are correlated, and which values are outliers?

## Data cleaning

Column names standardised to `snake_case`, text trimmed and missing-value markers converted, duplicate check, numeric types
for `age` / `hours_per_day` / `bpm`, a range check for impossible values, `music_effects` standardised to
*Improve / No effect / Worsen*, and the result saved as `clean_data.csv`. The cleaned data has 1,000 rows, 15 columns and no
missing values or duplicates.

## Key insights

- **Music mostly helps:** 72% say music improves how they feel, 17% notice no effect and 11% feel worse.
- **Younger people listen more:** age and daily listening hours have a strong negative correlation (r = −0.74); people aged
  13–20 listen about 6.8 hours a day, those over 40 about 2.3.
- **Genre separates the effects:** Ambient, Classical and Lofi listeners report *Improve* about 85% of the time; Rock and
  Metal are mostly *No effect*; Blues and Indie mostly *Worsen*.
- **Late night at home** is the typical listening situation (50% late night, 42% at home).
- **Mental-health groups differ:** Autism (ASD) reports *Improve* 91% of the time and Bipolar disorder 22%; Depression is
  split evenly between *Improve* and *Worsen*; ADHD listens to the fastest music (median 140 BPM) and Anxiety the slowest (70 BPM).
- **Outliers:** 87 ages above 40.5 and 2 tempos above about 155 BPM are flagged by the IQR rule; they are plausible answers and were kept.

The full discussion, limitations and recommendations are in Step 7 of the notebook.

---

## How to run

Requires Python 3.10 or newer.

```bash
git clone <this repository's URL>
cd <repository folder>
python -m pip install -r requirements.txt
```

### Notebook
Open `Music_Mental_Health_Eda.ipynb` in Jupyter or VS Code and choose **Run All**. The notebook reads
`Music_Mental_Health.csv` from the same folder, writes `clean_data.csv`, and saves every chart to `plots/`.

### Dashboard
Run it from inside the app folder so its theme and audio files are picked up:

```bash
cd streamlit_app
python -m streamlit run app.py
```

Then open the address it prints (usually http://localhost:8501). Turn your sound on: the dashboard plays music.

### Presentation
Open `presentation/music_listening_presentation.html` in a browser. Use ← / → to move between slides, **N** for speaker
notes, **F** for full screen, and the play button in the bottom bar to start the presentation timer.

---

## Dashboard

A Streamlit app in a purple music-player style. Every chart and number responds to the filters.

- **Filter panel:** four sections (Mood, Listener, Listening, Sound) with pills, range sliders, dropdowns and a multiselect;
  the dataset description is under **About**.
- **Home:** key figures, an album shelf and a playable track list of the top genres, top settings and reasons, and
  interactive versions of the EDA charts.
- **Top Charts:** a chart builder (histogram, counts, box plot, scatter, heatmap, grouped bars, correlation) and a Cramér's V
  ranking of which variables relate most to the reported effect.
- **Genre Jukebox:** every genre has a short synthesised loop at that genre's real median BPM.
- **Game Zone:** *Guess the Mood* (guess a real respondent's reported effect from an animated scene) and *Mind Reader*
  (build a character and a naive Bayes model predicts the effect, with an honest accuracy check).
- **Plot Gallery, Data and Insights:** the notebook's charts with notes, a data preview with summary statistics and a data
  dictionary, and insights written from the filtered data.
- **Music player:** a player bar at the bottom plays the genre loops from anywhere in the app.

| File | Purpose |
|---|---|
| `app.py` | the dashboard |
| `player.py` | album covers, music player, album shelf and track list |
| `scene.py` | the animated listener scenes used in the games |
| `sounds.py` | synthesises one loop per genre at its median BPM |
| `style.css` | styling |
| `static/loops/` | the genre loops (WAV) |
| `plots/` | the notebook's charts for the Plot Gallery |
| `.streamlit/config.toml` | theme and static file serving |

---

## Limitations

- The dataset is an extended version of the original survey; some added fields are derived or simulated, and
  `mental_disorder` is a group label, not a clinical diagnosis.
- The reported effect is self-reported, and the analysis is descriptive: it shows associations, not cause and effect.
- The sample is young (median age 21) and several groups have fewer than 30 records.

## References

- Rasgaitis, C. *Music & Mental Health Survey Results.* Kaggle. https://www.kaggle.com/datasets/catherinerasgaitis/mxmh-survey-results
- *Music Therapy Practices and Perspectives Regarding the Mental Health Needs of People With Intellectual Disabilities* (2026). https://doi.org/10.1093/mtp/miag005
- *Clinical Implications of College Students’ Music Listening Habits and Perceptions of Personal Impact* (2025). https://doi.org/10.1093/mtp/miaf008
