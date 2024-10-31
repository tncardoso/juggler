import argparse
import yaml
import os
import glob
import pathlib
import litellm
from juggler.tui import Juggler
from juggler.template import Template
from juggler.model import ContextFile
from juggler.sh import SHAgent
import juggler.complete as comp

def init(config):
    #litellm.set_verbose=True
    os.environ["OPENAI_API_KEY"] = config.get("openai", {}).get("api_key", "")
    os.environ["ANTHROPIC_API_KEY"] = config.get("anthropic", {}).get("api_key", "")

def tui(args, config):
    app = Juggler(args.model)
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

    print("contex_dir", args.context_dir)
    context = []

    if args.context_dir != None:
        context_glob = glob.iglob(args.context_dir)
        for fname in context_glob:
            with open(fname, "r") as f:
                context.append(ContextFile(
                    filename=fname,
                    content=f.read(),
                ))

    inputs = []
    for f in args.files:
        inputs.append(f.read())

    with open(template_fname, "r") as f:
        content = f.read()
        t = Template(args.model, content)
        t.run(context, inputs)

def complete(args, config):
    comp.complete(args.model, args.filename)

def shell(args, config):
    sh = SHAgent(args.model)
    sh.run()

def main():
    # read juggler config
    config_path = (pathlib.Path(__file__)
                   .parent.parent
                   .resolve().joinpath("juggler.yaml"))
    config = None
    with open(config_path) as f:
        config = yaml.safe_load(f)
    init(config)

    parser = argparse.ArgumentParser(description="Working with LLMs")
    parser.add_argument("--model", 
                        choices=["gpt-4o", "claude-3-5-sonnet-20240620"],
                        default="claude-3-5-sonnet-20240620")
    subparsers = parser.add_subparsers(dest="command")

    tui_parser = subparsers.add_parser("tui", help="Run TUI")
    tests_parser = subparsers.add_parser("tests", help="Run tests")

    run_parser = subparsers.add_parser("run", help="Run template")
    run_parser.add_argument("--context-dir", type=str, default=None,
                            help="Add specified files to context")
    run_parser.add_argument("template", help="Template name")
    run_parser.add_argument("files", nargs="*",
                            type=argparse.FileType("r"),
                            help="Input files")

    file_parser = subparsers.add_parser("complete", help="Autocomplete end of file")
    file_parser.add_argument("filename", help="Filename")

    sh_parser = subparsers.add_parser("shell", help="Shell Agent")

    args = parser.parse_args()

    if args.command == "tui":
        tui(args, config)
    elif args.command == "tests":
        tests(args, config)
    elif args.command == "run":
        run(args, config)
    elif args.command == "complete":
        complete(args, config)
    elif args.command == "shell":
        shell(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

