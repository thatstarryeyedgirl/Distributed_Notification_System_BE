import re

def substitute_template(template_str: str, variables: dict) -> str:
    if not variables:
        variables = {}
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables.get(m.group(1), "")), template_str)

