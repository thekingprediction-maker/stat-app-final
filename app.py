# app.py — STAT APP robusta (auto-detect fogli) 
# Requisiti: streamlit pandas numpy scipy openpyxl
import streamlit as st
import pandas as pd
import numpy as np
import math
import os
from statistics import mean
from scipy.stats import norm, poisson

st.set_page_config(page_title="STAT APP — Pronostici Tiri & Falli", layout="wide")
st.markdown("<h1 style='color:#0b57a4;'>⚽ STAT APP — Pronostici Tiri & Falli</h1>", unsafe_allow_html=True)
st.write("Engine: EWMA + shrinkage + Poisson/Normal mixture · selezione arbitro per falli · backtest integrato")

# -----------------------------
# Cerca automaticamente un file Excel nella root del repo
# Se preferisci un nome fisso, metti qui 'data_all.xlsx' o il nome che vuoi
POSSIBLE_FILES = ["dati tiri e falli serie a e liga.xlsx", "data_all.xlsx", "mega_file.xlsx",
                  "tiri_serie_a.xlsx","falli_serie_a.xlsx","falli_liga.xlsx"]

def find_excel():
    # cerca file nell'area di lavoro /app o /workspace oppure /mnt/data
    search_paths = [".", "/workspace", "/app", "/mnt/data"]
    for p in search_paths:
        try:
            for fname in os.listdir(p):
                lower = fname.lower()
                if lower.endswith(".xlsx") or lower.endswith(".xls"):
                    # preferisci nomi in POSSIBLE_FILES
                    if fname in POSSIBLE_FILES:
                        return os.path.join(p, fname)
            # se non trovi preferisci, prendi il primo excel trovato
            for fname in os.listdir(p):
                lower = fname.lower()
                if lower.endswith(".xlsx") or lower.endswith(".xls"):
                    return os.path.join(p, fname)
        except Exception:
            continue
    return None

EXCEL_PATH = find_excel()
if EXCEL_PATH is None:
    st.error("Nessun file Excel trovato nella root. Carica qui il file unico con tutti i dati o i tre file separati.")
    st.stop()

st.info(f"Uso file: {os.path.basename(EXCEL_PATH)}")

# -----------------------------
# Carica tutte le sheet e cerca i fogli utili
# -----------------------------
@st.cache_data(ttl=600)
def load_all_sheets(path):
    try:
x = pd.read_excel(path, sheet_name=None)
        return x
    except Exception as e:
        return None

sheets = load_all_sheets(EXCEL_PATH)
if sheets is None:
    st.error("Errore leggendo il file Excel. Controlla che non sia protetto e che sia .xlsx.")
    st.stop()

# funzione helper per trovare foglio con parola chiave
def sheet_by_keyword(keywords):
    for name, df in sheets.items():
        lname = name.lower()
        for kw in keywords:
            if kw in lname:
                return name, df
    # fallback: try to find by column names
    for name, df in sheets.items():
        cols = " ".join([c.lower() for c in df.columns])
        for kw in keywords:
            if kw in cols:
                return name, df
    return None, None

# identifica fogli
tiri_sheet_name, df_tiri = sheet_by_keyword(["tiri", "shots", "shots_on", "shoot"])
falli_ita_sheet_name, df_falli_ita = sheet_by_keyword(["falli", "fouls", "arbitro", "referee", "serie a", "serie_a"])
falli_liga_sheet_name, df_falli_liga = sheet_by_keyword(["liga", "spagna", "spain", "laliga", "la liga", "falli_liga"])

# se non trovati, prova a prendere altri fogli in ordine
if df_tiri is None:
    # try first sheet that contains numeric columns
    for name, df in sheets.items():
        if df.shape[1] >= 3:
            df_tiri = df; tiri_sheet_name = name; break
if df_falli_ita is None:
    for name, df in sheets.items():
        if "arbitro" in " ".join([c.lower() for c in df.columns]) or "referee" in " ".join([c.lower() for c in df.columns]):
            df_falli_ita = df; falli_ita_sheet_name = name; break
if df_falli_liga is None:
    # try any sheet with 'liga' or 'spain' in name
    for name, df in sheets.items():
        if 'liga' in name.lower() or 'spain' in name.lower() or 'la liga' in name.lower():
            df_falli_liga = df; falli_liga_sheet_name = name; break

# show mapping summary
st.sidebar.header("File & sheet trovati")
st.sidebar.write("Excel:", os.path.basename(EXCEL_PATH))
st.sidebar.write("Tiri sheet:", tiri_sheet_name)
st.sidebar.write("Falli SA sheet:", falli_ita_sheet_name)
st.sidebar.write("Falli Liga sheet:", falli_liga_sheet_name)

# -----------------------------
# mapping colonne tollerante
# -----------------------------
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

# TIRI
tiri_team_col = find_col(df_tiri, ["squadra","team","team name"]) if df_tiri is not None else None
tiri_home_col = find_col(df_tiri, ["home team","squadra_casa","home"]) if df_tiri is not None else None
tiri_away_col = find_col(df_tiri, ["away team","squadra_ospite","away"]) if df_tiri is not None else None
tiri_tot_col = find_col(df_tiri, ["tiri_tot","tiri totali","total shots","shots"]) if df_tiri is not None else None
tiri_sot_col = find_col(df_tiri, ["tiri in porta","shots on target","sot","shots_on_target"]) if df_tiri is not None else None

# FALLI ITA
falli_ita_team_col = find_col(df_falli_ita, ["squadra","team"]) if df_falli_ita is not None else None
falli_ita_falli_col = find_col(df_falli_ita, ["falli","fouls","falli_commessi"]) if df_falli_ita is not None else None
falli_ita_arb_col = find_col(df_falli_ita, ["arbitro","referee","official"]) if df_falli_ita is not None else None
falli_ita_arb_mean_col = find_col(df_falli_ita, ["media_arbitro","avg_ref","ref_avg"]) if df_falli_ita is not None else None

# FALLI LIGA
falli_liga_team_col = find_col(df_falli_liga, ["squadra","team"]) if df_falli_liga is not None else None
falli_liga_falli_col = find_col(df_falli_liga, ["falli","fouls"]) if df_falli_liga is not None else None

# -----------------------------
# Build histories
# -----------------------------
team_stats = {}
arbitri_stats = {}

def add_team_val(team, key, val):
    if team is None or pd.isna(team): return
    t = str(team).strip()
    if t == "": return
    team_stats.setdefault(t, {}).setdefault(key, []).append(safe_float(val))

# populate from tiri sheet (aggregated or match-level)
if df_tiri is not None:
    if tiri_team_col and tiri_team_col in df_tiri.columns and tiri_tot_col and tiri_tot_col in df_tiri.columns:
        # aggregated per-team
        for _, r in df_tiri.iterrows():
            team = r.get(tiri_team_col)
            if pd.isna(team): continue
            add_team_val(team, 'tiri', r.get(tiri_tot_col))
            if tiri_sot_col and tiri_sot_col in df_tiri.columns:
                add_team_val(team, 'sot', r.get(tiri_sot_col))
    else:
        # try match-level: detect home/away shot columns
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

# falli serie a
if df_falli_ita is not None:
    for _, r in df_falli_ita.iterrows():
        team = r.get(falli_ita_team_col) if falli_ita_team_col in df_falli_ita.columns else None
        if team is not None and not pd.isna(team):
            if falli_ita_falli_col and falli_ita_falli_col in df_falli_ita.columns:
                add_team_val(team, 'falli', r.get(falli_ita_falli_col))
        # arbitri stats
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

# falli liga
if df_falli_liga is not None:
    for _, r in df_falli_liga.iterrows():
        team = r.get(falli_liga_team_col) if falli_liga_team_col and (falli_liga_team_col in df_falli_liga.columns) else None
        if team is not None and not pd.isna(team):
            if falli_liga_falli_col and (falli_liga_falli_col in df_falli_liga.columns):
                add_team_val(team, 'falli_liga', r.get(falli_liga_falli_col))

# -----------------------------
# MODEL helpers
# -----------------------------
def ewma(vals, span=6):
    arr = [safe_float(v) for v in vals if v is not None and not pd.isna(v)]
    if len(arr)==0: return 0.0
    s = pd.Series(arr)
    return float(s.ewm(span=span, adjust=False).mean().iloc[-1])

def shrink_est(est, prior, n, alpha=10.0):
    if n<=0: return prior
    w = n/(n+alpha)
    return w*est + (1-w)*prior

def pstdev(vals):
    try:
        arr = [safe_float(v) for v in vals if v is not None and not pd.isna(v)]
        return float(pd.Series(arr).std(ddof=0)) if len(arr)>0 else 0.0
    except:
        return 0.0

def p_over_mix(mu, sigma, thresh, w_pois=0.6):
    k = math.floor(thresh)
    mu_pos = max(mu, 0.0)
    try:
        p_p = 1.0 - poisson.cdf(k, mu_pos)
    except:
        p_p = 0.0
    try:
        p_n = 1.0 - norm.cdf(thresh + 0.5, loc=mu, scale=max(sigma,0.1))
    except:
        p_n = 0.0
    return float(min(1.0, max(0.0, w_pois*p_p + (1-w_pois)*p_n)))

# -----------------------------
# Sidebar params
# -----------------------------
st.sidebar.header("Parametri modello")
span = st.sidebar.slider("Span EWMA", 3, 12, value=6)
alpha = st.sidebar.slider("Shrink α", 1.0, 30.0, value=10.0)
w_p = st.sidebar.slider("Peso Poisson (mixture)", 0.0, 1.0, 0.6)
spreads = st.sidebar.multiselect("Linee (spread) da valutare", [8.5,9.5,10.5,11.5,12.5,13.5,14.5], default=[9.5,10.5,11.5,12.5])
st.sidebar.write("Arbitri rilevati (Serie A):", sorted(list(arbitri_stats.keys()))[:30])

# -----------------------------
# Main UI: menu con tre sezioni
# -----------------------------
st.markdown("### Seleziona sezione")
section = st.selectbox("Sezione", ["Tiri Serie A", "Falli Serie A", "Falli Liga", "Backtest"])

def compute_expect(home, away, key):
    h_vals = team_stats.get(home, {}).get(key, [])
    a_vals = team_stats.get(away, {}).get(key, [])
    mu_h_recent = ewma(h_vals, span=span) if len(h_vals)>0 else 0.0
    mu_a_recent = ewma(a_vals, span=span) if len(a_vals)>0 else 0.0
    mu_h_overall = mean(h_vals) if len(h_vals)>0 else 0.0
    mu_a_overall = mean(a_vals) if len(a_vals)>0 else 0.0
    mu_h = shrink_est(0.7*mu_h_recent + 0.3*mu_h_overall, mu_h_overall, len(h_vals), alpha)
    mu_a = shrink_est(0.7*mu_a_recent + 0.3*mu_a_overall, mu_a_overall, len(a_vals), alpha)
    mu_tot = mu_h + mu_a
    sigma_h = max(0.6, pstdev(h_vals) if len(h_vals)>1 else max(0.6, mu_h*0.25))
    sigma_a = max(0.6, pstdev(a_vals) if len(a_vals)>1 else max(0.6, mu_a*0.25))
    sigma_tot = math.sqrt(sigma_h**2 + sigma_a**2)
    return mu_h, mu_a, mu_tot, sigma_tot

# teams list build
teams = sorted(list(team_stats.keys()))
if len(teams)==0:
    st.error("Nessuna squadra trovata nei dati. Controlla il file Excel e le intestazioni.")
    st.stop()

# UI per sezione
if section == "Tiri Serie A":
    st.header("Tiri — Serie A")
    home = st.selectbox("Casa", teams)
    away = st.selectbox("Ospite", [t for t in teams if t!=home] or teams)
    if home and away:
        mu_h, mu_a, mu, sigma = compute_expect(home, away, 'tiri')
        st.write(f"Atteso tiri totali: {mu:.2f} (home {mu_h:.2f} | away {mu_a:.2f}) — sigma {sigma:.2f}")
        rows = []
        for L in sorted(spreads):
            p = p_over_mix(mu, sigma, L, w_p)
            rows.append({"line": L, "p_over": round(p,3), "p_under": round(1-p,3)})
        st.table(pd.DataFrame(rows))
elif section == "Falli Serie A":
    st.header("Falli — Serie A")
    home = st.selectbox("Casa", teams, key="home_fa")
    away = st.selectbox("Ospite", [t for t in teams if t!=home] or teams, key="away_fa")
    arb_list = ["(nessuno)"] + sorted(list(arbitri_stats.keys()))
    arb = st.selectbox("Arbitro (opzionale)", arb_list)
    if home and away:
        mu_h, mu_a, mu, sigma = compute_expect(home, away, 'falli')
        arb_note = ""
        if arb and arb != "(nessuno)" and arb in arbitri_stats:
            arb_mean = mean(arbitri_stats[arb])
            adj = (arb_mean - (mu/2.0)) * 0.5
            mu = mu + adj
            arb_note = f"(arb adj {adj:.2f}, arb_mean {arb_mean:.2f})"
        st.write(f"Atteso falli totali: {mu:.2f} {arb_note} — sigma {sigma:.2f}")
        rows = []
        for L in sorted(spreads):
            p = p_over_mix(mu, sigma, L, w_p)
            rows.append({"line": L, "p_over": round(p,3), "p_under": round(1-p,3)})
        st.table(pd.DataFrame(rows))
elif section == "Falli Liga":
    st.header("Falli — Liga (Spagna)")
    # use same team list but may be empty for liga-specific teams
    home = st.selectbox("Casa (Liga)", teams, key="home_l")
    away = st.selectbox("Ospite (Liga)", [t for t in teams if t!=home] or teams, key="away_l")
    if home and away:
        mu_h, mu_a, mu, sigma = compute_expect(home, away, 'falli_liga')
        st.write(f"Atteso falli totali (Liga): {mu:.2f} — sigma {sigma:.2f}")
        rows = []
        for L in sorted(spreads):
            p = p_over_mix(mu, sigma, L, w_p)
            rows.append({"line": L, "p_over": round(p,3), "p_under": round(1-p,3)})
        st.table(pd.DataFrame(rows))
else:
    st.header("Backtest & Accuracy")
    st.write("Esegui backtest solo se i fogli contengono righe match-by-match (colonne Home/Away + valori).")
    can_backtest = False
    # try detect match-level tiri
    if df_tiri is not None and (tiri_home_col in df_tiri.columns and tiri_away_col in df_tiri.columns):
        can_backtest = True
    if not can_backtest:
        st.info("Non trovo colonne Home/Away chiare in foglio tiri — backtest non possibile con i dati attuali.")
    else:
        st.write("Eseguo backtest tiri usando colonne Home/Away e valori match-level.")
        # detect home/away shot columns
        home_sh_col = None; away_sh_col = None
        for c in df_tiri.columns:
            cl = c.lower()
            if "home" in cl and ("shot" in cl or "tiri" in cl): home_sh_col = c
            if "away" in cl and ("shot" in cl or "tiri" in cl): away_sh_col = c
        if home_sh_col is None or away_sh_col is None:
            st.info("Non trovo chiaramente le colonne home/away shots per backtest.")
        else:
            st.write(f"Uso colonne: {home_sh_col} | {away_sh_col}")
            thr = st.number_input("Soglia backtest (es. 22.5)", value=22.5, step=0.5)
            window = st.slider("Span EWMA backtest", 3, 12, 6)
            df_hist = df_tiri.copy().reset_index(drop=True)
            preds=[]; actuals=[]
            hist = {}
            for idx, r in df_hist.iterrows():
                ht = r.get(tiri_home_col); at = r.get(tiri_away_col)
                if pd.isna(ht) or pd.isna(at):
                    preds.append(None); actuals.append(None); continue
                ht = str(ht).strip(); at = str(at).strip()
                hvals = hist.get(ht, []); avals = hist.get(at, [])
                mu_h = ewma(hvals, span=window) if len(hvals)>0 else (mean(hvals) if len(hvals)>0 else 0.0)
                mu_a = ewma(avals, span=window) if len(avals)>0 else (mean(avals) if len(avals)>0 else 0.0)
                mu_pred = mu_h + mu_a
                p = p_over_mix(mu_pred, max(0.8, math.sqrt((np.std(hvals) if len(hvals)>1 else mu_h*0.25)**2 + (np.std(avals) if len(avals)>1 else mu_a*0.25)**2)), thr, w_p)
                preds.append(p)
                real_h = safe_float(r.get(home_sh_col)); real_a = safe_float(r.get(away_sh_col))
                actuals.append(1 if (real_h + real_a) > thr else 0)
                hist.setdefault(ht, []).append(real_h); hist.setdefault(at, []).append(real_a)
            df_bt = pd.DataFrame({"pred":preds,"actual":actuals}).dropna()
            if df_bt.empty:
                st.info("Backtest non ha righe utili.")
            else:
                cutoff = st.slider("Soglia probabilità per segnale OVER", 0.5, 0.9, 0.58)
                df_bt['pred_over'] = df_bt['pred'] >= cutoff
                acc = (df_bt['pred_over'] == df_bt['actual']).mean()
                st.metric("Accuracy backtest", f"{acc*100:.2f}%")
                st.dataframe(df_bt.head(300))

st.markdown("<small>Nota: il raggiungimento del 75% dipende dai dati. Questo motore fornisce gli strumenti per testare, calibrare e migliorare il modello tramite backtest e ottimizzazione.</small>", unsafe_allow_html=True)    <!-- Navbar -->
    <nav class="bg-slate-900/95 backdrop-blur border-b border-slate-800 p-4 sticky top-0 z-50 flex justify-between items-center pt-safe-top shadow-2xl">
        <div class="flex items-center gap-3">
            <div class="bg-green-500/20 p-2 rounded-lg border border-green-500/30">
                <i class="fas fa-brain text-green-400 text-xl"></i>
            </div>
            <div>
                <h1 class="font-bold text-lg leading-none tracking-tight">BetAnalyst <span class="text-[10px] text-green-400 bg-green-900/30 px-1 rounded">PRO</span></h1>
                <p class="text-[9px] text-slate-400 uppercase tracking-wider font-semibold">Fixed Layout v11.1</p>
            </div>
        </div>
        <button onclick="openDataModal()" class="bg-slate-800 border border-slate-600 text-[10px] font-bold px-4 py-2 rounded-lg text-slate-300 hover:text-white transition active:scale-95">
            DATABASE <i class="fas fa-database ml-1"></i>
        </button>
    </nav>

    <main class="max-w-xl mx-auto p-4 space-y-6">

        <!-- League Selector -->
        <div class="grid grid-cols-2 gap-1 p-1 bg-slate-800/50 rounded-xl border border-slate-700">
            <button onclick="setLeague('SerieA')" id="btn-SerieA" class="py-2.5 rounded-lg text-xs font-bold uppercase transition-all bg-slate-700 text-white shadow-lg border border-slate-600">
                🇮🇹 Serie A
            </button>
            <button onclick="setLeague('Liga')" id="btn-Liga" class="py-2.5 rounded-lg text-xs font-bold text-slate-500 uppercase transition-all hover:bg-slate-800">
                🇪🇸 Liga
            </button>
        </div>

        <!-- Analysis Core -->
        <div class="bg-slate-800 rounded-2xl p-5 shadow-2xl border border-slate-700 relative overflow-hidden">
            <!-- Background Tech Effect -->
            <div class="absolute top-0 right-0 p-3 opacity-10 pointer-events-none">
                <i class="fas fa-microchip text-6xl text-white"></i>
            </div>
            
            <div class="absolute top-3 right-3">
                <span class="text-[9px] font-mono text-green-400 bg-green-900/20 border border-green-900 px-2 py-1 rounded-full flex items-center gap-1">
                    <i class="fas fa-circle text-[6px] animate-pulse"></i> DATA OK
                </span>
            </div>

            <h2 class="text-xs font-bold text-slate-400 uppercase mb-4 tracking-wider">Configurazione Match</h2>
            
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Casa</label>
                    <select id="homeTeam" class="input-dark w-full p-3 rounded-xl mt-1.5 font-bold text-sm appearance-none shadow-sm focus:ring-2 focus:ring-green-500/50 transition-all"></select>
                </div>
                <div>
                    <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Ospite</label>
                    <select id="awayTeam" class="input-dark w-full p-3 rounded-xl mt-1.5 font-bold text-sm appearance-none shadow-sm focus:ring-2 focus:ring-green-500/50 transition-all"></select>
                </div>
            </div>

            <div class="mt-4 relative">
                <label class="text-[10px] font-bold text-slate-500 uppercase ml-1 flex justify-between">
                    <span>Arbitro</span>
                    <span class="text-xs text-green-500 lowercase font-normal">split home/away attivo</span>
                </label>
                <select id="referee" class="input-dark w-full p-3 rounded-xl mt-1.5 font-mono text-xs border-slate-600 focus:border-green-500 appearance-none"></select>
                <div class="absolute right-3 top-9 pointer-events-none text-slate-500"><i class="fas fa-chevron-down"></i></div>
            </div>

            <button onclick="calculate()" class="w-full mt-6 bg-gradient-to-r from-emerald-600 to-green-500 hover:from-emerald-500 hover:to-green-400 text-white font-bold py-4 rounded-xl shadow-lg uppercase text-sm tracking-widest transition-all transform active:scale-[0.98] flex justify-center items-center gap-2 group">
                <span>Esegui Analisi</span> 
                <i class="fas fa-bolt group-hover:animate-pulse"></i>
            </button>
        </div>

        <!-- Results Section -->
        <div id="resultsArea" class="hidden space-y-6">
            
            <!-- Matchup Header -->
            <div class="flex justify-between items-center bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                <div class="text-center w-1/3">
                    <h3 id="resHome" class="font-bold text-white text-sm leading-tight">Home</h3>
                </div>
                <div class="text-center w-1/3">
                    <span class="text-[10px] text-slate-500 font-bold bg-slate-900 px-2 py-1 rounded-full">VS</span>
                    <div class="mt-1 text-[9px] text-yellow-500 font-mono" id="resRef">Ref</div>
                </div>
                <div class="text-center w-1/3">
                    <h3 id="resAway" class="font-bold text-white text-sm leading-tight">Away</h3>
                </div>
            </div>

            <!-- AI STRATEGY BOX -->
            <div class="result-card bg-slate-800 rounded-xl border border-green-900/30 shadow-2xl overflow-hidden">
                <div class="bg-slate-900/50 p-3 border-b border-slate-700 flex justify-between items-center">
                    <h3 class="text-xs font-bold text-green-400 uppercase flex items-center gap-2">
                        <i class="fas fa-robot"></i> Algoritmo Predittivo
                    </h3>
                    <span class="text-[9px] bg-green-900/20 text-green-400 px-2 py-0.5 rounded border border-green-900/30">Confidenza > 70%</span>
                </div>
                
                <div class="p-4 grid grid-cols-1 gap-4">
                    <!-- Falli Recommendation -->
                    <div class="flex items-center justify-between gap-4">
                        <div class="flex-1">
                            <div class="text-[10px] text-slate-400 uppercase font-bold mb-1">Falli Attesi</div>
                            <div class="text-2xl font-bold text-white tracking-tight" id="stratFoulsExp">--</div>
                        </div>
                        <div class="flex-1 text-right space-y-1">
                            <div class="bg-slate-700/30 rounded px-2 py-1 border border-slate-600/50 inline-block w-full">
                                <span class="text-[9px] text-slate-400 mr-1">OVER</span>
                                <span class="text-xs font-bold text-green-400" id="stratFoulsOver">--</span>
                            </div>
                            <div class="bg-slate-700/30 rounded px-2 py-1 border border-slate-600/50 inline-block w-full">
                                <span class="text-[9px] text-slate-400 mr-1">UNDER</span>
                                <span class="text-xs font-bold text-green-400" id="stratFoulsUnder">--</span>
                            </div>
                        </div>
                    </div>

                    <!-- Tiri Recommendation (Conditional) -->
                    <div id="strategyShotsContainer" class="pt-4 border-t border-slate-700 flex items-center justify-between gap-4">
                        <div class="flex-1">
                            <div class="text-[10px] text-slate-400 uppercase font-bold mb-1">Tiri Attesi</div>
                            <div class="text-2xl font-bold text-white tracking-tight" id="stratShotsExp">--</div>
                        </div>
                        <div class="flex-1 text-right space-y-1">
                            <div class="bg-slate-700/30 rounded px-2 py-1 border border-slate-600/50 inline-block w-full">
                                <span class="text-[9px] text-slate-400 mr-1">OVER</span>
                                <span class="text-xs font-bold text-green-400" id="stratShotsOver">--</span>
                            </div>
                            <div class="bg-slate-700/30 rounded px-2 py-1 border border-slate-600/50 inline-block w-full">
                                <span class="text-[9px] text-slate-400 mr-1">UNDER</span>
                                <span class="text-xs font-bold text-green-400" id="stratShotsUnder">--</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Navigation Tabs -->
            <div class="flex border-b border-slate-700">
                <button onclick="switchTab('match')" id="tab-match" class="tab-btn active flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-colors">Match Totals</button>
                <button onclick="switchTab('teams')" id="tab-teams" class="tab-btn flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-colors">Team Stats</button>
            </div>

            <!-- Detailed Grids -->
            <div id="view-match" class="space-y-4 result-card">
                <!-- Shots Match -->
                <div id="matchShotsBox" class="bg-slate-800/50 rounded-xl p-3 border border-slate-700">
                    <div class="flex justify-between items-center mb-2 border-b border-slate-700 pb-2">
                        <h3 class="text-xs font-bold text-blue-400 uppercase"><i class="fas fa-bullseye mr-1"></i> Tiri Totali</h3>
                        <span class="text-[10px] font-mono text-slate-400">Att: <span id="expShotsMatch" class="text-white font-bold">--</span></span>
                    </div>
                    <div id="gridShotsMatch" class="space-y-1"></div>
                </div>

                <!-- SOT Match -->
                <div id="matchSotBox" class="bg-slate-800/50 rounded-xl p-3 border border-slate-700">
                    <div class="flex justify-between items-center mb-2 border-b border-slate-700 pb-2">
                        <h3 class="text-xs font-bold text-purple-400 uppercase"><i class="fas fa-crosshairs mr-1"></i> In Porta</h3>
                        <span class="text-[10px] font-mono text-slate-400">Att: <span id="expSotMatch" class="text-white font-bold">--</span></span>
                    </div>
                    <div id="gridSotMatch" class="space-y-1"></div>
                </div>

                <!-- Fouls Match -->
                <div id="matchFoulsBox" class="bg-slate-800/50 rounded-xl p-3 border border-yellow-900/30">
                    <div class="flex justify-between items-center mb-2 border-b border-slate-700 pb-2">
                        <h3 class="text-xs font-bold text-yellow-400 uppercase"><i class="fas fa-exclamation-triangle mr-1"></i> Falli</h3>
                        <span class="text-[10px] font-mono text-slate-400">Att: <span id="expFoulsMatch" class="text-white font-bold">--</span></span>
                    </div>
                    <div id="gridFoulsMatch" class="space-y-1"></div>
                </div>
            </div>

            <div id="view-teams" class="hidden space-y-6 result-card">
                
                <!-- Home Stats -->
                <div class="border-l-2 border-green-500 pl-4 space-y-3">
                    <h4 class="text-green-400 text-xs font-bold uppercase mb-3">Statistiche Casa</h4>
                    
                    <div id="homeShotsBox">
                        <div class="flex justify-between text-[10px] mb-1">
                            <span class="text-slate-400 uppercase font-bold">Tiri</span>
                            <span class="font-mono text-white" id="expShotsHome">--</span>
                        </div>
                        <div id="gridShotsHome" class="space-y-1"></div>
                    </div>

                    <div id="homeSotBox">
                        <div class="flex justify-between text-[10px] mb-1">
                            <span class="text-slate-400 uppercase font-bold">In Porta</span>
                            <span class="font-mono text-white" id="expSotHome">--</span>
                        </div>
                        <div id="gridSotHome" class="space-y-1"></div>
                    </div>

                    <div id="homeFoulsBox">
                        <div class="flex justify-between text-[10px] mb-1">
                            <span class="text-slate-400 uppercase font-bold">Falli</span>
                            <span class="font-mono text-white" id="expFoulsHome">--</span>
                        </div>
                        <div id="gridFoulsHome" class="space-y-1"></div>
                    </div>
                </div>

                <!-- Away Stats -->
                <div class="border-l-2 border-red-500 pl-4 space-y-3">
                    <h4 class="text-red-400 text-xs font-bold uppercase mb-3">Statistiche Ospite</h4>
                    
                    <div id="awayShotsBox">
                        <div class="flex justify-between text-[10px] mb-1">
                            <span class="text-slate-400 uppercase font-bold">Tiri</span>
                            <span class="font-mono text-white" id="expShotsAway">--</span>
                        </div>
                        <div id="gridShotsAway" class="space-y-1"></div>
                    </div>

                    <div id="awaySotBox">
                        <div class="flex justify-between text-[10px] mb-1">
                            <span class="text-slate-400 uppercase font-bold">In Porta</span>
                            <span class="font-mono text-white" id="expSotAway">--</span>
                        </div>
                        <div id="gridSotAway" class="space-y-1"></div>
                    </div>

                    <div id="awayFoulsBox">
                        <div class="flex justify-between text-[10px] mb-1">
                            <span class="text-slate-400 uppercase font-bold">Falli</span>
                            <span class="font-mono text-white" id="expFoulsAway">--</span>
                        </div>
                        <div id="gridFoulsAway" class="space-y-1"></div>
                    </div>
                </div>
            </div>

        </div>
    </main>

    <!-- Data Modal -->
    <div id="dataModal" class="fixed inset-0 bg-black/90 z-[100] hidden flex flex-col animate-fade-in backdrop-blur-sm">
        <div class="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-900 pt-safe-top">
            <h3 class="font-bold text-white text-sm uppercase tracking-wider"><i class="fas fa-server mr-2 text-green-500"></i>Dati & Pesi</h3>
            <button onclick="closeDataModal()" class="text-slate-400 hover:text-white p-2"><i class="fas fa-times text-xl"></i></button>
        </div>
        
        <div class="p-5 overflow-y-auto flex-1 space-y-6 pb-20">
            
            <div class="bg-slate-800/50 p-3 rounded-lg border border-slate-700 flex justify-between items-center">
                <div>
                    <div class="text-[10px] text-slate-400 uppercase font-bold">Fascia Giornata</div>
                    <div class="text-xs text-white">6ª - 10ª</div>
                </div>
                <div class="text-right">
                    <div class="text-[10px] text-slate-400 uppercase font-bold">Peso Dati</div>
                    <div class="text-xs font-mono text-green-400">1.4x (Curr) / 1.0x (Hist)</div>
                </div>
            </div>

            <div>
                <div class="flex justify-between mb-2">
                    <label class="text-[10px] font-bold uppercase text-blue-400">1. Tiri (Solo Serie A)</label>
                    <span class="text-[9px] text-slate-500">CSV Raw Data</span>
                </div>
                <textarea id="csvShots" class="input-dark w-full h-32 p-3 text-[10px] font-mono rounded-xl border-slate-700 focus:border-blue-500 transition-colors" spellcheck="false"></textarea>
            </div>

            <div>
                <div class="flex justify-between mb-2">
                    <label class="text-[10px] font-bold uppercase text-yellow-400">2. Falli (Serie A + Liga)</label>
                    <span class="text-[9px] text-slate-500">CSV Raw Data</span>
                </div>
                <textarea id="csvFouls" class="input-dark w-full h-32 p-3 text-[10px] font-mono rounded-xl border-slate-700 focus:border-yellow-500 transition-colors" spellcheck="false"></textarea>
            </div>

            <div class="flex gap-3 pt-2">
                <button onclick="resetData()" class="flex-1 py-3 rounded-xl bg-red-500/10 text-red-400 text-xs font-bold border border-red-500/20 hover:bg-red-500/20 transition-colors">Reset Default</button>
                <button onclick="saveData()" class="flex-[2] py-3 rounded-xl bg-green-600 text-white text-xs font-bold shadow-lg hover:bg-green-500 transition-colors">Salva Database</button>
            </div>
        </div>
    </div>

    <script>
        // --- DATABASE CORRETTO (v11.1) ---
        
        const DEFAULT_SHOTS_CSV = `Squadra,Partite Casa,Tiri Fatti Casa,Tiri Subiti Casa,Tiri in porta Fatti Casa,Tiri in porta Subiti Casa,Partite Trasferta,Tiri Fatti Trasferta,Tiri Subiti Trasferta,Tiri in porta Fatti Trasferta,Tiri in porta Subiti Trasferta
Atalanta,6,103,53,29,15,5,57,62,16,28
Bologna,5,75,34,21,9,6,67,70,23,22
Cagliari,5,44,63,15,22,6,61,82,19,30
Como,6,83,59,33,23,5,63,62,17,18
Cremonese,5,43,67,18,21,6,46,115,16,37
Empoli,5,45,60,15,20,6,55,75,18,25
Fiorentina,5,72,58,18,26,6,56,78,13,29
Frosinone,6,70,60,25,22,5,50,65,17,20
Genoa,6,81,49,22,16,5,52,65,19,25
Hellas Verona,5,69,55,30,18,6,66,79,24,26
Inter,6,113,52,39,23,5,86,48,21,14
Juventus,6,120,67,40,20,5,78,55,25,18
Lazio,6,95,58,32,19,5,60,50,20,18
Lecce,5,55,70,18,25,6,48,88,15,30
Milan,5,88,50,35,18,6,92,75,32,25
Monza,5,65,55,22,18,6,60,70,20,24
Napoli,6,105,45,36,15,5,80,42,28,12
Pisa,5,50,75,15,25,6,55,80,18,28
Roma,6,98,55,30,20,5,65,60,22,21
Salernitana,5,50,70,17,25,6,55,85,18,30
Sassuolo,6,80,65,28,24,5,62,70,21,25
Torino,5,68,62,24,22,6,55,72,18,28
Udinese,6,70,65,25,24,5,52,68,18,25`;

        const DEFAULT_FOULS_CSV = `Anno,Squadra,Casa,Media,Lega
2025/26,Atalanta,Casa,13.5,SerieA
2025/26,Atalanta,Fuori,14.2,SerieA
2025/26,Bologna,Casa,15.8,SerieA
2025/26,Bologna,Fuori,14.7,SerieA
2025/26,Cagliari,Casa,17.2,SerieA
2025/26,Cagliari,Fuori,13.8,SerieA
2025/26,Como,Casa,15.0,SerieA
2025/26,Como,Fuori,14.5,SerieA
2025/26,Cremonese,Casa,14.0,SerieA
2025/26,Cremonese,Fuori,14.0,SerieA
2025/26,Empoli,Casa,14.0,SerieA
2025/26,Empoli,Fuori,13.5,SerieA
2025/26,Fiorentina,Casa,18.4,SerieA
2025/26,Fiorentina,Fuori,15.5,SerieA
2025/26,Frosinone,Casa,14.5,SerieA
2025/26,Frosinone,Fuori,15.0,SerieA
2025/26,Genoa,Casa,12.8,SerieA
2025/26,Genoa,Fuori,13.0,SerieA
2025/26,Hellas Verona,Casa,7.4,SerieA
2025/26,Hellas Verona,Fuori,8.8,SerieA
2025/26,Inter,Casa,8.8,SerieA
2025/26,Inter,Fuori,14.6,SerieA
2025/26,Juventus,Casa,12.1,SerieA
2025/26,Juventus,Fuori,12.5,SerieA
2025/26,Lazio,Casa,13.0,SerieA
2025/26,Lazio,Fuori,14.0,SerieA
2025/26,Lecce,Casa,14.0,SerieA
2025/26,Lecce,Fuori,13.5,SerieA
2025/26,Milan,Casa,11.5,SerieA
2025/26,Milan,Fuori,13.0,SerieA
2025/26,Monza,Casa,12.0,SerieA
2025/26,Monza,Fuori,12.5,SerieA
2025/26,Napoli,Casa,10.2,SerieA
2025/26,Napoli,Fuori,11.5,SerieA
2025/26,Pisa,Casa,14.5,SerieA
2025/26,Pisa,Fuori,14.0,SerieA
2025/26,Roma,Casa,12.5,SerieA
2025/26,Roma,Fuori,12.8,SerieA
2025/26,Salernitana,Casa,15.0,SerieA
2025/26,Salernitana,Fuori,15.5,SerieA
2025/26,Sassuolo,Casa,11.0,SerieA
2025/26,Sassuolo,Fuori,11.5,SerieA
2025/26,Torino,Casa,14.0,SerieA
2025/26,Torino,Fuori,15.0,SerieA
2025/26,Udinese,Casa,13.5,SerieA
2025/26,Udinese,Fuori,13.0,SerieA
2025/26,Real Madrid,Casa,10.0,Liga
2025/26,Real Madrid,Fuori,9.5,Liga
2025/26,Barcelona,Casa,11.0,Liga
2025/26,Barcelona,Fuori,10.5,Liga
2025/26,Atletico Madrid,Casa,13.5,Liga
2025/26,Atletico Madrid,Fuori,14.0,Liga
2025/26,Sevilla,Casa,14.5,Liga
2025/26,Sevilla,Fuori,13.0,Liga
2025/26,Valencia,Casa,12.0,Liga
2025/26,Valencia,Fuori,12.5,Liga
2025/26,Real Sociedad,Casa,13.0,Liga
2025/26,Real Sociedad,Fuori,12.8,Liga
2025/26,Villarreal,Casa,11.5,Liga
2025/26,Villarreal,Fuori,11.2,Liga
2025/26,Athletic Bilbao,Casa,14.0,Liga
2025/26,Athletic Bilbao,Fuori,14.5,Liga
2025/26,Real Betis,Casa,13.8,Liga
2025/26,Real Betis,Fuori,13.2,Liga
2025/26,Getafe,Casa,15.5,Liga
2025/26,Getafe,Fuori,15.0,Liga
2025/26,Osasuna,Casa,12.8,Liga
2025/26,Osasuna,Fuori,13.0,Liga
2025/26,Celta Vigo,Casa,14.2,Liga
2025/26,Celta Vigo,Fuori,14.8,Liga
2025/26,Alavés,Casa,15.0,Liga
2025/26,Alavés,Fuori,15.5,Liga
2025/26,Rayo Vallecano,Casa,13.0,Liga
2025/26,Rayo Vallecano,Fuori,13.5,Liga
2025/26,Mallorca,Casa,14.0,Liga
2025/26,Mallorca,Fuori,14.2,Liga
2025/26,Granada,Casa,16.0,Liga
2025/26,Granada,Fuori,16.5,Liga
2025/26,Cádiz,Casa,15.5,Liga
2025/26,Cádiz,Fuori,15.8,Liga
2025/26,Almería,Casa,16.5,Liga
2025/26,Almería,Fuori,17.0,Liga
2025/26,Girona,Casa,11.8,Liga
2025/26,Girona,Fuori,12.2,Liga`;

        const REFEREES_DB = {
            SerieA: [
                {name: "Media Campionato", h:12.5, a:12.5},
                {name: "Ayroldi Giovanni", h:14.8, a:17.0},
                {name: "Sozza Simone", h:12.8, a:14.4},
                {name: "Colombo Andrea", h:13.75, a:14.5},
                {name: "Guida Marco", h:13.4, a:13.4},
                {name: "Doveri Daniele", h:12.6, a:10.8},
                {name: "Massa Davide", h:15.75, a:17.25},
                {name: "Piccinini Marco", h:13.0, a:17.67},
                {name: "Marinelli Livio", h:13.0, a:9.33},
                {name: "Fourneau Francesco", h:14.0, a:14.33},
                {name: "Marcenaro Matteo", h:11.4, a:15.2},
                {name: "Feliciani Ermanno", h:11.25, a:13.0},
                {name: "Rapuano Antonio", h:13.0, a:14.9},
                {name: "La Penna Federico", h:13.0, a:14.7},
                {name: "Di Bello Marco", h:12.5, a:13.7},
                {name: "Mariani Maurizio", h:12.0, a:13.9},
                {name: "Fabbri Michael", h:12.0, a:12.9},
                {name: "Abisso Rosario", h:11.5, a:13.0},
                {name: "Sacchi Juan Luca", h:11.5, a:12.8},
                {name: "Zufferli Luca", h:11.0, a:11.8},
                {name: "Arena Alberto", h:12.2, a:9.0},
                {name: "Chiffi Daniele", h:10.4, a:13.0},
                {name: "Orsato Daniele", h:11.8, a:12.2},
                {name: "Pairetto Luca", h:12.3, a:12.7},
                {name: "Prontera Alessandro", h:11.2, a:12.3},
                {name: "Valeri Paolo", h:10.5, a:11.0},
                {name: "Aureliano Gianluca", h:12.0, a:13.5},
                {name: "Di Marco Davide", h:13.0, a:12.0},
                {name: "Dionisi Federico", h:13.5, a:14.0},
                {name: "Giua Antonio", h:11.5, a:12.5},
                {name: "Massimi Luca", h:14.0, a:13.0},
                {name: "Tremolada Paride", h:12.0, a:13.0},
                {name: "Bonacina Kevin", h:12.5, a:12.5}
            ],
            Liga: [
                {name: "Media Campionato", h:12.5, a:12.5},
                {name: "Galech Apezteguía", h:14.0, a:14.71},
                {name: "Gil Manzano", h:11.29, a:9.57},
                {name: "Hernandez Maeso", h:11.83, a:9.67},
                {name: "Ortiz Arias", h:11.43, a:11.14},
                {name: "Diaz de Mera", h:12.57, a:14.43},
                {name: "Munuera Montero", h:16.0, a:12.67},
                {name: "Garcia Verdura", h:11.43, a:11.57},
                {name: "Guzman Mansilla", h:12.83, a:16.17},
                {name: "Busquets Ferrer", h:14.0, a:14.0},
                {name: "Martinez Munuera", h:13.5, a:13.5},
                {name: "Hernandez Hernandez", h:13.3, a:13.3},
                {name: "Alberola Rojas", h:13.2, a:13.3},
                {name: "Soto Grado", h:12.0, a:11.9},
                {name: "De Burgos Bengoetxea", h:12.5, a:12.5},
                {name: "Muniz Ruiz", h:12.4, a:12.4},
                {name: "Melero Lopez", h:12.2, a:12.2},
                {name: "Cordero Vega", h:12.1, a:12.1},
                {name: "Pulido Santana", h:12.0, a:12.0}
            ]
        };

        let currentLeague = 'SerieA';
        let dbShots = [], dbFouls = {};
        
        const W_CUR = 1.4; 
        const W_HIS = 1.0;

        function init() {
            document.getElementById('csvShots').value = localStorage.getItem('ba_shots_v11') || DEFAULT_SHOTS_CSV;
            document.getElementById('csvFouls').value = localStorage.getItem('ba_fouls_v11') || DEFAULT_FOULS_CSV;
            processData();
            updateUI();
        }

        function openDataModal() { document.getElementById('dataModal').classList.remove('hidden'); }
        function closeDataModal() { document.getElementById('dataModal').classList.add('hidden'); }
        function resetData() { 
            document.getElementById('csvShots').value = DEFAULT_SHOTS_CSV; 
            document.getElementById('csvFouls').value = DEFAULT_FOULS_CSV; 
            localStorage.removeItem('ba_shots_v11');
            localStorage.removeItem('ba_fouls_v11');
            processData();
            updateUI();
        }
        function saveData() {
            localStorage.setItem('ba_shots_v11', document.getElementById('csvShots').value);
            localStorage.setItem('ba_fouls_v11', document.getElementById('csvFouls').value);
            processData();
            updateUI();
            closeDataModal();
        }

        function processData() {
            const rawShots = document.getElementById('csvShots').value.trim().split('\n');
            dbShots = [];
            for(let i=1; i<rawShots.length; i++) {
                const col = rawShots[i].split(',');
                if(col.length<11) continue;
                const gp_h = parseFloat(col[1])||1, gp_a = parseFloat(col[6])||1;
                dbShots.push({
                    name: col[0].trim(),
                    home: { avgShots: (parseFloat(col[2])/gp_h), avgConc: (parseFloat(col[3])/gp_h), avgSot: (parseFloat(col[4])/gp_h), avgSotConc: (parseFloat(col[5])/gp_h) },
                    away: { avgShots: (parseFloat(col[7])/gp_a), avgConc: (parseFloat(col[8])/gp_a), avgSot: (parseFloat(col[9])/gp_a), avgSotConc: (parseFloat(col[10])/gp_a) }
                });
            }

            const rawFouls = document.getElementById('csvFouls').value.trim().split('\n');
            let temp = {};
            for(let i=1; i<rawFouls.length; i++) {
                const col = rawFouls[i].split(',');
                if(col.length<5) continue;
                const season=col[0].trim(), team=col[1].trim(), venue=col[2].trim().toLowerCase(), val=parseFloat(col[3]), league=col[4].trim();
                const key = league + '|' + team;
                if(!temp[key]) temp[key] = { h_curr:null, h_old:null, a_curr:null, a_old:null, league:league, name:team };
                
                if(season.includes('2025')) {
                    if(venue==='casa') temp[key].h_curr = val;
                    if(venue==='fuori') temp[key].a_curr = val;
                } else {
                    if(venue==='casa') temp[key].h_old = val;
                    if(venue==='fuori') temp[key].a_old = val;
                }
            }
            
            dbFouls = {};
            for(let k in temp) {
                let t = temp[k];
                if(!dbFouls[t.league]) dbFouls[t.league] = {};
                
                let h = (t.h_curr ? (t.h_curr*W_CUR + (t.h_old||t.h_curr)*W_HIS)/(W_CUR+W_HIS) : (t.h_old||13));
                let a = (t.a_curr ? (t.a_curr*W_CUR + (t.a_old||t.a_curr)*W_HIS)/(W_CUR+W_HIS) : (t.a_old||13));
                
                dbFouls[t.league][t.name] = { home: h, away: a };
            }
        }

        function updateUI() {
            const hSel = document.getElementById('homeTeam');
            const aSel = document.getElementById('awayTeam');
            hSel.innerHTML = ''; aSel.innerHTML = '';
            
            let teams = [];
            if(currentLeague === 'SerieA') {
                if(dbFouls['SerieA']) teams = Object.keys(dbFouls['SerieA']).sort();
            } else {
                if(dbFouls['Liga']) teams = Object.keys(dbFouls['Liga']).sort();
            }
            
            teams.forEach(t => {
                hSel.innerHTML += `<option value="${t}">${t}</option>`;
                aSel.innerHTML += `<option value="${t}">${t}</option>`;
            });
            if(teams.length>1) { hSel.selectedIndex = 0; aSel.selectedIndex = 1; }

            const rSel = document.getElementById('referee');
            rSel.innerHTML = '';
            const refs = (REFEREES_DB[currentLeague] || []).sort((a,b) => a.name.localeCompare(b.name));
            refs.forEach(r => rSel.innerHTML += `<option value="${r.name}">${r.name} (H:${r.h} A:${r.a})</option>`);
            
            const els = document.querySelectorAll('#strategyShotsContainer, #matchShotsBox, #matchSotBox, #homeShotsBox, #homeSotBox, #awayShotsBox, #awaySotBox');
            if(currentLeague==='Liga') els.forEach(e=>e.parentElement.classList.add('hidden'));
            else els.forEach(e=>e.parentElement.classList.remove('hidden'));
            
            document.getElementById('resultsArea').classList.add('hidden');
        }

        function setLeague(l) {
            currentLeague = l;
            document.getElementById('btn-SerieA').className = l === 'SerieA' ? 'py-2.5 rounded-lg text-xs font-bold uppercase transition-all bg-slate-700 text-white shadow-lg border border-slate-600' : 'py-2.5 rounded-lg text-xs font-bold text-slate-500 uppercase transition-all hover:bg-slate-800';
            document.getElementById('btn-Liga').className = l === 'Liga' ? 'py-2.5 rounded-lg text-xs font-bold uppercase transition-all bg-slate-700 text-white shadow-lg border border-slate-600' : 'py-2.5 rounded-lg text-xs font-bold text-slate-500 uppercase transition-all hover:bg-slate-800';
            updateUI();
        }

        function switchTab(t) {
            document.getElementById('tab-match').classList.remove('active');
            document.getElementById('tab-teams').classList.remove('active');
            document.getElementById('tab-'+t).classList.add('active');
            document.getElementById('view-match').classList.add('hidden');
            document.getElementById('view-teams').classList.add('hidden');
            document.getElementById('view-'+t).classList.remove('hidden');
        }

        function poisson(k, lambda) {
            let p = Math.exp(-lambda);
            for(let i=0; i<k; i++) p *= lambda/(i+1);
            return p;
        }
        function getOverProb(line, lambda) {
            let cum = 0;
            for(let i=0; i<=Math.floor(line); i++) cum += poisson(i, lambda);
            return (1 - cum) * 100;
        }
        function generateSmartLines(lambda) {
            const center = Math.floor(lambda);
            let lines = [];
            for (let i = -2; i <= 2; i++) {
                let val = center + i + 0.5;
                if(val > 0.5) lines.push(val);
            }
            return lines;
        }
        function getSafeLine(lambda, type) {
            let line = Math.floor(lambda);
            const threshold = 70; 
            if (type === 'over') {
                while (getOverProb(line - 0.5, lambda) < threshold && line > 0) line--;
                return line - 0.5;
            } else {
                while ((100 - getOverProb(line + 0.5, lambda)) < threshold) line++;
                return line + 0.5;
            }
        }

        function calculate() {
            const hName = document.getElementById('homeTeam').value;
            const aName = document.getElementById('awayTeam').value;
            const refName = document.getElementById('referee').value;
            
            if(hName === aName) return alert("Seleziona due squadre diverse");

            const refObj = REFEREES_DB[currentLeague].find(r => r.name === refName);
            const refLeagueAvgH = 12.5; 
            const refLeagueAvgA = 12.5; 
            const refH = refObj ? refObj.h : refLeagueAvgH;
            const refA = refObj ? refObj.a : refLeagueAvgA;
            
            // 1. FALLI
            const hF = dbFouls[currentLeague][hName] ? dbFouls[currentLeague][hName].home : 13;
            const aF = dbFouls[currentLeague][aName] ? dbFouls[currentLeague][aName].away : 13;
            
            const expFoulsH = hF * (refH / refLeagueAvgH);
            const expFoulsA = aF * (refA / refLeagueAvgA);
            const totalFouls = expFoulsH + expFoulsA;

            // 2. TIRI
            let totalShots=0, totalSot=0, expShotsH=0, expShotsA=0, expSotH=0, expSotA=0;
            if(currentLeague==='SerieA') {
                const hStats = dbShots.find(t => t.name === hName);
                const aStats = dbShots.find(t => t.name === aName);
                
                const hS = hStats ? hStats.home : {avgShots:12, avgConc:12, avgSot:4, avgSotConc:4};
                const aS = aStats ? aStats.away : {avgShots:11, avgConc:13, avgSot:3.5, avgSotConc:4.5};

                let L = { sh_h:0, sh_a:0, sot_h:0, sot_a:0 };
                if(dbShots.length > 0) {
                    dbShots.forEach(t => { L.sh_h += t.home.avgShots; L.sh_a += t.away.avgShots; L.sot_h += t.home.avgSot; L.sot_a += t.away.avgSot; });
                    const count = dbShots.length;
                    L.sh_h/=count; L.sh_a/=count; L.sot_h/=count; L.sot_a/=count;
                } else {
                    L = { sh_h:12.5, sh_a:11.5, sot_h:4.2, sot_a:3.8 };
                }

                expShotsH = (hS.avgShots / L.sh_h) * (aS.avgConc / L.sh_a) * L.sh_h;
                expShotsA = (aS.avgShots / L.sh_a) * (hS.avgConc / L.sh_h) * L.sh_a;
                totalShots = expShotsH + expShotsA;

                expSotH = (hS.avgSot / L.sot_h) * (aS.avgSotConc / L.sot_a) * L.sot_h;
                expSotA = (aS.avgSot / L.sot_a) * (hS.avgSotConc / L.sot_h) * L.sot_a;
                totalSot = expSotH + expSotA;
            }

            // RENDER
            document.getElementById('resHome').innerText = hName;
            document.getElementById('resAway').innerText = aName;
            document.getElementById('resRef').innerText = refName;

            // Falli UI
            document.getElementById('stratFoulsExp').innerText = totalFouls.toFixed(1);
            document.getElementById('stratFoulsOver').innerText = getSafeLine(totalFouls, 'over');
            document.getElementById('stratFoulsUnder').innerText = getSafeLine(totalFouls, 'under');
            
            document.getElementById('expFoulsMatch').innerText = totalFouls.toFixed(1);
            document.getElementById('expFoulsHome').innerText = expFoulsH.toFixed(1);
            document.getElementById('expFoulsAway').innerText = expFoulsA.toFixed(1);

            renderGrid('gridFoulsMatch', totalFouls, generateSmartLines(totalFouls), 'Falli');
            renderGrid('gridFoulsHome', expFoulsH, generateSmartLines(expFoulsH), 'Falli');
            renderGrid('gridFoulsAway', expFoulsA, generateSmartLines(expFoulsA), 'Falli');

            // Tiri UI
            if(currentLeague==='SerieA') {
                document.getElementById('stratShotsExp').innerText = totalShots.toFixed(1);
                document.getElementById('stratShotsOver').innerText = getSafeLine(totalShots, 'over');
                document.getElementById('stratShotsUnder').innerText = getSafeLine(totalShots, 'under');
                
                document.getElementById('expShotsMatch').innerText = totalShots.toFixed(1);
                document.getElementById('expSotMatch').innerText = totalSot.toFixed(1);
                document.getElementById('expShotsHome').innerText = expShotsH.toFixed(1);
                document.getElementById('expSotHome').innerText = expSotH.toFixed(1);
                document.getElementById('expShotsAway').innerText = expShotsA.toFixed(1);
                document.getElementById('expSotAway').innerText = expSotA.toFixed(1);

                renderGrid('gridShotsMatch', totalShots, generateSmartLines(totalShots), 'Tiri');
                renderGrid('gridSotMatch', totalSot, generateSmartLines(totalSot), 'SOT');
                renderGrid('gridShotsHome', expShotsH, generateSmartLines(expShotsH), 'Tiri');
                renderGrid('gridSotHome', expSotH, generateSmartLines(expSotH), 'SOT');
                renderGrid('gridShotsAway', expShotsA, generateSmartLines(expShotsA), 'Tiri');
                renderGrid('gridSotAway', expSotA, generateSmartLines(expSotA), 'SOT');
            }

            document.getElementById('resultsArea').classList.remove('hidden');
            switchTab('match');
        }

        function renderGrid(id, lambda, lines, type) {
            const el = document.getElementById(id);
            if(!el) return;
            el.innerHTML = '';
            lines.forEach(l => {
                const over = getOverProb(l, lambda);
                const under = 100 - over;
                const isOv = over >= 70; 
                const isUn = under >= 70;

                el.innerHTML += `
                <div class="grid grid-cols-3 gap-2 text-[10px] mb-1.5 items-center">
                    <div class="font-bold text-slate-400 bg-slate-700/30 px-2 py-1 rounded border border-slate-600/30">Over ${l}</div>
                    <div class="py-1.5 text-center rounded font-mono border ${isOv ? 'bg-green-900/40 border-green-500/50 text-green-400 shadow-[0_0_10px_rgba(16,185,129,0.1)]' : 'bg-slate-800 border-slate-700 text-slate-500'}">
                        <span class="font-bold">${over.toFixed(0)}%</span>
                    </div>
                    <div class="py-1.5 text-center rounded font-mono border ${isUn ? 'bg-green-900/40 border-green-500/50 text-green-400 shadow-[0_0_10px_rgba(16,185,129,0.1)]' : 'bg-slate-800 border-slate-700 text-slate-500'}">
                        <span class="font-bold">Und ${under.toFixed(0)}%</span>
                    </div>
                </div>`;
            });
        }

        window.onload = init;
    </script>
</body>
</html>


