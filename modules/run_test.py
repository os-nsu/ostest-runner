import subprocess
import shutil
import os
import threading
import time
import signal
import logging
import threading

def stop_event_watcher(proc, stop_event, wait_intervals, timeout = 0, message = ""):
	wait = True
	start_time = time.time()
	while wait:
		time.sleep(wait_intervals)
		if proc.poll() is not None:
			#if proc.returncode != 0:   ### Tests exit with non-zero codes
			#	logging.error(f"Error in {message}:\n{proc.stderr.read()}")
			#	return False, proc.stdout, proc.stderr
			wait = False
		if timeout != 0 and time.time() - start_time > timeout:
			logging.error(f"Stop {message} due to timeout")
			wait = False
			proc.send_signal(signal.SIGINT)
			proc.wait()
			return False, proc.stdout, proc.stderr
		if stop_event.is_set():
			logging.info(f"Stop {message} due to signal recieve")
			wait = False
			proc.send_signal(signal.SIGINT)
			proc.wait()
			raise KeyboardInterrupt("Stop signal recieved")
	return True, proc.stdout, proc.stderr

def start_with_signal_watch(args, cwd, stop_event, clean_up, message = ""):
	try:
		proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
	except Exception as e:
		logging.error(f"Can't start {message}: {e}")
		raise RuntimeError(f"Can't start {message}: {e}") from e
	is_good, out, err = stop_event_watcher(proc, stop_event, 0.01, message = message)
	if not is_good:
		clean_up()
		return False, out, err
	return True, out, err

def get_parameters(task_json, worker_num):
	return {
		"worker_num": worker_num,
		"project_dir": task_json["repositoryUrl"].split("/")[-1].rstrip(".git"),
		"user": task_json["repositoryUrl"].split("/")[-2],
		"attempt": str(task_json["attempt"]),
		"repositoryUrl": task_json["repositoryUrl"],
		"branch": task_json["branch"],
		"laboratoryNumber": str(task_json["laboratoryNumber"]),
		"connectedTests": task_json["connectedTests"],
		"dir_path": os.path.dirname(os.path.realpath(__file__)) + "/../"
	}

def clone_repo(params, stop_event, cleaners):
	os.makedirs(f"labs/{params["worker_num"]}/{params["user"]}/", exist_ok=True)
	clean_up = lambda: shutil.rmtree(f"labs/{params["worker_num"]}/{params["user"]}/{params["project_dir"]}", ignore_errors=True)
	cleaners.append(clean_up)
	clean_up()
	args = ["git",
			"clone",
			params["repositoryUrl"],
			"--branch",
			params["branch"]]
	cwd = params["dir_path"] + f"labs/{params["worker_num"]}/{params["user"]}/"
	is_good, _, _ = start_with_signal_watch(args, cwd, stop_event, clean_up, "git clone repo")
	if not is_good:
		raise RuntimeError(f"Clone repo error")
	return f"labs/{params["worker_num"]}/{params["user"]}/{params["project_dir"]}"

def create_report_folder(params):
	report_dir = f"tests/reports/{params["worker_num"]}/{params["user"]}/{params["project_dir"]}"
	os.makedirs(report_dir, exist_ok=True)
	return report_dir

def clone_test(params, stop_event, cleaners):
	clean_up = lambda: shutil.rmtree(f"tests/tests", ignore_errors=True)
	cleaners.append(clean_up)
	tests_dir = "tests"
	os.makedirs(tests_dir, exist_ok=True)
	clean_up()
	args = [
		"git",
		"clone",
		"https://github.com/os-nsu/tests.git"
	]
	cwd = params["dir_path"] + tests_dir
	is_good, _, _ = start_with_signal_watch(args, cwd, stop_event, clean_up, "git clone tests")
	if not is_good:
		raise RuntimeError(f"Clone tests error")
	return f"{tests_dir}/tests"

def pip_install(tests_dir):
	args = [
		"pip",
		"install",
		"-r",
		"requirements.txt"
	]
	try:
		proc = subprocess.Popen(args, cwd=tests_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
		proc.wait()
	except Exception as e:
		logging.error(f"Can't start pip: {e}")
		raise RuntimeError(f"Can't start pip: {e}") from e

def tests(params, stop_event, repo_dir, reports_dir, tests_dir, cleaners):
	clean_up = lambda : None
	cleaners.append(clean_up)
	args = [
		"./run_tests.py",
		"--src",
		f"../../{repo_dir}",
		f"--junit-xml=../../{reports_dir}/report.xml"
	]
	is_good, out, err = start_with_signal_watch(args, params["dir_path"] + tests_dir, stop_event, clean_up, "tests run")
	try:
		with open(f"{reports_dir}/stdout_output_{params["attempt"]}", "w") as outfile:
			outfile.write(out.read())
	except IOError as e:
		logging.error(f"Error while writing {reports_dir}/stdout_output_{params["attempt"]} file")
		raise RuntimeError(f"Error while writing {reports_dir}/stdout_output_{params["attempt"]} file") from e
	except OSError as e:
		logging.error(f"Cannot open {reports_dir}/stdout_output_{params["attempt"]} file")
		raise RuntimeError(f"Cannot open {reports_dir}/stdout_output_{params["attempt"]} file") from e
	if not is_good:
		try:
			with open(f"{reports_dir}/stderr_output_{params["attempt"]}", "w") as outfile:
				outfile.write(err.read())
		except IOError as e:
			logging.error(f"Error while writing {reports_dir}/stderr_output_{params["attempt"]} file")
			raise RuntimeError(f"Error while writing {reports_dir}/stderr_output_{params["attempt"]} file") from e
		except OSError as e:
			logging.error(f"Cannot open {reports_dir}/stderr_output_{params["attempt"]} file")
			raise RuntimeError(f"Cannot open {reports_dir}/stderr_output_{params["attempt"]} file") from e
		raise RuntimeError("Error while running tests")
	return f"{reports_dir}/report.xml"

def clean_up_cleaners(cleaners):
	for cleaner in cleaners:
		cleaner()

def run_test(task_json, stop_event, worker_num):
	params = get_parameters(task_json, worker_num)
	cleaners = []
	report_folder_dir = create_report_folder(params)

	try:
		repo_dir = clone_repo(params, stop_event, cleaners)
		tests_dir = clone_test(params, stop_event, cleaners)
		pip_install(tests_dir)
		report_file_name = tests(params, stop_event, repo_dir, report_folder_dir, tests_dir, cleaners)
	except RuntimeError as e:
		logging.error(f"Error while running tests: {e}")
		clean_up_cleaners(cleaners)
		raise RuntimeError from e
	except KeyboardInterrupt as e:
		logging.info(f"Testing stopped due to: {e}")
		clean_up_cleaners(cleaners)
		raise KeyboardInterrupt from e
	return report_file_name
