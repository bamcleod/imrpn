
all:
	$(MAKE) test

test:	Force
	cd test; ./imrpn-test.sh

Force:
