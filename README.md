# Sports Tournament Scheduling (STS) problem

### Team Members

- 0001164895 - Alessia Bedeschi - alessia.bedeschi@studio.unibo.it
- 0001169541 - Julian Pajo - julian.pajo@studio.unibo.it


## Setup

### Build Docker Image

To build the docker image use the command:  
```bash
docker-compose build
```

---

## Usage

### Run All Configurations for All Models

This runs the full battery of tests for all implemented models.

```bash
docker-compose run cdmo-models --all
```

To restrict the run to a single model (e.g. CP only):

```bash
docker-compose run cdmo-models --all --model cp
```

---

### Run a Single Configuration

Specify the model type, number of teams, solver, and options:

```bash
docker-compose run cdmo-models --single --model cp --teams 8 --sb --hf 2 --opt --solver gecode
```

#### Parameters

* `--model`: One of `cp`, `sat`, `smt`, `mip`
* `--teams`: Number of teams (default `6`)
* `--sb`: Enable symmetry breaking
* `--hf`: Search strategy to use (for CP only)

  * `1` = default
  * `2` = dom/wdeg
  * `3` = dom/wdeg + luby
  * `4` = dom/wdeg + luby + LNS
* `--opt`: Enable optimization
* `--solver`: One of `gecode`, `chuffed`, `gurobi`, `cplex`

  * CP models: `gecode`, `chuffed`
  * MIP models: `gurobi`, `cplex`

To disable optional flags like `--sb` or `--opt`, simply omit them.

---

### Examples

#### CP (Constraint Programming)

Run CP model with 8 teams, symmetry breaking, dom/wdeg heuristic, optimization, and Gecode solver:

```bash
docker-compose run cdmo-models --single --model cp --teams 8 --sb --hf 2 --opt --solver gecode
```

Run all CP configurations:

```bash
docker-compose run cdmo-models --all --model cp
```

---

#### SAT (Boolean Satisfiability)

Run SAT model with 6 teams (default), no optimization, symmetry breaking:

```bash
docker-compose run cdmo-models --single --model sat --teams 6 --sb --solver glucose
```

---

#### SMT (Satisfiability Modulo Theories)

Run SMT model with 10 teams:

```bash
docker-compose run cdmo-models --single --model smt --teams 10 --solver z3
```

---

#### MIP (Mixed-Integer Programming)

Run MIP model with 12 teams, optimization enabled, using Gurobi:

```bash
docker-compose run cdmo-models --single --model mip --teams 12 --opt --solver gurobi
```