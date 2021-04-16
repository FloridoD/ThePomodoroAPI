#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
from psycopg2.extras import RealDictCursor
import psycopg2, uuid

app = Flask(__name__)
api = Api(app)
class Database:

    def __init__(self):
        connection = psycopg2.connect(user = "ylhmlqpfkqbwxu",password = "86acc7cb14978bd57697eaa59022eec26a08f1930662da86502de3e39fd30e0d",host = "ec2-54-247-158-179.eu-west-1.compute.amazonaws.com",port = "5432",database = "dadih75qcq1ih")
        self.connection=connection

    def login(self, username, password):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM person WHERE username = '"+username+"' AND password = '"+password+"';")
        if cursor.rowcount < 1:
            return False
        else:
            return True
    def insertOrEditUser(self,user_data):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        try:
            query = 'INSERT INTO person (username, password, email, name, bio) values (\''+user_data['username']+'\', \''+user_data['password']+'\', \''+user_data['email']+'\', \''+user_data['name']+'\', \''+user_data["bio"]+'\');'
            cursor.execute(query)
            print(query)
            
        except Exception as e:
            print(e)
            try:
                cursor.execute('UPDATE person SET password = \'%s\', name = \'%s\', bio = \'%s\';'%(user_data['password'],user_data['name'],user_data['bio']))
            except Exception as e2:
                print(e2)
                self.connection.commit()
                cursor.close()
                return False 
        self.connection.commit()
        cursor.close()
        return True
    def getUser(self,user_data):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT username,name,bio FROM person WHERE username = '"+user_data['username']+"';")
        if cursor.rowcount < 1:
            return False
        else:
            return cursor.fetchall()[0]


class Login(Resource):
    def __init__(self,database):
        self.database = database
    def get(self): # {"username": "...", "password": "..."}
        return self.database.login(request.args.get("username"),request.args.get("password"))

class User(Resource):
    def __init__(self,database):
        self.database = database
    def post(self):
        return self.database.insertOrEditUser(request.args)
    def get(self):
        return self.database.getUser(request.args)
database = Database()
api.add_resource(Login, '/login',resource_class_args=(database,))
api.add_resource(User, '/user',resource_class_args=(database,))

if __name__ == "__main__": 
    app.run(debug=True)