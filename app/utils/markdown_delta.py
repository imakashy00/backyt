import re
import json


def markdown_to_quill_delta(markdown):
    """
    Convert markdown to Quill Delta format with proper code block handling.

    Args:
        markdown (str): Input markdown text

    Returns:
        dict: Quill Delta format object
    """
    delta = {"ops": []}
    lines = markdown.split("\n")
    i = 0
    in_code_block = False
    code_block_content = ""
    code_lang = ""

    while i < len(lines):
        line = lines[i]

        # Handle code blocks - check if we're starting a code block
        if not in_code_block and line.strip().startswith("```"):
            in_code_block = True
            code_lang = line.strip()[3:].strip().lower()
            code_block_content = ""
            i += 1
            continue

        # Handle code blocks - check if we're ending a code block
        elif in_code_block and line.strip().startswith("```"):
            in_code_block = False

            # Map common language aliases to standardized names
            language_mapping = {
                "js": "javascript",
                "py": "python",
                "rb": "ruby",
                "cs": "csharp",
                "ts": "typescript",
                "sh": "bash",
                "c++": "cpp",
                "html": "html",
                "css": "css",
                "java": "java",
                "php": "php",
                "go": "go",
                "rust": "rust",
                "swift": "swift",
                "kotlin": "kotlin",
                "sql": "sql",
                "r": "r",
                "scala": "scala",
                "dart": "dart",
                "perl": "perl",
                "powershell": "powershell",
                "c#": "csharp",
                "": "",  # Default for empty language specification
            }

            # Normalize language name if it's in our mapping
            if code_lang in language_mapping:
                code_lang = language_mapping[code_lang]

            # Add the code content
            delta["ops"].append({"insert": code_block_content.rstrip()})

            # Add the code-block attribute with language if specified
            delta["ops"].append(
                {
                    "insert": "\n",
                    "attributes": {"code-block": code_lang if code_lang else True},
                }
            )

            i += 1
            continue

        # If we're inside a code block, add the line to our code content
        elif in_code_block:
            code_block_content += line + "\n"
            i += 1
            continue

        # Skip empty lines but preserve them in delta
        if line.strip() == "":
            delta["ops"].append({"insert": "\n"})
            i += 1
            continue

        # Handle horizontal line
        if re.match(r"^-{3,}$|^_{3,}$|^\*{3,}$", line.strip()):
            # Add divider operation
            delta["ops"].append({"insert": "\n", "attributes": {"divider": True}})
            i += 1
            continue

        # Handle headers
        header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if header_match:
            level = len(header_match.group(1))
            text = header_match.group(2)

            # Add the header text
            process_inline_formatting(text, delta)

            # Add the newline with header attribute
            delta["ops"].append({"insert": "\n", "attributes": {"header": level}})

            i += 1
            continue

        # Handle unordered lists
        list_match = re.match(r"^(\s*)([-*+])\s+(.+)$", line)
        if list_match:
            indent_level = len(list_match.group(1)) // 2
            list_item_text = list_match.group(3)

            # Process the text with inline formatting
            process_inline_formatting(list_item_text, delta)

            # Add newline with list attributes
            attributes = {"list": "bullet"}
            if indent_level > 0:
                attributes["indent"] = str(indent_level)

            delta["ops"].append({"insert": "\n", "attributes": attributes})

            i += 1
            continue

        # Handle ordered lists
        ordered_list_match = re.match(r"^(\s*)(\d+)[.)]\s+(.+)$", line)
        if ordered_list_match:
            indent_level = len(ordered_list_match.group(1)) // 2
            list_item_text = ordered_list_match.group(3)

            # Process the text with inline formatting
            process_inline_formatting(list_item_text, delta)

            # Add newline with list attributes
            attributes = {"list": "ordered"}
            if indent_level > 0:
                attributes["indent"] = str(indent_level)

            delta["ops"].append({"insert": "\n", "attributes": attributes})

            i += 1
            continue

        # Handle blockquotes
        blockquote_match = re.match(r"^>\s+(.+)$", line)
        if blockquote_match:
            blockquote_text = blockquote_match.group(1)

            # Process the text with inline formatting
            process_inline_formatting(blockquote_text, delta)

            # Add newline with blockquote attribute
            delta["ops"].append({"insert": "\n", "attributes": {"blockquote": True}})

            i += 1
            continue

        # Handle normal paragraph text
        process_inline_formatting(line, delta)

        # Add a paragraph break
        delta["ops"].append({"insert": "\n"})

        i += 1

    return json.dumps(delta,indent=1)


def process_inline_formatting(text, delta):
    """
    Process inline formatting for a text line and add to delta ops

    Args:
        text (str): Line of text to process
        delta (dict): Delta object to append operations to
    """
    i = 0
    while i < len(text):
        # Handle bold formatting with ** or __
        bold_match = re.match(r"\*\*(.+?)\*\*|__(.+?)__", text[i:])
        if bold_match:
            bold_text = bold_match.group(1) or bold_match.group(2)
            match_len = len(bold_match.group(0))

            # Check for nested formatting in the bold text
            if any(c in bold_text for c in ["*", "_", "`"]):
                nested_delta = {"ops": []}
                process_inline_formatting(bold_text, nested_delta)

                # Apply bold to all nested delta ops
                for op in nested_delta["ops"]:
                    if "attributes" not in op:
                        op["attributes"] = {}
                    op["attributes"]["bold"] = True
                    delta["ops"].append(op)
            else:
                # Simple bold text
                delta["ops"].append({"insert": bold_text, "attributes": {"bold": True}})

            i += match_len
            continue

        # Handle italic formatting with * or _
        italic_match = re.match(
            r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)",
            text[i:],
        )
        if italic_match:
            italic_text = italic_match.group(1) or italic_match.group(2)
            match_len = len(italic_match.group(0))

            delta["ops"].append({"insert": italic_text, "attributes": {"italic": True}})

            i += match_len
            continue

        # Handle inline code formatting with `
        code_match = re.match(r"`(.+?)`", text[i:])
        if code_match:
            code_text = code_match.group(1)
            match_len = len(code_match.group(0))

            delta["ops"].append({"insert": code_text, "attributes": {"code": True}})

            i += match_len
            continue

        # Find the next special character
        next_special = len(text)
        for char in ["**", "__", "*", "_", "`"]:
            pos = text.find(char, i)
            if pos != -1 and pos < next_special:
                next_special = pos

        # Add plain text up to the next special character
        if next_special > i:
            delta["ops"].append({"insert": text[i:next_special]})
            i = next_special
        else:
            # No more special characters, add the rest of the text
            delta["ops"].append({"insert": text[i:]})
            break


def to_json(delta):
    """
    Convert delta object to JSON string with indentation

    Args:
        delta (dict): Delta object

    Returns:
        str: JSON string representation
    """
    return json.dumps(delta, indent=2)
