dist:
	python setup.py sdist bdist_wheel
upload: dist
	twine upload dist/*
local:
	pip install -e .
installer:
	pyinstaller -F redwall_main.py
clean:
	rm -rf build dist redwall.egg-info redwall/__pycache__ redwall/*.pyc
