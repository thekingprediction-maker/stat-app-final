# app.py
# STAT APP — Pronostici Tiri & Falli (EWMA + shrinkage + Poisson/Normal mixture)
# Requisiti: streamlit, pandas, numpy, scipy, openpyxl

import streamlit as st
import pandas as pd
import numpy as np
import math
from statistics import mean
from scipy.stats import norm, poisson

st.set_page_config(page_title="STAT APP — Pronostici Tiri & Falli", layout="wide")
st.markdown("<h1 style='color:#0b57a4;'>⚽ STAT APP — Pronostici Tiri & Falli</h1>", unsafe_allow_html=True)
st.write("Engine: EWMA + shrinkage + Poisson/Normal mixture · Seleziona squadre e arbitro (se disponibile) · Scegli linee/bookmakers e vedi EV.")

# -------------------------
# UTILITY
# -------------------------
def safe_load(path):
    try:
        return pd.read_excel(path)
    except Exception:
        return None

def find_col(df, candidates):
    if df is None: return None
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

# -------------------------
# MODELLI STATISTICI DI BASE
# -------------------------
def ewma_series(vals, span=6):
    arr = [safe_float(v) for v in vals if (v is not None and not pd.isna(v))]
    if len(arr) == 0:
        return 0.0
    s = pd.Series(arr)
    return float(s.ewm(span=span, adjust=False).mean().iloc[-1])

def shrink_estimate(estimate, prior, n, alpha=10.0):
    if n <= 0:
        return prior
    w = n / (n + alpha)
    return w * estimate + (1 - w) * prior

def sample_stdev(vals):
    try:
        arr = [safe_float(v) for v in vals if (v is not None and not pd.isna(v))]
        if len(arr) <= 1:
            return float(np.std(arr, ddof=0)) if len(arr)>0 else 0.0
        return float(np.std(arr, ddof=0))
    except Exception:
        return 0.0

def p_over_mixture(mu, sigma, threshold, w_poisson=0.6):
    # mixture of Poisson tail and continuity-corrected normal tail
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
    mix = w_poisson * p_pois + (1 - w_poisson) * p_norm
    return float(min(1.0, max(0.0, mix)))

# -------------------------
# LOAD FILES (DEVONO ESSERE NELLA ROOT)
# -------------------------
FILE_TIRI = "tiri_serie_a.xlsx"
FILE_FALLI_ITA = "falli_serie_a.xlsx"
FILE_FALLI_LIGA = "falli_liga.xlsx"

df_tiri = safe_load(FILE_TIRI)
df_falli_ita = safe_load(FILE_FALLI_ITA)
df_falli_liga = safe_load(FILE_FALLI_LIGA)

if df_tiri is None:
    st.error(f"File mancante o non leggibile: {FILE_TIRI}. Caricalo nella root del repo.")
if df_falli_ita is None:
    st.warning(f"File mancante o non leggibile: {FILE_FALLI_ITA}. Alcune funzioni falli Serie A potrebbero non funzionare.")
if df_falli_liga is None:
    st.info(f"File mancante o non leggibile: {FILE_FALLI_LIGA}. La sezione Falli Liga sarà disabilitata finché non lo carichi.")

# -------------------------
# MAPPING COLONNE (TOLLERANTE)
# -------------------------
# TIRI
tiri_team_col = find_col(df_tiri, ["squadra", "team", "team name", "squad"])
tiri_home_col = find_col(df_tiri, ["home team", "squadra_casa", "squadra casa"])
tiri_away_col = find_col(df_tiri, ["away team", "squadra_ospite", "squadra ospite"])
tiri_tot_col = find_col(df_tiri, ["tiri_tot", "tiri totali", "tiri", "total shots", "shots"])
tiri_sot_col = find_col(df_tiri, ["tiri in porta", "shots on target", "sot", "tiri_porta"])

# FALLI ITA
falli_ita_team_col = find_col(df_falli_ita, ["squadra", "team"])
falli_ita_falli_col = find_col(df_falli_ita, ["falli", "fouls", "falli_commessi"])
falli_ita_arbitro_col = find_col(df_falli_ita, ["arbitro","referee","official"])
falli_ita_arb_media_col = find_col(df_falli_ita, ["media_arbitro","avg_ref","ref_avg"])

# FALLI LIGA
falli_liga_team_col = find_col(df_falli_liga, ["squadra","team"])
falli_liga_falli_col = find_col(df_falli_liga, ["falli","fouls"])

# -------------------------
# COSTRUISCI CRONOLOGIE PER SQUADRE E ARBITRI
# team_stats[team] = {'tiri':[], 'sot':[], 'falli':[], 'falli_liga':[]}
# -------------------------
team_stats = {}
arbitri_stats = {}

def add_team_value(team, key, val):
    if team is None or pd.isna(team): return
    t = str(team).strip()
    if t == "": return
    team_stats.setdefault(t, {}).setdefault(key, []).append(safe_float(val))

# process tiri dataframe heuristically
if df_tiri is not None:
    # try aggregated per-team (common)
    if tiri_team_col and tiri_team_col in df_tiri.columns:
        for _, r in df_tiri.iterrows():
            team = r.get(tiri_team_col)
            if pd.isna(team): continue
            if tiri_tot_col and tiri_tot_col in df_tiri.columns:
                add_team_value(team, 'tiri', r.get(tiri_tot_col))
            else:
                # fallback: use numeric mean of row
                nums = r.select_dtypes(include='number')
                add_team_value(team, 'tiri', nums.mean() if len(nums)>0 else 0.0)
            if tiri_sot_col and tiri_sot_col in df_tiri.columns:
                add_team_value(team, 'sot', r.get(tiri_sot_col))
    else:
        # attempt match-level rows (home/away columns)
        for _, r in df_tiri.iterrows():
            home = r.get(tiri_home_col) if tiri_home_col in df_tiri.columns else None
            away = r.get(tiri_away_col) if tiri_away_col in df_tiri.columns else None
            # try recognize home_shots / away_shots columns
            home_shots = None
            away_shots = None
            for c in df_tiri.columns:
                cl = c.lower()
                if "home" in cl and ("shot" in cl or "tiri" in cl):
                    home_shots = r.get(c)
                if "away" in cl and ("shot" in cl or "tiri" in cl):
                    away_shots = r.get(c)
            if home is not None and not pd.isna(home):
                add_team_value(home, 'tiri', home_shots if home_shots is not None else None)
            if away is not None and not pd.isna(away):
                add_team_value(away, 'tiri', away_shots if away_shots is not None else None)

# process falli serie a
if df_falli_ita is not None:
    for _, r in df_falli_ita.iterrows():
        team = r.get(falli_ita_team_col) if falli_ita_team_col and falli_ita_team_col in df_falli_ita.columns else None
        if team is not None and not pd.isna(team):
            if falli_ita_falli_col and falli_ita_falli_col in df_falli_ita.columns:
                add_team_value(team, 'falli', r.get(falli_ita_falli_col))
        # arbitro stats
        if falli_ita_arbitro_col and falli_ita_arbitro_col in df_falli_ita.columns:
            arb = r.get(falli_ita_arbitro_col)
            if pd.notna(arb):
                arb_name = str(arb).strip()
                if falli_ita_arb_media_col and (falli_ita_arb_media_col in df_falli_ita.columns):
                    val = safe_float(r.get(falli_ita_arb_media_col))
                elif falli_ita_falli_col and (falli_ita_falli_col in df_falli_ita.columns):
                    val = safe_float(r.get(falli_ita_falli_col))
                else:
                    val = 0.0
                arbitri_stats.setdefault(arb_name, []).append(val)

# process falli liga
if df_falli_liga is not None:
    for _, r in df_falli_liga.iterrows():
        team = r.get(falli_liga_team_col) if falli_liga_team_col and (falli_liga_team_col in df_falli_liga.columns) else None
        if team is not None and not pd.isna(team):
            if falli_liga_falli_col and (falli_liga_falli_col in df_falli_liga.columns):
                add_team_value(team, 'falli_liga', r.get(falli_liga_falli_col))

# -------------------------
# SIDEBAR PARAMS (SICURI)
# -------------------------
st.sidebar.header("Parametri Modello")
span = st.sidebar.slider("Span EWMA (partite recenti)", min_value=3, max_value=12, value=6, step=1)
alpha = st.sidebar.slider("Shrink α (stabilità)", min_value=1.0, max_value=30.0, value=10.0, step=1.0)
poisson_weight = st.sidebar.slider("Peso Poisson (mixture)", min_value=0.0, max_value=1.0, value=0.6, step=0.05)
spread_default = [8.5,9.5,10.5,11.5,12.5,13.5,14.5]
spread_selected = st.sidebar.multiselect("Scegli linee/spread da valutare", spread_default, default=spread_default[:6])
st.sidebar.write("Arbitri disponibili (es.):", sorted(list(arbitri_stats.keys()))[:30])

# -------------------------
# INTERFACCIA PRINCIPALE
# -------------------------
st.subheader("Seleziona mercato, squadre e arbitro")
market = st.selectbox("Mercato", [
    "Tiri totali (partita)",
    "Tiri in porta (partita)",
    "Tiri squadra (home/away)",
    "Falli totali (partita)",
    "Falli squadra (home/away)"])

# teams list
teams = sorted(list(team_stats.keys()))
if len(teams) == 0:
    # fallback to reading team names from files
    fallback = set()
    if df_tiri is not None:
        for c in df_tiri.columns:
            if "team" in c.lower() or "squad" in c.lower():
                fallback.update(df_tiri[c].dropna().astype(str).str.strip().unique().tolist())
    teams = sorted(list(fallback))

if len(teams) == 0:
    st.error("Nessuna squadra trovata nei file. Controlla le intestazioni Excel.")
    st.stop()

col1, col2, col3 = st.columns([2,2,1])
with col1:
    home = st.selectbox("Squadra Casa", teams)
with col2:
    away = st.selectbox("Squadra Ospite", [t for t in teams if t!=home] or teams)
with col3:
    arb_choice = st.selectbox("Arbitro (opzionale)", ["(nessuno)"] + sorted(list(arbitri_stats.keys())))

st.markdown("---")

# -------------------------
# CALCOLI: aspettative e varianza
# -------------------------
def compute_expectations(home, away, key, span, alpha):
    h_vals = team_stats.get(home, {}).get(key, [])
    a_vals = team_stats.get(away, {}).get(key, [])
    mu_h_recent = ewma_series(h_vals, span=span) if len(h_vals)>0 else 0.0
    mu_a_recent = ewma_series(a_vals, span=span) if len(a_vals)>0 else 0.0
    mu_h_overall = mean(h_vals) if len(h_vals)>0 else 0.0
    mu_a_overall = mean(a_vals) if len(a_vals)>0 else 0.0
    mu_h = shrink_estimate(0.7 * mu_h_recent + 0.3 * mu_h_overall, mu_h_overall, len(h_vals), alpha)
    mu_a = shrink_estimate(0.7 * mu_a_recent + 0.3 * mu_a_overall, mu_a_overall, len(a_vals), alpha)
    mu_total = mu_h + mu_a
    sigma_h = max(0.6, sample_stdev(h_vals) if len(h_vals)>1 else max(0.6, mu_h*0.25))
    sigma_a = max(0.6, sample_stdev(a_vals) if len(a_vals)>1 else max(0.6, mu_a*0.25))
    sigma_total = math.sqrt(sigma_h**2 + sigma_a**2)
    return mu_h, mu_a, mu_total, sigma_total

# select metric key from market
if market.startswith("Tiri totali"):
    metric_key = 'tiri'
elif market.startswith("Tiri in porta"):
    metric_key = 'sot'
elif market.startswith("Tiri squadra"):
    metric_key = 'tiri'
elif market.startswith("Falli totali"):
    metric_key = 'falli' if ('falli' in team_stats.get(home, {}) or 'falli' in team_stats.get(away, {})) else 'falli_liga'
else:
    metric_key = 'falli' if ('falli' in team_stats.get(home, {}) or 'falli' in team_stats.get(away, {})) else 'falli_liga'

mu_h, mu_a, mu_total, sigma_total = compute_expectations(home, away, metric_key, span, alpha)

# adjust for referee if applicable
arb_note = ""
if metric_key.startswith("falli") and arb_choice and arb_choice != "(nessuno)":
    arb_vals = arbitri_stats.get(arb_choice, [])
    if len(arb_vals)>0:
        arb_mean = mean(arb_vals)
        arb_adj = (arb_mean - (mu_total/2.0)) * 0.5
        mu_total = mu_total + arb_adj
        arb_note = f"(Arbitro adj: {arb_adj:.2f}, arb_mean: {arb_mean:.2f})"

# -------------------------
# Evaluate spreads -> probabilities, fair odds, EV
# -------------------------
lines = sorted(set(spread_selected))
results = []
for L in lines:
    p = p_over_mixture(mu_total, sigma_total, L, w_poisson=poisson_weight)
    fair_over = (1.0 / p) if p>0 else None
    fair_under = (1.0 / (1.0 - p)) if p<1 else None
    results.append({"line": L, "p_over": p, "p_under": 1-p, "fair_odds_over": fair_over, "fair_odds_under": fair_under})

df_lines = pd.DataFrame(results)

# display table safely (no Styler)
st.subheader("Valutazione linee & probabilità")
st.dataframe(df_lines.reset_index(drop=True), use_container_width=True)

# allow user to input bookmaker odds for EV calculation
st.subheader("Confronto con quote bookmaker (opzionali)")
odds = {}
for row in df_lines.to_dict(orient='records'):
    L = row['line']
    key_o = f"odd_over_{L}"
    key_u = f"odd_under_{L}"
    cols = st.columns([1,1,1])
    with cols[0]:
        st.write(f"Linea {L}")
    with cols[1]:
        odds[key_o] = st.number_input(f"Quote BOOK OVER {L}", min_value=1.01, value=2.0, step=0.01, key=key_o)
    with cols[2]:
        odds[key_u] = st.number_input(f"Quote BOOK UNDER {L}", min_value=1.01, value=1.8, step=0.01, key=key_u)

# compute EV table
ev_rows = []
for row in df_lines.to_dict(orient='records'):
    L = row['line']
    p = row['p_over']
    odd_over = odds.get(f"odd_over_{L}", None)
    odd_under = odds.get(f"odd_under_{L}", None)
    ev_over = None
    ev_under = None
    if odd_over:
        ev_over = p * (odd_over - 1) - (1 - p)
    if odd_under:
        ev_under = (1 - p) * (odd_under - 1) - p
    ev_rows.append({"line": L, "p_over": p, "ev_over": ev_over, "p_under": 1-p, "ev_under": ev_under})

df_ev = pd.DataFrame(ev_rows)
st.subheader("Expected Value (EV) per linea")
st.dataframe(df_ev, use_container_width=True)

# recommendations: best by EV if available, else by probability
st.markdown("---")
st.subheader("Raccomandazioni")
best_over = None
best_under = None
if df_ev['ev_over'].notna().any():
    best_over = df_ev.loc[df_ev['ev_over'].idxmax()]
    best_under = df_ev.loc[df_ev['ev_under'].idxmax()]
else:
    best_over = df_lines.loc[df_lines['p_over'].idxmax()]
    best_under = df_lines.loc[df_lines['p_under'].idxmax()]

st.markdown(f"**Miglior OVER** → Linea {best_over['line']} — P(over) = {best_over['p_over']*100:.1f}%")
st.markdown(f"**Miglior UNDER** → Linea {best_under['line']} — P(under) = {best_under['p_under']*100:.1f}%")

def signal_label(p):
    if p >= 0.75: return "Molto Forte"
    if p >= 0.60: return "Forte"
    if p >= 0.55: return "Buono"
    if p >= 0.51: return "Debole"
    return "Neutro/Sconsigliato"

st.markdown("---")
st.write(f"Mu totale previsto: **{mu_total:.2f}** (home {mu_h:.2f} | away {mu_a:.2f}) {arb_note}")
st.metric("Sigma stimata", f"{sigma_total:.2f}")
st.write(f"Segnale OVER (miglior linea): **{signal_label(best_over['p_over'])}** — {best_over['p_over']*100:.1f}%")
st.write(f"Segnale UNDER (miglior linea): **{signal_label(best_under['p_under'])}** — {best_under['p_under']*100:.1f}%")

# diagnostics
st.markdown("---")
st.subheader("Diagnostica — ultime osservazioni (esempi)")
sample_home = team_stats.get(home, {}).get(metric_key, [])[-8:]
sample_away = team_stats.get(away, {}).get(metric_key, [])[-8:]
st.write(f"{home} ultime: {sample_home}")
st.write(f"{away} ultime: {sample_away}")

st.markdown("<i>Nota:</i> Il modello è avanzato ma la precisione reale dipende dalla qualità e granularità dei tuoi dati (match-by-match migliora molto). Per spingere verso 75% serve backtest, feature engineering e calibrazione — posso farlo quando sei pronto.", unsafe_allow_html=True)
