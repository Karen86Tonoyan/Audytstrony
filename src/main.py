from __future__ import annotations

from arena import Arena


def choose_from_list(title: str, options: list[str], default_value: str) -> str:
    print(f"\n{title}")
    for idx, item in enumerate(options, start=1):
        marker = " (default)" if item == default_value else ""
        print(f"{idx}. {item}{marker}")

    raw = input("Choose number or press Enter for default: ").strip()
    if not raw:
        return default_value

    if not raw.isdigit():
        print("Invalid input. Using default.")
        return default_value

    index = int(raw) - 1
    if index < 0 or index >= len(options):
        print("Out of range. Using default.")
        return default_value

    return options[index]


def main() -> None:
    arena = Arena()

    defaults = arena.config.get("defaults", {})
    default_task = defaults.get("task_mode", "answer")
    default_thinking = defaults.get("thinking_mode", "balanced")
    default_evaluation = defaults.get("evaluation_mode", "best_overall")
    default_shape = defaults.get("answer_shape", "direct")

    print("GPT Arena Open Source")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("Question: ").strip()
        if not question:
            print("Please enter a question.\n")
            continue
        if question.lower() in {"exit", "quit"}:
            print("Bye.")
            break

        task_mode = choose_from_list(
            "Available task modes:",
            arena.list_task_modes(),
            default_task,
        )

        thinking_mode = choose_from_list(
            "Available thinking modes:",
            arena.list_thinking_modes(),
            default_thinking,
        )

        evaluation_mode = choose_from_list(
            "Available evaluation modes:",
            arena.list_evaluation_modes(),
            default_evaluation,
        )

        answer_shape = choose_from_list(
            "Available answer shapes:",
            arena.list_answer_shapes(),
            default_shape,
        )

        result = arena.run_round(
            question=question,
            task_mode=task_mode,
            thinking_mode=thinking_mode,
            evaluation_mode=evaluation_mode,
            answer_shape=answer_shape,
        )

        print("\n--- Round summary ---")
        print(f"Hard question: {result.is_hard}")
        print(f"Task mode: {result.task_mode}")
        print(f"Roles used: {', '.join(result.selected_roles)}")
        print(f"Thinking mode: {result.thinking_mode}")
        print(f"Evaluation mode: {result.evaluation_mode}")
        print(f"Answer shape: {result.answer_shape}")
        print(f"Conflict detected: {result.conflict_detected}")
        print(f"Confidence: {result.confidence}")
        print(f"Needs escalation: {result.needs_escalation}")

        if result.task_mode == "code":
            print("\n--- Generated approaches ---")
            for item in result.approaches:
                print(f"- {item['name']}: {item['description']}")
            print(f"\nSelected approach: {result.selected_approach}")

        print("\n--- Final answer ---")
        print(result.final_answer)
        print("\nSaved to logs/results.jsonl\n")


if __name__ == "__main__":
    main()
