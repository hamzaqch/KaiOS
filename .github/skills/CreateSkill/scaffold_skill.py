#!/usr/bin/env python3
"""Write a compliant SKILL.md skeleton for a new KaiOS skill.

Produces ``<root>/<PascalName>/SKILL.md`` with valid frontmatter and the
ideal-state section shape already in place, so the author fills in content
rather than remembering the contract. Refuses to overwrite unless --force.

Exit codes: 0 written, 1 refused (target exists, invalid name), 2 usage.
"""

import argparse
import json
import os
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONT_NAME = re.compile(r"^name:\s*[\"']?(?P<name>[^\"'\s]+)", re.MULTILINE)
MAX_NAME = 64
MAX_DESCRIPTION = 1024

TEMPLATE = """---
name: {name}
description: "{description}"{hint}
---

# {title} — {tagline}

## What this produces

<!-- One paragraph: the artifact or state this skill leaves behind. Not a list of
     steps, not a restatement of the title. What is different afterwards. -->

## Done looks like

<!-- Testable outcomes. Each line should be something a reader could check
     without asking the author what was meant. -->

- 
- 
- 

## USE WHEN

<!-- The situation, in prose. The description frontmatter carries the trigger
     words; this section carries the judgment about when the skill earns its
     invocation. -->

## NOT FOR

<!-- The neighbouring skills and the cases that belong to them, so routing is
     unambiguous. -->

## {body_heading}

<!-- The substance. Prefer tables and prose over numbered steps. Numbered steps
     are capped at eight unless the run is a tool contract or a safety gate and
     carries a keep tag. -->

## Output format contract

<!-- What the caller gets back and in what shape. Delete this section only if
     the skill produces a file rather than a response. -->

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python .github/skills/{pascal}/<tool>.py --help` | every bundled tool supports --help and exits 0 |

<!-- Delete this section if the skill bundles no tools. Every bundled tool:
     standard library only, --help exits 0, a --json output mode, argument
     arrays passed to subprocess.run, never a shell string, explicit utf-8. -->

## Constraints and gotchas

<!-- The things that bite. One line each, concrete, ideally traced to the moment
     the lesson was learned. -->

- 
"""


def to_pascal(name):
    return "".join(part.capitalize() for part in name.split("-") if part)


def existing_names(root):
    """Map declared skill name to the directory declaring it, under a skills root."""
    found = {}
    if not os.path.isdir(root):
        return found
    for entry in sorted(os.listdir(root)):
        candidate = os.path.join(root, entry, "SKILL.md")
        if not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as handle:
                head = handle.read(4096)
        except OSError:
            continue
        match = FRONT_NAME.search(head)
        if match:
            found[match.group("name")] = os.path.join(root, entry)
    return found


def build_parser():
    parser = argparse.ArgumentParser(
        prog="scaffold_skill.py",
        description="Write a compliant SKILL.md skeleton for a new skill.",
    )
    parser.add_argument("--name", required=True, help="skill name, lowercase-hyphen")
    parser.add_argument(
        "--description",
        required=True,
        help="frontmatter description; must contain USE WHEN and NOT FOR",
    )
    parser.add_argument("--argument-hint", default="", help="optional argument hint")
    parser.add_argument("--tagline", default="what it is in six words", help="title suffix")
    parser.add_argument(
        "--body-heading",
        default="How it works",
        help="heading for the substance section",
    )
    parser.add_argument(
        "--root",
        default=os.path.join(".github", "skills"),
        help="skills root directory (default .github/skills)",
    )
    parser.add_argument(
        "--dir-name",
        default="",
        help="override the PascalCase directory name",
    )
    parser.add_argument("--force", action="store_true", help="overwrite an existing SKILL.md")
    parser.add_argument("--json", action="store_true", help="emit the result as JSON")
    return parser


def report(args, payload, human):
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(human)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    problems = []
    if not NAME_RE.match(args.name):
        problems.append("name must be lowercase with hyphens only")
    if len(args.name) > MAX_NAME:
        problems.append("name exceeds %d chars" % MAX_NAME)
    if len(args.description) > MAX_DESCRIPTION:
        problems.append("description exceeds %d chars" % MAX_DESCRIPTION)
    if "USE WHEN" not in args.description:
        problems.append("description must contain the literal USE WHEN")
    if "NOT FOR" not in args.description:
        problems.append("description must contain the literal NOT FOR")
    if '"' in args.description:
        problems.append("description must not contain a double quote")
    if problems:
        report(args, {"written": None, "problems": problems}, "refused:\n  " + "\n  ".join(problems))
        return 1

    taken = existing_names(args.root)
    pascal = args.dir_name or to_pascal(args.name)
    directory = os.path.join(args.root, pascal)
    owner = taken.get(args.name)
    if owner and os.path.normpath(owner) != os.path.normpath(directory):
        message = (
            "refused: name %r is already declared by %s. Skill names must be globally "
            "unique or routing becomes a coin flip; extend that skill or pick another name."
            % (args.name, owner)
        )
        report(args, {"written": None, "problems": [message]}, message)
        return 1
    target = os.path.join(directory, "SKILL.md")
    if os.path.exists(target) and not args.force:
        message = "refused: %s already exists (use --force)" % target
        report(args, {"written": None, "problems": [message]}, message)
        return 1

    hint = ""
    if args.argument_hint:
        hint = '\nargument-hint: "%s"' % args.argument_hint.replace('"', "'")

    content = TEMPLATE.format(
        name=args.name,
        description=args.description,
        hint=hint,
        title=pascal,
        tagline=args.tagline,
        pascal=pascal,
        body_heading=args.body_heading,
    )
    os.makedirs(directory, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)

    payload = {"written": target, "name": args.name, "directory": directory}
    report(
        args,
        payload,
        "wrote %s\nnext: fill the sections, then\n  python "
        ".github/skills/CreateSkill/validate_skill.py %s" % (target, directory),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
