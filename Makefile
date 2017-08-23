all:
	python setup.py sdist bdist_wheel
local:
	pip install .
twine:
	twine upload
clean:
	rm -rf build dist redwall.egg-info redwall/__pycache__ redwall/*.pyc
