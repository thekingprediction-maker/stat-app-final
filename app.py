# app.py — STAT APP Definitivo (design bookmaker, tiri + falli + arbitri + backtest)
# Requisiti: streamlit pandas numpy scipy openpyxl

import streamlit as st
import pandas as pd
import numpy as np
import math
from statistics import mean
from scipy.stats import norm, poisson

# ---------------- page config & style (bookmaker feel)
st.set_page_config(page_title="STAT APP — Pronostici", layout="wide")
st.markdown("""
<style>
body { font-family: "Helvetica Neue", Arial, sans-serif; }
.header { color: #0b57a4; font-weight:700; font-size:32px; margin-bottom:6px; }
.sub { color:#333; margin-bottom:18px; }
.card { background: #ffffff; border-radius:10px; padding:14px; box-shadow: 0 6px 18px rgba(2,6,23,0.06); }
.bookmark-header { background: linear-gradient(90deg,#082f66,#0b57a4); color: white; padding:12px; border-radius:8px; }
.kpi { font-size:18px; font-weight:700; color:#0b57a4; }
.small { color:#666; font-size:13px; }
.btn { background:#0b57a4; color:#fff; padding:8px 12px; border-radius:6px; }
.op-card { background:#f6f9ff; padding:10px; border-radius:8px; }
.warn { background:#fff4e6; padding:8px; border-radius:6px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header">⚽ STAT APP — Pronostici Tiri & Falli</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Interfaccia stile bookmaker • EWMA + shrinkage + Poisson/Normal mixture • backtest integrato</div>', unsafe_allow_html=True)
st.markdown("---")

# ---------------- Helpers: load + mapping + numerics ----------------
@st.cache_data(ttl=900)
def safe_load(path):
    try:
        return pd.read_excel(path)
    except Exception as e:
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
    except:
        return 0.0

# Stat helpers
def ewma_series(vals, span=6):
    arr = [safe_float(v) for v in vals if v is not None and not pd.isna(v)]
    if len(arr)==0: return 0.0
    s = pd.Series(arr)
    return float(s.ewm(span=span, adjust=False).mean().iloc[-1])

def shrink_estimate(est, prior, n, alpha=10.0):
    if n<=0: return prior
    w = n/(n+alpha)
    return w*est + (1-w)*prior

def sample_stdev(vals):
    try:
        arr = [safe_float(v) for v in vals if v is not None and not pd.isna(v)]
        return float(np.std(arr, ddof=0)) if len(arr)>0 else 0.0
    except:
        return 0.0

def p_over_mixture(mu, sigma, threshold, w_poisson=0.6):
    k = math.floor(threshold)
    mu_pos = max(mu, 0.0)
    try:
        p_pois = 1.0 - poisson.cdf(k, mu_pos)
    except:
        p_pois = 0.0
    try:
        p_norm = 1.0 - norm.cdf(threshold + 0.5, loc=mu, scale=max(sigma, 0.1))
    except:
        p_norm = 0.0
    mix = w_poisson * p_pois + (1-w_poisson) * p_norm
    return float(min(1.0, max(0.0, mix)))

# ---------------- Files (root) ----------------
FILE_TIRI = "tiri_serie_a.xlsx"
FILE_FALLI_ITA = "falli_serie_a.xlsx"
FILE_FALLI_LIGA = "falli_liga.xlsx"

df_tiri = safe_load(FILE_TIRI)
df_falli_ita = safe_load(FILE_FALLI_ITA)
df_falli_liga = safe_load(FILE_FALLI_LIGA)

# show small status
cols_status = st.columns(3)
with cols_status[0]:
    st.markdown(f"<div class='op-card'><b>Tiri Serie A</b><div class='small'>{'OK' if df_tiri is not None else 'MANCANTE'}</div></div>", unsafe_allow_html=True)
with cols_status[1]:
    st.markdown(f"<div class='op-card'><b>Falli Serie A</b><div class='small'>{'OK' if df_falli_ita is not None else 'MANCANTE'}</div></div>", unsafe_allow_html=True)
with cols_status[2]:
    st.markdown(f"<div class='op-card'><b>Falli Liga</b><div class='small'>{'OK' if df_falli_liga is not None else 'MANCANTE'}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ---------------- Map common columns (tollerante) ----------------
# Tiri
tiri_team_col = find_col(df_tiri, ["squadra","team","team name"])
tiri_home_col = find_col(df_tiri, ["home team","squadra_casa","squadra casa"])
tiri_away_col = find_col(df_tiri, ["away team","squadra_ospite","squadra ospite"])
tiri_tot_col = find_col(df_tiri, ["tiri_tot","tiri totali","total shots","shots"])
tiri_sot_col = find_col(df_tiri, ["tiri in porta","shots on target","sot","tiri_porta"])

# Falli ITA
falli_ita_team_col = find_col(df_falli_ita, ["squadra","team"])
falli_ita_falli_col = find_col(df_falli_ita, ["falli","fouls","falli_commessi"])
falli_ita_arb_col = find_col(df_falli_ita, ["arbitro","referee","official"])
falli_ita_arb_mean_col = find_col(df_falli_ita, ["media_arbitro","avg_ref","ref_avg"])

# Falli LIGA
falli_liga_team_col = find_col(df_falli_liga, ["squadra","team"])
falli_liga_falli_col = find_col(df_falli_liga, ["falli","fouls"])

# ---------------- Build team histories & arbitri ----------------
team_stats = {}   # team -> keys: 'tiri','sot','falli','falli_liga'
arbitri_stats = {}  # arb -> list

def add_team_val(team, key, val):
    if team is None or pd.isna(team): return
    t = str(team).strip()
    if t== "": return
    team_stats.setdefault(t, {}).setdefault(key, []).append(safe_float(val))

# Populate from tiri sheet (agg or match)
if df_tiri is not None:
    # aggregated per team common case
    if tiri_team_col and tiri_team_col in df_tiri.columns:
        for _, r in df_tiri.iterrows():
            team = r.get(tiri_team_col)
            if pd.isna(team): continue
            if tiri_tot_col and tiri_tot_col in df_tiri.columns:
                add_team_val(team, 'tiri', r.get(tiri_tot_col))
            else:
                nums = r.select_dtypes(include='number')
                add_team_val(team, 'tiri', nums.mean() if len(nums)>0 else 0.0)
            if tiri_sot_col and tiri_sot_col in df_tiri.columns:
                add_team_val(team, 'sot', r.get(tiri_sot_col))
    else:
        # match-level heuristic
        for _, r in df_tiri.iterrows():
            home = r.get(tiri_home_col) if tiri_home_col in df_tiri.columns else None
            away = r.get(tiri_away_col) if tiri_away_col in df_tiri.columns else None
            home_sh = None; away_sh = None
            for c in df_tiri.columns:
                cl = c.lower()
                if "home" in cl and ("shot" in cl or "tiri" in cl):
                    home_sh = r.get(c)
                if "away" in cl and ("shot" in cl or "tiri" in cl):
                    away_sh = r.get(c)
            if home and not pd.isna(home):
                add_team_val(home, 'tiri', home_sh)
            if away and not pd.isna(away):
                add_team_val(away, 'tiri', away_sh)

# Populate falli serie a + arbitri
if df_falli_ita is not None:
    for _, r in df_falli_ita.iterrows():
        team = r.get(falli_ita_team_col) if falli_ita_team_col and falli_ita_team_col in df_falli_ita.columns else None
        if team is not None and not pd.isna(team):
            if falli_ita_falli_col and falli_ita_falli_col in df_falli_ita.columns:
                add_team_val(team, 'falli', r.get(falli_ita_falli_col))
        # arbitri
        if falli_ita_arb_col and falli_ita_arb_col in df_falli_ita.columns:
            arb = r.get(falli_ita_arb_col)
            if pd.notna(arb):
                name = str(arb).strip()
                if falli_ita_arb_mean_col and (falli_ita_arb_mean_col in df_falli_ita.columns):
                    val = safe_float(r.get(falli_ita_arb_mean_col))
                elif falli_ita_falli_col and (falli_ita_falli_col in df_falli_ita.columns):
                    val = safe_float(r.get(falli_ita_falli_col))
                else:
                    val = 0.0
                arbitri_stats.setdefault(name, []).append(val)

# Populate falli liga
if df_falli_liga is not None:
    for _, r in df_falli_liga.iterrows():
        team = r.get(falli_liga_team_col) if falli_liga_team_col and (falli_liga_team_col in df_falli_liga.columns) else None
        if team is not None and not pd.isna(team):
            if falli_liga_falli_col and (falli_liga_falli_col in df_falli_liga.columns):
                add_team_val(team, 'falli_liga', r.get(falli_liga_falli_col))

# ---------------- Sidebar: model params (safe)
st.sidebar.header("Parametri modello")
span = st.sidebar.slider("Span EWMA (recenti partite)", min_value=3, max_value=12, value=6, step=1)
alpha = st.sidebar.slider("Shrink α", min_value=1.0, max_value=30.0, value=10.0, step=1.0)
poisson_weight = st.sidebar.slider("Peso Poisson (mixture)", min_value=0.0, max_value=1.0, value=0.6, step=0.05)
spread_default = [8.5,9.5,10.5,11.5,12.5,13.5,14.5]
spread_selected = st.sidebar.multiselect("Linee da valutare", spread_default, default=spread_default[:5])
st.sidebar.caption("Design: colori e layout ispirati a siti bookmaker")

# ---------------- Main navigation: three sections + backtest
tab = st.tabs(["Tiri Serie A", "Falli Serie A", "Falli Liga", "Backtest & Accuracy"])

# Helper: compute expectations
def compute_expectations(home, away, key):
    h_vals = team_stats.get(home, {}).get(key, [])
    a_vals = team_stats.get(away, {}).get(key, [])
    mu_h_recent = ewma_series(h_vals, span=span) if len(h_vals)>0 else 0.0
    mu_a_recent = ewma_series(a_vals, span=span) if len(a_vals)>0 else 0.0
    mu_h_overall = mean(h_vals) if len(h_vals)>0 else 0.0
    mu_a_overall = mean(a_vals) if len(a_vals)>0 else 0.0
    mu_h = shrink_estimate(0.7*mu_h_recent + 0.3*mu_h_overall, mu_h_overall, len(h_vals), alpha)
    mu_a = shrink_estimate(0.7*mu_a_recent + 0.3*mu_a_overall, mu_a_overall, len(a_vals), alpha)
    mu_total = mu_h + mu_a
    sigma_h = max(0.6, sample_stdev(h_vals) if len(h_vals)>1 else max(0.6, mu_h*0.25))
    sigma_a = max(0.6, sample_stdev(a_vals) if len(a_vals)>1 else max(0.6, mu_a*0.25))
    sigma_total = math.sqrt(sigma_h**2 + sigma_a**2)
    return mu_h, mu_a, mu_total, sigma_total

# ---------------- Tab 1: Tiri Serie A ----------------
with tab[0]:
    st.markdown("<div class='card'><b>Tiri — Serie A</b></div>", unsafe_allow_html=True)
    # teams from team_stats (tiri entries)
    teams = sorted(list(team_stats.keys()))
    if len(teams)==0:
        st.warning("Nessuna squadra trovata nei dati tiri.")
    home = st.selectbox("Casa", teams)
    away = st.selectbox("Ospite", [t for t in teams if t!=home] or teams)
    st.write("Scegli linee da valutare (spread):", spread_selected)
    if home and away:
        mu_h, mu_a, mu_total, sigma_total = compute_expectations(home, away, 'tiri')
        st.markdown(f"**Atteso totale tiri:** {mu_total:.2f} (casa {mu_h:.2f} | ospite {mu_a:.2f})")
        st.markdown(f"**Sigma stimata:** {sigma_total:.2f}")
        # calc for each line
        rows = []
        for L in sorted(spread_selected):
            p = p_over_mixture(mu_total, sigma_total, L, w_poisson=poisson_weight)
            rows.append({"line": L, "p_over": round(p,3), "p_under": round(1-p,3)})
        st.table(pd.DataFrame(rows))
        best = max(rows, key=lambda r: r['p_over'])
        st.success(f"Miglior OVER consigliato linea {best['line']} — P={best['p_over']*100:.1f}%")

# ---------------- Tab 2: Falli Serie A ----------------
with tab[1]:
    st.markdown("<div class='card'><b>Falli — Serie A</b></div>", unsafe_allow_html=True)
    teams_f = sorted(list(team_stats.keys()))
    if len(teams_f)==0:
        st.warning("Nessuna squadra trovata nei dati falli.")
    home_f = st.selectbox("Casa (Falli Serie A)", teams_f, key="home_f")
    away_f = st.selectbox("Ospite (Falli Serie A)", [t for t in teams_f if t!=home_f] or teams_f, key="away_f")
    # arbitro selezionabile
    arb_list = ["(nessuno)"] + sorted(list(arbitri_stats.keys()))
    arb_sel = st.selectbox("Arbitro (influenza falli)", arb_list)
    if home_f and away_f:
        mu_h, mu_a, mu_total, sigma_total = compute_expectations(home_f, away_f, 'falli')
        # adjust for arb
        arb_note = ""
        if arb_sel and arb_sel != "(nessuno)" and arb_sel in arbitri_stats:
            arb_mean = mean(arbitri_stats[arb_sel])
            adj = (arb_mean - (mu_total/2.0)) * 0.5
            mu_total += adj
            arb_note = f"(adj arbitro: {adj:.2f})"
        st.markdown(f"**Atteso totale falli:** {mu_total:.2f} {arb_note}")
        st.markdown(f"**Sigma stimata:** {sigma_total:.2f}")
        rows = []
        for L in sorted(spread_selected):
            p = p_over_mixture(mu_total, sigma_total, L, w_poisson=poisson_weight)
            rows.append({"line": L, "p_over": round(p,3), "p_under": round(1-p,3)})
        st.table(pd.DataFrame(rows))
        best = max(rows, key=lambda r: r['p_over'])
        st.success(f"Miglior OVER falli: linea {best['line']} — P={best['p_over']*100:.1f}%")

# ---------------- Tab 3: Falli Liga ----------------
with tab[2]:
    st.markdown("<div class='card'><b>Falli — Liga (Spagna)</b></div>", unsafe_allow_html=True)
    teams_l = sorted(list(team_stats.keys()))
    home_l = st.selectbox("Casa (Liga)", teams_l, key="home_l")
    away_l = st.selectbox("Ospite (Liga)", [t for t in teams_l if t!=home_l] or teams_l, key="away_l")
    if home_l and away_l:
        mu_h, mu_a, mu_total, sigma_total = compute_expectations(home_l, away_l, 'falli_liga')
        st.markdown(f"**Atteso totale falli (Liga):** {mu_total:.2f}")
        st.markdown(f"**Sigma stimata:** {sigma_total:.2f}")
        rows = []
        for L in sorted(spread_selected):
            p = p_over_mixture(mu_total, sigma_total, L, w_poisson=poisson_weight)
            rows.append({"line": L, "p_over": round(p,3), "p_under": round(1-p,3)})
        st.table(pd.DataFrame(rows))
        best = max(rows, key=lambda r: r['p_over'])
        st.success(f"Miglior OVER falli Liga: linea {best['line']} — P={best['p_over']*100:.1f}%")

# ---------------- Tab 4: Backtest & Accuracy ----------------
with tab[3]:
    st.markdown("<div class='card'><b>Backtest & Accuracy</b></div>", unsafe_allow_html=True)
    st.write("Esegue un semplice backtest se il tuo file contiene righe match-by-match con colonne Home/Away e valori per tiri/falli.")
    st.write("Se i tuoi file sono *aggregati* (una riga per squadra), il backtest storico non può essere eseguito: serve storico partita-per-partita.")
    # try detect match-level tiri file
    match_level = False
    if df_tiri is not None:
        if (tiri_home_col in df_tiri.columns) and (tiri_away_col in df_tiri.columns):
            match_level = True
    if not match_level:
        st.info("Backtest non possibile: i tuoi file sembrano aggregati (non match-by-match). Per backtest servono righe match-per-partita.")
    else:
        st.subheader("Backtest Tiri — usa colonna tiri totale (per squadra) se presente")
        # detect column names for numeric tiri home/away in match-level
        # Try to find columns containing 'home' and 'shot' or 'tiri' and same for away
        home_sh_cols = [c for c in df_tiri.columns if "home" in c.lower() and ("shot" in c.lower() or "tiri" in c.lower())]
        away_sh_cols = [c for c in df_tiri.columns if "away" in c.lower() and ("shot" in c.lower() or "tiri" in c.lower())]
        if len(home_sh_cols)==0 or len(away_sh_cols)==0:
            st.info("Non trovo colonne chiare home_shots/away_shots nel file tiri. Se hai colonne match-level chiamami e le mappo.")
        else:
            hcol = home_sh_cols[0]; acol = away_sh_cols[0]
            st.write(f"Usando colonne: home={hcol} | away={acol}")
            # choose threshold for backtest
            thr = st.number_input("Soglia per OVER (es. 22.5 tiri tot.)", value=22.5, step=0.5)
            window = st.slider("Span EWMA usato nel backtest", 3, 12, 6)
            # run historical predicted vs real
            df_hist = df_tiri.copy().reset_index(drop=True)
            preds = []
            actuals = []
            # iterate rows and simulate online prediction using previous matches only (simple approach)
            # We'll build rolling averages per team
            hist_team = {}
            for idx, row in df_hist.iterrows():
                home_team = row.get(tiri_home_col)
                away_team = row.get(tiri_away_col)
                if pd.isna(home_team) or pd.isna(away_team):
                    preds.append(None); actuals.append(None); continue
                ht = str(home_team).strip(); at = str(away_team).strip()
                # compute mu from current hist_team
                h_vals = hist_team.get(ht, [])
                a_vals = hist_team.get(at, [])
                mu_h = ewma_series(h_vals, span=window) if len(h_vals)>0 else (mean(h_vals) if len(h_vals)>0 else 0.0)
                mu_a = ewma_series(a_vals, span=window) if len(a_vals)>0 else (mean(a_vals) if len(a_vals)>0 else 0.0)
                mu_pred = mu_h + mu_a
                # store pred
                p = p_over_mixture(mu_pred, max(0.8, math.sqrt((np.std(h_vals) if len(h_vals)>1 else mu_h*0.25)**2 + (np.std(a_vals) if len(a_vals)>1 else mu_a*0.25)**2)), thr, w_poisson=poisson_weight)
                preds.append(p)
                # actual total from file
                real_h = safe_float(row.get(hcol)); real_a = safe_float(row.get(acol))
                actual_total = real_h + real_a
                actuals.append(1 if actual_total > thr else 0)
                # update hist_team with actuals (we feed model with reality after prediction)
                hist_team.setdefault(ht, []).append(real_h)
                hist_team.setdefault(at, []).append(real_a)
            # compute accuracy for a chosen decision rule p>=0.58 -> predict OVER
            df_bt = pd.DataFrame({"pred_p": preds, "actual_over": actuals})
            df_bt = df_bt.dropna()
            if df_bt.empty:
                st.info("Backtest non ha prodotto righe utili.")
            else:
                threshold_p = st.slider("Soglia probabilità per considerare OVER (es. 0.58)", 0.5, 0.9, 0.58, 0.01)
                df_bt['pred_over'] = df_bt['pred_p'] >= threshold_p
                accuracy = (df_bt['pred_over'] == df_bt['actual_over']).mean()
                st.metric("Accuracy backtest", f"{accuracy*100:.2f}%")
                st.write("Dettaglio backtest (prime righe):")
                st.dataframe(df_bt.head(200))

st.markdown("---")
st.markdown("<div class='small'>Nota: il target 75% è ambizioso. Per raggiungerlo servono dati match-by-match estesi, feature engineering (formazioni, infortuni, motivazione), calibrazione parametri e backtest iterativo. Questo tool fornisce l'infrastruttura per arrivarci.</div>", unsafe_allow_html=True)
