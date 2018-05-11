#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, json, jsonify

app = Flask(__name__)

@app.route('/')
def hello_world():
	return 'Hello, World!'

@app.route('/mt', methods=['POST', 'GET'])
def mt():
	error = None
	if request.method == 'POST':
		#app.logger.debug(vars(request))
		#app.logger.debug(request.get_json())
		#app.logger.debug(request.json)
		app.logger.debug(request.get_data())
		app.logger.debug(request.get_json())
		app.logger.debug(request.mimetype)
		app.logger.debug(request.content_type)

		return jsonify(request.get_json())
	return "Got your get"
