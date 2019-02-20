test:
	python3 setup.py test

release-to-pypi:
	python3 setup.py sdist
	twine upload dist/*
