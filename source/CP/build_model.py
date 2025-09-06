from minizinc import Model


def build_model(path, use_sb=False, heuristic=1, use_optimization=False):
    """
    Builds dynamically a MiniZinc model from the given path with specified options.

    Params:
        path: The path to the MiniZinc model file.
        use_sb: Boolean indicating if symmetry breaking is used.
        heuristic: Integer selecting the search strategy:
            1 -> Default search
            2 -> dom/wdeg + random value
            3 -> dom/wdeg + random value + restarts (Luby L=250)
            4 -> dom/wdeg + random value + restarts + LNS (85% fixed)
        use_optimization: Boolean indicating if optimization is used.
    Returns:
        A tuple containing:
            - model: A MiniZinc Model object.
            - extra_params: A dictionary with additional parameters for the instance.
    """

    model = Model()
    model.add_file(path)

    # Objective function
    if use_optimization:
        solve_prefix = "solve minimize max_imbalance;"
    else:
        solve_prefix = "solve satisfy;"

    # Default (heuristic = 1)
    if heuristic == 1:
        model.add_string(solve_prefix)

    # Heuristic 2: dom/wdeg + random value
    elif heuristic == 2:
        search = """
        solve :: seq_search([
            int_search([O[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min),
            int_search([PL[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min),
            int_search([per[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min)
        ])
        """
        model.add_string(search + (" minimize max_imbalance;" if use_optimization else " satisfy;"))

    # Heuristic 3: dom/wdeg + random value + restarts (Luby L=250)
    elif heuristic == 3:
        search = """
        solve 
        :: seq_search([
            int_search([O[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min),
            int_search([PL[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min),
            int_search([per[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min)
        ])
        :: restart_luby(250)
        """
        model.add_string(search + (" minimize max_imbalance;" if use_optimization else " satisfy;"))

    # Heuristic 4: dom/wdeg + random value + restarts + LNS (85% fixed)
    elif heuristic == 4:
        search = """
        solve 
        :: seq_search([
            int_search([O[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min),
            int_search([PL[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min),
            int_search([per[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min)
        ])
        :: restart_luby(250)
        :: relax_and_reconstruct(
            [O[t,w] | t in TEAMS, w in WEEKS] ++
            [PL[t,w] | t in TEAMS, w in WEEKS] ++
            [per[t,w] | t in TEAMS, w in WEEKS], 85)
        """
        model.add_string(search + (" minimize max_imbalance;" if use_optimization else " satisfy;"))

    else:
        raise ValueError("Unknown heuristic index (must be 1-4).")

    return model, {"sb": use_sb, "heuristic": heuristic, "opt": use_optimization}



