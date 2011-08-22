#!/usr/bin/env python

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

import sys
import os
import subprocess
import gtk
import webkit
import gtksourceview2
from email.parser import Parser
import pickle

import threading

from EDHelpers import EDData
from EDHelpers import EDServer


class EmailDissector:

	def on_window_destroy(self, widget, data=None):
		self.server_stop()
		gtk.main_quit()
	
	def on_window_focus(self, widget, data=None):
		if self.window.get_urgency_hint():
			self.window.set_urgency_hint(False)
		
	def __init__(self):
		
		# http://mocksmtpapp.com similar mac only app...
		self._app_dir = os.path.split(__file__)[0]
		self._attachments_dir = os.path.join(self._app_dir, "EDAttachments")
		self._gui_dir = os.path.join(self._app_dir, "EDInterfaces")
		self._config_file = 'config.pkl'
		
		self._settings = {
				'address': '127.0.0.1',
				'port': 1025,
				'mailstore': 'mail.sqlite',
				'mailstoretable': 'mail',
				'sourcescheme': 'twilight', # classic, oblivion, tango, kate, cobalt or custom in SourceViewSchemes folder
			}
		self._read_config_file()
		
		self._default_html = "<html><body><h1>Hello Friend</h1></body></html>"
		self._current_html = self._default_html

		self._server = None
		self._db = EDData.Store(self._settings['mailstore'], self._settings['mailstoretable'])
		
		builder = gtk.Builder()
		builder.add_from_file(os.path.join(self._gui_dir, "MainWindow.glade"))

		self.window = builder.get_object("MainWindow")
		builder.connect_signals(self)
		
		#Start the server
		rtbtn = builder.get_object("StartButton").set_active(True)
		
		#Get the Tree
		self.tree = builder.get_object("EmailTreeView")
		self.tree_model = self.tree.get_model()
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("To/Date", cell, markup=0)
		self.tree.append_column(col)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("ID", cell, text=1)
		col.set_visible(False)
		self.tree.append_column(col)
		
		#Get the Attachments IconView
		self.attachments = builder.get_object("AttachmentsIconView")
		self.attachments.set_text_column(0)
		self.attachments.set_pixbuf_column(1)
		self.attachments_model = self.attachments.get_model()
		#self.attachments_model.set_sort_column_id(0, gtk.SORT_ASCENDING)
		
		#Add Browsing elements
		#Webkit
		self.webkitbrowser = webkit.WebView()
		builder.get_object("HTMLScrollWindow").add_with_viewport(self.webkitbrowser)
		self.webkitbrowser.show()
		self.webkitbrowser.load_string(self._current_html, "text/html", "utf-8", "test")
		#self.webkitbrowser.load_uri("http://google.com")
		
		#Add source view
		self.sv_lang_mgr = gtksourceview2.LanguageManager()
		self.sv_buffer = gtksourceview2.Buffer()
		self.sv_style_mgr = gtksourceview2.StyleSchemeManager()
		self.sv_style_mgr.prepend_search_path(os.path.join(self._gui_dir, 'SourceViewSchemes'))
		scheme = self.sv_style_mgr.get_scheme(self._settings['sourcescheme'])
		#print self.sv_style_mgr.get_scheme_ids()
		if scheme:
			self.sv_buffer.set_style_scheme(scheme)
		self.sv_buffer.set_language(self.sv_lang_mgr.get_language('html'))
		self.sv_buffer.set_text(self._current_html)
		self.sv_buffer.set_highlight_syntax(True)
		self.sourceview = gtksourceview2.View(self.sv_buffer)
		self.sourceview.set_show_line_numbers(True)
		builder.get_object("SourceScrollWindow").add_with_viewport(self.sourceview)
		self.sourceview.show()
		
		#Set Raw View
		self.text_view = builder.get_object("TextTextView")
		self.text_view_buffer = gtk.TextBuffer()
		self.text_view.set_buffer(self.text_view_buffer)
		
		#Set Raw View
		self.raw_view = builder.get_object("RawTextView")
		self.raw_view_buffer = gtk.TextBuffer()
		self.raw_view.set_buffer(self.raw_view_buffer)
		
		#Labels
		self.to_label = builder.get_object("ToLabelVal")
		self.from_label = builder.get_object("FromLabelVal")
		self.subject_label = builder.get_object("SubjectLabelVal")
		
		self.window.show()
		
		# GO!
		self.populateTree()
	
	#::::::::::::::::::::::::::::::::::::::::::::::::::::
	#	Server methods
	#::::::::::::::::::::::::::::::::::::::::::::::::::::
	def server_start(self):		
		self._server = EDServer.Server(self, self._settings['address'], self._settings['port'])
		self._server.start()
		
	def server_stop(self):
		if self._server:
			self._server.stop()
		self._server = None
	
	
	#::::::::::::::::::::::::::::::::::::::::::::::::::::
	#	Button Signals
	#::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_PreferencesButton_clicked(self, widget):
		builder = gtk.Builder()
		builder.add_from_file(os.path.join(self._gui_dir, "PreferencesDialog.glade"))

		dialog = builder.get_object("PreferencesDialog")
		builder.connect_signals(self)
		
		# set the defualts
		ConfigPortTextBox = builder.get_object("ConfigPortTextBox")
		ConfigPortTextBox.set_value(self._settings['port'])
		
		response = dialog.run()
	
		if response == 1:
			old_port = self._settings['port']
			self._settings['port'] = ConfigPortTextBox.get_value_as_int()
			
			self._write_config_file(self._settings)
			
			# restart the server if the port changed
			if old_port != self._settings['port']:
				md = gtk.MessageDialog(type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, flags=gtk.DIALOG_MODAL, message_format="You must reastart the service for the changes to take place")
				md.run()
				md.destroy()
		
		dialog.destroy()

	def on_StartButton_toggled(self, widget):
		
		if widget.get_active():
			self.server_start()
			widget.set_stock_id('gtk-media-play')
			widget.set_tooltip_text('Click to Stop')
		else:
			self.server_stop()
			widget.set_stock_id('gtk-media-pause')
			widget.set_tooltip_text('Click to Start')

	def on_RefreshButton_clicked(self, widget):
		#self.tree_model.clear()
		self.populateTree()

	def on_DeleteButton_clicked(self, widget):
		model, titr = self.tree.get_selection().get_selected()
		if titr:
			row_id = model.get(titr, 1)[0]
			if row_id != 0:
				self._db.connect()
				row = self._db.deleteEmailRow(row_id)
				self._db.disconnect()
		
				model.remove(titr)

	def on_EmailTreeView_row_activated(self, widget, path, view_column):
		model, titr = self.tree.get_selection().get_selected()
		row_text, row_id = model.get(titr, 0, 1)
		
		if row_id != 0:
			self._db.connect()
			row = self._db.getEmailRow(row_id)
			row_attachments = self._db.getEmailAttachmentRows(row_id)
			self._db.disconnect()
		
			self.populateDetails(row, row_attachments)
	
			# mark it as read if it isn't already
			if row['has_read'] == 0:
				self._db.connect()
				rows = self._db.markEmailRowRead(row_id, 1)
				self._db.disconnect()
				
				#search and replace <b> in description
				row_text = row_text.replace("<b>","").replace("</b>","")
				model.set_value(titr, 0, row_text)
	
	def on_AttachmentsIconView_item_activated(self, widget, item):
		filedata = self.attachments_model[item] #filedata = [0=FileName, 1=FileIcon, 2=FileTooltip, 3=FileId]
		
		# push the file to the user
		fileloc = os.path.join(self._attachments_dir, filedata[0])
		
		print "Open File "+ filedata[0]
		self._db.connect()
		row = self._db.getEmailAttachmentRow(filedata[3])
		self._db.disconnect()
		
		# write a binary or text file..
		#ftype = row['content_type'].split('/')
		#if ftype in ['text']:
		#	outfile = open(fileloc,"w")
		#else:
		#	outfile = open(fileloc,"wb")
		outfile = open(fileloc,"wb")
		outfile.write(row['filedata'])
		outfile.close()
		
		# open the file for the user
		# http://stackoverflow.com/questions/434597/open-document-with-default-application-in-python
		try:
			os.startfile(fileloc)
		except AttributeError:
			if os.name == 'mac':
				subprocess.call(('open', fileloc))
			elif os.name == 'nt':
				subprocess.call(('start', fileloc), shell=True)
			elif os.name == 'posix':
				subprocess.call(('xdg-open', fileloc))

	def on_EmptyMailboxButton_clicked(self, widget):	
		print "Empty Mailbox"
		
		self._db.connect()
		row = self._db.createTables()
		self._db.disconnect()
		
		self.populateTree()
		
	#::::::::::::::::::::::::::::::::::::::::::::::::::::
	#	Worker functions
	#::::::::::::::::::::::::::::::::::::::::::::::::::::
	def populateDetails(self, row, attachments):
		main_body = row['body_text']
		if row['body_html'] != "":
			main_body = row['body_html']
		
		#print item
		self.to_label.set_label(row['to_addr'])
		self.from_label.set_label(row['from_addr'])
		self.subject_label.set_label(row['subject'])
		
		# source view
		self.sv_buffer.set_text(main_body)
		self.sv_buffer.set_language(self.sv_lang_mgr.get_language(row['body_type']))
		
		# browser view
		self.webkitbrowser.load_string(main_body, ("text/"+ row['body_type']), "utf-8", row['subject'])
		
		# text view
		self.text_view_buffer.set_text(row['body_text'])
		
		# raw view
		self.raw_view_buffer.set_text(row['headers'])
		
		#attachments
		self.attachments_model.clear()
		
		#empty attachments from self._attachments_dir
		for f in os.listdir(self._attachments_dir):
			file_path = os.path.join(self._attachments_dir, f)
			if os.path.isfile(file_path):
				os.unlink(file_path)

		if len(attachments) > 0:
			for f in attachments:
				self.attachments_model.append([f['filename'], self.getAttachmentIcon(gtk.STOCK_FILE), f['content_type'], f['id']])
		
		
	def getAttachmentIcon(self, name):
		theme = gtk.icon_theme_get_default()
		return theme.load_icon(name, 48, 0)	
		
	def populateTree(self):
		self._db.connect()
		rows = self._db.getEmailRows()
		self._db.disconnect()
		
		# loop through tree and create a store of parents open and 
		# a store for selected item, then we can set them below
		# check parent by email, and item by id
		
		# find selected
		sel_row_id = -1
		model, sel_itr = self.tree.get_selection().get_selected()
		if sel_itr != None:
			sel_row_text, sel_row_id = model.get(sel_itr, 0, 1)
		
		# find expanded
		parents_open = []
		def eachrowitr_findopen(rmodel, rpath, riter, user_data):
			curr_email, curr_id = rmodel.get(riter, 0, 1)
			if curr_id == 0 and self.tree.row_expanded(rpath):
				parents_open.append(curr_email)
		self.tree_model.foreach(eachrowitr_findopen, '');
		
		
		self.tree_model.clear()
		
		curr_parent = None
		for i in range(len(rows)):
			if i == 0 or rows[i-1]['to_addr'] != rows[i]['to_addr']:
				curr_parent = self.tree_model.append(parent=None, row=[ rows[i]['to_addr'], 0 ] )
			
			# html or text?
			curr_markup = '<span foreground="#5770B3">txt</span>  '
			if rows[i]['body_type'] == 'html':
				curr_markup = '<span foreground="#A31F37">&lt;/&gt;</span>  '
				
			# read or unread?
			if rows[i]['has_read'] == 1:
				curr_markup = curr_markup + rows[i]['subject']
			else:
				curr_markup = curr_markup + '<b>' + rows[i]['subject'] + '</b>'
			
			curr_markup = curr_markup + '\n<span foreground="#777777">' + rows[i]['created'].strftime("%Y-%m-%d %H:%M") +'</span>'
			
			# has attachments?
			if rows[i]['attachment_count'] == 1 :
				curr_markup = curr_markup + '\n<span foreground="#999999">'+ str(rows[i]['attachment_count']) +' Attachment</span>'
			elif rows[i]['attachment_count'] > 1 :
				curr_markup = curr_markup + '\n<span foreground="#999999">'+ str(rows[i]['attachment_count']) +' Attachments</span>'
			
			self.tree_model.append(parent=curr_parent, row=[ curr_markup, rows[i]['id'] ] )
		
		
		if len(parents_open) == 0 and len(rows) > 0:
			parents_open.append(rows[0]['to_addr'])
			
		# ok now reopen those parents
		def eachrowitr_reopen(rmodel, rpath, riter, user_data):
			curr_email, curr_id = rmodel.get(riter, 0, 1)
			if curr_id == 0 and curr_email in parents_open:
				self.tree.expand_row(rpath, False)
			if curr_id == sel_row_id:
				self.tree.get_selection().select_path(rpath)
		self.tree_model.foreach(eachrowitr_reopen, '');
		

	def _read_config_file(self):
		
		#if file doesn't exist, create it.. write defaults return
		if not os.path.exists(self._config_file):
			self._write_config_file(self._settings)
			return self._settings
		
		pkl_file = open(self._config_file, 'rb')
		self._settings = pickle.load(pkl_file)
		pkl_file.close()
		
		return self._settings
	
	def _write_config_file(self, settings):
				
		output = open(self._config_file, 'wb')
		pickle.dump(settings, output)
		output.close()

		return


if __name__ == "__main__":
	ped = EmailDissector()
	
	gtk.main()
	

