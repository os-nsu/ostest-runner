import subprocess
import shutil
import os
import threading
import time
import signal

def stop_event_watcher(proc, stop_event, wait_intervals, timeout = 0, message = ""):
    wait = True
    start_time = time.time()
    while wait:
        time.sleep(wait_intervals)
        if proc.poll() is not None:
            #if proc.returncode != 0:   ### Tests exit with non-zero codes
            #    print(f"Error in {message}:\n{proc.stderr.read()}")
            #    return False
            wait = False
        if timeout != 0 and time.time() - start_time > timeout:
            print(f"Stop {message} due to timeout")
            wait = False
            proc.send_signal(signal.SIGINT)
            proc.wait()
            return False, proc.stdout, proc.stderr
        if stop_event.is_set():
            print(f"Stop {message} due to signal recieve")
            wait = False
            proc.send_signal(signal.SIGINT)
            proc.wait()
            return False, proc.stdout, proc.stderr
    return True, proc.stdout, proc.stderr

def start_with_signal_watch(args, cwd, stop_event, clean_up, message = ""):
    try:
        proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        print(f"Can't start {message}: {e}")
        return False, None, None
    is_good, out, err = stop_event_watcher(proc, stop_event, 0.01, message = message)
    if not is_good:
        clean_up()
        return False, out, err
    return True, out, err

def get_parameters(task_json):
    return {
        "project_dir": task_json["repositoryUrl"].split("/")[-1].rstrip(".git"),
        "user": task_json["repositoryUrl"].split("/")[-2],
        "attempt": str(task_json["attempt"]),
        "repositoryUrl": task_json["repositoryUrl"],
        "branch": task_json["branch"],
        "laboratoryNumber": str(task_json["laboratoryNumber"]),
        "connectedTests": task_json["connectedTests"],
        "dir_path": os.path.dirname(os.path.realpath(__file__)) + "/"
    }

def clone_repo(params, stop_event, cleaners):
    os.makedirs(f"labs/{params["user"]}/", exist_ok=True)
    clean_up = lambda: shutil.rmtree(f"labs/{params["user"]}/{params["project_dir"]}", ignore_errors=True)
    cleaners.append(clean_up)
    clean_up()
    args = ["git",
            "clone",
            params["repositoryUrl"],
            "--branch",
            params["branch"]]
    cwd = params["dir_path"] + f"labs/{params["user"]}/"
    is_good, _, _ = start_with_signal_watch(args, cwd, stop_event, clean_up, "git clone repo")
    if not is_good:
        return None
    return f"labs/{params["user"]}/{params["project_dir"]}"

def create_report_folder(params):
    report_dir = f"tests/reports/{params["user"]}/{params["project_dir"]}"
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
        return None
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
        return True
    except Exception as e:
        print(f"Can't start pip: {e}")
        return False

def tests(params, stop_event, repo_dir, reports_dir, tests_dir, cleaners):
    clean_up = lambda : None
    cleaners.append(clean_up)
    args = [
        "./run_tests.py",
        "--src",
        f"../../{repo_dir}",
        f"--junit-xml=../../{reports_dir}/report_attempt_{params["attempt"]}.xml"
    ]
    is_good, out, err = start_with_signal_watch(args, params["dir_path"] + tests_dir, stop_event, clean_up, "tests run")
    try:
        with open(f"{reports_dir}/stdout_output_{params["attempt"]}", "w") as outfile:
            outfile.write(out.read())
    except IOError:
        print(f"Error while writing {report_dir}/stdout_output_{params["attempt"]} file")
        return None
    except OSError:
        print(f"Cannot open {report_dir}/stdout_output_{params["attempt"]} file")
        return None
    if not is_good:
        try:
            with open(f"{reports_dir}/stdout_output_{params["attempt"]}", "w") as outfile:
                outfile.write(err.read())
        except IOError:
            print(f"Error while writing {report_dir}/stderr_output_{params["attempt"]} file")
            return None
        except OSError:
            print(f"Cannot open {report_dir}/stderr_output_{params["attempt"]} file")
            return None
        return None
    return f"{reports_dir}/report_attempt_{params["attempt"]}.xml"

def clean_up_cleaners(cleaners):
    for i in cleaners:
        i()

def run_test(task_json, stop_event):
    params = get_parameters(task_json)
    cleaners = []
    report_folder_dir = create_report_folder(params)

    repo_dir = clone_repo(params, stop_event, cleaners)
    if repo_dir is None or stop_event.is_set():
        print(f"repo_dir: {repo_dir}, stop_event {stop_event.is_set()}")
        clean_up_cleaners(cleaners)
        return None
    tests_dir = clone_test(params, stop_event, cleaners)
    if tests_dir is None or stop_event.is_set():
        print(f"tests_dir: {tests_dir}, stop_event {stop_event.is_set()}")
        clean_up_cleaners(cleaners)
        return None
    if not pip_install(tests_dir):
        print(f"pip_install: {false}, stop_event {stop_event.is_set()}")
        clean_up_cleaners(cleaners)
        return None
    report_file_name = tests(params, stop_event, repo_dir, report_folder_dir, tests_dir, cleaners)
    if report_file_name is None:
        print(f"report_file_name: {report_file_name}, stop_event {stop_event.is_set()}")
        return None
    return report_file_name
