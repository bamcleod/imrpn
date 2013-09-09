
all:
	$(MAKE) test

test:	Force
	cd test; ./imrpn-test.sh

install:
	cp -p imrpn.py 		~/bin/imrpn
	mkdir -p 		~/.imrpn
	cp -p xpa.py 		~/.imrpn/.
	cp -p dotable.py	~/.imrpn/.
	cp -p fits.py 		~/.imrpn/.
	cp -p imrpn.rc 		~/.imrpn/.
	cp -p imrpn-extend.py 	~/.imrpn/.
	cp -p README		~/.imrpn/.

Force:
