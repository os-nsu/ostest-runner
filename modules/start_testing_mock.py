import logging
from modules.parse_result import Parser

def start_testing_mock(task, network, parser): ## For backend testing
	logging.info(f"Received task")
	task_json = task.json()

	## TODO: Execute run_test.sh

	result = {}

	## For testing
	xml_path1 = "mock_server/reports/passed_report.xml"
	xml_path2 = "mock_server/reports/failed_report.xml"

	if task_json["repositoryUrl"] == "https://github.com/os-nsu/proxy-grisha.git":
		result = parser.parse_xml_result(xml_path1)
	elif task_json["repositoryUrl"] == "https://github.com/os-nsu/proxy-anton.git":
		result = parser.parse_xml_result(xml_path2)

	result["id"] = task_json["id"]

	logging.info(f"post body: {result}")

	network.post_results(result)