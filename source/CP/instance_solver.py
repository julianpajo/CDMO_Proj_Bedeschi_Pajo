from minizinc import Instance
import datetime


def solve_instance(num_teams, solver, model, extra_params):
    """
    Solves a MiniZinc instance with the given parameters.

    Params:
        num_teams: The number of teams in the instance.
        solver: The name of the solver to use.
        model: The MiniZinc model to solve.
        extra_params: A dictionary of additional parameters for the instance.
    Returns:
        A MiniZinc result object containing the solution.
    """
    
    instance = Instance(solver, model)

    instance["teams"] = num_teams

    for key, value in extra_params.items():
        instance[key] = value

    name_parts = [f"{num_teams}"]
    for key, value in extra_params.items():
        if value:
            name_parts.append(str(key))

    result = instance.solve(
            timeout=datetime.timedelta(minutes=5),
            free_search=not extra_params.get("hf", False),
        )

    return result
