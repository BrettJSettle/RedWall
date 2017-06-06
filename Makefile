all:
	python setup.py sdist bdist_wheel
clean:
	rm -rf build dist redwall.egg-info
