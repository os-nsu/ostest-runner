import requests
import logging
import time

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
		self.__refresh_time = config.refresh_time
		self.__token_type = None
		self.__authToken = None
		self.__refreshToken = None

	def __refreshAuthToken(self):
		body = {"refreshToken": self.__refreshToken}
		logging.debug(f"refreshToken body:{body}")
		response = requests.post(self.__config.backend_url + self.__config.token_refresh_api_path, json=body, headers={"Content-Type": "application/json"})
		logging.debug(f"refreshToken response:{response}")
		if response:
			response_json = response.json()
			self.__last_token_update = time.time()
			logging.info(f"refresh token success, return code:\n{response.status_code}")
			logging.debug(f"refresh token response body:{response_json}")
			self.__token_type = response_json["type"]
			self.__authToken = response_json["accessToken"]
			self.__refreshToken = response_json["refreshToken"]
		else:
			logging.error(f"refresh token error, setting reseting auth, return code:\n{response.status_code}")
			self.__token_type = None
			self.__authToken = None
			self.__get_auth_token()

	def __get_auth_token(self):
		if self.__authToken is not None:
			if (time.time()-self.__last_token_update>self.__refresh_time):
				self.__refreshAuthToken()
			return f"{self.__token_type} {self.__authToken}"
		body = {"username": self.__config.login, "password": self.__config.password}
		logging.debug(f"login body:{body}")
		response = requests.post(self.__config.backend_url + self.__config.login_api_path, json=body, headers={"Content-Type": "application/json"})
		logging.debug(f"login response:{response}")
		if response:
			response_json = response.json()
			self.__last_token_update = time.time()
			logging.info(f"auth success, return code:\n{response.status_code}")
			logging.debug(f"login response body:{response_json}")
			self.__token_type = response_json["type"]
			self.__authToken = response_json["accessToken"]
			self.__refreshToken = response_json["refreshToken"]
			return f"{self.__token_type} {self.__authToken}"
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
			if (response.status_code == 401):
				self.__token_type = None
				self.__authToken = None
				logging.info(f"relogining and resending results")
				self.post_results(result)