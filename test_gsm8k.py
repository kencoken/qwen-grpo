"""GSM8K verifier tests (the task-specific half; shared format/normalization
cases live in test_rewards.py)."""

from tasks.gsm8k import correctness_reward, gold_answer, verify


def test_gold_answer_parses_gsm8k_solution():
    sol = "She sells 16 - 3 - 4 = <<16-3-4=9>>9 eggs.\n#### 18"
    assert gold_answer(sol) == "18"


def test_gold_answer_strips_commas():
    assert gold_answer("blah blah\n#### 1,234") == "1234"


def test_verify_normalizes_both_sides():
    assert verify("<think>.</think><answer>$1,000</answer>", answer="1000")
    assert not verify("<think>.</think><answer>999</answer>", answer="1000")
    assert not verify("no tags at all", answer="1000")


def test_correctness_reward_values():
    completions = [
        "<think>.</think><answer>$1,000</answer>",  # right, needs normalizing
        "<think>.</think><answer>999</answer>",     # wrong
        "no tags at all",                           # unparseable
    ]
    assert correctness_reward(completions, ["1000", "1,000", "1000"]) == [1.0, 0.0, 0.0]


def test_correctness_reward_logs_metrics():
    logged = {}
    completions = [
        "<think>.</think><answer>4</answer>",
        "<think>.</think><answer>4</answer>",
        "<think>.</think><answer>5</answer>",
        "junk",
    ]
    correctness_reward(
        completions, ["4"] * 4, log_metric=lambda k, v: logged.__setitem__(k, v)
    )
    assert logged["accuracy"] == 0.5
    assert logged["unique_answer_rate"] == 0.75  # {"4", "5", None} of 4
