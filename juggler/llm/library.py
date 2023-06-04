import re
import guidance
from pydantic import BaseModel
from typing import Iterator, Tuple, List

from juggler.message import LLMMessage, MessageType

class GuidanceTokenizer(BaseModel):
    llm: guidance.llms.LLM = None
    roles: set[str] = set(["system", "assistant", "user"])
    tags: dict[str, Tuple[bool, str]] = {}
    tags_re: str = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

        all_tags = []
        for role in self.roles:
            self.tags[self.llm.role_start(role)] = (True, role)
            self.tags[self.llm.role_end(role)] = (False, role)

            all_tags.append(re.escape(self.llm.role_start(role)))
            all_tags.append(re.escape(self.llm.role_end(role)))
            
        self.tags_re = "|".join(all_tags)

    def tokenize(self, content: str) -> List[LLMMessage]:
        # naive algorithm, can be optimized later
        messages = []

        current_role = None
        start_pos = None
        for match in re.finditer(self.tags_re, content):
            start, role = self.tags[match.group(0)]

            if start:
                current_role = role
                start_pos = match.end()
            else:
                snippet = content[start_pos:match.start()]
                messages.append(LLMMessage(
                    MessageType.from_openai_role(current_role),
                    snippet
                ))

                current_role = None
                start_pos = None

        if current_role != None:
            messages.append(LLMMessage(
                MessageType.from_openai_role(current_role),
                content[start_pos:]
            ))
        
        return messages


class GuidanceLibrary(BaseModel):
    llm: guidance.llms.LLM = None
    tokenizer: GuidanceTokenizer = None
    prompts: dict[str, str] = {}
    default_prompt: str = """{{#system~}}
You are a helpful assistant that can answer questions using markdown.
{{~/system}}

{{~#each msgs}}
{{#user~}}
{{this.user_text}}
{{~/user}}

{{#assistant~}}
{{this.ai_text}}
{{~/assistant}}
{{~/each}}

{{#user~}}
{{last_user_text}}
{{~/user}}

{{#assistant~}}
{{gen 'last_ai_text' temperature=0}}
{{~/assistant}}
"""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, prompts: dict[str, str]={}):
        super().__init__()
        self.llm = guidance.llms.OpenAI("gpt-3.5-turbo")
        self.tokenizer = GuidanceTokenizer(self.llm)
        self.prompts = prompts

    def has_program(self, program: str) -> bool:
        return program in self.prompts
    
    def run_alias(self, name: str, **kwargs) -> Iterator[List[LLMMessage]]:
        return self.run(self.prompts[name], **kwargs)

    def run_messages(self, msgs: List[LLMMessage]) -> Iterator[List[LLMMessage]]:
        assert msgs[-1].type == MessageType.USER
        last_user_text = msgs[-1].content
        prepared_msgs = []

        for i in range(0, len(msgs)-1, 2):
            assert msgs[i].type == MessageType.USER
            assert msgs[i+1].type == MessageType.AI
            prepared_msgs.append({
                "user_text": msgs[i].content,
                "ai_text": msgs[i+1].content,
            })

        return self.run(self.default_prompt,
                        msgs=prepared_msgs,
                        last_user_text=last_user_text)
        

    def run(self, program: str, **kwargs) -> Iterator[List[LLMMessage]]:
        """
        Run uses a declarative setting. Every message is always returned
        during stream.
        """

        program = guidance(program, **kwargs)
        for content in program(llm=self.llm, stream=True):
            msgs = self.tokenizer.tokenize(str(content))
            yield msgs

if __name__ == "__main__":
    cont = """<|im_start|>system
Write a poem<|im_end|>

<|im_start|>assistant
In the stillness of the night,
I hear the whispers of the stars,
As they twinkle in the sky,
And light up the world afar.

The moon shines bright and clear,
Casting shadows on the ground,
And the breeze whispers in my ear,
A melody without a sound.

The world is peaceful and calm,
As I sit and watch the night,
And I feel a sense of warmth,
As the stars shine so bright.

In this moment of tranquility,
I am at peace with the world,
And I know that everything will be alright,
As the night unfolds.

So I close my eyes and breathe,
And let the night embrace me,
For in this moment of serenity,
I am free.<|im_end|>
"""
    lib = GuidanceLibrary()
    for msgs in lib.run_alias("test", topic="masogna"):
        print(msgs[-1].content)
    #llm = guidance.llms.OpenAI("gpt-3.5-turbo")
    #tokenizer = GuidanceTokenizer(llm)
    #msgs = tokenizer.tokenize(cont)