Evolutionary Algorithm (EA) 2
=============================

Solve a :ref:`small system <small-test-system>` with Evolutionary Algorithmes. Use decision encoded as inidies of available places. We use python module `DEAP <https://github.com/deap/deap>`_. See `DEAP documentation <https://deap.readthedocs.io/en/master/overview.html>`_ for more information.


For this tutorial we need following modules

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: import copy
    :end-at: from prp.solvers.optimal_fixed import get_place_costs

Parameters
----------

We define paths to JSON files of a small warehouse system

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: LAYOUT_FILE = "../data/10-layout.json"
    :end-at: DEPARTURES_FILE = "../data/10-departures.json"

and store the solution to a JSON file:

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: SOLUTION_FILE =
    :lines: 1

We also store intermediate results to an CSV file. Set it to None if you do not want to create the CSV file.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: CSV_FILE =
    :lines: 1


We set parameters for the evolutionary algorithm. The evolutionary algorithms are random, use **random.seed(...)** to make results reproducible.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: random.seed(7)
    :end-at: MAX_NO_IMPROVEMENTS =

Place Order
-----------
Before we can use the evolutionary algorithm, we need to create a fixed order of places. Each :math:`k`-th  element of the genome with value :math:`i` means: go to the :math:`i`-th place when making :math:`k`-th decision to send a pod to the storage. Note, :math:`k` is usually smaller than decision time :math:`t`, because at the very beginning the system does not send pods to storage until the corresponding queue is full.

For this tutorial we sort places by their average costs. The cheapest places are in the front.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: def get_place_ordered_by_avg_costs():
    :end-at: print("Use place order: {}"
    :lines: 1-5, 10-11

Calculate
---------

Load a warehouse model from JSON files.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :pyobject: load_problem

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: warehouse = load_problem()
    :lines: 1


Use helper class *evo_only_free.Helper* with our place order to translate between the Pod Reposition Problems and an Evolutionary Problem.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: helper = evo.Helper
    :lines: 1

An evolutionary algorithm maximizes fitness of individuals, but we want to minimize costs of individuals. To minimize the costs we define the fitness as *FitnessMin* := (-1)*costs.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: creator.create("FitnessMin",
    :lines: 1

Our individuals are sequence of signed integers (type = "l"), whose fitness is *FitnessMin*.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: creator.create("Individual",
    :lines: 1


Setup DEAP solver.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: toolbox = base.Toolbox()
    :lines: 1

Create initial population from a cheapest-place solution.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: initial_solution = helper.cheapest_place_solution
    :end-at: toolbox.register("population",

Add rules for mating. Use two-point random crossover.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: toolbox.register("mate",
    :lines: 1

Add rules for mutation. Select uniform mutation in such a way that on average there is 3 mutation in an individual.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: toolbox.register("mutate",
    :lines: 1-2

Use helper.evaluate() to calculate fitness. This method returns average costs.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: toolbox.register("evaluate", helper.evaluate)
    :lines: 1

Use tournament based selection. That means, 100 times select random 3 and add the best one to the new population.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: toolbox.register("select", tools.selTournament, tournsize=3)
    :lines: 1

Before we start optimization, we can print out the initial solution and its fitness (=costs).

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: ind1 = toolbox.individual()
    :end-at: print("Initial fitness: {}"

Generate initial population with *POPULATION_SIZE* individuals.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: pop = toolbox.population(n=POPULATION_SIZE)
    :lines: 1

Store the best individual after each new population. At the end the hall of fame will contain only one individual with the best fitness.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: hof = tools.HallOfFame(1)
    :lines: 1

Store some population statistics.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: stats = tools.Statistics
    :end-at: stats.register("Max", numpy.max)

Optionally switch on multiprocessing.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: pool = multiprocessing.Pool()
    :lines: 1-2

Start calculation.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: pop, logbook = evo_simple.eaSimple(pop
    :lines: 1-3

Store intermediate results to *CSV_FILE*.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: if CSV_FILE is not None:
    :end-at: csvfile.close()

Print out the best solution and save it to a JSON file.

.. literalinclude:: ../../examples/use-evo-only-free.py
    :start-at: print(hof)
    :end-at: recorder.store_solution_to_json
    :lines: 1-3,7-9

