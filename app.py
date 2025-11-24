<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#0f172a">
    <title>BetAnalyst Pro v11.1</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root { --bg-dark: #0b1120; --card: #1e293b; --accent: #10b981; }
        body { 
            background-color: var(--bg-dark); color: #f8fafc; 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }
        .input-dark { background-color: #0f172a; border: 1px solid #334155; color: white; }
        
        /* Advanced Badge Style */
        .badge-edge { background: linear-gradient(45deg, #064e3b, #10b981); border: 1px solid #34d399; color: white; }
        
        /* Grid Animation */
        @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .result-card { animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }

        .tab-btn.active { border-bottom: 2px solid #10b981; color: #10b981; background: rgba(16, 185, 129, 0.1); }
        
        .odds-box { background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; transition: transform 0.1s; }
        .odds-box:active { transform: scale(0.96); }
        .odds-box.value-bet { background-color: #064e3b; border-color: #34d399; box-shadow: 0 0 12px rgba(52, 211, 153, 0.25); }
        .odds-box.value-bet .prob-text { color: #34d399; font-weight: 800; }
    </style>
</head>
<body class="pb-24 safe-area-pb">

    <!-- Navbar -->
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


