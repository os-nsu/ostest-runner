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
import subprocess
import os
from run_test import run_test
from start_testing_mock import start_testing_mock
from parse_xml import parse_xml_result

stop_event = threading.Event()
jobs_pool = None

get_task_api_path = "/api/task/available"
post_task_api_path = "/api/task/result"

class Config(object):
	pass

def signal_handler(signum, frame):
	print(f"\nReceived signal, terminating...")
	stop_event.set()

def start_testing(config, task):
	print(f"Received task")
	task_json = task.json()

	xml_path = run_test(task_json, stop_event)

	if xml_path is None:
		## TODO: create task resubmission or failure message send
		return

	result = {}

	result = parse_xml_result(xml_path)

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
				if config.mock:
					futures.append(jobs_pool.submit(start_testing_mock, config, task)) ## for backend testing
				else:
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
	parser.add_argument("--mock", action="store_true") ## For backend testing
	parser.add_argument("--backend-url", default="http://localhost:5000")
	parser.add_argument("--concurrent", type=int, default=2)
	parser.add_argument("--check-interval", type=int, default=5)
	args = parser.parse_args()

	config = Config()
	config.mock = args.mock ## For backend testing
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
