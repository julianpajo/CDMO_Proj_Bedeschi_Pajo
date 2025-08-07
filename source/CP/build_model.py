from minizinc import Model


def build_model(path, use_sb=False, use_heuristics=False, use_optimization=False):
    model = Model()
    model.add_file(path)

    if use_optimization:
        model.add_string("""
        array[Teams] of var 0..weeks: num_home = [sum([bool2int(home[w,p] = t) | w in Weeks, p in Periods]) | t in Teams];
        array[Teams] of var 0..weeks: num_away = [sum([bool2int(away[w,p] = t) | w in Weeks, p in Periods]) | t in Teams];
        array[Teams] of var int: imbalances = [abs(num_home[t] - num_away[t]) | t in Teams];
        var int: max_imbalance = max(imbalances);
        """)

        if use_heuristics:
            model.add_string("""
            solve :: int_search(vars, first_fail, indomain_min)
                  minimize max_imbalance;
            """)
        else:
            model.add_string("solve minimize max_imbalance;")

    elif use_heuristics:
        model.add_string("""
        solve :: int_search(vars, first_fail, indomain_min)
              satisfy;
        """)
    else:
        model.add_string("solve satisfy;")

    return model, {"sb": use_sb, "hf": use_heuristics, "opt": use_optimization}
