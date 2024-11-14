import requests
import logging

def get_task(config):
	get_task_url = config.backend_url + config.get_task_api_path
	response = None
	try:
		response = requests.get(get_task_url)
	except requests.exceptions.RequestException as e:
		logging.error(f"No task available: got exception:\n{e}")
		return

	if response:
		return response
	else:
		logging.info(f"No task available: response status code:\n{response.status_code}")

def post_results(config, result):
	response = requests.post(config.backend_url + config.post_task_api_path, json=result)
	if response:
		logging.info(f"Sent results to backend server successfully, return code:\n{response.status_code}")
	else:
		logging.error(f"Couldn't send results to backend server, return code:\n{response.status_code}")