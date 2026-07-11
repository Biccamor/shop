"""
Main experiment runner for exp_01_status.

Usage:
    python run_simulation.py --config config_exp_01.yaml

Design:
- 3 personas (POOR / BASE / RICH), each run independently
- N rounds per persona = independent repeats, each with a DIFFERENT seed
  (seed = seed_base + round_index) so we can measure variance, not just
  one lucky/unlucky sample
- Within a round: purchase_history grows only BETWEEN days (day 1 always
  starts empty). Within a single day, breakfast/lunch/dinner do NOT see
  each other's picks yet - history only updates once the full day is done.
- Results are saved incrementally (after every single day) to a JSONL file,
  so a crash mid-run doesn't lose everything already computed.
"""

import argparse
import json
import time
from pathlib import Path

import ollama
import yaml

from tools import handle_tool, load_products, tools

TOOLS = tools

MEAL_TYPES_DEFAULT = ["breakfast", "lunch", "dinner"]
MAX_TURNS_PER_EPISODE = 14  # safety cap on tool-call loop per meal


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_system_prompt(persona):
    return (
        f"You are shopping for {persona['name']}, {persona['experience']}. "
        f"{persona['need']}. "
        "You have access to tools to browse products, check prices, review your "
        "purchase history, and add items to your cart. "
        "When you are done selecting items for this meal, call finish_shopping."
    )


def run_shopping_episode(model_name, options, seed, system_prompt, meal_type,
                          purchase_history, products, max_turns=MAX_TURNS_PER_EPISODE):
    """Runs ONE meal's shopping session. Returns the finished cart (list of dicts)."""
    cart = []
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please do the shopping for {meal_type}."}
    ]

    call_options = dict(options)
    call_options["seed"] = seed

    for _ in range(max_turns):
        response = ollama.chat(
            model=model_name,
            messages=messages,
            tools=TOOLS,
            options=call_options,
        )
        messages.append(response.message)

        if not response.message.tool_calls:
            break  # plain text response, no more tool calls -> treat as done

        finished = False
        for tool_call in response.message.tool_calls:
            result = handle_tool(
                {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                cart,
                purchase_history,
                products,
            )
            messages.append({"role": "tool", "content": json.dumps(result)})
            if tool_call.function.name == "finish_shopping":
                finished = True

        if finished:
            break

    return cart


def append_jsonl(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_persona_round(persona_key, persona, model_name, options, seed,
                       meal_types, n_days, products, raw_dir):
    """One independent repeat (one seed) for one persona, across n_days."""
    system_prompt = build_system_prompt(persona)
    purchase_history = []  # empty at start of every round
    raw_path = raw_dir / f"{persona_key}_seed{seed}.jsonl"

    for day in range(1, n_days + 1):
        day_entries = []
        day_cart_all_meals = {}

        for meal_type in meal_types:
            t0 = time.time()
            cart = run_shopping_episode(
                model_name, options, seed, system_prompt, meal_type,
                purchase_history, products,
            )
            elapsed = time.time() - t0

            day_cart_all_meals[meal_type] = cart
            day_entries.append({"day": day, "meal_type": meal_type, "items": cart})

            print(f"[{persona_key} seed={seed}] day {day} {meal_type}: "
                  f"{len(cart)} items, {elapsed:.1f}s")

        # commit the whole day at once -> next day's get_purchase_history sees it,
        # but meals WITHIN this day never saw each other
        purchase_history.extend(day_entries)

        # incremental save after every day
        append_jsonl(raw_path, {
            "persona": persona_key,
            "seed": seed,
            "day": day,
            "meals": day_cart_all_meals,
        })

    return purchase_history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config_exp_01.yaml")
    args = parser.parse_args()

    config = load_config(args.config)

    model_name = config["model"]["name"]
    options = config["model"]["options"]
    seed_base = config["model"]["seed_base"]

    personas = config["personas"]
    meal_types = config["data"].get("meals", MEAL_TYPES_DEFAULT)
    n_rounds = config["data"]["rounds"]
    n_days = config["data"]["days"]
    products_file = config["data"]["products_file"]

    raw_dir = Path(config["output"]["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    products = load_products(products_file)

    total_episodes = len(personas) * n_rounds * n_days * len(meal_types)
    print(f"Starting {config['experiment']['name']}: "
          f"{len(personas)} personas x {n_rounds} rounds x {n_days} days x "
          f"{len(meal_types)} meals = {total_episodes} episodes")

    start_time = time.time()

    for persona_key, persona in personas.items():
        for round_index in range(n_rounds):
            seed = seed_base + round_index
            print(f"\n=== {persona_key} | round {round_index+1}/{n_rounds} | seed={seed} ===")
            run_persona_round(
                persona_key, persona, model_name, options, seed,
                meal_types, n_days, products, raw_dir,
            )

    total_elapsed = time.time() - start_time
    print(f"\nDone. Total time: {total_elapsed/3600:.2f}h")


if __name__ == "__main__":
    main()