from itertools import product
import subprocess
from z3 import *
import json
#import re


def solver_to_dimacs(solver):
    """
    Converte le assertions() del solver in stringa DIMACS CNF
    e restituisce (dimacs_str, var_map).
    var_map: { z3.BoolRef : int } mapping a ID DIMACS.
    """
    F = And(solver.assertions())

    # Usa la pipeline di Z3 per pb -> bitvector -> CNF
    T = Then('simplify', 'pb2bv', 'bit-blast', 'tseitin-cnf')
    G = T(F)

    clauses = []
    atoms = set()

    for subgoal in G:
        for c in subgoal:
            if is_or(c):
                lits = list(c.children())
            else:
                lits = [c]
            clauses.append(lits)
            for lit in lits:
                atoms.add(lit.arg(0) if is_not(lit) else lit)

    atoms = sorted(list(atoms), key=lambda a: a.decl().name())
    var_map = {a: i+1 for i,a in enumerate(atoms)}

    dimacs_lines = [f"p cnf {len(var_map)} {len(clauses)}"]
    for lits in clauses:
        row = []
        for lit in lits:
            if is_not(lit):
                row.append(-var_map[lit.arg(0)])
            else:
                row.append(var_map[lit])
        dimacs_lines.append(" ".join(str(l) for l in row) + " 0")

    return "\n".join(dimacs_lines) + "\n", var_map



def get_all_variables_for_dimacs(home, per, solver, Teams, Weeks, Periods):
    """
    Funzione principale per costruire il mapping completo da Z3 → DIMACS.
    Restituisce mapping {"to_var", "to_id"}.
    """
    try:
        dimacs_str, var_map = solver_to_dimacs(solver)
        mapping = build_variable_mapping(home, per, var_map, Teams, Weeks, Periods)
        return mapping
    except Exception as e:
        print(f"[ERROR] in get_all_variables_for_dimacs: {e}")
        return None



def get_all_variables_for_dimacs_from_variables_only(home, per, Teams, Weeks, Periods, solver):
    """
    Costruisce il mapping variabile -> ID DIMACS a partire dalle variabili Z3
    del modello home/per e dal solver.
    
    Restituisce mapping:
        {"to_var": {dimacs_id: ("home"/"period", i,j,w[,p])},
         "to_id": {name: dimacs_id}}
    """
    try:
        mapping = {"to_var": {}, "to_id": {}}

        # 1. Converte il solver in DIMACS e ottiene la mappa Z3 -> DIMACS ID
        dimacs_str, var_map = solver_to_dimacs(solver)
        z3name2id = {v.decl().name(): vid for v, vid in var_map.items()}

        # 2. Associa tutte le variabili del modello
        # home: [i,j,w]
        for (i,j,w), var in home.items():
            name = var.decl().name()
            vid = z3name2id.get(name)
            if vid is not None:
                mapping["to_var"][vid] = ("home", i, j, w)
                mapping["to_id"][name] = vid

        # per: [i,w,p]
        for (i,w,p), var in per.items():
            name = var.decl().name()
            vid = z3name2id.get(name)
            if vid is not None:
                mapping["to_var"][vid] = ("period", i, w, p)
                mapping["to_id"][name] = vid

        return mapping

    except Exception as e:
        print(f"[ERROR] in get_all_variables_for_dimacs_from_variables_only: {e}")
        return None




def build_variable_mapping(home, per, var_map, Teams, Weeks, Periods):
    """
    Costruisce un mapping leggibile per ricostruire lo schedule da DIMACS.

    Params:
        home, per: dizionari di variabili Z3
        var_map: dizionario {z3_var: dimacs_id} prodotto da solver_to_dimacs
        Teams, Weeks, Periods: liste di indici
    
    Returns:
        mapping = {"to_var": {dimacs_id: (tipo, i,j,w[,p])},
                   "to_id": {nome_var: dimacs_id}}
    """
    mapping = {"to_var": {}, "to_id": {}}

    # reverse map
    z3name2id = {v.decl().name(): vid for v, vid in var_map.items()}

    # home[i,j,w]
    for i, j, w in product(Teams, Teams, Weeks):
        if i == j:
            continue
        z3_var = home.get((i, j, w))
        if z3_var is None:
            continue
        name = z3_var.decl().name()
        vid = z3name2id.get(name)
        if vid is not None:
            mapping["to_var"][vid] = ("home", i, j, w)
            mapping["to_id"][name] = vid

    # per[i,w,p]
    for i, w, p in product(Teams, Weeks, Periods):
        z3_var = per.get((i, w, p))
        if z3_var is None:
            continue
        name = z3_var.decl().name()
        vid = z3name2id.get(name)
        if vid is not None:
            mapping["to_var"][vid] = ("period", i, w, p)
            mapping["to_id"][name] = vid

    return mapping
