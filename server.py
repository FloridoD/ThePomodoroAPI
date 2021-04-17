#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from logging import NullHandler
from flask import Flask, request, jsonify, make_response
from flask.helpers import make_response
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
from psycopg2.extras import RealDictCursor
import psycopg2, uuid
import json
from functools import wraps
import jwt
import datetime
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
api = Api(app)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-acess-token' in request.headers:
            token = request.headers['x-acess-token']

        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
            username = data['username']
            print(username)
        except:
            return jsonify({'message': 'Token is invalid'}), 401

        return f(username, *args, **kwargs)

    return decorated

class Database:

    def __init__(self):
        connection = psycopg2.connect(user = "ylhmlqpfkqbwxu",password = "86acc7cb14978bd57697eaa59022eec26a08f1930662da86502de3e39fd30e0d",host = "ec2-54-247-158-179.eu-west-1.compute.amazonaws.com",port = "5432",database = "dadih75qcq1ih")
        self.connection=connection

    def query(self, query_str):
        cursor = self.connection.cursor()
        cursor.execute(query_str)

        if cursor.rowcount < 1:
            return None 

        return {'results':
            [dict(zip([column[0] for column in cursor.description], row))
             for row in cursor.fetchall()]}
    
    def login(self, username, password):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM person WHERE username = '"+username+"' AND password = '"+password+"';")
        if cursor.rowcount < 1:
            return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login Required!"'})
        else:
            token = jwt.encode({'public_id':username, 'exp': datetime.datetime.utcnow()+datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
            return jsonify({'token': token})
    def addUser(self,user_data):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        try:
            query = 'INSERT INTO person (username, password, email, name, bio) values (\''+user_data['username']+'\', \''+user_data['password']+'\', \''+user_data['email']+'\', \''+user_data['name']+'\', \''+user_data["bio"]+'\');'
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
            return jsonify({'message': 'New user created'})
            
        except Exception as e:
            print(e)
            self.connection.commit()
            return jsonify({'message': 'error'})

    def editUser(self,user_data):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('UPDATE person SET password = \'%s\', name = \'%s\', bio = \'%s\', image = \'%s\' WHERE username = \'%s\';'%(user_data['password'],user_data['name'],user_data['bio'],user_data['image'],user_data['username']))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e2:
            print(e2)
            self.connection.commit()
            cursor.close()
            return jsonify({'message': 'error'})
    def getUser(self,user_data):
        try:
            query = f"SELECT id,username,name,bio,image FROM person WHERE username = '{user_data['username']}';"
            results = self.query(query)
            data = results["results"][0]

            if results is None:
                return jsonify({"message" : "User not Found"})
            else:
                return jsonify(data)
        except Exception as e:
            print("Error:" + str(e))
            return False
    def getUsersLastNRecipes(self, username, ini, fim):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id,name,post_date,rating,image FROM recipe WHERE person_id = (SELECT id FROM person WHERE username = \'%s\');"%(username))
        if fim >= cursor.rowcount:
            fim = cursor.rowcount-1
        try:
            c = cursor.fetchall()[ini:fim+1]
            for i in c:
                i["post_date"] = i["post_date"].strftime("%m/%d/%Y, %H:%M:%S")
            return c
        except Exception as e:
            print(e)
            return False
    def addRecipe(self, recipe_data):
        cursor = self.connection.cursor()
        try:
            ingredientes = json.loads(recipe_data['ingredients'])
            query = 'INSERT INTO recipe (name, image, description, preparation, post_date, person_id) values (\'%s\',\'%s\',\'%s\',\'%s\',CURRENT_TIMESTAMP, \'%s\') RETURNING id;'%(recipe_data["name"],recipe_data["image"],recipe_data["description"],recipe_data["preparation"],recipe_data["person_id"])
            print(query)  
            cursor.execute(query)
            id_of_new_row = cursor.fetchone()[0]
            print(query) 
            self.addIngredients(ingredientes,id_of_new_row)
        except Exception as e:
           print(e)
           self.connection.commit()
           return False
        self.connection.commit()
        cursor.close()
        return True
    def addIngredients(self,ingredientes, recipe_id):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        query = "INSERT INTO ingredient (name) values "
        for i in ingredientes:
            query+="('"+i+"'),"
        query = query[:-1]+" ON CONFLICT (name) DO NOTHING;"
        cursor.execute(query)
        print(query)  
        self.connection.commit()
        query = "INSERT INTO recipe_ingredient (recipe_id,ingredient_id,quantity) values "
        for i in ingredientes:
            query+="(%s,(SELECT id FROM ingredient WHERE name = \'%s\'),\'%s\'),"%(recipe_id,i,ingredientes[i])
        query = query[:-1]+";"
        cursor.execute(query)
        print(query)  
        self.connection.commit()
    def deleteRecipe(self,recipe_data):
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("DELETE FROM recipe WHERE id = %s;"%recipe_data["id"])
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.commit()
            return False
    def getRecipe(self, recipe_id):
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM recipe WHERE id = \'%s\';"%(recipe_id))
            c = cursor.fetchone()
            c["post_date"] = c["post_date"].strftime("%m/%d/%Y, %H:%M:%S")
            return json.dumps({"recipe":c,"ingredients":self.getIngredients(recipe_id)})
        except Exception as e:
            print(e)
            return False
    def getIngredients(self, recipe_id):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT recipe_ingredient.ingredient_id, ingredient.name, recipe_ingredient.quantity FROM ingredient, recipe_ingredient WHERE recipe_ingredient.recipe_id = \'%s\' AND recipe_ingredient.ingredient_id = ingredient.id;"%(recipe_id))
        return cursor.fetchall()
class Login(Resource):
    def __init__(self,database):
        self.database = database

    def get(self):
        auth = request.authorization

        if not auth or not auth.username or not auth.password:
            return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login Required!"'})

        return self.database.login(auth.username, auth.password)

class User(Resource):
    def __init__(self,database):
        self.database = database
    def post(self):
        if "edit" in request.form:
            return self.database.editUser(request.form)
        else:
            return self.database.addUser(request.form)
    def get(self):
        return self.database.getUser(request.form)

class Recipe(Resource):
    def __init__(self,database):
        self.database = database
    def post(self):
        return self.database.addRecipe(request.form)
    def get(self):
        return self.database.getRecipe(request.form["id"])
    def delete(self):
        return self.database.deleteRecipe(request.form)
database = Database()
api.add_resource(Login, '/login',resource_class_args=(database,))
api.add_resource(User, '/user',resource_class_args=(database,))
api.add_resource(Recipe, '/recipe',resource_class_args=(database,))

if __name__ == "__main__": 
    app.run(debug=True)