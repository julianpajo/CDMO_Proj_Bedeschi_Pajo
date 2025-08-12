from minizinc import Model


def build_model(path, use_sb=False, use_heuristics=False, use_optimization=False):
    """
    Builds dinamically a MiniZinc model from the given path with specified options.

    Params:
        path: The path to the MiniZinc model file.
        use_sb: Boolean indicating if symmetry breaking is used.
        use_heuristics: Boolean indicating if heuristics are used.
        use_optimization: Boolean indicating if optimization is used.
    Returns:
        A tuple containing:
            - model: A MiniZinc Model object.
            - extra_params: A dictionary with additional parameters for the instance.
    """

    model = Model()
    model.add_file(path)

    if use_optimization:
        if use_heuristics:
            model.add_string("""
                    solve :: seq_search([
                        int_search([O[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min, complete),
                        int_search([P[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min, complete),
                        int_search([per[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min, complete)
                    ]) minimize max_imbalance;
                """)
        else:
            model.add_string("solve minimize max_imbalance;")
    elif use_heuristics:
        model.add_string("""
        solve :: seq_search([
            int_search([O[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min, complete),
            int_search([P[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min, complete),
            int_search([per[t,w] | t in TEAMS, w in WEEKS], dom_w_deg, indomain_min, complete)
        ]) satisfy;
        """)
    else:
        model.add_string("solve satisfy;")

    return model, {"sb": use_sb, "hf": use_heuristics, "opt": use_optimization}
