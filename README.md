# CDMO
Modelling &amp; solving the Sports Tournament Scheduling (STS) problem

## Setup

### Build Docker Image

```bash
docker-compose build
```

---

## Usage

### Run All Configurations for All Models

This runs the full battery of tests for all implemented models (currently only `cp`).

```bash
docker-compose run cdmo-models --all
```

---

### Run a Single Configuration

Specify the model type, number of teams, solver, and options:

```bash
docker-compose run cdmo-models --single --model cp --teams 8 --sb --hf --opt --solver gecode
```

* `--model`: One of `cp`, `sat`, `smt`, `mip` (future support for all)
* `--teams`: Number of teams (default 6)
* `--sb`: Enable symmetry breaking
* `--hf`: Enable heuristics
* `--opt`: Enable optimization
* `--solver`: MiniZinc solver (default `gecode`)

To disable optional flags like `--sb`, simply omit them.