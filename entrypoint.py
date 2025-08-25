import argparse
from source.CP import cp_model
from source.SAT import sat_model
from source.MIP import mip_model


def run_all_models(selected_model=None):
    models = {
        "cp": cp_model,
        "sat": sat_model,
        # "smt": smt_model,
        "mip": mip_model
    }

    if selected_model:
        if selected_model in models:
            print(f"Running all configurations for model: {selected_model}")
            models[selected_model].run_all()
        else:
            print(f"Model '{selected_model}' not implemented.")
    else:
        for model_name, model in models.items():
            print(f"Running all configurations for model: {model_name}")
            model.run_all()


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true",
                      help="Run all configurations for all models (or one model if --model is given)")
    mode.add_argument("--single", action="store_true", help="Run a single configuration")
    parser.add_argument("--teams", type=int, default=6, help="Number of teams (for --single)")
    parser.add_argument("--sb", action="store_true", help="Enable symmetry breaking")
    parser.add_argument("--hf", type=int, choices=[1, 2, 3, 4], default=1,
                        help="Search strategy to use: "
                             "1=default, 2=dom/wdeg, 3=dom/wdeg+luby, 4=dom/wdeg+luby+LNS")
    parser.add_argument("--opt", action="store_true", help="Enable optimization")
    parser.add_argument("--solver", type=str, choices=["gecode", "chuffed", "gurobi", "cplex"],
                        help="Solver to use (CP: gecode, chuffed | MIP: gurobi, cplex)")
    parser.add_argument("--model", type=str, choices=["cp", "sat", "smt", "mip"],
                        help="Which model to run")

    args = parser.parse_args()

    if args.all:
        run_all_models(selected_model=args.model)

    elif args.single:
        if args.model == "cp":
            cp_model.run_single_instance(
                n=args.teams,
                solver=args.solver,
                use_sb=args.sb,
                use_heuristics=args.hf,
                use_optimization=args.opt
            )
        elif args.model == "sat":
            sat_model.run_single_instance(
                n=args.teams,
                solver="z3",
                use_sb=args.sb,
                use_optimization=args.opt
            )
        elif args.model == "mip":
            mip_model.run_single_instance(
                n=args.teams,
                solver=args.solver,
                use_sb=args.sb,
                use_optimization=args.opt
            )
        else:
            print(f"Single run for model '{args.model}' not implemented yet.")


if __name__ == "__main__":
    main()
