Binary Integer Programming
===================================================

Solve a :ref:`small system <small-test-system>` with Binary Integer Programming (BIP) exactly. Use *pulp* python package with *COIN* library.

We first import all necessary modules

.. literalinclude:: ../../examples/use-bip.py
    :start-at: from prp.solvers.simple 
    :end-at: import prp.solvers.bip

Parameters
----------

We define paths to JSON files of a small warehouse system:

.. literalinclude:: ../../examples/use-bip.py
    :lines: 40-43

and store the results to a JSON file:

.. literalinclude:: ../../examples/use-bip.py
    :lines: 46


Load a warehouse model from JSON files:

.. literalinclude:: ../../examples/use-bip.py
    :lines: 49-60,73

Calculate
---------

Sometimes we can solve a problem a little bit faster if we provide an upper bound for the objective function. We can obtain a simple bound if we solve this problem with another method -- for example *Cheapest place*.

.. literalinclude:: ../../examples/use-bip.py
    :start-at: def get_cheapest_place_costs
    :end-at: return warehouse.total_costs

Optionally, you can switch on logging.

.. literalinclude:: ../../examples/use-bip.py
    :start-at: import logging
    :lines: 1

.. literalinclude:: ../../examples/use-bip.py
    :start-at: logging.basicConfig(level=logging.DEBUG)
    :lines: 1

We use the optional parameter *costs_upper_bound* to speed up calculation.

.. literalinclude:: ../../examples/use-bip.py
    :start-at: upper_costs = get_cheapest_place_costs
    :end-at: (solution, problem) = bip.solve
    :lines: 1,3

Finally we save the results.

.. literalinclude:: ../../examples/use-bip.py
    :start-at: utils.create_missing_directories_of_file(SOLUTION_FILE)
    :end-at: recorder.store_solution_to_json

Test
----

Optionally, we can test our optimal solution for consistency

.. literalinclude:: ../../examples/use-bip.py
    :start-at: for place_id in solution:
    :end-at: print("Problem is NOT solved

and print the results.

.. literalinclude:: ../../examples/use-bip.py
    :start-at: print("Total costs {c}
    :lines: 1



