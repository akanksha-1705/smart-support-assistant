import csv
import requests

URL = "http://127.0.0.1:8000/chat"

with open("testcases.csv", newline="", encoding="utf-8") as file:
    tests = list(csv.DictReader(file))

passed = 0

for test in tests:
    try:
        response = requests.post(
            URL,
            json={"message": test["question"]},
            timeout=60
        )

        if response.status_code == 200:
            passed += 1
            result = "PASS"
        else:
            result = "FAIL"

        print(f'{test["id"]}: {result}')

    except Exception as e:
        print(f'{test["id"]}: FAIL - {e}')

print()
print(f"Passed: {passed}/{len(tests)}")
print(f"Failed: {len(tests) - passed}/{len(tests)}")