.PHONY: clean
clean:
	-pyclean .

.PHONY: run
run:
	python3 slapp.pyw

.PHONY: debug
debug:
	python3 slapp.pyw debug
