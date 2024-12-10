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
	task["id"] = attempt_num
	task["status"] = "AVAILABLE"
	if task_count % 7 == 0:
		task["repositoryUrl"] = "https://github.com/os-nsu/proxy-grisha.git"
		task["branch"] = "main"
		task["laboratoryNumber"] = 1
		task["connectedTests"] = []
	elif task_count % 7 == 1:
		task["repositoryUrl"] = "https://github.com/os-nsu/proxy-anton.git"
		task["branch"] = "develop"
		task["laboratoryNumber"] = 2
		task["connectedTests"] = ["test_files_exist",				## 1 lab
								  "test_static_library_compilation",## 1 lab
								  "test_static_library_inclusion", 	## 1 lab
								  "test_plugin_compilation",		## 1 lab
								  "test_proxy_with_empty_config",	## 2 lab
								  "test_proxy_without_config"]		## 2 lab
	elif task_count % 7 == 2:
		task["repositoryUrl"] = "https://github.com/os-nsu/proxy-grisha.git"
		task["branch"] = "main"
		task["laboratoryNumber"] = 1
		task["connectedTests"] = ["test_static_library_compilation",
								  "test_static_library_inclusion"] ## have dependency, must skip
	elif task_count % 7 == 3:
		task["repositoryUrl"] = "https://github.com/os-nsu/proxy-anton.git"
		task["branch"] = "develop"
		task["laboratoryNumber"] = 1
		task["connectedTests"] = ["test_files_exist", ## 1 lab
								  "test_directories_exist"]	## 1 lab
	elif task_count % 7 == 4:
		task["repositoryUrl"] = "https://github.com/os-nsu/proxy-anton.git"
		task["branch"] = "develop"
		task["laboratoryNumber"] = [1]
	elif task_count % 7 == 5:
		task["repositoryUrl"] = "https://github.com/os-nsu/proxy-grisha.git"
		task["branch"] = "develop"
		task["laboratoryNumber"] = [1, 2]
		task["connectedTests"] = ["test_files_exist",				## 1 lab
								  "test_static_library_compilation",## 1 lab
								  "test_static_library_inclusion", 	## 1 lab
								  "test_plugin_compilation",		## 1 lab
								  "test_proxy_with_empty_config",	## 2 lab
								  "test_execution_with_sanitizers"] ## 3 lab
	elif task_count % 7 == 6:
		task["repositoryUrl"] = "https://github.com/os-nsu/proxy-grisha.git"
		task["branch"] = "develop"
		task["connectedTests"] = ["test_files_exist",				## 1 lab
								  "test_static_library_compilation",## 1 lab
								  "test_static_library_inclusion", 	## 1 lab
								  "test_plugin_compilation",		## 1 lab
								  "test_proxy_with_empty_config"]	## 2 lab
	task_count += 1
	attempt_num += 1
	return task

@app.route("/api/task/result", methods=['POST'])
def receive_results():
	result = request.json
	print(f"Got result from runner:\n{result}")
	return "", 200
