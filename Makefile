dist:
	python setup.py sdist bdist_wheel
local:
	pip install -e .
clean:
	rm -rf build dist redwall.egg-info redwall/__pycache__ redwall/*.pyc
