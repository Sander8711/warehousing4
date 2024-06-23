To update html documentation run:
make html

When you want to add or to remove a module:
1) Adjust index.rst
2) Go to the doc directory and run
sphinx-build -b html  ./source _build
Then rebuild documentation with
make html
