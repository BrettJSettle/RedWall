all:
	python setup.py sdist bdist_wheel
twine:
	twine upload
clean:
	rm -rf build dist redwall.egg-info
