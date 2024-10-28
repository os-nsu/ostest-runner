#!/usr/bin/env python3

# The main entrypoint for runner

import random
import sys
import time
import requests
import argparse
import signal
from concurrent.futures import ThreadPoolExecutor
import threading
import xml.etree.ElementTree as ET

stop_event = threading.Event()
jobs_pool = None

get_task_api_path = "/api/task/available"
post_task_api_path = "/api/task/result"

class Config(object):
	pass

def signal_handler(signum, frame):
	print(f"\nReceived signal, terminating...")
	stop_event.set()

def parse_xml_result(report_path):
	result = {}
	attempt_result = {}
	test_results = []

	test_suites = ET.parse(report_path).getroot()
	test_suit = test_suites.find('testsuite')

	attempt_result["isPassed"] = int(test_suit.get("errors")) == 0 and int(test_suit.get("failures")) == 0
	attempt_result["isError"] = int(test_suit.get("errors")) != 0
	attempt_result["errorDetails"] = "error during task execution" if attempt_result["isError"] else ""
	attempt_result["duration"] = test_suit.get("time")

	for testcase in test_suit.findall("testcase"):
		test_result = {}

		class_name = testcase.get("classname")
		test_name = testcase.get("name")
		name = class_name.replace("tests.", "")
		name = name + "::" + test_name

		test_result["name"] = name
		test_result["isPassed"] = True
		test_result["description"] = ""
		test_result["duration"] = testcase.get("time")
		test_result["memoryUsed"] = random.randrange(1000, 2000)

		if len(testcase):
			failure = testcase.find("failure")
			if failure is not None:
				test_result["isPassed"] = False
				test_result["description"] = failure.text

		test_results.append(test_result)

	attempt_result["testCases"] = test_results

	result["testResults"] = attempt_result
	return result


def start_testing(config, task):
	print(f"Received task")
	task_json = task.json()

	## TODO: Execute run_test.sh

	result = {}

	## For testing
	xml_path1 = "tests/reports/passed_report.xml"
	xml_path2 = "tests/reports/failed_report.xml"

	if task_json["repositoryUrl"] == "https://github.com/os-nsu/proxy-grisha.git":
		result = parse_xml_result(xml_path1)
	elif task_json["repositoryUrl"] == "https://github.com/os-nsu/proxy-anton.git":
		result = parse_xml_result(xml_path2)

	result["attempt"] = task_json["attempt"]

	print(f"post body: {result}")

	post_results(result)

def post_results(result):
	response = requests.post(config.backend_url + post_task_api_path, json=result)
	if response:
		print(f"Sent results to backend server successfully, return code:\n{response.status_code}")
	else:
		print(f"Couldn't send results to backend server, return code:\n{response.status_code}")

def get_task(config):
	get_task_url = config.backend_url + get_task_api_path
	response = None
	try:
		response = requests.get(get_task_url)
	except requests.exceptions.RequestException as e:
		print(f"No task available: got exception:\n{e}")
		return

	if response:
		return response
	else:
		print(f"No task available: response status code:\n{response.status_code}")

def main_loop(config):
	running = True

	futures = []

	global jobs_pool
	jobs_pool = ThreadPoolExecutor(max_workers=config.concurrent)

	while running:
		if stop_event.is_set():
			running = False
			continue

		if len(futures) < config.concurrent:
			task = get_task(config)
			if task:
				futures.append(jobs_pool.submit(start_testing, config, task))
		else:
			print(f"\nNo space for new job")

		for task in futures[:]:
			print(f"checking task: {task}")
			if task.done():
				print(f"done task: {task}, result: {task.result()}")
				futures.remove(task)

		time.sleep(config.check_interval)

	jobs_pool.shutdown()

	return 0

def parse_args():
	parser = argparse.ArgumentParser(description="Run parallel make checks with various tools")
	parser.add_argument("--backend-url", default="http://localhost:5000")
	parser.add_argument("--concurrent", type=int, default=2)
	parser.add_argument("--check-interval", type=int, default=5)
	args = parser.parse_args()

	config = Config()
	config.backend_url = args.backend_url
	config.concurrent = args.concurrent
	config.check_interval = args.check_interval

	return config

if __name__ == "__main__":
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	config = parse_args()
	ret_code = main_loop(config)

	sys.exit(ret_code)
