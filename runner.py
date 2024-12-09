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
from multiprocessing.pool import worker

from modules.futures_store import FuturesStore
from modules.run_test import TestRunner
from modules.start_testing_mock import start_testing_mock
from modules.parse_result import Parser
from modules.network import Network
from modules.network import NetworkWithAuth
import logging


stop_event = threading.Event()
is_in_loop = False

class Config(object):
	pass

def signal_handler(signum, frame):
	logging.info(f"Received signal, terminating...")
	stop_event.set()
	global is_in_loop
	if is_in_loop:
		is_in_loop = False
		raise KeyboardInterrupt("Stop sleeping")


def start_testing(task, network, parser, worker_num):
	logging.info(f"Received task")
	task_json = task.json()
	result = {}
	runner = TestRunner(task_json, stop_event, worker_num, 0.01, 20)
	try:
		xml_path = runner.run_test()
		result = parser.parse_xml_result(xml_path)
	except RuntimeError as e:
		logging.error(f"run_test exited with due to {e}")
		result = parser.parse_error_result(e)
	except KeyboardInterrupt as e:
		logging.info(f"run_test exited with due to {e}")
		result = parser.parse_error_result(e)

	result["id"] = task_json["id"]

	logging.debug(f"\npost body: {result}")

	network.post_results(result)


def main_loop(config):
	running = True

	futures_store = FuturesStore(config.concurrent)

	global is_in_loop
	jobs_pool = ThreadPoolExecutor(max_workers=config.concurrent)

	network = Network(config)
	if config.auth:
		network = NetworkWithAuth(config)
	else:
		network = Network(config)

	parser = Parser()
	while running:
		try:
			if stop_event.is_set():
				running = False
				continue
			is_in_loop = True
			while len(futures_store) < config.concurrent:
				task = network.get_task()
				if not task:
					break
				if task.json().get("status") is not None and task.json()["status"] == "UNAVAILABLE":
					break
				if config.mock:
					futures_store.append(jobs_pool.submit(start_testing_mock, task, network, parser)) ## for backend testing
				else:
					worker_num = futures_store.get_next_worker_num()
					futures_store.append(jobs_pool.submit(start_testing, task, network, parser, worker_num))
			if len(futures_store) == config.concurrent:
				logging.info(f"No space for new job")
			if len(futures_store) < config.concurrent:
				logging.info(f"No more tasks")

			tasks_done = 0

			for task in futures_store:
				logging.info(f"checking task: {task}")
				if task.done():
					tasks_done += 1
					logging.info(f"done task: {task}, result: {task.result()}")
					futures_store.remove(task)
			if tasks_done == 0:
				time.sleep(config.check_interval)
			is_in_loop = False
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
	parser.add_argument("--login-api", type=str, default="/api/v1/login")
	parser.add_argument("--token-refresh-api", type=str, default="/api/v1/auth/refresh")
	parser.add_argument("--refresh-time", type=int, default=60, help="time between requests for token refresh")
	parser.add_argument("--login", type=str, default="dora_explorer")
	parser.add_argument("--password", type=str, default="dora_explorer")
	parser.add_argument("--auth", action="store_true", help="use if backend has authentication") ## For auth
	parser.add_argument("--logger-level", type=str, default="error", help="debug, info, warning, error, critical. Default is error")
	parser.add_argument("--logger-output", type=str, default="", help="log file path, default stdout")
	args = parser.parse_args()

	config = Config()
	config.mock = args.mock ## For backend testing
	config.backend_url = args.backend_url
	config.concurrent = args.concurrent
	config.check_interval = args.check_interval
	config.get_task_api_path = args.get_api
	config.post_task_api_path = args.post_api
	config.login_api_path = args.login_api
	config.token_refresh_api_path = args.token_refresh_api
	config.refresh_time = args.refresh_time
	config.login = args.login
	config.password = args.password
	config.auth = args.auth ## For auth
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
