import os
import yaml
import frontmatter
import guidance
import json

from pydantic import BaseModel, PrivateAttr
from typing import Optional
from deepdiff import DeepDiff
from pathlib import Path
from juggler.log import *

class YAMLLoader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super().__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))

        with open(filename, 'r') as f:
            return f.read()

YAMLLoader.add_constructor('!include', YAMLLoader.include)

class Tester(BaseModel):
    base_dir: Path
    _llm: guidance.llms.OpenAI = PrivateAttr()

    def init(self):
        self._llm = guidance.llms.OpenAI("gpt-3.5-turbo")

    def run_test(self, tpath: Path, config):
        succ(f"testing file {tpath}")
        meta = frontmatter.load(tpath)
        #print(meta.keys())

        content = meta.content
        prog = guidance(content, llm=self._llm)
        res = prog(**config["vars"])
        #print(res)
        #print(res.variables())

        if "verbose" in meta:
            for verbose_var in meta["verbose"]:
                value = res.get(verbose_var)
                info(f"    {verbose_var}: \"{value}\"")

        if "assert" in meta:
            for assert_var in meta["assert"].keys():
                if meta["assert"][assert_var]["type"] == "json":
                    #print("RAW")
                    #print(res.get(assert_var))
                    expected = meta["assert"][assert_var]["value"]
                    actual = None
                    try:
                        actual = json.loads(res.get(assert_var))
                    except json.decoder.JSONDecodeError:
                        error(f"    {assert_var}: invalid json")
                        error(f"    \"{res.get(assert_var)}\"")

                    diff = DeepDiff(expected, actual)
                    if diff:
                        error(f"   {assert_var}: " + str(actual))
                        error("   " + str(diff))
                        return False
                    else:
                        succ("    ok!")
                        return True

                

    def run_tests(self, dir: Path, config):
        config_path = Path(os.path.join(dir, "config.yaml"))
        
        # read directory config, if exists
        if config_path.exists():
            info(f"reading config file: {config_path}")
            new_config = yaml.load(config_path.open("r"), YAMLLoader)
            config.update(new_config)
            #print(config)

        # run tests in directory
        for tpath in dir.glob("*.guidance"):
            self.run_test(tpath, config)

        # inception, go one level deeper
        for new_dir in dir.iterdir():
            if new_dir.is_dir():
                self.run_tests(new_dir, config)

    def run(self):
        self.run_tests(self.base_dir, {})

if __name__ == "__main__":
    t = Tester(base_dir="tests")
    t.init()
    t.run()
