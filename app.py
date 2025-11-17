# app.py — Advanced pronostici Tiri & Falli (usa i tuoi 3 file Excel)
import streamlit as st
import pandas as pd
import numpy as np
import math
from statistics import mean
from scipy.stats import norm, poisson

st.set_page_config(page_title="STAT APP - Advanced", layout="wide")
st.markdown("<h1 style='text-align:center;color:#0b57a4;'>⚽ STAT APP — Pronostici Tiri & Falli</h1>", unsafe_allow_html=True)
st.write("Modello: EWMA + shrinkage + Poisson/Normal mixture · Seleziona squadre e arbitro per risultati più precisi.")

# ---------------------------
# Config: nomi file (devi avere questi nella root del repo)
# ---------------------------
FILE_TIRI = "tiri_serie_a.xlsx"
FILE_FALLI_ITA = "falli_serie_a.xlsx"
FILE_FALLI_LIGA = "falli_liga.xlsx"

# ---------------------------
# Helpers: mapping e funzioni statistiche
# ---------------------------
def find_col(df, candidates):
    if df is None: 
        return None
    cols = list(df.columns)
    low = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in low:
            return low[cand.lower()]
    # match by substring
    for cand in candidates:
        k = cand.lower()
        for c in cols:
            if k in c.lower():
                return c
    return None

def safe_float(x):
    try:
        return float(x)
    except:
        return 0.0

def ewma(values, span=6):
    vals = [safe_float(v) for v in values if pd.notna(v)]
    if len(vals) == 0:
        return 0.0
    s = pd.Series(vals)
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

def p_over_mixture(mu, sigma, threshold, w_poisson=0.6):
    # Poisson tail
    # poisson.cdf(k, mu) gives P(X<=k) for integer k; for half-threshold use floor
    k = math.floor(threshold)
    try:
        p_pois = 1.0 - poisson.cdf(k, max(mu, 0.0))
    except Exception:
        p_pois = 0.0
    # Normal tail with continuity correction:
    try:
        p_norm = 1.0 - norm.cdf(threshold + 0.5, loc=mu, scale=max(sigma, 0.1))
    except Exception:
        p_norm = 0.0
    return w_poisson * p_pois + (1 - w_poisson) * p_norm

# ---------------------------
# Load files (tollerante)
# ---------------------------
@st.cache_data(ttl=900)
def load_excel(path):
    try:
        return pd.read_excel(path)
    except Exception as e:
        return None

df_tiri = load_excel(FILE_TIRI)
df_falli_ita = load_excel(FILE_FALLI_ITA)
df_falli_liga = load_excel(FILE_FALLI_LIGA)

# status files
if df_tiri is None:
    st.error(f"File non trovato o non leggibile: {FILE_TIRI}. Caricalo nella root del repo.")
if df_falli_ita is None:
    st.warning(f"File non trovato o non leggibile: {FILE_FALLI_ITA}. Alcune funzioni falli Serie A disabilitate.")
if df_falli_liga is None:
    st.info(f"File non trovato o non leggibile: {FILE_FALLI_LIGA}. Se vuoi analizzare la Liga caricalo.")

# ---------------------------
# Detect columns (tollerante)
# ---------------------------
# TIRI
tiri_team_col = find_col(df_tiri, ["squadra", "team", "team name", "squad"])
tiri_tot_col  = find_col(df_tiri, ["tiri_tot", "tiri totali", "tiri", "tiri_totali", "tiri_tot"])
tiri_sot_col  = find_col(df_tiri, ["tiri in porta", "sot", "shots on target", "tiri_porta", "tiri_in_porta"])

# FALLI SERIE A
falli_ita_team_col = find_col(df_falli_ita, ["squadra", "team"])
falli_ita_falli_col = find_col(df_falli_ita, ["falli", "fouls", "falli_commessi"])
falli_ita_arbitro_col = find_col(df_falli_ita, ["arbitro", "referee"])
falli_ita_arb_media_col = find_col(df_falli_ita, ["media_arbitro", "avg_ref", "media_arbitro"])

# FALLI LIGA
falli_liga_team_col = find_col(df_falli_liga, ["squadra", "team"])
falli_liga_falli_col = find_col(df_falli_liga, ["falli", "fouls"])

# show detected mapping on sidebar
st.sidebar.subheader("Mapping colonne (rilevate)")
st.sidebar.write("Tiri:", {"team": tiri_team_col, "tiri_tot": tiri_tot_col, "tiri_sot": tiri_sot_col})
st.sidebar.write("Falli Serie A:", {"team": falli_ita_team_col, "falli": falli_ita_falli_col, "arbitro": falli_ita_arbitro_col, "arb_media": falli_ita_arb_media_col})
st.sidebar.write("Falli Liga:", {"team": falli_liga_team_col, "falli": falli_liga_falli_col})

# ---------------------------
# Build team history dictionaries
# ---------------------------
team_stats = {}   # team -> {'tiri':[...], 'sot':[...], 'falli':[...]}
arbitri_stats = {}  # arb -> [values]

def add_team_value(team, key, value):
    if team is None or team=="" or pd.isna(team):
        return
    team = str(team).strip()
    team_stats.setdefault(team, {}).setdefault(key, []).append(safe_float(value))

# build from tiri df
if df_tiri is not None and tiri_team_col is not None:
    for _, r in df_tiri.iterrows():
        try:
            team = r.get(tiri_team_col)
            if pd.isna(team): continue
            team = str(team).strip()
            if tiri_tot_col in df_tiri.columns:
                add_team_value(team, 'tiri', r.get(tiri_tot_col))
            if tiri_sot_col in df_tiri.columns:
                add_team_value(team, 'sot', r.get(tiri_sot_col))
        except Exception:
            continue

# build from falli Serie A df
if df_falli_ita is not None and falli_ita_team_col is not None:
    for _, r in df_falli_ita.iterrows():
        try:
            team = r.get(falli_ita_team_col)
            if pd.isna(team): continue
            team = str(team).strip()
            if falli_ita_falli_col in df_falli_ita.columns:
                add_team_value(team, 'falli', r.get(falli_ita_falli_col))
            # arb stats
            if falli_ita_arbitro_col in df_falli_ita.columns:
                arb = r.get(falli_ita_arbitro_col)
                if pd.notna(arb):
                    arb = str(arb).strip()
                    # arb mean if exists else use falli value
                    if falli_ita_arb_media_col in df_falli_ita.columns:
                        val = safe_float(r.get(falli_ita_arb_media_col))
                    elif falli_ita_falli_col in df_falli_ita.columns:
                        val = safe_float(r.get(falli_ita_falli_col))
                    else:
                        val = 0.0
                    arbitri_stats.setdefault(arb, []).append(val)
        except Exception:
            continue

# build from falli liga
if df_falli_liga is not None and falli_liga_team_col is not None:
    for _, r in df_falli_liga.iterrows():
        try:
            team = r.get(falli_liga_team_col)
            if pd.isna(team): continue
            team = str(team).strip()
            if falli_liga_falli_col in df_falli_liga.columns:
                add_team_value(team, 'falli_liga', r.get(falli_liga_falli_col))
        except Exception:
            continue

# ---------------------------
# UI controls
# ---------------------------
st.sidebar.header("Parametri Modello")
span = st.sidebar.slider("Span EWMA (partite recenti)", 3, 12, 6)
alpha_shrink = st.sidebar.slider("Shrink α (stabilità)", 1.0, 30.0, 10.0)
poisson_weight = st.sidebar.slider("Peso Poisson (mixture)", 0.0, 1.0, 60) / 100.0  # 0..1
spread_choices = st.sidebar.multiselect("Linee/spread da valutare (esempio)", [8.5,9.5,10.5,11.5,12.5,13.5,14.5,15.5,16.5,17.5,18.5,19.5,20.5,21.5,22.5], default=[9.5,10.5,11.5,12.5,13.5,14.5,15.5])
market = st.sidebar.selectbox("Mercato", ["Tiri totali (partita)", "Tiri in porta (partita)", "Tiri squadra (home/away)", "Falli totali (partita)", "Falli squadra (home/away)"])
st.sidebar.write("Arbitri disponibili (Serie A):", sorted(list(arbitri_stats.keys()))[:20])

st.markdown("---")
st.subheader("Seleziona matchup e parametri")

teams_available = sorted(team_stats.keys())
if len(teams_available)==0:
    st.warning("Nessuna squadra trovata nei file. Controlla le intestazioni dei file Excel.")
home = st.selectbox("Squadra casa", teams_available) if teams_available else ""
away = st.selectbox("Squadra ospite", teams_available) if teams_available else ""
arb_choice = None
if len(arbitri_stats)>0:
    arb_choice = st.selectbox("Arbitro (opzionale)", ["(nessuno)"] + sorted(arbitri_stats.keys()))
else:
    st.info("Dati arbitro non disponibili o non rilevati automaticamente.")

# ---- helper per expected per match ----
def expected_match_mu_sigma(home, away, metric_key, span, alpha):
    # metric_key: 'tiri','sot','falli','falli_liga'
    h_vals = team_stats.get(home, {}).get(metric_key, [])
    a_vals = team_stats.get(away, {}).get(metric_key, [])
    mu_h_recent = ewma(h_vals, span=span) if len(h_vals)>0 else 0.0
    mu_a_recent = ewma(a_vals, span=span) if len(a_vals)>0 else 0.0
    mu_h_overall = mean(h_vals) if len(h_vals)>0 else 0.0
    mu_a_overall = mean(a_vals) if len(a_vals)>0 else 0.0
    mu_h = shrink(0.7 * mu_h_recent + 0.3 * mu_h_overall, mu_h_overall, len(h_vals), alpha)
    mu_a = shrink(0.7 * mu_a_recent + 0.3 * mu_a_overall, mu_a_overall, len(a_vals), alpha)
    mu_total = mu_h + mu_a
    sigma_h = max(0.6, pstdev(h_vals) if len(h_vals)>1 else max(0.6, mu_h * 0.25))
    sigma_a = max(0.6, pstdev(a_vals) if len(a_vals)>1 else max(0.6, mu_a * 0.25))
    sigma_total = math.sqrt(sigma_h ** 2 + sigma_a ** 2)
    return mu_h, mu_a, mu_total, sigma_total

# ---------------------------
# Compute & display results
# ---------------------------
if home and away:
    st.markdown(f"### Match: **{home}**  vs  **{away}**")
    # choose metric key mapping
    if market.startswith("Tiri totali"):
        key = 'tiri'
    elif market.startswith("Tiri in porta"):
        key = 'sot'
    elif market.startswith("Tiri squadra"):
        key = 'tiri'
    elif market.startswith("Falli totali"):
        # prefer Serie A falli if present else use liga
        key = 'falli' if ('falli' in team_stats.get(home,{})) or ('falli' in team_stats.get(away,{})) else 'falli_liga'
    else:  # falli squadra
        key = 'falli' if ('falli' in team_stats.get(home,{})) or ('falli' in team_stats.get(away,{})) else 'falli_liga'

    mu_h, mu_a, mu_total, sigma_total = expected_match_mu_sigma(home, away, key, span, alpha_shrink)

    # if falli and arb present, adjust mu_total with arb effect
    arb_adj_text = ""
    if market.startswith("Falli") and arb_choice and arb_choice != "(nessuno)":
        arb_vals = arbitri_stats.get(arb_choice, [])
        if len(arb_vals)>0:
            arb_mean = mean(arb_vals)
            # shift: arb_mean influences total moderately
            arb_adj = (arb_mean - (mu_total/2.0)) * 0.5
            mu_total = mu_total + arb_adj
            arb_adj_text = f"(Arbitro adj: {arb_adj:.2f}, arb_mean: {arb_mean:.2f})"

    st.write(f"Mu home: {mu_h:.2f} | Mu away: {mu_a:.2f} | Mu total: {mu_total:.2f} {arb_adj_text}")
    st.write(f"Sigma totale stimata: {sigma_total:.2f}")

    # evaluate each spread and produce table
    lines = sorted(set(spread_choices))
    results = []
    for L in lines:
        p = p_over_mixture(mu_total, sigma_total, L, w_poisson=poisson_weight)
        # implied fair odds (decimal) for over
        fair_odds = (1.0 / p) if p>0 else None
        results.append({"line": L, "p_over": p, "p_under": 1-p, "fair_odds_over": fair_odds})

    df_lines = pd.DataFrame(results)
    # mark best line by highest probability of chosen side (user likely plays over)
    # we'll compute best over and best under
    best_over = df_lines.loc[df_lines["p_over"].idxmax()]
    best_under = df_lines.loc[df_lines["p_under"].idxmax()]

    # Display recommended lines
    st.markdown("#### Risultati per linee selezionate")
    colA, colB = st.columns([2,3])
    with colA:
        st.write("Tabella linee")
        st.dataframe(df_lines.style.format({"line":"{:.1f}", "p_over":"{:.3f}", "p_under":"{:.3f}", "fair_odds_over":"{:.2f}"}))
    with colB:
        st.markdown("**Consigli rapidi**")
        st.markdown(f"- **Miglior OVER**: Linea {best_over['line']} → P(over) = {best_over['p_over']*100:.1f}%  (fair odds ≈ {best_over['fair_odds_over']:.2f})")
        st.markdown(f"- **Miglior UNDER**: Linea {best_under['line']} → P(under) = {best_under['p_under']*100:.1f}%")

    # Simple judgement thresholds
    st.markdown("---")
    st.subheader("Segnali")
    def signal_from_p(p):
        if p >= 0.70:
            return "Forte"
        elif p >= 0.58:
            return "Buono"
        elif p >= 0.50:
            return "Moderato"
        else:
            return "Debole"

    st.write(f"Segnale OVER sulla miglior linea: {signal_from_p(best_over['p_over'])} ({best_over['p_over']*100:.1f}%)")
    st.write(f"Segnale UNDER sulla miglior linea: {signal_from_p(best_under['p_under'])} ({best_under['p_under']*100:.1f}%)")

    # diagnostics: recent values
    st.markdown("---")
    st.subheader("Diagnostica (ultime osservazioni sample)")
    s_home = team_stats.get(home, {}).get(key, [])[-8:]
    s_away = team_stats.get(away, {}).get(key, [])[-8:]
    st.write(f"Ultimi {len(s_home)} - {home}: {s_home}")
    st.write(f"Ultimi {len(s_away)} - {away}: {s_away}")

else:
    st.info("Seleziona squadra casa e squadra ospite per visualizzare pronostici.")
