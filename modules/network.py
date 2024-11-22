import requests
import logging

class Network:
	def __init__(self, config):
		self.__config = config

	def get_task(self):
		get_task_url = self.__config.backend_url + self.__config.get_task_api_path
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

	def post_results(self, result):
		response = requests.post(self.__config.backend_url + self.__config.post_task_api_path, json=result)
		if response:
			logging.info(f"Sent results to backend server successfully, return code:\n{response.status_code}")
		else:
			logging.error(f"Couldn't send results to backend server, return code:\n{response.status_code}")

class NetworkWithAuth:
	def __init__(self, config):
		self.__config = config

	def __get_auth_token(self):
		body = {"username": self.__config.login, "password": self.__config.password}
		logging.debug(f"login body:{body}")
		response = requests.post(self.__config.backend_url + self.__config.login_api_path, json=body, headers={"Content-Type": "application/json"})
		logging.debug(f"response:{response}")
		if response:
			response_json = response.json()
			logging.info(f"auth success, return code:\n{response.status_code}")
			logging.debug(f"login response body:{response_json}")
			return f"{response_json["type"]} {response_json["accessToken"]}"
		else:
			logging.error(f"auth error, return code:\n{response.status_code}")
			return

	def get_task(self):
		get_task_url = self.__config.backend_url + self.__config.get_task_api_path
		response = None
		try:
			response = requests.get(get_task_url, headers={"Authorization":self.__get_auth_token()})
		except requests.exceptions.RequestException as e:
			logging.error(f"No task available: got exception:\n{e}")
			return

		if response:
			logging.debug(f"task response body:{response.json()}")
			return response
		else:
			logging.info(f"No task available: response status code:\n{response.status_code}")

	def post_results(self, result):
		response = requests.post(self.__config.backend_url + self.__config.post_task_api_path, json=result, headers={"Authorization":self.__get_auth_token()})
		if response:
			logging.info(f"Sent results to backend server successfully, return code:\n{response.status_code}")
		else:
			logging.error(f"Couldn't send results to backend server, return code:\n{response.status_code}")