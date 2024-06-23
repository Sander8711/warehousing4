Tetris
======

Solve the :ref:`small system <small-test-system>` with Tetris algorithm. For the pod priorities we will use frequencies.

For this tutorial we need following modules:

.. literalinclude:: ../../examples/use-tetris.py
    :start-at: import prp.recorder
    :end-at: import prp.solvers.tetris

If you want to use logging call

.. literalinclude:: ../../examples/use-tetris.py
    :start-at: import logging
    :lines: 1

Parameters
----------

We define paths to JSON files of the small warehouse system

.. literalinclude:: ../../examples/use-tetris.py
    :start-at: LAYOUT_FILE = "../data/10-layout.json"
    :end-at: DEPARTURES_FILE = "../data/10-departures.json"

and store the solution to a JSON file:

.. literalinclude:: ../../examples/use-tetris.py
    :start-at: SOLUTION_FILE =
    :lines: 1

Calculate
---------

Load the warehouse model from JSON files.

.. literalinclude:: ../../examples/use-tetris.py
    :start-at: def load_problem():
    :end-at: warehouse = load_problem()


If you want to switch on logging, add

.. literalinclude:: ../../examples/use-tetris.py
    :start-at: import logging
    :lines: 1

For the tetris algorithm we need to decide whether we want to consider only the costs from station or we want to consider the costs from the station and to the next station. In this tutorial we will use costs in both directions. For more information see :ref:`cheapest-place <costs_type>` algorithm.

We also need to decide how to calculate priority of the pods:

* By frequency: That means, a pod which departs more frequently has a higher priority than pods which depart less frequently.

or

* By sojourn time: That means, a pod with a shorter sojourn time in the storage have higher priority than pods with longer sojourn time. The sojourn time is the time between the arrival to the storage and departure to the storage.

We select full decision costs for the costs and pod frequency for the priority.

.. literalinclude:: ../../examples/use-tetris.py
    :start-at: solution = tetris.solve
    :lines: 1

We test our final result and print the costs.

.. literalinclude:: ../../examples/use-tetris.py
    :start-at: for place_id in solution
    :end-at: print("Total costs


Finally we store the solution to a JSON file.

.. literalinclude:: ../../examples/use-tetris.py
    :start-at: utils.create_missing_directories_of_file
    :end-at: recorder.store_solution_to_json
