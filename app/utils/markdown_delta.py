import re
import json


def markdown_to_quill_delta(markdown):
    """
    Convert markdown to Quill Delta format.

    Args:
        markdown (str): Input markdown text

    Returns:
        dict: Quill Delta format object
    """
    delta = {"ops": []}
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines but preserve them in delta
        if line.strip() == "":
            delta["ops"].append({"insert": "\n"})
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

        # Handle code blocks
        if line.startswith("```"):
            code_lang = line[3:].strip()
            code_content = ""
            i += 1

            while i < len(lines) and not lines[i].startswith("```"):
                code_content += lines[i] + "\n"
                i += 1

            # Skip the closing ```
            i += 1

            # Add the code content
            delta["ops"].append({"insert": code_content})

            # Add the code-block attribute
            delta["ops"].append(
                {
                    "insert": "\n",
                    "attributes": {"code-block": True if not code_lang else code_lang},
                }
            )

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

        # Handle code formatting with `
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


# # Example usage
# if __name__ == "__main__":
#     markdown_example = """# 🎥 Extracting Audio from Video with Flixier
# ## 🎉 Introduction
# - Extract audio from almost any video (online or offline) in just a few clicks!
# ## 📜 Important Note
# - When using audio from another's video:
#   - Obtain consent from the owner 📜
#   - Alternatively, use it under fair use 🤝
# ## 📽️ Steps to Extract Audio on PC
# 1. **Upload File**
#    - Upload video file from your device. 💻
   
# 2. **Detach Audio**
#    - Right-click on video and select **Detach Audio**. 🎶
   
# 3. **Delete Video File**
#    - Select video file and delete it. 🗑️
# 4. **Edit Audio**
#    - Adjust playback speed, create loops, or apply equalizer settings. 🎚️
# 5. **Export Audio**
#    - Click **export button**, select audio format, then click **Export Video** to download audio in under three minutes! ⏳
# ## 🌐 Importing Audio from Online Platforms
# 1. **Example with Facebook**
#    - Copy video link from Facebook, go to Flixier, select **import**, and paste the link.
# 2. **Detach and Export Audio**
#    - Detach audio file and export it. 📤
# 3. **Combining Multiple Audio Files**
#    - Import from multiple platforms (YouTube, TikTok) following the same process. 📹📱
# 4. **Position Audio on Timeline**
#    - Arrange audio on the timeline as desired. 📊 
# ## 🔧 Enhance Audio Quality
# 1. Select **quick tools**.
# 2. Click **enhance audio**.
# 3. Apply necessary settings and click **Enhance Audio**!
# ## 👍 Conclusion
# - Extract audio from videos easily! 
# - If helpful:
#   - Like this video! ☑️
#   - Subscribe for more! 🔔
# ## 👋 Until Next Time
# - Happy editing! ✂️"""

    # delta = markdown_to_quill_delta(markdown_example)
    # print(json.dumps(delta, indent=2))
