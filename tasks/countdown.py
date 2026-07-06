"""Countdown (the TinyZero task): reach a target number from N given numbers,
each used exactly once, with + - * / and parentheses.

The Phase-C difficulty laboratory task. Two properties GSM8K lacked:
difficulty is a *generative dial* (num_numbers: 3 = easy … 6 = very hard),
and data is unlimited — fresh problems every run, no train/test reuse, eval
sets as large as statistics demand. Solvability is guaranteed by
construction: the target is produced by evaluating a random expression over
the sampled numbers.
"""

import ast
import random
from fractions import Fraction

from datasets import Dataset

from rewards import CORRECT_REWARD, answer_block, completion_text

SYSTEM_PROMPT = (
    "Solve the puzzle. Think step by step between <think> and </think>, then "
    "give only your final arithmetic expression between <answer> and "
    "</answer>.\nRespond exactly in this format:\n"
    "<think>\n...\n</think>\n<answer>\n(3 + 5) * 7\n</answer>"
)

USER_TEMPLATE = (
    "Using the numbers {numbers} exactly once each, and only + - * / and "
    "parentheses, write an expression that equals {target}."
)

OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
       ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}
OP_CHARS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}


# --- generation ----------------------------------------------------------------

def _random_expression(rng, numbers):
    """Random full-paren expression string over `numbers` + its exact value."""
    if len(numbers) == 1:
        return str(numbers[0]), Fraction(numbers[0])
    split = rng.randint(1, len(numbers) - 1)
    left, lval = _random_expression(rng, numbers[:split])
    right, rval = _random_expression(rng, numbers[split:])
    op = rng.choice(list(OPS))
    if op is ast.Div and rval == 0:
        op = ast.Add  # any op is fine; just avoid dividing by zero
    return f"({left} {OP_CHARS[op]} {right})", OPS[op](lval, rval)


def _make_problem(rng, num_numbers):
    """(numbers, target, one_solution). Integer targets in 1..999 only —
    rejection-sample until the random expression lands there."""
    while True:
        numbers = [rng.randint(1, 99) for _ in range(num_numbers)]
        shuffled = numbers[:]
        rng.shuffle(shuffled)
        expr, value = _random_expression(rng, shuffled)
        if value.denominator == 1 and 1 <= value <= 999:
            return numbers, int(value), expr


def _load(n, num_numbers, seed):
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        numbers, target, _ = _make_problem(rng, num_numbers)
        rows.append({
            "prompt": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",
                 "content": USER_TEMPLATE.format(numbers=numbers, target=target)},
            ],
            "numbers": numbers,
            "target": target,
        })
    return Dataset.from_list(rows)


def load_train(n, num_numbers=4, seed=0, **_):
    return _load(n, num_numbers, seed)


def load_eval(n, num_numbers=4, seed=0, **_):
    # offset the stream so train/eval never overlap for the same seed
    return _load(n, num_numbers, seed + 100_000)


# --- verification ----------------------------------------------------------------

def _safe_eval(node):
    """Evaluate an AST allowing only int literals, + - * / and unary minus.
    Fraction arithmetic keeps division exact (7/2*4 == 14, no float fuzz).
    Anything else (names, calls, **, floats) raises ValueError."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return Fraction(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval(node.operand)
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    raise ValueError(f"disallowed syntax: {ast.dump(node)}")


def verify(text, numbers, target, **_):
    """The completion's <answer> expression must (a) parse, (b) use exactly
    the given numbers (multiset match on literals), (c) equal the target."""
    block = answer_block(text)
    if block is None:
        return False
    try:
        tree = ast.parse(block.strip(), mode="eval").body
        literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)]
        if sorted(literals) != sorted(numbers):
            return False
        return _safe_eval(tree) == target
    except (SyntaxError, ValueError, ZeroDivisionError, TypeError):
        return False


# many expressions are valid answers -> majority voting is meaningless
canonical = None


def correctness_reward(completions, numbers, target, log_metric=None, **kwargs):
    """+1.0 if the expression checks out. unique_answer_rate counts distinct
    answer blocks — the collapse detector, same role as in GSM8K."""
    texts = [completion_text(c) for c in completions]
    rewards = [
        CORRECT_REWARD if verify(t, ns, tg) else 0.0
        for t, ns, tg in zip(texts, numbers, target)
    ]
    if log_metric is not None:
        blocks = [(answer_block(t) or "").strip() for t in texts]
        log_metric("accuracy", sum(r > 0 for r in rewards) / len(rewards))
        log_metric("unique_answer_rate", len(set(blocks)) / len(blocks))
    return rewards


if __name__ == "__main__":
    # Eyeball one rendered example: python -m tasks.countdown
    ds = load_train(1, num_numbers=4, seed=0)
    for message in ds[0]["prompt"]:
        print(f"--- {message['role']} ---\n{message['content']}")
    print(f"--- meta ---\nnumbers={ds[0]['numbers']} target={ds[0]['target']}")
