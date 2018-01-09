.PHONY: clean
clean:
	-pyclean .

.PHONY: run
run:
	python3 slapp.py

.PHONY: debug
debug:
	python3 slapp.py debug
