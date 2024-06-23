.. Pod Repositioning Problem documentation master file, created by
   sphinx-quickstart on Wed Sep 19 11:12:51 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Pod Repositioning Problem's documentation
=====================================================

Pod Repositioning Problem (PRP) is a mathematical model of a robotized warehouse.
See `our paper on ResearchGate <https://www.researchgate.net/publication/328225522_Deterministic_Pod_Repositioning_Problem_in_Robotic_Mobile_Fulfillment_Systems>`_.
The source code is `here <https://bitbucket.org/rkrenzler/pod-repositioning-problem>`_.

* **First steps:**

    * :doc:`Overview <overview>`
    * :doc:`How to build a small test problem <small-test-system>`
    * :doc:`Cheapest place<cheapest>`

* **Algorithms:**
    * :doc:`Binary Integer Programming<bip>`
    * :doc:`Fixed place<fixed>`
    * :doc:`Evolutionary algorithm 1<evo>`
    * :doc:`Evolutionary algorithm 2<evo-only-free>`
    * :doc:`Tetris<tetris>`

* **Larger systems:**
    * :doc:`How to convert RAWSimo Layout to PRP layout <rawsimo-layout>`

.. toctree::
    :hidden:

    overview
    small-test-system
    cheapest
    bip
    fixed
    evo
    evo-only-free
    tetris
    rawsimo-layout

