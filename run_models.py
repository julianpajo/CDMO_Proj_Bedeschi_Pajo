import argparse
from source.CP import cp_model
from source.SAT import sat_model


def run_all_models():
    models = {
        "cp": cp_model,
        "sat": sat_model,
        # "smt": smt_model,
        # "mip": mip_model,
    }

    for model_name, model in models.items():
        print(f"Running all configurations for model: {model_name}")
        model.run_all()


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true", help="Run all configurations for all models")
    mode.add_argument("--single", action="store_true", help="Run a single configuration")

    parser.add_argument("--teams", type=int, default=6, help="Number of teams (for --single)")
    parser.add_argument("--sb", action="store_true", help="Enable symmetry breaking")
    parser.add_argument("--hf", action="store_true", help="Enable heuristics")
    parser.add_argument("--opt", action="store_true", help="Enable optimization")
    parser.add_argument("--solver", type=str, default="gecode", help="MiniZinc solver to use")

    parser.add_argument("--model", type=str, choices=["cp", "sat", "smt", "mip"], default="cp",
                        help="Which model to run (only relevant with --single)")

    args = parser.parse_args()

    if args.all:
        run_all_models()
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
                num_teams=args.teams,
                use_sb=args.sb
            )
        else:
            print(f"Single run for model '{args.model}' not implemented yet.")


if __name__ == "__main__":
    main()