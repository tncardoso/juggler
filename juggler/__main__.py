import argparse
import logging
import os
import glob
import pathlib
from juggler.tui import Juggler
from juggler.template import Template, TemplateLoader
from juggler.model import ContextFile
from juggler.sh import SHAgent
from juggler.config import *
import juggler.complete as comp


def init(config: Config) -> None:
    logging.basicConfig(level=logging.DEBUG)
    # litellm.set_verbose=True
    if config.openai:
        os.environ["OPENAI_API_KEY"] = config.openai.key
    if config.anthropic:
        os.environ["ANTHROPIC_API_KEY"] = config.anthropic.key


def tui(args: argparse.Namespace, config: Config) -> None:
    app = Juggler(args.model)
    app.run()


def list_templates(args: argparse.Namespace, config: Config) -> None:
    args.loader.list()

def run(args: argparse.Namespace, config: Config) -> None:
    logging.info("loading context files from", args.context_dir)
    context = []
    if args.context_dir != None:
        context_glob = glob.iglob(args.context_dir)
        for fname in context_glob:
            with open(fname, "r") as f:
                context.append(
                    ContextFile(
                        filename=fname,
                        content=f.read(),
                    )
                )

    logging.info("reading input files")
    inputs = []
    for f in args.files:
        inputs.append(f.read())

    t = args.loader.get_by_name(args.model, args.template + ".j2")
    if t:
        t.run(context, inputs)


def complete(args: argparse.Namespace, config: Config):
    comp.complete(args.model, args.filename)


def shell(args: argparse.Namespace, config: Config):
    sh = SHAgent(args.model)
    sh.run()


def main():
    config = read_config()
    init(config)

    parser = argparse.ArgumentParser(description="Working with LLMs")
    parser.add_argument(
        "--model",
        choices=[
            "gpt-4o",
            "claude-3-5-sonnet-20240620",
            "o1-mini",
        ],
        default="claude-3-5-sonnet-20240620",
    )
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="List available templates")
    tui_parser = subparsers.add_parser("tui", help="Run TUI")

    run_parser = subparsers.add_parser("run", help="Run template")
    run_parser.add_argument(
        "--context-dir", type=str, default=None, help="Add specified files to context"
    )
    run_parser.add_argument("template", help="Template name")
    run_parser.add_argument(
        "files", nargs="*", type=argparse.FileType("r"), help="Input files"
    )

    file_parser = subparsers.add_parser("complete", help="Autocomplete end of file")
    file_parser.add_argument("filename", help="Filename")

    sh_parser = subparsers.add_parser("shell", help="Shell Agent")

    args = parser.parse_args()

    # add template loader to args
    pkg_dir = pathlib.Path(__file__).parent.resolve().joinpath("prompts")
    config_dir = Path.home().joinpath(".config/juggler/prompts")
    args.loader = TemplateLoader(
        [
            pkg_dir,
            config_dir,
        ]
    )

    if args.command == "tui":
        tui(args, config)
    elif args.command == "list":
        list_templates(args, config)
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
