from typing import List, Dict, Union
import json

class Message:


    def __init__(self, role: str, content: Union[str, List[str]]):
        self.role = role
        if isinstance(content, str):
            content = [content]
        self.content = content

    def gen_content(self) -> List[str]:
        text_content_string = ""
        final_content = []
        for c in self.content:
            if self.is_image_content(c):
                final_content.append({"type": "image_url", "image_url": {"url": c}})
            else:
                text_content_string += f"\n\n {c}"
        final_content.append({"type": "text", "text": text_content_string})
        return final_content
    
    def is_image_content(self, content_entry):
        return "data:image/" in content_entry[:15]

    def to_markdown(self):
        # check content for multipart
        mkdn = ""
        # is multi part, iterate through
        for entry in self.content:
            if "data:image" in entry[:10]:
                mkdn += f'\n\n ![]({entry})'
            else:
                mkdn += f'\n\n {entry}'
        return mkdn

    def to_string(self):        
        return {'role': self.role, 'content': self.gen_content()}
    
    # json will either container a single message or an array including a message and an image
    def to_msg(message_as_json:str):
        if isinstance(message_as_json, dict):
            maybe_msg = message_as_json
            # check the basic properties are accounted for
            if "role" in maybe_msg and "content" in maybe_msg:
                role = maybe_msg["role"]
                content = []
                if isinstance(maybe_msg["content"], str):
                    content.append(maybe_msg["content"])
                if isinstance(maybe_msg["content"], list):
                    for entry in maybe_msg["content"]:
                        if entry["type"] == "text":
                            content.append(entry["text"])
                        if entry["type"] == "image_url":
                            content.append(entry["image_url"]["url"])
            return Message(role, content)
        else:
            print(f"Failed to load message from json object: {message_as_json}")
            return