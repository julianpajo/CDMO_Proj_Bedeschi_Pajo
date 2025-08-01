from source.CP import cp_model


def main():
    #cp_model.run_single_instance(6, 'gecode', use_sb=False, use_heuristics=False, use_optimization=False)
    cp_model.run_all()


if __name__ == "__main__":
    main()
