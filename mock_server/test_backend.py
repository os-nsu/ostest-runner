#!/usr/bin/env python3

# backend mock for testing

from flask import Flask, request

app = Flask(__name__)

task_count = 0
attempt_num = 0

@app.route("/api/task/available", methods=['GET'])
def send_task():
	global task_count, attempt_num

	task = {}
	task["attempt"] = attempt_num

	if task_count % 2 == 0:
		task["repositoryUrl"] = "https://github.com/os-nsu/proxy-grisha.git"
		task["branch"] = "main"
		task["laboratoryNumber"] = 1
		task["connectedTests"] = ["test1", "test2"]
	else:
		task["repositoryUrl"] = "https://github.com/os-nsu/proxy-anton.git"
		task["branch"] = "develop"
		task["laboratoryNumber"] = 2
		task["connectedTests"] = ["test3", "test4"]

	task_count += 1
	attempt_num += 1
	return task

@app.route("/api/task/result", methods=['POST'])
def receive_results():
	result = request.json
	print(f"Got result from runner:\n{result}")
	return "", 200
