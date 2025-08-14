# =========================
# PARAMETERS (come i tuoi)
# =========================
param n;
param W := n - 1;
param P := n div 2;

param use_sb default 0;  # symmetry breaking (0/1)
param use_opt default 0; # optimization (0/1)

set TEAMS := 1..n;
set WEEKS := 1..W;
set PERIODS := 1..P;

# Insieme delle coppie NON orientate (i<k)
set EDGES := {i in TEAMS, k in TEAMS: i < k};

# =========================
# DECISION VARIABLES
# =========================
# 1) Matching per settimana (non orientato)
var y {i in TEAMS, k in TEAMS, w in WEEKS: i < k} binary;

# 2) Assegnazione ai periodi (link a y)
var A {i in TEAMS, k in TEAMS, w in WEEKS, p in PERIODS: i < k} binary;

# 3) Orientamento home/away per la coppia scelta in w
var H {h in TEAMS, a in TEAMS, w in WEEKS: h <> a} binary;

# Per l'ottimizzazione (come i tuoi)
var home_games {t in TEAMS} integer >= 0 <= W;
var away_games {t in TEAMS} integer >= 0 <= W;
var imbalance  {t in TEAMS} integer >= 0 <= W;   # (ti permetto anche 0)
var max_imbalance integer >= 0 <= W;

# =========================
# CONSTRAINTS
# =========================

# (1) Ogni coppia gioca esattamente una volta (sul totale delle settimane)
s.t. PairOnce {(i,k) in EDGES}:
    sum {w in WEEKS} y[i,k,w] = 1;

# (2) Ogni team gioca una volta a settimana (perfect matching settimanale)
s.t. OnePerWeek {t in TEAMS, w in WEEKS}:
    sum {k in TEAMS: k < t} y[k,t,w] +
    sum {k in TEAMS: k > t} y[t,k,w] = 1;

# (3) Assegna ogni partita scelta ad un periodo (bijective per settimana)
#    - ogni coppia giocata in w va in esattamente un periodo
s.t. AssignOnePeriod {(i,k) in EDGES, w in WEEKS}:
    sum {p in PERIODS} A[i,k,w,p] = y[i,k,w];

#    - in ogni settimana e periodo, c'è esattamente una partita
s.t. OneMatchPerSlot {w in WEEKS, p in PERIODS}:
    sum {(i,k) in EDGES} A[i,k,w,p] = 1;

# (4) Al più due volte nello stesso periodo per squadra (sul torneo)
s.t. MaxTwoPerPeriod {t in TEAMS, p in PERIODS}:
    sum {w in WEEKS}
        (
          # tutti i match incidenti a t assegnati al periodo p
          sum {k in TEAMS: k < t} A[k,t,w,p] +
          sum {k in TEAMS: k > t} A[t,k,w,p]
        ) <= 2;

# (5) Orientamento home/away coerente con la scelta del match
#     Una delle due direzioni deve valere se e solo se la coppia è scelta in w
s.t. HA_link {(i,k) in EDGES, w in WEEKS}:
    H[i,k,w] + H[k,i,w] = y[i,k,w];

# =========================
# SYMMETRY BREAKING (stile matching)
# =========================
# SB1: fissare una partita nella week 1 (es: 1 vs 2) se use_sb=1
s.t. SB1:
    sum {p in PERIODS} A[1,2,1,p] = use_sb;

# SB2: ordine avversari per team 1: in week w, gioca con w+1 (se use_sb=1)
s.t. SB2 {w in WEEKS: w+1 <= n}:
    y[min(1,w+1), max(1,w+1), w] >= use_sb;

# =========================
# HOME/AWAY e OBIETTIVO
# =========================
s.t. HomeGamesDef {t in TEAMS}:
    home_games[t] = sum {a in TEAMS, w in WEEKS: a <> t} H[t,a,w];

s.t. AwayGamesDef {t in TEAMS}:
    away_games[t] = sum {h in TEAMS, w in WEEKS: h <> t} H[h,t,w];

s.t. Imbalance1 {t in TEAMS}: imbalance[t] >= home_games[t] - away_games[t];
s.t. Imbalance2 {t in TEAMS}: imbalance[t] >= away_games[t] - home_games[t];

s.t. MaxImbalanceDef {t in TEAMS}: max_imbalance >= imbalance[t];

minimize MaxImbalanceObj: use_opt * max_imbalance;
