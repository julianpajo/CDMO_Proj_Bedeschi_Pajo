from minizinc import Instance
import datetime


def solve_instance(num_teams, solver, model, extra_params):
    instance = Instance(solver, model)

    instance["teams"] = num_teams

    for key, value in extra_params.items():
        instance[key] = value

    name_parts = [f"{num_teams}"]
    for key, value in extra_params.items():
        if value:
            name_parts.append(str(key))

    result = instance.solve(timeout=datetime.timedelta(minutes=5),
                            optimisation_level=5, free_search=True)

    return result
