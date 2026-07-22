"""
Main experiment runner for exp_01_status.

Usage:
    python src/main.py --config exp_01.yaml

Design:
- 3 personas (POOR / BASE / RICH), each run independently
- N rounds per persona = independent repeats, each with a DIFFERENT seed
  (seed = seed_base + round_index) so we can measure variance, not just
  one lucky/unlucky sample
- Within a round: purchase_history grows only BETWEEN days (day 1 always
  starts empty). Within a single day, breakfast/lunch/dinner do NOT see
  each other's picks yet - history only updates once the full day is done.
- purchase_history exposed to the model is a ROLLING WINDOW of the last
  HISTORY_WINDOW_DAYS days (not the full, ever-growing history). This keeps
  prompt size roughly constant even over very long runs (e.g. 1000 days),
  avoiding silent num_ctx truncation and runaway per-call latency.
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


MEAL_TYPES_DEFAULT = ["breakfast", "lunch", "dinner"]
MAX_TURNS_PER_EPISODE = 12  # safety cap on tool-call loop per meal
HISTORY_WINDOW_DAYS = 14    # rolling window: only last N days visible via get_purchase_history

client = ollama.Client(host='http://localhost:11434')


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_windowed_history(purchase_history, current_day, window_days=HISTORY_WINDOW_DAYS):
    """
    Returns only entries from the last `window_days` days relative to current_day.
    E.g. on day 50 with window_days=14, only days 36-49 are visible
    (current_day itself is excluded - it hasn't happened yet).
    If window_days is None, returns the full unfiltered history.
    """
    if window_days is None:
        return purchase_history
    cutoff = current_day - window_days
    return [h for h in purchase_history if h["day"] > cutoff]


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
    """Runs ONE meal's shopping session. Returns (cart, tool_call_sequence, forced_stop).
    `purchase_history` here should already be the WINDOWED slice the caller wants
    the model to see (see get_windowed_history)."""
    cart = []
    tool_call_sequence = []
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please do the shopping for {meal_type}."}
    ]

    call_options = dict(options)
    call_options["seed"] = seed

    forced_stop = True  # will be set False if the episode ends naturally

    for _ in range(max_turns):
        response = client.chat(
            model=model_name,
            messages=messages,
            tools=tools,
            options=call_options,
        )
        messages.append(response.message)

        if not response.message.tool_calls:
            forced_stop = False  # plain text response = natural end
            break

        finished = False
        for tool_call in response.message.tool_calls:
            tool_call_sequence.append(tool_call.function.name)
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
            forced_stop = False  # natural end via finish_shopping tool
            break

    return cart, tool_call_sequence, forced_stop


def append_jsonl(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_existing_progress(raw_path):
    """
    Reads an existing raw JSONL file (if any) and returns:
      - purchase_history reconstructed from ALL completed days (unwindowed -
        the windowing is applied later, per-day, at call time)
      - last_completed_day (0 if file doesn't exist / is empty)
    """
    if not raw_path.exists():
        return [], 0

    purchase_history = []
    last_day = 0
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            day = record["day"]
            last_day = max(last_day, day)
            for meal_type, cart in record["meals"].items():
                purchase_history.append({"day": day, "meal_type": meal_type, "items": cart})

    return purchase_history, last_day


def run_persona_round(persona_key, persona, model_name, options, seed,
                       meal_types, n_days, products, raw_dir,
                       history_window_days=HISTORY_WINDOW_DAYS):
    """One independent repeat (one seed) for one persona, across n_days.
    Resumes automatically if a partial raw file already exists.
    purchase_history keeps growing (full record, saved to disk), but only
    the last `history_window_days` days are exposed to the model each day."""
    system_prompt = build_system_prompt(persona)
    raw_path = raw_dir / f"{persona_key}_seed{seed}.jsonl"

    purchase_history, last_completed_day = load_existing_progress(raw_path)

    if last_completed_day >= n_days:
        print(f"[{persona_key} seed={seed}] already complete "
              f"({last_completed_day}/{n_days} days), skipping.")
        return purchase_history

    if last_completed_day > 0:
        print(f"[{persona_key} seed={seed}] resuming from day "
              f"{last_completed_day + 1}/{n_days} "
              f"({len(purchase_history)} prior meal-entries loaded, "
              f"window={history_window_days} days)")

    for day in range(last_completed_day + 1, n_days + 1):
        day_entries = []
        day_cart_all_meals = {}
        day_sequences = {}
        day_forced_stops = {}

        # only the rolling window is visible to the model this day,
        # even though `purchase_history` itself keeps the full record
        windowed_history = get_windowed_history(purchase_history, day, history_window_days)

        for meal_type in meal_types:
            t0 = time.time()
            cart, tool_call_sequence, forced_stop = run_shopping_episode(
                model_name, options, seed, system_prompt, meal_type,
                windowed_history, products,
            )
            elapsed = time.time() - t0

            day_cart_all_meals[meal_type] = cart
            day_sequences[meal_type] = tool_call_sequence
            day_forced_stops[meal_type] = forced_stop
            day_entries.append({"day": day, "meal_type": meal_type, "items": cart})

            stop_flag = " [FORCED STOP]" if forced_stop else ""
            print(f"[{persona_key} seed={seed}] day {day} {meal_type}: "
                  f"{len(cart)} items, {elapsed:.1f}s, "
                  f"history_visible={len(windowed_history)} entries, "
                  f"tools={tool_call_sequence}{stop_flag}")

        # commit today's picks to the FULL history (saved to disk in full),
        # windowing only affects what's shown to the model, not what's stored
        purchase_history.extend(day_entries)

        append_jsonl(raw_path, {
            "persona": persona_key,
            "seed": seed,
            "day": day,
            "meals": day_cart_all_meals,
            "tool_call_sequences": day_sequences,
            "forced_stops": day_forced_stops,
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

    # Support either:
    #   data.history_window_days: 14          (single variant, backward compatible)
    #   data.history_window_variants: [14, 100, null]   (multiple variants, compared side by side)
    if "history_window_variants" in config["data"]:
        window_variants = config["data"]["history_window_variants"]
    else:
        window_variants = [config["data"].get("history_window_days", HISTORY_WINDOW_DAYS)]

    base_raw_dir = Path(config["output"]["raw_dir"])
    products = load_products(products_file)

    total_episodes = (len(personas) * n_rounds * n_days * len(meal_types)
                       * len(window_variants))
    print(f"Starting {config['experiment']['name']}: "
          f"{len(personas)} personas x {n_rounds} rounds x {n_days} days x "
          f"{len(meal_types)} meals x {len(window_variants)} window variants "
          f"{window_variants} = {total_episodes} episodes")

    start_time = time.time()

    for window_days in window_variants:
        # each variant gets its own subfolder, e.g. results/exp_01/raw/window_14/,
        # results/exp_01/raw/window_full/ (for None), so runs never collide
        variant_label = f"window_{window_days}" if window_days is not None else "window_full"
        raw_dir = base_raw_dir / variant_label
        raw_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n\n########## VARIANT: {variant_label} ##########")

        for persona_key, persona in personas.items():
            for round_index in range(n_rounds):
                seed = seed_base + round_index
                print(f"\n=== [{variant_label}] {persona_key} | round {round_index+1}/{n_rounds} | seed={seed} ===")
                run_persona_round(
                    persona_key, persona, model_name, options, seed,
                    meal_types, n_days, products, raw_dir,
                    history_window_days=window_days,
                )

    total_elapsed = time.time() - start_time
    print(f"\nDone. Total time: {total_elapsed/3600:.2f}h")


if __name__ == "__main__":
    main()