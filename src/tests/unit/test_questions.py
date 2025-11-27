import json
import pandas as pd 
from server.agent import StockAgent


EXCEL_PATH = "src/tests/AI Intern test questions.xlsx"
JSON_REPORT_PATH = "src/tests/test_results.json"

def run_tests_from_excel():
    df = pd.read_excel(EXCEL_PATH)
    
    if "question" not in df.columns or "expected_answer" not in df.columns:
        raise ValueError("Excel phải có cột 'question' và 'expected_answer'")

    agent = StockAgent()  
    results = []

    # 2. Duyệt từng câu hỏi
    for _, row in df.iterrows():
        question = str(row["question"])
        expected = str(row["expected_answer"])
        try:
            answer = agent.run(question)
            passed = answer == expected
        except Exception as e:
            answer = str(e)
            passed = False

        results.append({
            "question": question,
            "expected_answer": expected,
            "actual_answer": answer,
            "passed": passed
        })

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] Question: {question}\nActual Answer:\n{answer}\n")

    # 3. Lưu kết quả ra JSON
    with open(JSON_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Test report saved to {JSON_REPORT_PATH}")

if __name__ == "__main__":
    run_tests_from_excel()
    