# OSTEST Runner

Takes tasks from backend and starts executing tests.
After tests uploads results back.

## Run

```
./runner.py --backend-url http://localhost:5000
```

Will start asking backend for new tasks.

If backend has auth, use --auth
You can set login and password with --login and --password, default is dora_explorer for both

```
./runner.py --backend-url http://localhost:8080 -auth
```

## Logger

You can set logger level and output by --logger-level(default is error) and --logger-output(default is empty string == stdout)
Logger levels: debug, info, warning, error, critical

### Start mock backend

```
flask --app mock_server/test_backend run
```


## Contract

Runner goes to "/api/task/available" and waits for response with following format:

GET:
```json
{
    "attempt": 21,
    "repositoryUrl": "https://github.com/os-nsu/proxy-grisha.git",
    "branch": "main",
    "laboratoryNumber": 1,
    "connectedTests": [
        "test1",
        "test2"
    ]
}
```

After tests have finished it parses xml report and return result to "/api/task/result":

POST:
```json
{
   "testResults":{
      "isPassed":false,
      "isError":false,
      "errorDetails":"",
      "duration":"15.866",
      "testCases": [
         {
            "name":"test_build::test_successful_make_clean",
            "isPassed":true,
            "description":"",
            "duration":"0.487",
            "memoryUsed":1772
         },
         {
            "name":"test_executable::test_run_with_invalid_arguments",
            "isPassed":false,
            "description":"steps/proxy_steps.py:25: in run_proxy_with_args\n    result = subprocess.run([proxy_bin_name] + args, cwd=project_dir, check=False, capture_output=True, text=True, timeout=timeout)\n/usr/lib/python3.12/subprocess.py:550: in run\n    stdout, stderr = process.communicate(input, timeout=timeout)\n/usr/lib/python3.12/subprocess.py:1209: in communicate\n    stdout, stderr = self._communicate(input, endtime, timeout)\n/usr/lib/python3.12/subprocess.py:2116: in _communicate\n    self._check_timeout(endtime, orig_timeout, stdout, stderr)\n/usr/lib/python3.12/subprocess.py:1253: in _check_timeout\n    raise TimeoutExpired(\nE   subprocess.TimeoutExpired: Command \\'[\\'/home/borodun/git/os-nsu/proxy-anton/develop/install/proxy\\', \\'--invalid_arg\\']\\' timed out after 1 seconds\n\nDuring handling of the above exception, another exception occurred:\ntests/test_executable.py:46: in test_run_with_invalid_arguments\n    result = run_proxy_with_args(project_dir, proxy_bin_name, [\\'--invalid_arg\\'], timeout=proxy_timeout)\nsteps/proxy_steps.py:27: in run_proxy_with_args\n    pytest.fail(f\"Proxy not finished in {timeout} seconds.\")\nE   Failed: Proxy not finished in 1 seconds.",
            "duration":"1.003",
            "memoryUsed":1491
         }
      ]
   },
   "attempt":21
}
```