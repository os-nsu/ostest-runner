

def start_testing_mock(config, task): ## For backend testing
	print(f"Received task")
	task_json = task.json()

	## TODO: Execute run_test.sh

	result = {}

	## For testing
	xml_path1 = "mock_server/reports/passed_report.xml"
	xml_path2 = "mock_server/reports/failed_report.xml"

	if task_json["repositoryUrl"] == "https://github.com/os-nsu/proxy-grisha.git":
		result = parse_xml_result(xml_path1)
	elif task_json["repositoryUrl"] == "https://github.com/os-nsu/proxy-anton.git":
		result = parse_xml_result(xml_path2)

	result["attempt"] = task_json["attempt"]

	print(f"post body: {result}")

	post_results(result)