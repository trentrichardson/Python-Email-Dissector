# Copyright 2011 Trent Richardson
#
# This file is part of Python Email Dissector.
#
# Python Email Dissector is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# Python Email Dissector is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Python Email Dissector. If not, see <http://www.gnu.org/licenses/>.

import smtpd
import asyncore
import threading
from datetime import datetime
from email.parser import Parser

#from example
from email.Header import decode_header
import email
from base64 import b64decode
import sys
#from email.Parser import Parser as EmailParser
from email.utils import parseaddr
from StringIO import StringIO

#http://code.activestate.com/recipes/440690-smtp-mailsink/

class LocalSMTPServer(smtpd.SMTPServer):
	
	def process_message(self, peer, mailfrom, rcpttos, data):
		print 'Receiving message from:', peer
		print 'Message addressed from:', mailfrom
		print 'Message addressed to  :', rcpttos
		print 'Message length        :', len(data)
		

		
		""" 
		Thoughts:
		- msg.get_payload() could be a message or a list of messages, see links below
		- loop through messages if multipart, and log them all, that way we get a text view and an html view if available
		- we need some html formmating on our left tree, would be nice for bold/normal and html/text indication (icon for each?)
		
		Resources:
		- examples of parsing: http://docs.python.org/library/email-examples.html
		- loop through and look for an html msg: http://stackoverflow.com/questions/594545/email-body-is-a-string-sometimes-and-a-list-sometimes-why
		- email.msg api: http://docs.python.org/library/email.message.html#module-email.message
		- http://www.ianlewis.org/en/parsing-email-attachments-python
		
		"""
		
		msg = self.email_parse(data)
		body_type = 'plain'
		if msg['body_html'] is not None:
			body_type = 'html'
		
		# also need to figure out what to do with attachments...
		# this code blow says that the handling of attachments isn't the best
		# we can create folders with the row id or store in the db (Store in DB would be easiest)
		self._parent._parent._db.connect()
		row_id = self._parent._parent._db.insertEmailRow(datetime.now(), 0, unicode(msg['to']), unicode(msg['from']), unicode(msg['subject']), unicode(msg['body_text']), unicode(msg['body_html']), unicode(body_type), unicode(data) )
		
		# if attachments insert them as well
		if msg['attachments'] is not None:
			for ma in msg['attachments']:
				attch_id = self._parent._parent._db.insertEmailAttachmentRow(row_id, ma['filename'], ma['content_type'], ma['filedata'])
		
		self._parent._parent._db.disconnect()
		
		self._parent._parent.populateTree()
		
		if not self._parent._parent.window.is_active():
			self._parent._parent.window.set_urgency_hint(True)
		
		return
	
	
	def set_parent(self, parentSelf):
		self._parent = parentSelf
	
		
	def email_parse(self, content):

		p = Parser()
		msgobj = p.parsestr(content)
		if msgobj['Subject'] is not None:
			decodefrag = decode_header(msgobj['Subject'])
			subj_fragments = []
			for s , enc in decodefrag:
				if enc:
					s = unicode(s , enc).encode('utf8','replace')
				subj_fragments.append(s)
			subject = ''.join(subj_fragments)
		else:
			subject = None

		attachments = []
		body_text = ""
		body_html = ""
		for part in msgobj.walk():
			attachment = self.email_parse_attachment(part)
			if attachment:
				attachments.append(attachment)
			elif part.get_content_type() == "text/plain":
				body_text += unicode(part.get_payload(decode=True),part.get_content_charset(),'replace').encode('utf8','replace')
			elif part.get_content_type() == "text/html":
				body_html += unicode(part.get_payload(decode=True),part.get_content_charset(),'replace').encode('utf8','replace')
		return { 'subject': subject, 'body_text': body_text, 'body_html': body_html, 'from': parseaddr(msgobj.get('From'))[1], 'to': parseaddr(msgobj.get('To'))[1], 'attachments': attachments }


	def email_parse_attachment(self, message_part):
		
		content_disposition = message_part.get("Content-Disposition", None)
		if content_disposition:
			dispositions = content_disposition.strip().split(";")
			if bool(content_disposition and dispositions[0].lower() == "attachment"):
				attachment = {
						'filedata': message_part.get_payload(),
						'content_type': message_part.get_content_type(),
						'filename': "default"
					}
				for param in dispositions[1:]:
					name,value = param.split("=")
					name = name.strip().lower()

					if name == "filename":
						attachment['filename'] = value.replace('"','')
				
				return attachment
				
		return None
		

class Server(threading.Thread):
	def __init__(self, parentSelf, address, port):
		self._parent = parentSelf
		self._address = self._parent._settings['address'] #address
		self._port = self._parent._settings['port'] #port
		
		self._stopevent = threading.Event()
		self.threadName = "EDLocalSMTPServer"
		threading.Thread.__init__(self, name=self.threadName)
		
	def run(self):
		print "Service Started at: "+ self._address +":"+ str(self._port)
		self._server = LocalSMTPServer((self._address, self._port), None)
		self._server.set_parent(self)
		self._stopevent.clear()
		while not self._stopevent.isSet():
			asyncore.loop(timeout=0.01, count=1)
		#asyncore.loop()
		#asyncore.loop(use_poll=True)
		
	def stop(self):
		self._stopevent.set()
		threading.Thread.join(self, 0.01)
		self._server.close()
		print "Service Stopped"
