#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import NoReturn
from flask import Flask, request, jsonify, make_response
from flask.helpers import make_response
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
from psycopg2.extras import RealDictCursor
import cloudinary
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
import psycopg2, uuid
import json
from functools import wraps
import jwt
import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey' #str(uuid.uuid1())
api = Api(app)

cloud = "the-pomodoro"
preset = "atzts87s"

def upload_local_image():
    """Uploads image to cloudinary database and returns url"""
    url = None

    with open("image.jpg", "rb") as f:
        data = f.read()
        image = bytearray(data)
        url = cloudinary.uploader.unsigned_upload(image, preset, cloud_name = "the-pomodoro").get('url')

    return url

def upload_image(image):
    return cloudinary.uploader.unsigned_upload(image, preset, cloud_name = "the-pomodoro").get('url')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'x-acess-token' in request.headers:
            token = request.headers['x-acess-token']
            
        if not token:
            return make_response(jsonify({'message' : 'Token is missing!'}), 401)
            
        try:
            print(app.config.get('SECRET_KEY'))
            data = jwt.decode(token, app.config.get('SECRET_KEY'), algorithms=["HS256"])
            username = data.get('public_id')
            
        except Exception as e:
            print(e)
            return make_response(jsonify({'message': 'Token is invalid'}), 401)

        return f(username, *args, **kwargs)

    return decorated

class Database:

    def __init__(self):
        connection = psycopg2.connect(user = "ylhmlqpfkqbwxu",password = "86acc7cb14978bd57697eaa59022eec26a08f1930662da86502de3e39fd30e0d",host = "ec2-54-247-158-179.eu-west-1.compute.amazonaws.com",port = "5432",database = "dadih75qcq1ih")
        self.connection=connection
        self.ingredientes = self.getAllIngredients()

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
            expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)

            token = jwt.encode({'public_id':username, 'exp': expire}, app.config.get('SECRET_KEY'), algorithm="HS256")
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
            return jsonify({'message': 'Username already exists'})

    def getFriends(self, user_data):

        return ''

    def getFriendsRecipes(self, user_data):

        return ''

    def getLikedRecipes(self, user_data):

        return ''

    def editUser(self,username,user_data):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute('UPDATE person SET password = \'%s\', name = \'%s\', bio = \'%s\', image = \'%s\' WHERE username = \'%s\';'%(user_data['password'],user_data['name'],user_data['bio'],user_data['image'],username))
            self.connection.commit()
            cursor.close()
            return jsonify({'message':'user updated'})
        except Exception as e2:
            self.connection.commit()
            cursor.close()
            return jsonify({'message': 'error'})

    def getUserByUsername(self, username):
        try:
            query = f"SELECT id,username,name,bio,image FROM person WHERE username = '{username}';"
            results = self.query(query)

            if results is None:
                return None
            else:
                return results.get("results")[0]
        except Exception:
            return None

    def getUser(self,user_data):
        try:
            query = f"SELECT id,username,name,bio,image FROM person WHERE username = '{user_data['username']}';"
            results = self.query(query)

            if results is None:
                return jsonify({"message" : "User not Found"})
            else:
                data = results.get('results')[0]
                print(data)
                data["recipes"] = []
                recipes = self.getUsersLastNRecipes(user_data['username'],int(user_data['ini']),int(user_data['fim']))
                
                for recipe in recipes:
                    data["recipes"].append(recipe)

                return jsonify(data)

        except Exception as e:
            print("Error" + str(e))
            return jsonify({"message" : "User not Found"})

    def getUsersLastNRecipes(self, username, ini, fim):
        query = "SELECT id,name,post_date,description,rating,image FROM recipe WHERE person_id = (SELECT id FROM person WHERE username = \'%s\');"%(username)
        
        recipes = self.query(query)

        if recipes is None:
            return None

        recipes = recipes.get('results')

        if fim > len(recipes): fim = len(recipes) 
        
        for recipe in recipes:
            recipe['post_date'] = recipe['post_date'].strftime("%m/%d/%Y, %H:%M:%S")

        return recipes[ini: fim]

    def addRecipe(self, username, recipe_data):
        cursor = self.connection.cursor()
        try:
            ingredientes = recipe_data['ingredients']
            query = f"INSERT INTO recipe (name, image, description, preparation, post_date, person_id) values('{recipe_data['name']}', '{recipe_data['image']}', '{recipe_data['description']}', '{recipe_data['preparation']}', CURRENT_TIMESTAMP, (SELECT id from person where username = '{username}')) RETURNING id"
            cursor.execute(query)
            id_of_new_row = cursor.fetchone()[0]
            print(query)
            self.addIngredients(ingredientes,id_of_new_row)
        except Exception as e:
            print(e)
            self.connection.commit()
            return jsonify({'message' : 'wrong data'})

        self.connection.commit()
        cursor.close()
        return jsonify({'message' : 'sucess'})

    def addIngredients(self,ingredientes, recipe_id):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        query = "INSERT INTO ingredient (name) values "
        for i in ingredientes:
            query += f"('{i.get('name')}'),"

        query = query[:-1]+" ON CONFLICT (name) DO NOTHING;"
        cursor.execute(query)
        self.connection.commit()
        print(query)  

        query = "INSERT INTO recipe_ingredient (recipe_id,ingredient_id,quantity) values "
        for i in ingredientes:
            query += f"({recipe_id},(SELECT id FROM ingredient WHERE name = '{i.get('name')}'),'{i.get('quantity')}'),"  
        query = query[:-1]+";"
        cursor.execute(query)
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
            query = f'select r.name, r.description, r.preparation, r.rating, r.rates, p.name "author", r.image, r.post_date from recipe r, person p where r.person_id = p.id and r.id = {recipe_id};'
            cursor.execute(query)
            c = cursor.fetchone()
            c["post_date"] = c["post_date"].strftime("%m/%d/%Y, %H:%M:%S")
            return jsonify({"recipe":c,"ingredients":self.getIngredients(recipe_id)})
        except Exception as e:
            print(e)
            return False

    def getIngredients(self, recipe_id):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT recipe_ingredient.ingredient_id, ingredient.name, recipe_ingredient.quantity FROM ingredient, recipe_ingredient WHERE recipe_ingredient.recipe_id = \'%s\' AND recipe_ingredient.ingredient_id = ingredient.id;"%(recipe_id))
        return cursor.fetchall()

    def getRecipesFromIngredients(self,ingredientes):
        query = "SELECT recipe_id, ingredient_id, recipe.* FROM recipe_ingredient, recipe WHERE ingredient_id IN (SELECT ingredient.id FROM ingredient WHERE LOWER(ingredient.name) IN ("
        for i in ingredientes:
            query+="'"+i+"',"
        query = query[:-1] + ")) AND recipe_id = id;"
        results = self.query(query)
        print(query)
        dic = {}
        out = {}
        print(results)
        for i in results["results"]:
            if i["recipe_id"] in dic:
                dic[i["recipe_id"]]+= [i["ingredient_id"]]
            else:
                dic[i["recipe_id"]] = [i]
        for i in dic:
            if len(ingredientes) == len(dic[i]):
                out[i] = dic[i][0]
        if out:
            return jsonify(out)
        else:
            return jsonify({'message': 'Sorry, no recipes found'})

    def getAllIngredients(self):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT name, COUNT(ingredient_id) FROM ingredient, recipe_ingredient WHERE id = ingredient_id GROUP BY name ORDER BY -COUNT(ingredient_id);")
        k = 1000
        if cursor.rowcount < 1000:
            k = cursor.rowcount
        out = []
        cu = cursor.fetchall()[:k]
        for i in cu:
            out += [i["name"]]
        out.sort()
        return out

    def getIngredientsFromText(self, query):
        res = []
        n = 0
        for i in self.ingredientes:
            if query in i:
                res += [i]
                n +=1
            if n == 5:
                break
        return jsonify(res)
        
    def getRecipeFromText(self, query):
        """Get recipe from text"""
        results = self.query("SELECT * FROM recipe WHERE name LIKE '%"+query+"%';")
        return jsonify(results)

    def rateRecipe(self,username,rate_data):
        """Add rating to recipe"""
        if(self.getUsersRateOnRecipe(username,rate_data['recipe_id']) != None):
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            try:
                query = 'INSERT INTO rating (rate, rate_date, recipe_id, person_id) values ('+rate_data['rate']+',CURRENT_TIMESTAMP,'+rate_data['recipe_id']+',(SELECT id FROM person WHERE username = \''+username+'\'));'
                cursor.execute(query)
                self.connection.commit()
                cursor.execute('UPDATE recipe SET rating = rating*(1-1/(rates+1)) + %s*(1/(rates+1)), rates = rates + 1;'%(rate_data['rate']))
                self.connection.commit()
                return jsonify({'message': 'Rating Inserted'})
            except Exception as e:
                print(e)
                self.connection.commit()
                return jsonify({'message': 'Error'})
        else:
            return jsonify({'message': 'User already voted'})
    def getUsersRateOnRecipe(self, user, recipe):
        try:
            query = "SELECT rate FROM rating WHERE person_id = (SELECT id FROM person WHERE username = %s) AND recipe_id = \'%\'"%(user,recipe)
            results = self.query(query)
            if results != None:
                return jsonify(results)
            else:
                return None
        except Exception as e:
            print(e)
            return jsonify({'message': 'Error'})
    def follow(self,username,person):
        try:
            cursor = self.connection.cursor()
            query = 'UPDATE person SET followers = followers + 1 WHERE username = \'%s\';'%(person)
            cursor.execute(query)
            self.connection.commit()
            query = 'UPDATE person SET following = following + 1 WHERE username = \'%s\';'%(username)
            cursor.execute(query)
            self.connection.commit()
            query = 'INSERT INTO person_person (person_id,person_id1) values ((SELECT id FROM person WHERE username = \'%s\'),(SELECT id FROM person WHERE username = \'%s\'));'%(person,username)
            self.connection.commit()
        except Exception as e:
            print(e)
            self.connection.commit()
            return jsonify({'message': 'Error'})
    def isFollowing(self,username,person):
        query = 'SELECT * FROM person_person WHERE person_id = (SELECT id FROM person WHERE username = \'%s\') AND person_id1 = (SELECT id FROM person WHERE username = \'%s\');'%(person,username)
        if self.query() != None:
            return False
        else:
            return True
    def getFriends(self, user_data):

        return ''

    def getFriendsRecipes(self, user_data):

        return ''

    def getLikedRecipes(self, user_data):

        return ''

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
        """Estabeleçe conexão com base de dados"""
        self.database = database
    
    def put(self):
        """Regista um utilizador"""
        data = request.get_json()
        return self.database.addUser(data)

    def get(self):
        """Retorna os dados dum utilizador"""
        data = request.get_json()
        return self.database.getUser(data)
    
    @token_required
    def post(username, self):
        """Atualiza os dados dum utilizador"""
        data = request.get_json()
        return self.database.editUser(username, data)


class Recipe(Resource):
    def __init__(self,database):
        """Estabeleçe conexão com base de dados"""
        self.database = database

    @token_required
    def post(username, self):
        """Cria uma receita associada a um utilizador"""
        data = request.get_json()
        return self.database.addRecipe(username, data)

    def get(self):
        """Retorna uma receita com base no id"""
        id = request.get_json().get('id')
        return self.database.getRecipe(id)

    def delete(self):
        """Elimina uma receita da base de dados"""
        return self.database.deleteRecipe(request.form)

class SearchByIngredients(Resource):
    def __init__(self,database):
        self.database = database

    def post(self):
        return self.database.getRecipesFromIngredients(request.get_json()['ingredients'])

    def get(self):
        return self.database.getIngredientsFromText(request.get_json()['query'])

class SearchByName(Resource):
    def __init__(self,database):
        self.database = database

    def post(self):
        return self.database.getRecipeFromText(request.get_json()['query'])

class Rate(Resource):
    def __init__(self,database):
        self.database = database
    @token_required
    def post(self,username):
        return self.database.rateRecipe(username,request.get_json())
    @token_required
    def get(self,username):
        return self.database.getUsersRateOnRecipe(username,request.get_json()['recipe_id'])

database = Database()
api.add_resource(Login, '/login',resource_class_args=(database,))
api.add_resource(User, '/user',resource_class_args=(database,))
api.add_resource(Recipe, '/recipe',resource_class_args=(database,))
api.add_resource(SearchByIngredients, '/search_by_ingredients',resource_class_args=(database,))
api.add_resource(SearchByName, '/search_by_name',resource_class_args=(database,))

if __name__ == "__main__": 
    #upload_image()
    app.run(debug=True)
