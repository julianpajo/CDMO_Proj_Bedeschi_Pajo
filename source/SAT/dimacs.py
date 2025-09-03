from itertools import product
from z3 import *


def solver_to_dimacs(solver):
    """
    Converts the assertions() of a Z3 solver into a DIMACS CNF string
    and returns (dimacs_str, var_map).
    var_map: { z3.BoolRef : int } mapping to DIMACS IDs.
    """
    F = And(solver.assertions())

    # pb -> bitvector -> CNF
    T = Then('elim-and', 'pb2bv', 'bit-blast', 'tseitin-cnf')
    G = T(F)

    clauses = []
    atoms = set()

    for subgoal in G:
        for c in subgoal:
            lits = list(c.children()) if is_or(c) else [c]
            clauses.append(lits)
            for lit in lits:
                atoms.add(lit.arg(0) if is_not(lit) else lit)

    atoms = sorted(list(atoms), key=lambda a: a.decl().name())
    var_map = {a: i+1 for i, a in enumerate(atoms)}

    dimacs_lines = [f"p cnf {len(var_map)} {len(clauses)}"]
    for lits in clauses:
        row = []
        for lit in lits:
            row.append(-var_map[lit.arg(0)] if is_not(lit) else var_map[lit])
        dimacs_lines.append(" ".join(str(l) for l in row) + " 0")

    return "\n".join(dimacs_lines) + "\n", var_map


def build_variable_mapping(home, per, var_map, Teams, Weeks, Periods):
    """
    Builds a readable mapping to reconstruct the schedule from DIMACS.

    Parameters:
        home, per: 3D lists of Z3 variables
        var_map: dictionary {z3_var: dimacs_id} produced by solver_to_dimacs
        Teams, Weeks, Periods: index ranges
    
    Returns:
        mapping = {"to_var": {dimacs_id: (type, i,j,w[,p])},
                   "to_id": {variable_name: dimacs_id}}
    """
    mapping = {"to_var": {}, "to_id": {}}
    z3name2id = {v.decl().name(): vid for v, vid in var_map.items()}

    # home[i][j][w]
    for i, j, w in product(Teams, Teams, Weeks):
        if i == j:
            continue
        z3_var = home[i][j][w]
        name = z3_var.decl().name()
        vid = z3name2id.get(name)
        if vid is not None:
            mapping["to_var"][vid] = ("home", i, j, w)
            mapping["to_id"][name] = vid

    # per[i][w][p]
    for i, w, p in product(Teams, Weeks, Periods):
        z3_var = per[i][w][p]
        name = z3_var.decl().name()
        vid = z3name2id.get(name)
        if vid is not None:
            mapping["to_var"][vid] = ("period", i, w, p)
            mapping["to_id"][name] = vid

    return mapping


def get_all_variables_for_dimacs_from_variables_only(home, per, Teams, Weeks, Periods, solver):
    """
    Builds the variable -> DIMACS ID mapping from Z3 model variables (home/per)
    and the solver, when home/per are 3D lists (matrices).

    Returns mapping:
        {"to_var": {dimacs_id: ("home"/"period", i,j,w[,p])},
         "to_id": {variable_name: dimacs_id}}
    """
    try:
        # 1) DIMACS + Z3-var -> DIMACS-id map
        _, var_map = solver_to_dimacs(solver)
        z3name2id = {v.decl().name(): vid for v, vid in var_map.items()}

        mapping = {"to_var": {}, "to_id": {}}

        # 2) home[i][j][w]
        for i in Teams:
            for j in Teams:
                if i == j:
                    continue
                for w in Weeks:
                    var = home[i][j][w]
                    name = var.decl().name()
                    vid = z3name2id.get(name)
                    if vid is not None:
                        mapping["to_var"][vid] = ("home", i, j, w)
                        mapping["to_id"][name] = vid

        # 3) per[i][w][p]
        for i in Teams:
            for w in Weeks:
                for p in Periods:
                    var = per[i][w][p]
                    name = var.decl().name()
                    vid = z3name2id.get(name)
                    if vid is not None:
                        mapping["to_var"][vid] = ("period", i, w, p)
                        mapping["to_id"][name] = vid

        return mapping

    except Exception as e:
        print(f"[ERROR] in get_all_variables_for_dimacs_from_variables_only: {e}")
        return None
