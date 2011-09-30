default:
	@echo "...Um, OK then...\nCompiling, Please Wait...\n"
	@sleep 5
	@echo "All Done! Now type 'sudo make install'.\n"

install:
	@sudo ./setup.sh

love:
	@echo "Oh, Yeah, Baby!"
	@sleep 1
	@echo "Was it good for you too?"

clean:

