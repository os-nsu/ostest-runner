#!/usr/bin/env python3

# The main entrypoint for runner

import random
import sys
import time
import argparse
import signal
from concurrent.futures import ThreadPoolExecutor
import threading
import subprocess
import os
from modules.run_test import run_test
from modules.start_testing_mock import start_testing_mock
from modules.parse_result import parse_xml_result
from modules.parse_result import parse_error_result
import logging
from modules.network import get_task
from modules.network import post_results

stop_event = threading.Event()
is_in_loop = False

class Config(object):
	pass

def signal_handler(signum, frame):
	logging.info(f"\nReceived signal, terminating...")
	stop_event.set()
	global is_in_loop
	if is_in_loop:
		is_in_loop = False
		raise KeyboardInterrupt("Stop sleeping")

def start_testing(config, task, worker_num):
	worker_num = getWorkerNum()

	logging.info(f"Received task")
	task_json = task.json()

	result = {}

	try:
		xml_path = run_test(task_json, stop_event, worker_num)
		result = parse_xml_result(xml_path)
	except RuntimeError as e:
		logging.error(f"run_test exited with due to {e}")
		result = parse_error_result(e)
	except KeyboardInterrupt as e:
		logging.info(f"run_test exited with due to {e}")
		return

	result["attempt"] = task_json["attempt"]

	logging.debug(f"post body: {result}")

	post_results(config, result)
	releaseWorkerNum(worker_num)

def main_loop(config):
	running = True

	futures = []

	global is_in_loop
	jobs_pool = ThreadPoolExecutor(max_workers=config.concurrent)
	worker_num = 0
	while running:
		try:
			if stop_event.is_set():
				running = False
				continue
			is_in_loop = True
			if len(futures) < config.concurrent:
				task = get_task(config)
				if task:
					if config.mock:
						futures.append(jobs_pool.submit(start_testing_mock, config, task)) ## for backend testing
					else:
						futures.append(jobs_pool.submit(start_testing, config, task, worker_num))
						worker_num = (worker_num + 1) % config.concurrent
			else:
				logging.info(f"\nNo space for new job")

			for task in futures[:]:
				logging.info(f"checking task: {task}")
				if task.done():
					logging.info(f"done task: {task}, result: {task.result()}")
					futures.remove(task)
			time.sleep(config.check_interval)
		except KeyboardInterrupt as e:
			logging.debug(f"Done sleeping due to exception: {e}")

	jobs_pool.shutdown()

	return 0

def configure_logger(config):
	logger_level_match = {
		"debug": logging.DEBUG,
		"info": logging.INFO,
		"warning": logging.WARNING,
		"error": logging.ERROR,
		"critical": logging.CRITICAL,
	}
	format = "%(asctime)s %(levelname)s %(message)s"
	if len(config.logger_output) == 0:
		logging.basicConfig(level=logger_level_match[config.logger_level], format=format)
		return
	logging.basicConfig(level=logger_level_match[config.logger_level], filename=config.logger_output, format=format)

def parse_args():
	parser = argparse.ArgumentParser(description="Run parallel make checks with various tools")
	parser.add_argument("--mock", action="store_true") ## For backend testing
	parser.add_argument("--backend-url", default="http://localhost:5000")
	parser.add_argument("--concurrent", type=int, default=2)
	parser.add_argument("--check-interval", type=int, default=5)
	parser.add_argument("--get-api", type=str, default="/api/task/available")
	parser.add_argument("--post-api", type=str, default="/api/task/result")
	parser.add_argument("--logger-level", type=str, default="error", help="debug, info, warning, error, critical")
	parser.add_argument("--logger-output", type=str, default="", help="log file path, default stdout")
	args = parser.parse_args()

	config = Config()
	config.mock = args.mock ## For backend testing
	config.backend_url = args.backend_url
	config.concurrent = args.concurrent
	config.check_interval = args.check_interval
	config.get_task_api_path = args.get_api
	config.post_task_api_path = args.post_api
	config.logger_level = args.logger_level
	config.logger_output = args.logger_output

	return config

if __name__ == "__main__":
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	config = parse_args()
	configure_logger(config)
	ret_code = main_loop(config)

	sys.exit(ret_code)
