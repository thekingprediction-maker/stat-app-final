# app.py — STAT APP completo: Tiri & Falli — EWMA + Shrinkage + Poisson/Normal mixture
# Requisiti (requirements.txt): streamlit pandas numpy scipy openpyxl

import streamlit as st
import pandas as pd
import numpy as np
import math
from statistics import mean
from scipy.stats import norm, poisson

# ---------------------------
# Config pagina
# ---------------------------
st.set_page_config(page_title="STAT APP — Pronostici Tiri & Falli", layout="wide")
st.markdown("""
<style>
.card { background: #f8fbff; border-radius:10px; padding:12px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
.header { color:#0b57a4; font-weight:700; }
.small { font-size:0.9rem; color:#333; }
.reco { background:#e9f9ee; padding:8px; border-radius:8px; }
.warn { background:#fff4e6; padding:8px; border-radius:8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='header'>⚽ STAT APP — Pronostici Tiri & Falli</h1>", unsafe_allow_html=True)
st.markdown("<div class='small'>Engine: EWMA + shrinkage + Poisson/Normal mixture · supporto arbitri · scelta linee/bookmakers · EV & consigli</div>", unsafe_allow_html=True)
st.markdown("---")

# ---------------------------
# Utility: caricamento tollerante e mappatura colonne
# ---------------------------
@st.cache_data(ttl=600)
def safe_load(path):
    try:
        return pd.read_excel(path)
    except Exception:
        return None

def find_col(df, candidates):
    if df is None:
        return None
    cols = list(df.columns)
    low = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in low:
            return low[cand.lower()]
    for cand in candidates:
        k = cand.lower()
        for c in cols:
            if k in c.lower():
                return c
    return None

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0

# ---------------------------
# Files (devono stare nella root)
# ---------------------------
FILE_TIRI = "tiri_serie_a.xlsx"
FILE_FALLI_ITA = "falli_serie_a.xlsx"
FILE_FALLI_LIGA = "falli_liga.xlsx"

df_tiri = safe_load(FILE_TIRI)
df_falli_ita = safe_load(FILE_FALLI_ITA)
df_falli_liga = safe_load(FILE_FALLI_LIGA)

# Messaggi se file mancanti
if df_tiri is None:
    st.error(f"File mancante o non leggibile: {FILE_TIRI}. Caricalo nella root del repo e riavvia.")
if df_falli_ita is None:
    st.warning(f"File mancante o non leggibile: {FILE_FALLI_ITA}. Funzionalità falli Serie A parziali.")
if df_falli_liga is None:
    st.info(f"File mancante o non leggibile: {FILE_FALLI_LIGA}. Funzionalità falli Liga disabilitate finché non carichi il file.")

# ---------------------------
# Rileva colonne utili (tolleranza)
# ---------------------------
# TIRI: cerchiamo colonne per team, tiri totali, tiri in porta, match-level home/away se presenti
tiri_team_col = find_col(df_tiri, ["squadra", "team", "team name", "squad"])
tiri_home_col = find_col(df_tiri, ["home team", "squadra_casa", "squadra casa", "casa"])
tiri_away_col = find_col(df_tiri, ["away team", "squadra_ospite", "trasferta", "ospite"])
tiri_tot_col = find_col(df_tiri, ["tiri_tot", "tiri totali", "tiri fatti", "total shots", "shots"])
tiri_sot_col = find_col(df_tiri, ["tiri in porta","shots on target","sot","tiri_porta","shots_on_target"])

# FALLI Serie A
falli_ita_team_col = find_col(df_falli_ita, ["squadra","team"])
falli_ita_home_col = find_col(df_falli_ita, ["home team","squadra_casa"])
falli_ita_away_col = find_col(df_falli_ita, ["away team","squadra_ospite"])
falli_ita_falli_col = find_col(df_falli_ita, ["falli","fouls","falli_commessi"])
falli_ita_arbitro_col = find_col(df_falli_ita, ["arbitro","referee","official"])
falli_ita_arb_media_col = find_col(df_falli_ita, ["media_arbitro","avg_ref","media_arbitro","ref_avg"])

# FALLI LIGA
falli_liga_team_col = find_col(df_falli_liga, ["squadra","team"])
falli_liga_falli_col = find_col(df_falli_liga, ["falli","fouls"])

# ---------------------------
# Costruzione cronologie team & arbitri (da file aggregati o match-level)
# ---------------------------
team_stats = {}      # team -> {'tiri':[], 'sot':[], 'falli':[], 'falli_liga':[]}
arbitri_stats = {}   # arb -> [values]

def add_value(team, key, val):
    if team is None or pd.isna(team): return
    team = str(team).strip()
    if team == "": return
    team_stats.setdefault(team, {}).setdefault(key, []).append(safe_float(val))

# proviamo a ricavare dati: se df_tiri sembra match-level (home/away exist), usiamo quello, altrimenti assume "team-level" (una riga per team)
if df_tiri is not None:
    # if match-level
    if tiri_home_col and tiri_away_col and tiri_tot_col and (tiri_home_col in df_tiri.columns) and (tiri_away_col in df_tiri.columns):
        # proviamo a leggere ogni riga come partita con 'home' e 'away' col
        # cerchiamo anche col tiri_home/tiri_away per count, ma se non esistono proviamo a cercare generic numeric
        # common patterns: columns for home shots and away shots might be something like 'home_shots' / 'away_shots'
        # We'll attempt to detect numeric columns containing 'home' and 'away' and 'shot' words
        for _, r in df_tiri.iterrows():
            home = r.get(tiri_home_col)
            away = r.get(tiri_away_col)
            # tiri totali per riga: try tiri_tot_col (common), else fallback to numeric columns mean
            if tiri_tot_col and tiri_tot_col in df_tiri.columns:
                # assume tiri_tot is total for team row - skip for match-level
                pass
            # attempt to find home_shots & away_shots fields
            home_shots = None
            away_shots = None
            # check columns with substrings
            for c in df_tiri.columns:
                cl = c.lower()
                if "home" in cl and ("shot" in cl or "tiri" in cl):
                    home_shots = r.get(c)
                if "away" in cl and ("shot" in cl or "tiri" in cl):
                    away_shots = r.get(c)
            # fallback: if no home_shots found, try columns that contain 'shots' and interpret differently (skip complexity)
            if home is not None:
                add_value(home, 'tiri', home_shots if home_shots is not None else None)
            if away is not None:
                add_value(away, 'tiri', away_shots if away_shots is not None else None)
    else:
        # aggregated rows (per team)
        for _, r in df_tiri.iterrows():
            team = r.get(tiri_team_col) if tiri_team_col in df_tiri.columns else None
            if pd.isna(team) or team is None:
                continue
            if tiri_tot_col and tiri_tot_col in df_tiri.columns:
                add_value(team, 'tiri', r.get(tiri_tot_col))
            else:
                # fallback: any numeric column average
                nums = r.select_dtypes(include='number')
                if len(nums)>0:
                    add_value(team, 'tiri', nums.mean())
            if tiri_sot_col and tiri_sot_col in df_tiri.columns:
                add_value(team, 'sot', r.get(tiri_sot_col))

# FALLI Serie A: similar approach - prefer aggregated per-team rows with 'falli' and 'arbitro' columns
if df_falli_ita is not None:
    # aggregated style expected: each row a team or match-level: we'll support both but prefer extracting per-team falli
    for _, r in df_falli_ita.iterrows():
        # try team col
        team = None
        if falli_ita_team_col and falli_ita_team_col in df_falli_ita.columns:
            team = r.get(falli_ita_team_col)
        else:
            # possibly match-level with home/away columns
            if falli_ita_home_col and falli_ita_away_col:
                team = None  # skip for match-level in this section (we'll handle less comprehensively)
        if team is not None and not pd.isna(team):
            if falli_ita_falli_col and falli_ita_falli_col in df_falli_ita.columns:
                add_value(team, 'falli', r.get(falli_ita_falli_col))
        # arb stats
        if falli_ita_arbitro_col and falli_ita_arbitro_col in df_falli_ita.columns:
            arb = r.get(falli_ita_arbitro_col)
            if pd.notna(arb):
                arb = str(arb).strip()
                # use arb media if present else falli value
                if falli_ita_arb_media_col and (falli_ita_arb_media_col in df_falli_ita.columns):
                    val = safe_float(r.get(falli_ita_arb_media_col))
                elif falli_ita_falli_col and (falli_ita_falli_col in df_falli_ita.columns):
                    val = safe_float(r.get(falli_ita_falli_col))
                else:
                    val = 0.0
                arbitri_stats.setdefault(arb, []).append(val)

# FALLI LIGA
if df_falli_liga is not None:
    for _, r in df_falli_liga.iterrows():
        team = r.get(falli_liga_team_col) if falli_liga_team_col and (falli_liga_team_col in df_falli_liga.columns) else None
        if team is not None and not pd.isna(team):
            if falli_liga_falli_col and (falli_liga_falli_col in df_falli_liga.columns):
                add_value(team, 'falli_liga', r.get(falli_liga_falli_col))

# ---------------------------
# MODEL HELPERS: EWMA, shrink, sigma, p over mixture
# ---------------------------
def ewma(values, span=6):
    vals = [safe_float(v) for v in values if v is not None and not pd.isna(v)]
    if len(vals)==0:
        return 0.0
    s = pd.Series(vals)
    return float(s.ewm(span=span, adjust=False).mean().iloc[-1])

def shrink_est(est, prior, n, alpha=10.0):
    if n <= 0:
        return prior
    w = n/(n+alpha)
    return w*est + (1-w)*prior

def pstdev(vals):
    try:
        return float(pd.Series([safe_float(v) for v in vals]).std(ddof=0))
    except Exception:
        return 0.0

def p_over_mixture(mu, sigma, threshold, w_poisson=0.6):
    # integer tail for Poisson and continuity-corrected normal
    k = math.floor(threshold)
    mu_pos = max(mu, 0.0)
    try:
        p_pois = 1.0 - poisson.cdf(k, mu_pos)
    except Exception:
        p_pois = 0.0
    try:
        p_norm = 1.0 - norm.cdf(threshold + 0.5, loc=mu, scale=max(sigma, 0.1))
    except Exception:
        p_norm = 0.0
    return float(max(0.0, min(1.0, w_poisson * p_pois + (1-w_poisson) * p_norm)))

# ---------------------------
# Sidebar: parametri (Sicuri)
# ---------------------------
st.sidebar.header("Parametri Modello")
span = st.sidebar.slider("Span EWMA (partite recenti)", min_value=3, max_value=12, value=6, step=1)
alpha = st.sidebar.slider("Shrink α (maggiore = più stabilità)", min_value=1.0, max_value=30.0, value=10.0, step=1.0)
poisson_weight = st.sidebar.slider("Peso Poisson (mixture)", min_value=0.0, max_value=1.0, value=0.6, step=0.05)
# basic sets of spreads
default_spreads = [8.5,9.5,10.5,11.5,12.5,13.5,14.5,15.5,16.5,17.5,18.5,19.5,20.5,21.5,22.5]
spread_selected = st.sidebar.multiselect("Scegli linee/spread da valutare", default_spreads, default=default_spreads[:6])
st.sidebar.write("Arbitri rilevati (es.):", sorted(list(arbitri_stats.keys()))[:15])

# ---------------------------
# UI principale: selezione mercato e teams
# ---------------------------
market = st.selectbox("Scegli mercato", [
    "Tiri totali (partita)",
    "Tiri in porta (partita)",
    "Tiri squadra (home/away)",
    "Falli totali (partita)",
    "Falli squadra (home/away)"
])

# build list of teams from all datasets
all_teams = set(team_stats.keys())
if len(all_teams)==0:
    # fallback: try common columns in files
    if df_tiri is not None:
        cols = list(df_tiri.columns)
        for c in cols:
            if "team" in c.lower() or "squad" in c.lower():
                all_teams.update(df_tiri[c].dropna().astype(str).str.strip().unique().tolist())
all_teams = sorted(list(all_teams))
if len(all_teams)==0:
    st.error("Nessuna squadra rilevata: controlla i file Excel e le intestazioni.")
    st.stop()

col1, col2, col3 = st.columns([2,2,1])
with col1:
    home = st.selectbox("Squadra Casa", all_teams)
with col2:
    away = st.selectbox("Squadra Ospite", [t for t in all_teams if t!=home] or all_teams)
with col3:
    arb_choice = st.selectbox("Arbitro (opzionale)", ["(nessuno)"] + sorted(list(arbitri_stats.keys())))

st.markdown("---")

# ---------------------------
# Compute expected values per selected market
# ---------------------------
def compute_match_expectations(home, away, metric_key, span, alpha):
    # metric_key = 'tiri','sot','falli','falli_liga'
    h_vals = team_stats.get(home, {}).get(metric_key, [])
    a_vals = team_stats.get(away, {}).get(metric_key, [])
    mu_h_recent = ewma(h_vals, span=span) if len(h_vals)>0 else 0.0
    mu_a_recent = ewma(a_vals, span=span) if len(a_vals)>0 else 0.0
    mu_h_overall = mean(h_vals) if len(h_vals)>0 else 0.0
    mu_a_overall = mean(a_vals) if len(a_vals)>0 else 0.0
    mu_h = shrink_est(0.7 * mu_h_recent + 0.3 * mu_h_overall, mu_h_overall, len(h_vals), alpha)
    mu_a = shrink_est(0.7 * mu_a_recent + 0.3 * mu_a_overall, mu_a_overall, len(a_vals), alpha)
    mu_total = mu_h + mu_a
    sigma_h = max(0.6, pstdev(h_vals) if len(h_vals)>1 else max(0.6, mu_h * 0.25))
    sigma_a = max(0.6, pstdev(a_vals) if len(a_vals)>1 else max(0.6, mu_a * 0.25))
    sigma_total = math.sqrt(sigma_h**2 + sigma_a**2)
    return mu_h, mu_a, mu_total, sigma_total

# determine metric_key from market
if market.startswith("Tiri totali"):
    metric_key = 'tiri'
elif market.startswith("Tiri in porta"):
    metric_key = 'sot'
elif market.startswith("Tiri squadra"):
    metric_key = 'tiri'
elif market.startswith("Falli totali"):
    # prefer 'falli' if present else 'falli_liga'
    metric_key = 'falli' if ( 'falli' in team_stats.get(home, {}) or 'falli' in team_stats.get(away, {}) ) else 'falli_liga'
else:
    metric_key = 'falli' if ( 'falli' in team_stats.get(home, {}) or 'falli' in team_stats.get(away, {}) ) else 'falli_liga'

mu_h, mu_a, mu_total, sigma_total = compute_match_expectations(home, away, metric_key, span, alpha)

# adjust for arbitro if falli and arb selected
arb_adj_text = ""
if metric_key.startswith("falli") and arb_choice and arb_choice != "(nessuno)":
    arb_vals = arbitri_stats.get(arb_choice, [])
    if len(arb_vals)>0:
        arb_mean = mean(arb_vals)
        # moderate adjustment by arb_mean relative to league baseline
        arb_adj = (arb_mean - (mu_total/2.0)) * 0.5
        mu_total = mu_total + arb_adj
        arb_adj_text = f" (arb_adj {arb_adj:.2f})"

# ---------------------------
# Evaluate spreads: compute P(over), fair odds, EV if bookmaker odds given
# ---------------------------
results = []
for L in sorted(spread_selected):
    p = p_over_mixture(mu_total, sigma_total, L, w_poisson=poisson_weight)
    p_under = 1.0 - p
    fair_over = (1.0 / p) if p>0 else None
    fair_under = (1.0 / p_under) if p_under>0 else None
    results.append({"line": L, "p_over": p, "p_under": p_under, "fair_odds_over": fair_over, "fair_odds_under": fair_under})

df_lines = pd.DataFrame(results)

# allow user to enter bookmaker decimal odds for the selected lines (optional)
st.subheader("Valutazione linee & confronto quote bookmaker")
colA, colB = st.columns([2,3])
with colA:
    st.write("Linea selezionata e probabilità")
    st.table(df_lines.style.format({"line":"{:.1f}", "p_over":"{:.3f}", "p_under":"{:.3f}", "fair_odds_over":"{:.2f}"}))
with colB:
    st.write("Inserisci le quote del bookmaker (opzionali) per calcolare EV")
    # build inputs for odds
    odds_inputs = {}
    for i, row in df_lines.iterrows():
        key_over = f"odd_over_{row['line']}"
        key_under = f"odd_under_{row['line']}"
        odds_inputs[key_over] = st.number_input(f"Book odd OVER {row['line']}", min_value=1.01, value=2.0, step=0.01, key=key_over)
        odds_inputs[key_under] = st.number_input(f"Book odd UNDER {row['line']}", min_value=1.01, value=1.8, step=0.01, key=key_under)

# compute EV if odds provided
ev_rows = []
for row in df_lines.to_dict(orient='records'):
    line = row['line']
    p = row['p_over']
    odd_over = st.session_state.get(f"odd_over_{line}", None)
    odd_under = st.session_state.get(f"odd_under_{line}", None)
    ev_over = None
    ev_under = None
    if odd_over:
        ev_over = p * (odd_over - 1) - (1-p)
    if odd_under:
        ev_under = (1-p) * (odd_under - 1) - p
    ev_rows.append({"line": line, "p_over": p, "ev_over": ev_over, "p_under": 1-p, "ev_under": ev_under})

df_ev = pd.DataFrame(ev_rows)

st.markdown("---")
st.subheader("Raccomandazioni & decisione")
# choose best by EV (if odds provided) else by highest probability
best_over = None
best_under = None
if df_ev['ev_over'].notna().any():
    best_over = df_ev.loc[df_ev['ev_over'].idxmax()]
    best_under = df_ev.loc[df_ev['ev_under'].idxmax()]
else:
    # pick by highest p
    best_over = df_lines.loc[df_lines['p_over'].idxmax()]
    best_under = df_lines.loc[df_lines['p_under'].idxmax()]

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Miglior LINEA (OVER)**")
    st.markdown(f"Linea: **{best_over['line']}** — P(over) = **{best_over['p_over']*100:.1f}%**")
    if 'ev_over' in best_over:
        evv = best_over.get('ev_over', None)
        if evv is not None:
            st.markdown(f"Expected Value (OVER): {evv:.3f}")
with col2:
    st.markdown("**Miglior LINEA (UNDER)**")
    st.markdown(f"Linea: **{best_under['line']}** — P(under) = **{best_under['p_under']*100:.1f}%**")
    if 'ev_under' in best_under:
        evv2 = best_under.get('ev_under', None)
        if evv2 is not None:
            st.markdown(f"Expected Value (UNDER): {evv2:.3f}")

# Signal strength helper
def signal_from_p(p):
    if p >= 0.75:
        return "Molto Forte"
    elif p >= 0.60:
        return "Forte"
    elif p >= 0.55:
        return "Buono"
    elif p >= 0.51:
        return "Debole"
    else:
        return "Neutro / Sconsigliato"

st.markdown("---")
st.subheader("Segnale finale")
st.write(f"Mu totale previsto: **{mu_total:.2f}** (home {mu_h:.2f} | away {mu_a:.2f}) {arb_adj_text}")
st.metric("Sigma stimata", f"{sigma_total:.2f}")
st.markdown(f"Segnale OVER (miglior linea): **{signal_from_p(best_over['p_over'])}** — {best_over['p_over']*100:.1f}%")
st.markdown(f"Segnale UNDER (miglior linea): **{signal_from_p(best_under['p_under'])}** — {best_under['p_under']*100:.1f}%")

# Diagnostics: recent values for teams
st.markdown("---")
st.subheader("Diagnostica - ultimi valori (esempi)")
s_home = team_stats.get(home, {}).get(metric_key, [])[-8:]
s_away = team_stats.get(away, {}).get(metric_key, [])[-8:]
st.write(f"Ultimi {len(s_home)} osservazioni {home}: {s_home}")
st.write(f"Ultimi {len(s_away)} osservazioni {away}: {s_away}")

# End
st.markdown("<div class='card small'>Nota: il modello fornisce stime basate sui dati forniti. Miglioramenti (backtest, Poisson regressivo, features addizionali) aumentano la precisione.</div>", unsafe_allow_html=True)
