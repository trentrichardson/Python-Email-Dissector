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
import sqlite3


class Store:
	def __init__(self, filepath, tablename):
		self._filepath = filepath
		self._table = tablename
		self._conn = None
		self._cursor = None
	
	def connect(self):
		self._conn = sqlite3.connect(self._filepath, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
		self._conn.row_factory = sqlite3.Row
		self._cursor = self._conn.cursor()
		
	def disconnect(self):
		self._cursor.close()
		self._conn.close()
		self._conn = None
		self._cursor = None
		
	def createTables(self):
		sql = "DROP TABLE IF EXISTS "+ self._table +""";
			
			CREATE TABLE """+ self._table +""" (
				"id" INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL , 
				"created" TIMESTAMP, 
				"has_read" BOOL DEFAULT 0, 
				"to_addr" VARCHAR, 
				"from_addr" VARCHAR, 
				"subject" VARCHAR, 
				"body_text" TEXT, 
				"body_html" TEXT,
				"body_type" VARCHAR DEFAULT "plain",
				"headers" TEXT
			);
			
			DROP TABLE IF EXISTS """+ self._table +"""_attachments;
			
			CREATE TABLE """+ self._table +"""_attachments (
				"id" INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL , 
				"email_id" INTEGER,
				"filename" VARCHAR,
				"content_type" VARCHAR,
				"filedata" BLOB				
			);
			"""
		
		self._cursor.executescript(sql)
		self._conn.commit()
		
	def getEmailRows(self):
		sql = """
			select id, created, has_read, to_addr, from_addr, subject, body_type, 
				(select count(a1.id) from """+ self._table +"""_attachments as a1 where a1.email_id=m1.id) as attachment_count 
			from """+ self._table +""" as m1 
			order by to_addr asc, created desc limit 50"""
		return self._cursor.execute(sql).fetchall()
		
	def getEmailRow(self, row_id):
		sql = "select * from "+ self._table +" where id=:rid limit 1"
		return self._cursor.execute(sql, {'rid':row_id}).fetchone()
	
	def getEmailAttachmentRows(self, email_id):
		sql = "select * from "+ self._table +"_attachments where email_id=:email_id order by id"
		return self._cursor.execute(sql, {'email_id':email_id}).fetchall()
		
	def getEmailAttachmentRow(self, row_id):
		sql = "select * from "+ self._table +"_attachments where id=:rid limit 1"
		return self._cursor.execute(sql, {'rid':row_id}).fetchone()
		
	def insertEmailRow(self, created, has_read, to_addr, from_addr, subject, body_text, body_html, body_type, headers):
		sql = """
				insert into """+ self._table +""" (created, has_read, to_addr, from_addr, subject, body_text, body_html, body_type, headers) values 
				(:created, :has_read, :to_addr, :from_addr, :subject, :body_text, :body_html, :body_type, :headers)
			"""
		self._cursor.execute(sql, {'created':created, 'has_read':has_read, 'to_addr':to_addr, 'from_addr':from_addr, 'subject':subject, 'body_text':body_text, 'body_html':body_html, 'body_type':body_type, 'headers':headers})
		self._conn.commit()
		
		return self._cursor.lastrowid
		
	def insertEmailAttachmentRow(self, email_id, filename, content_type, filedata):
		sql = """
				insert into """+ self._table +"""_attachments (email_id, filename, content_type, filedata) values 
				(:email_id, :filename, :content_type, :filedata)
			"""
		self._cursor.execute(sql, {'email_id':email_id, 'filename':filename, 'content_type':content_type, 'filedata':sqlite3.Binary(filedata) })
		self._conn.commit()
		
		return self._cursor.lastrowid
		
	def deleteEmailRow(self, row_id):
		# remove the attachments
		sql = "delete from "+ self._table +"_attachments where email_id=:rid"
		self._cursor.execute(sql, {'rid':row_id})
		
		# remove the email
		sql = "delete from "+ self._table +" where id=:rid"
		self._cursor.execute(sql, {'rid':row_id})
		self._conn.commit()
		
	def markEmailRowRead(self, row_id, is_read):
		sql = "update "+ self._table +" set has_read=:read where id=:rid"
		self._cursor.execute(sql, {'read':is_read, 'rid':row_id})
		self._conn.commit()
		
	
