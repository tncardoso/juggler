import argparse
import yaml
import os
import pathlib
from juggler.tui import Juggler
from juggler.template import Template
import juggler.complete as comp

def init(config):
    os.environ["OPENAI_API_KEY"] = config.get("openai", {}).get("api_key", "")
    os.environ["ANTHROPIC_API_KEY"] = config.get("anthropic", {}).get("api_key", "")

def tui(args, config):
    app = Juggler()
    app.run()

def tests(args, config):
    openai_config = config.get("openai", {})

    t = Tester(base_dir="tests")
    t.init(
        base_url=openai_config.get("base_url", None),
        headers=openai_config.get("headers", None),
    )
    t.run()

def run(args, config):
    template_dir = pathlib.Path(__file__).parent.resolve().joinpath("prompts")
    template_fname = template_dir.joinpath(args.template + ".j2")

    with open(template_fname, "r") as f:
        content = f.read()
        t = Template(content)
        t.run()

def complete(args, config):
    comp.complete(args.filename)

def main():
    # read juggler config
    config = None
    with open("juggler.yaml") as f:
        config = yaml.safe_load(f)
    init(config)

    parser = argparse.ArgumentParser(description="Working with LLMs")
    parser.add_argument("--model", default="gpt-4o")
    subparsers = parser.add_subparsers(dest="command")

    tui_parser = subparsers.add_parser("tui", help="Run TUI")
    tests_parser = subparsers.add_parser("tests", help="Run tests")

    run_parser = subparsers.add_parser("run", help="Run template")
    run_parser.add_argument("template", help="Template name")

    file_parser = subparsers.add_parser("complete", help="Autocomplete end of file")
    file_parser.add_argument("filename", help="Filename")

    args = parser.parse_args()

    if args.command == "tui":
        tui(args, config)
    elif args.command == "tests":
        tests(args, config)
    elif args.command == "run":
        run(args, config)
    elif args.command == "complete":
        complete(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

