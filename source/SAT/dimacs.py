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



def get_all_variables_for_dimacs(solver, variables, Teams, Weeks, Periods):
    """
    Crea un mapping leggibile per ricostruire lo schedule.
    Restituisce None se non riesce a costruire il mapping.
    """
    try:
        mapping = {"to_var": {}, "to_id": {}}

        # Le variabili 'originali' x[w][p][s][t]
        for w in Weeks:
            for p in Periods:
                for s in [0,1]:
                    for t in Teams:
                        v = variables[w][p][s][t]
                        mapping["to_id"][v.decl().name()] = None

        # Adesso ricaviamo i veri id CNF da solver_to_dimacs
        dimacs_str, var_map = solver_to_dimacs(solver)

        # Reverse map
        z3name2id = { b.decl().name(): vid for b,vid in var_map.items() }

        # Riempie mapping["to_var"]
        for w in Weeks:
            for p in Periods:
                for s in [0,1]:
                    for t in Teams:
                        v = variables[w][p][s][t]
                        name = v.decl().name()
                        vid = z3name2id.get(name)
                        if vid is not None:
                            mapping["to_var"][vid] = (w,p,s,t,name)
                            mapping["to_id"][name] = vid

        return mapping
        
    except Exception as e:
        print(f"[ERROR] in get_all_variables_for_dimacs: {e}")
        return None



def get_all_variables_for_dimacs_from_variables_only(variables, Teams, Weeks, Periods, solver):
    """
    Costruisce il mapping variabile -> ID DIMACS a partire dalle variabili z3 e solver.
    """
    try:
        mapping = {"to_var": {}, "to_id": {}}

        # 1. Converte il solver in DIMACS e ottiene la mappa di Z3 -> DIMACS id
        dimacs_str, var_map = solver_to_dimacs(solver)

        # var_map è tipo { z3.BoolRef : id }
        z3name2id = { b.decl().name(): vid for b, vid in var_map.items() }

        # 2. Associa tutte le nostre variabili x[w][p][s][t]
        count = 0
        for w in Weeks:
            for p in Periods:
                for s in [0, 1]:
                    for t in Teams:
                        v = variables[w][p][s][t]
                        name = v.decl().name()
                        vid = z3name2id.get(name)
                        if vid is not None:
                            mapping["to_var"][vid] = (w, p, s, t, name)
                            mapping["to_id"][name] = vid
                            count += 1

        return mapping

    except Exception as e:
        print(f"[ERROR] in get_all_variables_for_dimacs_from_variables_only: {e}")
        return None


def build_variable_mapping(variables, var_map, Teams, Weeks, Periods):
    """
    Costruisce un mapping leggibile per ricostruire lo schedule da DIMACS.

    Params:
        variables: lista 4D [week][period][home/away][team] di variabili Z3
        var_map: dizionario {z3_var: dimacs_id} prodotto da solver_to_dimacs
        Teams: lista degli indici delle squadre
        Weeks: lista degli indici delle settimane
        Periods: lista degli indici dei periodi

    Returns:
        mapping = {"to_var": {dimacs_id: (w,p,s,t,name)},
                   "to_id": {name: dimacs_id}}
    """
    mapping = {"to_var": {}, "to_id": {}}

    # Reverse map: name Z3 -> ID DIMACS
    z3name2id = {v.decl().name(): vid for v, vid in var_map.items()}

    for w in Weeks:
        for p in Periods:
            for s in [0,1]:
                for t in Teams:
                    z3_var = variables[w][p][s][t]
                    name = z3_var.decl().name()
                    vid = z3name2id.get(name)
                    if vid is not None:
                        mapping["to_var"][vid] = (w, p, s, t, name)
                        mapping["to_id"][name] = vid

    return mapping
