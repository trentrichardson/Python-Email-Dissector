Python Email Dissector
======================

Copyright 2011 Trent Richardson

This file is part of Python Email Dissector.

Python Email Dissector is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

Python Email Dissector is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Python Email Dissector. If not, see <http://www.gnu.org/licenses/>.

About
-----
This program is not a general email client.  It simply creates a dummy smtp 
server to catch all outgoing mail and present it in html view, source view, 
text view (for multipart emails with alternate text versions), raw headers, 
and attachments.

While it does render html emails it does not present accurate test renderings 
of email clients.  The rendering is handled with webkit, so it likely supports 
more html features than normal email clients.

Author: [Trent Richardson](http://trentrichardson.com)

To Run on Linux:
----------------
- install pywebkit (via package manager if possible)
- install gtksourceview2
- main.py

To run on Windows:
------------------
- install python 2.7
- install these packages (specifically gtk, gtksourceview, webkit):
	http://opensourcepack.blogspot.com/2011/01/conservative-all-in-one-pygtk-installer.html
	(the pygtk_aio-2011_win32_installer_py25-27-rev5.exe is the latest as of 2011-08-17)
- run main.py

To Run on Mac:
--------------
I presume it should work, although I've not successfully installed webkit and gtksourceview

To Use:
-------
The server starts automatically.  The only configuration is the port, which is 1025 by 
default on 127.0.0.1.  Running port 25 may require admin priviledges.  When testing your
programs with this app point your smtp mail settings this host and port and the app 
will catch all outgoing emails.
