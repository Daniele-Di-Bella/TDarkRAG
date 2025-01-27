import argparse
import csv

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams, LLMTestCase


# GEval metric
def calculate_geval_correctness(question: str, to_be_evaluated: str, reference_text: str, keyword: str, csv_YN: bool):
    with open(to_be_evaluated, 'r', encoding='utf-8') as file:
        actual_output = file.read()

    with open(reference_text, 'r', encoding='utf-8') as file:
        expected_output = file.read()

    test_case = LLMTestCase(
        input=question,
        actual_output=actual_output,
        expected_output=expected_output
    )

    correctness_metric_4o = GEval(
        name="Correctness",
        criteria="The expected output is the real Wikipedia page on a given topic, while the actual output is a "
                 "potential Wikipedia page on the same topic: Your goal is to determine on a scale from 1 to 5 "
                 "whether the actual output is a good Wikipedia page based on the expected output. You should put "
                 "particular attention on the accuracy of the facts and data cited in the actual output with respect"
                 "to the ones cited in the expected output.",
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
        model="gpt-4o"
    )

    correctness_metric_4o_mini = GEval(
        name="Correctness",
        criteria="The expected output is the real Wikipedia page on a given topic, while the actual output is a "
                 "potential Wikipedia page on the same topic: Your goal is to determine on a scale from 1 to 5 "
                 "whether the actual output is a good Wikipedia page based on the expected output. You should put "
                 "particular attention on the accuracy of the facts and data cited in the actual output with respect"
                 "to the ones cited in the expected output.",
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
        model="gpt-4o-mini"
    )

    correctness_metric_4o.measure(test_case)
    correctness_metric_4o_mini.measure(test_case)

    with open(f"[Eval]{to_be_evaluated}", "w", encoding='utf-8') as file:
        file.write(actual_output)
        file.write(f"## Evaluation\n"
                   f"GEval 4o correctness score: {correctness_metric_4o.score}\n"
                   f"Reason: {correctness_metric_4o.reason}\n\n"
                   f"GEval 4o-mini correctness score: {correctness_metric_4o.score}\n"
                   f"Reason: {correctness_metric_4o.reason}")

    # Report the GEval score also in a .csv that will be used for statistical analysis
    if csv_YN:
        with open("evaluation.csv", 'a+', newline='', encoding='utf-8') as file:
            # Move the cursor to the beginning to read any existing content
            file.seek(0)
            reader = csv.reader(file)
            rows = list(reader)  # Read existing rows (if any)

            # Check if the file is empty, and if necessary, write the header
            if not rows:
                writer = csv.writer(file)
                writer.writerow(["Topic", "GEval 4o score", "GEval 4o-mini score"])

            # Add new rows
            writer = csv.writer(file)
            writer.writerow([keyword, correctness_metric_4o.score, correctness_metric_4o_mini.score])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Estimate the quality of the generated text through GEval metric.")
    parser.add_argument("--question", required=True, help="Question that the RAG system has to answer")
    parser.add_argument("--to_be_evaluated", required=True, help="Path to the generated file")
    parser.add_argument("--reference_text", required=True, help="Path to the reference file")
    parser.add_argument("--keyword", required=True, help="Entry for the CSV row in which the score will be stored."
                                                         "It's the same keyword that was used to retrieve the sources for the RAG")
    parser.add_argument("--csv_path", required=True, help="Path to the CSV file in which the scores are stored")

    args = parser.parse_args()

    calculate_geval_correctness(args.question, args.to_be_evaluated, args.reference_text, args.keyword, args.csv_path)
