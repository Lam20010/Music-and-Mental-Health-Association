# Music Listening Insights: Streamlit dashboard

Unit 3 individual final project: data exploration and dashboard development.

## Run it
1. Open a terminal **inside this folder** (so the `.streamlit` theme is picked up).
2. `python -m pip install -r requirements.txt`
3. `python -m streamlit run app.py`

Turn your volume on: the dashboard has a working music player (bottom dock) and the games play sounds.

## Files
| File | Purpose |
|---|---|
| `app.py` | the dashboard |
| `player.py` | helper script: data-drawn album covers, the docked music player, album shelf, playable track list |
| `scene.py` | helper script: the animated listener scene for the Guess the Mood game |
| `sounds.py` | helper script: synthesises one short loop per genre (tempo = that genre's median BPM in the data) |
| `static/loops/` | the 17 genre loops as WAV files, streamed by the player (re-rendered automatically if any are missing) |
| `style.css` | all styling |
| `clean_data.csv` | cleaned dataset created in the notebook |
| `plots/` | static EDA plots exported from the notebook + `manifest.json` (captions) for the Plot Gallery tab |
| `.streamlit/config.toml` | purple theme + static file serving for the loops |

## Tabs
Home, Top Charts, Genre Jukebox, Game Zone (Guess the Mood, Mind Reader), Plot Gallery, Data, Insights.
The filter panel at the top has four sections (Mood, Listener, Listening, Sound) and drives every tab; Reset, Export and **About** (dataset description) are in the top-right corner.

## Music player
Click any album, Top Genres row, genre tag, the featured genre card, the hero disc, a Jukebox tile or cover, or a Play button to
play that genre's loop in the player at the bottom. Each loop is also registered with Streamlit's media server, and the player
switches to that copy automatically if the static file cannot be loaded.
The player has play/pause, previous/next, shuffle, repeat, a seekable progress bar and volume, and keeps playing while you change filters.
Each album cover is drawn from the data: its LED bars are that genre's listening-hours distribution.

## Data note
Based on the MXMH Music & Mental Health survey topic (Kaggle). Results are descriptive, not clinical evidence or advice.

## Guess the Mood (Game Zone)
Each round shows a real survey respondent as an animated character: the scene is their listening setting, the sky is their
time of day, and they bob to their genre's real median BPM while that genre plays in the player. Guess whether music
improves their mood, has no effect, or makes it worse. Asking the character a question reveals a clue (hours per day,
reason for listening, mental-health group, exploring habits) but lowers the points (3 → 1). Answers are drawn evenly from
the three effects, so always guessing "Improve" does not win. Eight listeners per game, with a streak counter and a final score.

## Mind Reader (Game Zone)
Build your own listener in three cards — **Who you are** (name, age, female or male), **Look** (skin tone, hair colour, hairstyle) and
**Outfit** (T-shirt, hoodie, jacket, suit, sweater or dress, plus colour) — or press **Surprise me**; then their listening:
favourite genre (it starts playing as you pick it), time of day, setting and hours per day. The animated scene updates live.
**Read my mind** runs a small naive Bayes model trained on the survey; the character reacts with the predicted mood, and the
panel shows the probabilities, the "people like you" group from the data and an honest note on how accurate the model is.
