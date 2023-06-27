import argparse
import yaml
import guidance
from juggler.llm.library import GuidanceLibrary
from juggler.tui import Juggler

def tui(args, config):
    library = GuidanceLibrary(config["aliases"])
    app = Juggler(library)
    app.run()

def test(args, config):
    #f = open("tests/garcom.guidance", "r")
    f = open("tests/driver.guidance", "r")
    tst = f.read()
    f.close()

    llm = guidance.llms.OpenAI("gpt-3.5-turbo")
    test = guidance(tst, llm=llm)
    res = test()
    print(res)
    #print(dir(res))
    # res.variables(), skip llm
    # from IPython import embed; embed()
    print(res.variables())


def main():
    # read juggler config
    config = None
    with open("juggler.yml") as f:
        config = yaml.safe_load(f)

    parser = argparse.ArgumentParser(description="Working with LLMs")
    subparsers = parser.add_subparsers(dest="command")

    tui_parser = subparsers.add_parser("tui", help="Run TUI")
    test_parser = subparsers.add_parser("test", help="Run tests")
    args = parser.parse_args()

    if args.command == "tui":
        tui(args, config)
    elif args.command == "test":
        test(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

