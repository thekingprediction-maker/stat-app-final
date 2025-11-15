# app.py
import streamlit as st
import pandas as pd
import math
from statistics import mean
from scipy.stats import norm

st.set_page_config(page_title="Pronostici Statistici - Tiri & Falli", layout="wide")
st.title("Pronostici Statistici — Tiri & Falli (Serie A + Liga)")

# --- NAMES OF FILES (must be in repository root) ---
FILE_TIRI = "tiri_serie_a.xlsx"
FILE_FALLI_SERIEA = "falli_serie_a.xlsx"
FILE_FALLI_LIGA = "falli_liga.xlsx"

# --- UTILITIES ---
def safe_float(x):
    try:
        return float(str(x).strip())
    except:
        return 0.0

def ewma(values, span=5):
    if not values or len(values) == 0:
        return 0.0
    s = pd.Series([safe_float(v) for v in values])
    return float(s.ewm(span=span, adjust=False).mean().iloc[-1])

def pstdev(vals):
    try:
        return float(pd.Series([safe_float(v) for v in vals]).std(ddof=0))
    except:
        return 0.0

def shrink(estimate, prior, n, alpha=10.0):
    if n <= 0:
        return prior
    w = n / (n + alpha)
    return w * estimate + (1 - w) * prior

# --- PREDICTOR CLASS ---
class AdvancedPredictor:
    def __init__(self, shots_df: pd.DataFrame, fouls_seriea_df: pd.DataFrame, fouls_liga_df: pd.DataFrame):
        # Normalize headers to lowercase stripped strings
        self.shots_df = shots_df.copy()
        self.fouls_seriea_df = fouls_seriea_df.copy()
        self.fouls_liga_df = fouls_liga_df.copy()
        self.shots_df.columns = [c.strip() for c in self.shots_df.columns]
        self.fouls_seriea_df.columns = [c.strip() for c in self.fouls_seriea_df.columns]
        self.fouls_liga_df.columns = [c.strip() for c in self.fouls_liga_df.columns]

        # Build team histories
        self.team_stats = {}
        cols = [c.lower() for c in self.shots_df.columns]
        is_match_level = any(x in cols for x in ['squadra_casa', 'squadra_ospite', 'tiri_casa', 'tiri_ospite'])
        if is_match_level:
            # assume one row per match
            for _, r in self.shots_df.iterrows():
                home = str(r.get('squadra_casa') or r.get('Squadra Casa') or r.get('Home') or '').strip()
                away = str(r.get('squadra_ospite') or r.get('Squadra Ospite') or r.get('Away') or '').strip()
                if not home or not away:
                    continue
                hs = safe_float(r.get('tiri_casa') or r.get('Tiri Casa') or r.get('tiri_home') or 0)
                as_ = safe_float(r.get('tiri_ospite') or r.get('Tiri Ospite') or r.get('tiri_away') or 0)
                hst = safe_float(r.get('tiri_in_porta_casa') or r.get('Tiri in porta Casa') or r.get('shots_on_target_home') or 0)
                ast = safe_float(r.get('tiri_in_porta_ospite') or r.get('Tiri in porta Ospite') or r.get('shots_on_target_away') or 0)
                for team, kind, val in [(home, 'home_shots', hs), (home, 'home_sot', hst),
                                       (away, 'away_shots', as_), (away, 'away_sot', ast)]:
                    self.team_stats.setdefault(team, {}).setdefault(kind, []).append(val)
        else:
            # assume aggregated team rows
            for _, r in self.shots_df.iterrows():
                team = str(r.get('Squadra') or r.get('Team') or '').strip()
                if not team:
                    continue
                hs = safe_float(r.get('Tiri Fatti Casa') or r.get('home_shots') or 0)
                as_ = safe_float(r.get('Tiri Fatti Trasferta') or r.get('away_shots') or 0)
                hst = safe_float(r.get('Tiri in porta Fatti Casa') or r.get('home_shots_on_target') or 0)
                ast = safe_float(r.get('Tiri in porta Fatti Trasferta') or r.get('away_shots_on_target') or 0)
                self.team_stats.setdefault(team, {}).setdefault('home_shots', []).append(hs)
                self.team_stats.setdefault(team, {}).setdefault('away_shots', []).append(as_)
                self.team_stats.setdefault(team, {}).setdefault('home_sot', []).append(hst)
                self.team_stats.setdefault(team, {}).setdefault('away_sot', []).append(ast)

        # Fouls: combine both fouls dataframes
        for df in [self.fouls_seriea_df, self.fouls_liga_df]:
            for _, r in df.iterrows():
                team = str(r.get('Squadra') or r.get('Team') or '').strip()
                if not team:
                    continue
                typ = str(r.get('Tipo') or r.get('Type') or '').strip().lower()
                fc = safe_float(r.get('Falli Commessi') or r.get('Falli') or r.get('fouls_committed') or r.get('fouls') or 0)
                # if Tipo indicates home/casa use home_fouls, else away_fouls; fallback add to both lists as overall
                if typ.startswith('c') or typ.startswith('h'):
                    self.team_stats.setdefault(team, {}).setdefault('home_fouls', []).append(fc)
                elif typ.startswith('t') or typ.startswith('a') or typ.startswith('f'):  # trasfer, away, f(away)
                    self.team_stats.setdefault(team, {}).setdefault('away_fouls', []).append(fc)
                else:
                    # if can't tell, add to both for safety
                    self.team_stats.setdefault(team, {}).setdefault('home_fouls', []).append(fc)
                    self.team_stats.setdefault(team, {}).setdefault('away_fouls', []).append(fc)

        # league means as fallback
        total_shots = []
        total_sot = []
        total_fouls = []
        for t, v in self.team_stats.items():
            total_shots.append((mean(v.get('home_shots',[])) if v.get('home_shots') else 0) + (mean(v.get('away_shots',[])) if v.get('away_shots') else 0))
            total_sot.append((mean(v.get('home_sot',[])) if v.get('home_sot') else 0) + (mean(v.get('away_sot',[])) if v.get('away_sot') else 0))
            total_fouls.append((mean(v.get('home_fouls',[])) if v.get('home_fouls') else 0) + (mean(v.get('away_fouls',[])) if v.get('away_fouls') else 0))
        self.league_means = {
            'shots_total': mean(total_shots) if total_shots else 10.0,
            'sot_total': mean(total_sot) if total_sot else 3.0,
            'fouls_total': mean(total_fouls) if total_fouls else 24.0
        }

    def expected_for_match(self, home, away, metric='shots_total', span=6):
        # choose lists
        if metric == 'shots_total':
            home_vals = (self.team_stats.get(home,{}).get('home_shots',[]) + self.team_stats.get(home,{}).get('away_shots',[]))
            away_vals = (self.team_stats.get(away,{}).get('home_shots',[]) + self.team_stats.get(away,{}).get('away_shots',[]))
        elif metric == 'shots_on_target_total' or metric == 'sot_total':
            home_vals = (self.team_stats.get(home,{}).get('home_sot',[]) + self.team_stats.get(home,{}).get('away_sot',[]))
            away_vals = (self.team_stats.get(away,{}).get('home_sot',[]) + self.team_stats.get(away,{}).get('away_sot',[]))
        elif metric == 'fouls_total':
            home_vals = (self.team_stats.get(home,{}).get('home_fouls',[]) + self.team_stats.get(home,{}).get('away_fouls',[]))
            away_vals = (self.team_stats.get(away,{}).get('home_fouls',[]) + self.team_stats.get(away,{}).get('away_fouls',[]))
        else:
            raise Exception('metric not supported')

        # EWMA recent
        mu_home_recent = ewma(home_vals, span=span)
        mu_away_recent = ewma(away_vals, span=span)
        mu_home_overall = mean([safe_float(x) for x in home_vals]) if len(home_vals) > 0 else self.league_means.get(metric, self.league_means.get('shots_total', 10.0)/2.0)
        mu_away_overall = mean([safe_float(x) for x in away_vals]) if len(away_vals) > 0 else self.league_means.get(metric, self.league_means.get('shots_total', 10.0)/2.0)

        weight_recent = 0.7
        mu_home = weight_recent * mu_home_recent + (1 - weight_recent) * mu_home_overall
        mu_away = weight_recent * mu_away_recent + (1 - weight_recent) * mu_away_overall

        mu_home = shrink(mu_home, mu_home_overall, len(home_vals))
        mu_away = shrink(mu_away, mu_away_overall, len(away_vals))

        mu_total = mu_home + mu_away

        sigma_home = max(0.8, (pstdev(home_vals) if len(home_vals) > 1 else max(0.8, mu_home*0.25)))
        sigma_away = max(0.8, (pstdev(away_vals) if len(away_vals) > 1 else max(0.8, mu_away*0.25)))
        sigma_total = math.sqrt(sigma_home**2 + sigma_away**2)

        return mu_home, mu_away, mu_total, sigma_total

    def predict_over_probability(self, home, away, metric='shots_total', threshold=9.5, span=6):
        mu_h, mu_a, mu, sigma = self.expected_for_match(home, away, metric=metric, span=span)
        # continuity correction for integer counts
        p_over = 1.0 - norm.cdf(threshold + 0.5, loc=mu, scale=sigma)
        return {
            'home': home, 'away': away, 'metric': metric, 'threshold': threshold,
            'mu_home': mu_h, 'mu_away': mu_a, 'mu_total': mu, 'sigma_total': sigma,
            'p_over': float(p_over)
        }

# --- Load data (on start) ---
@st.cache_data(ttl=3600)
def load_data():
    try:
        shots = pd.read_excel(FILE_TIRI)
    except Exception as e:
        st.error(f"Errore leggendo {FILE_TIRI}: {e}")
        shots = pd.DataFrame()
    try:
        fouls_a = pd.read_excel(FILE_FALLI_SERIEA)
    except Exception as e:
        st.error(f"Errore leggendo {FILE_FALLI_SERIEA}: {e}")
        fouls_a = pd.DataFrame()
    try:
        fouls_l = pd.read_excel(FILE_FALLI_LIGA)
    except Exception as e:
        st.error(f"Errore leggendo {FILE_FALLI_LIGA}: {e}")
        fouls_l = pd.DataFrame()
    return shots, fouls_a, fouls_l

shots_df, fouls_seriea_df, fouls_liga_df = load_data()
predictor = AdvancedPredictor(shots_df, fouls_seriea_df, fouls_liga_df)

# --- UI ---
st.sidebar.header("Impostazioni pronostico")
metric = st.sidebar.selectbox("Mercato", ["shots_total", "shots_on_target_total", "fouls_total"])
threshold = st.sidebar.number_input("Soglia (es. 9.5, 10.5)", value=9.5, step=0.5)
span = st.sidebar.slider("Span EWMA (partite)", min_value=3, max_value=12, value=6)
home = st.sidebar.text_input("Squadra di casa (es: Atalanta)", value="")
away = st.sidebar.text_input("Squadra ospite (es: Milan)", value="")

col1, col2 = st.columns([2,3])

with col1:
    st.subheader("Selezione Teams")
    st.write("Suggerimento: copia i nomi esattamente come appaiono nei file Excel.")
    st.write("Esempio: 'Atalanta', 'Milan'")

with col2:
    st.subheader("Dati caricati")
    st.write(f"Rows Tiri: {len(shots_df)} | Rows Falli A: {len(fouls_seriea_df)} | Rows Falli L: {len(fouls_liga_df)}")

st.markdown("---")
st.header("Calcola pronostico")

if home and away:
    try:
        res = predictor.predict_over_probability(home, away, metric=metric, threshold=threshold, span=span)
        p_over = res['p_over']
        mu = res['mu_total']
        sigma = res['sigma_total']
        mu_h = res['mu_home']
        mu_a = res['mu_away']

        st.metric("Probabilità OVER", f"{p_over:.3f}")
        st.write(f"Mu totale previsto: {mu:.2f} (home: {mu_h:.2f} - away: {mu_a:.2f})")
        st.write(f"Sigma totale stimata: {sigma:.2f}")

        # suggerimento semplice
        if p_over >= 0.58:
            st.success("Segnale: OVER consigliato (p_over >= 0.58)")
        elif p_over <= 0.42:
            st.warning("Segnale: UNDER consigliato (p_over <= 0.42)")
        else:
            st.info("Segnale: probabilità neutra (0.42 < p < 0.58)")

        # mostra diagnostica storica (distribuzioni)
        st.markdown("### Diagnostica team (ultime partite)")
        def show_team_history(team, key_home, key_away):
            vals = []
            t = predictor.team_stats.get(team,{})
            vals.extend(t.get(key_home,[]))
            vals.extend(t.get(key_away,[]))
            return vals

        shots_home_hist = show_team_history(home, 'home_shots', 'away_shots')
        shots_away_hist = show_team_history(away, 'home_shots', 'away_shots')
        fouls_home_hist = show_team_history(home, 'home_fouls', 'away_fouls')
        fouls_away_hist = show_team_history(away, 'home_fouls', 'away_fouls')

        st.write("Esempio tiri - home (ultime):", shots_home_hist[-6:])
        st.write("Esempio tiri - away (ultime):", shots_away_hist[-6:])
        st.write("Esempio falli - home (ultime):", fouls_home_hist[-6:])
        st.write("Esempio falli - away (ultime):", fouls_away_hist[-6:])

    except Exception as e:
        st.error(f"Errore nel calcolo: {e}")
else:
    st.info("Inserisci squadra di casa e squadra ospite nella sidebar per calcolare il pronostico.")
