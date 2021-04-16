#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
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



class Login(Resource):
    def __init__(self,database):
        self.database = database
    def post(self): # {"username": "...", "password": "..."}
        return self.database.login(request.args.get("username"),request.args.get("password"))

database = Database()
api.add_resource(Login, '/login',resource_class_args=(database,))
if __name__ == "__main__": 
    app.run(debug=True)