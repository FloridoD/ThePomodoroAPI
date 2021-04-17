#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
from psycopg2.extras import RealDictCursor
import psycopg2, uuid
import json
from datetime import datetime
app = Flask(__name__)
api = Api(app)
class Database:

    def __init__(self):
        connection = psycopg2.connect(user = "ylhmlqpfkqbwxu",password = "86acc7cb14978bd57697eaa59022eec26a08f1930662da86502de3e39fd30e0d",host = "ec2-54-247-158-179.eu-west-1.compute.amazonaws.com",port = "5432",database = "dadih75qcq1ih")
        self.connection=connection

    def login(self, username, password):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id FROM person WHERE username = '"+username+"' AND password = '"+password+"';")
        if cursor.rowcount < 1:
            return False
        else:
            return True
    def addOrEditUser(self,user_data):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        try:
            query = 'INSERT INTO person (username, password, email, name, bio, image) values (\''+user_data['username']+'\', \''+user_data['password']+'\', \''+user_data['email']+'\', \''+user_data['name']+'\', \''+user_data["bio"]+'\', \''+user_data["image"]+'\');'
            cursor.execute(query)
            print(query)
            
        except Exception as e:
            print(e)
            self.connection.commit()
            try:
                cursor.execute('UPDATE person SET password = \'%s\', name = \'%s\', bio = \'%s\', image = \'%s\' WHERE username = \'%s\';'%(user_data['password'],user_data['name'],user_data['bio'],user_data['image'],user_data['username']))
            except Exception as e2:
                print(e2)
                self.connection.commit()
                cursor.close()
                return False 
        self.connection.commit()
        cursor.close()
        return True
    def getUser(self,user_data):
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            query = "SELECT id,username,name,bio,image FROM person WHERE username = '"+user_data['username']+"';"
            cursor.execute(query)
            print(query)
            if cursor.rowcount < 1:
                return False
            else:
                
                return json.dumps({"user":cursor.fetchone(),"recipes":self.getUsersLastNRecipes(user_data['username'],int(user_data['ini']),int(user_data['fim']))})
        except Exception as e:
            print(e)
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
    def get(self): # {"username": "...", "password": "..."}
        return self.database.login(request.form.get("username"),request.form.get("password"))

class User(Resource):
    def __init__(self,database):
        self.database = database
    def post(self):
        return self.database.addOrEditUser(request.form)
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