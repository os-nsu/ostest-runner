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
./runner.py --backend-url http://localhost:8080 --auth --logger-level=info
```

### Start mock backend

```
flask --app mock_server/test_backend run
```

Will start mock backend on 5000 port

```
./runner.py --backend-url http://localhost:5000 --logger-level=debug
```
## Logger

You can set logger level and output by ```--logger-level``` (default is error) and ```--logger-output``` (default is empty string == stdout)
Logger levels: debug, info, warning, error, critical

##

Argumets:

 - ```--mock``` returns to server predefined reports
 - ```--backend-url``` url to server
 - ```--concurrent``` number of workers
 - ```--check-interval``` interval time between checking tasks on backend
 - ```--check-proc-interval``` intervals between checks of process status
 - ```--timeout``` timeout for started processes
 - ```--get-api``` api path to task retrieval endpoint
 - ```--post-api``` api path to task result submition endpoint
 - ```--login-api``` api path to login endpoint
 - ```--token-refresh-api``` api path for login token refresh
 - ```--refresh-time``` time between requests for token refresh
 - ```--login``` login for authorization, default is dora_explorer
 - ```--password``` password for authorization, default is dora_explorer
 - ```--auth``` flag, indecationg that backend uses authorization
 - ```--logger-level``` logger level, default is info
 - ```--logger-output``` logger output file, default is "" and prints in stdout
 - ```--proxy-timeout``` timeout for one test proxy

## Contract

Runner goes to "/api/task/available" and waits for response with following format:

GET:
```json
{
    "status": "AVAILABLE",
    "id": 21,
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
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "isPassed": true,
  "duration": 0,
  "testResults": [
    {
      "isPassed": true,
      "description": "string",
      "memoryUsed": 0,
      "duration": 0,
      "name": "string"
    }
  ],
  "isError": true,
  "errorDetails": "string"
}
```