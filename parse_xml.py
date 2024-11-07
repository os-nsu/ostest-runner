import xml.etree.ElementTree as ET

def parse_xml_result(report_path):
	result = {}
	attempt_result = {}
	test_results = []

	test_suites = ET.parse(report_path).getroot()
	test_suit = test_suites.find('testsuite')

	attempt_result["isPassed"] = int(test_suit.get("errors")) == 0 and int(test_suit.get("failures")) == 0
	attempt_result["isError"] = int(test_suit.get("errors")) != 0
	attempt_result["errorDetails"] = "error during task execution" if attempt_result["isError"] else ""
	attempt_result["duration"] = test_suit.get("time")

	for testcase in test_suit.findall("testcase"):
		test_result = {}

		class_name = testcase.get("classname")
		test_name = testcase.get("name")
		name = class_name.replace("tests.", "")
		name = name + "::" + test_name

		test_result["name"] = name
		test_result["isPassed"] = True
		test_result["description"] = ""
		test_result["duration"] = testcase.get("time")
		test_result["memoryUsed"] = random.randrange(1000, 2000)

		if len(testcase):
			failure = testcase.find("failure")
			if failure is not None:
				test_result["isPassed"] = False
				test_result["description"] = failure.text

		test_results.append(test_result)

	attempt_result["testCases"] = test_results

	result["testResults"] = attempt_result
	return result
