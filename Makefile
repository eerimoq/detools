test:
	env CFLAGS=--coverage python3 setup.py test
	$(MAKE) test-sdist
	find . -name "*.gcno" -exec gcov {} +

test-sdist:
	rm -rf dist
	python3 setup.py sdist
	cd dist && \
	mkdir test && \
	cd test && \
	tar xf ../*.tar.gz && \
	cd detools-* && \
	python3 setup.py test

release-to-pypi:
	python3 setup.py sdist
	twine upload dist/*
