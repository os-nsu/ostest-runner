import subprocess
import shutil
import os
import threading
import time
import signal
import logging
import threading

class TestRunner:
	def __init__(self, task_json, stop_event, worker_num, wait_intervals=0.01, timeout=0):
		self.__params = self.__get_parameters(task_json, worker_num)
		self.__cleaners = []
		self.__wait_intervals = wait_intervals
		self.__timeout = timeout
		self.__stop_event = stop_event

	def __stop_event_watcher(self, proc, message = ""):
		wait = True
		start_time = time.time()
		while wait:
			time.sleep(self.__wait_intervals)
			if proc.poll() is not None:
				proc.wait()
				#if proc.returncode != 0:   ### Tests exit with non-zero codes
				#	logging.error(f"Error in {message}:\n{proc.stderr.read()}")
				#	return False, proc.stdout, proc.stderr
				wait = False
			if self.__timeout != 0 and time.time() - start_time > self.__timeout:
				logging.error(f"Stop {message} due to timeout")
				proc.send_signal(signal.SIGINT)
				proc.wait()
				raise RuntimeError(f"Timeout, {message} ran more than:{self.__timeout} seconds")
			if self.__stop_event.is_set():
				logging.info(f"Stop {message} due to stop signal")
				proc.send_signal(signal.SIGINT)
				proc.wait()
				raise KeyboardInterrupt("Stop signal received")
		return True, proc.stdout, proc.stderr

	def __start_with_signal_watch(self, args, cwd, clean_up, message = ""):
		try:
			logging.debug(f"Executing cmd: \"{' '.join(args)}\"")
			proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
		except Exception as e:
			logging.error(f"Can't start {message}: {e}")
			raise RuntimeError(f"Can't start {message}: {e}") from e
		is_good, out, err = self.__stop_event_watcher(proc, message = message)
		if not is_good:
			clean_up()
			return False, out, err
		return True, out, err

	def __get_parameters(self, task_json, worker_num):
		connectedTests = task_json.get("connectedTests", [])
		connectedTestsStringPattern = ""
		for test_name in connectedTests:
			connectedTestsStringPattern += f"{test_name} or "
		connectedTestsStringPattern = connectedTestsStringPattern.rstrip(" or ")
		logging.debug(f"Connected tests string pattern: {connectedTestsStringPattern}")

		labs = task_json.get("laboratoryNumber", [])
		laboratoryNumbers = []
		if isinstance(labs, list):
			for lab_number in labs:
				laboratoryNumbers.append(str(lab_number))
		else:
			laboratoryNumbers = [str(labs)]
		logging.debug(f"laboratoryNumbers: {laboratoryNumbers}")

		return {
			"worker_num": worker_num,
			"project_dir": task_json["repositoryUrl"].split("/")[-1].rstrip(".git"),
			"user": task_json["repositoryUrl"].split("/")[-2],
			"id": str(task_json["id"]),
			"repositoryUrl": task_json["repositoryUrl"],
			"branch": task_json["branch"],
			"laboratoryNumbers": laboratoryNumbers,
			"connectedTests": connectedTestsStringPattern,
			"dir_path": os.path.dirname(os.path.realpath(__file__)).rstrip("modules")
		}

	def __clone_repo(self):
		base_repo_dir = f"labs/{self.__params["worker_num"]}/{self.__params["user"]}/"
		os.makedirs(base_repo_dir, exist_ok=True)
		clean_up = lambda: shutil.rmtree(base_repo_dir + self.__params["project_dir"], ignore_errors=True)
		self.__cleaners.append(clean_up)
		clean_up()
		args = ["git",
				"clone",
				self.__params["repositoryUrl"],
				"--branch",
				self.__params["branch"]]
		cwd = self.__params["dir_path"] + base_repo_dir
		logging.debug(f"repo cloned {self.__params["worker_num"]}")
		is_good, _, _ = self.__start_with_signal_watch(args, cwd, clean_up, "git clone repo")
		if not is_good:
			raise RuntimeError(f"Clone repo error")
		return base_repo_dir + f"{self.__params["project_dir"]}"

	def __create_report_folder(self):
		report_dir = f"tests/reports/{self.__params["worker_num"]}/{self.__params["user"]}/{self.__params["project_dir"]}"
		os.makedirs(report_dir, exist_ok=True)
		return report_dir

	def __clone_test(self):
		tests_dir = f"tests/{self.__params["worker_num"]}"
		clean_up = lambda: shutil.rmtree(tests_dir + "tests", ignore_errors=True)
		self.__cleaners.append(clean_up)
		os.makedirs(tests_dir, exist_ok=True)
		clean_up()
		args = [
			"git",
			"clone",
			"https://github.com/os-nsu/tests.git"
		]
		cwd = self.__params["dir_path"] + tests_dir
		is_good, _, _ = self.__start_with_signal_watch(args, cwd, clean_up, "git clone tests")
		logging.debug(f"test cloned worker {self.__params["worker_num"]}")
		if not is_good:
			raise RuntimeError(f"Clone tests error")
		return f"{tests_dir}/tests"

	def __venv_create(self):
		venv_dir = f"./tests/{self.__params["worker_num"]}/venv"
		args = [
			"python",
			"-m",
			"venv",
			venv_dir
		]
		cwd = self.__params["dir_path"]
		try:
			proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
			proc.wait()
			logging.debug(f"venv created worker {self.__params["worker_num"]}")
		except Exception as e:
			logging.error(f"Can't create venv: {e}")
			raise RuntimeError(f"Can't create venv: {e}") from e
		return cwd + venv_dir

	def __pip_install(self, tests_dir, venv_dir):
		args = [
			f"{venv_dir}/bin/pip",
			"install",
			"-r",
			"requirements.txt"
		]
		try:
			proc = subprocess.Popen(args, cwd=tests_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
			proc.wait()
			logging.debug(f"pip install worker {self.__params["worker_num"]}")
		except Exception as e:
			logging.error(f"Can't start pip: {e}")
			raise RuntimeError(f"Can't start pip: {e}") from e

	def __tests(self, repo_dir, reports_dir, tests_dir, venv_dir):
		clean_up = lambda : None
		self.__cleaners.append(clean_up)
		args = [
			f"{venv_dir}/bin/python",
			"./run_tests.py",
			"--src",
			f"{self.__params["dir_path"]}{repo_dir}",
			f"--junit-xml={self.__params["dir_path"]}{reports_dir}/report.xml"
		]
		if len(self.__params["connectedTests"])!=0:
			args.append("-k")
			args.append(f"{self.__params["connectedTests"]}")
		if len(self.__params["laboratoryNumbers"])!=0:
			args.append("--lab-num")
			args += self.__params["laboratoryNumbers"]
		if self.__timeout != 0:
			args.append("--proxy_timeout")
			args.append(f"{int(self.__timeout * 0.9)}")

		cwd = self.__params["dir_path"] + tests_dir
		logging.debug(f"tests start worker {self.__params["worker_num"]}")
		is_good, out, err = self.__start_with_signal_watch(args, cwd, clean_up, "tests run")
		logging.debug(f"tests end worker {self.__params["worker_num"]}")
		stdout_id_output_dir = f"{reports_dir}/stdout_output_{self.__params["id"]}"
		stderr_id_output_dir = f"{reports_dir}/stderr_output_{self.__params["id"]}"
		try:
			with open(stdout_id_output_dir, "w") as outfile:
				outfile.write(out.read())
		except IOError as e:
			logging.error(f"Error while writing {stdout_id_output_dir} file")
			raise RuntimeError(f"Error while writing {stdout_id_output_dir} file") from e
		except OSError as e:
			logging.error(f"Cannot open {stdout_id_output_dir} file")
			raise RuntimeError(f"Cannot open {stdout_id_output_dir} file") from e
		if not is_good:
			try:
				with open(stderr_id_output_dir, "w") as outfile:
					outfile.write(err.read())
			except IOError as e:
				logging.error(f"Error while writing {stderr_id_output_dir} file")
				raise RuntimeError(f"Error while writing {stderr_id_output_dir} file") from e
			except OSError as e:
				logging.error(f"Cannot open {stderr_id_output_dir} file")
				raise RuntimeError(f"Cannot open {stderr_id_output_dir} file") from e
			raise RuntimeError("Error while running tests")
		return f"{reports_dir}/report.xml"

	def __clean_up_cleaners(self):
		logging.debug(f"cleanup worker {self.__params["worker_num"]}")
		for cleaner in self.__cleaners:
			cleaner()

	def run_test(self):
		logging.debug(f"started run_test worker {self.__params["worker_num"]}")
		report_folder_dir = self.__create_report_folder()
		try:
			repo_dir = self.__clone_repo()
			tests_dir = self.__clone_test()
			venv_dir = self.__venv_create()
			self.__pip_install(tests_dir, venv_dir)
			report_file_path = self.__tests(repo_dir, report_folder_dir, tests_dir, venv_dir)
			self.__clean_up_cleaners()
		except RuntimeError as e:
			logging.error(f"Error while running tests: {e}")
			self.__clean_up_cleaners()
			raise e
		except KeyboardInterrupt as e:
			logging.info(f"Testing stopped due to: {e}")
			self.__clean_up_cleaners()
			raise e
		return report_file_path
