
import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace all non-ascii characters in print statements
# This is a bit complex for a regex, so let's just find common emojis
content = content.replace("❌", "ERROR")
content = content.replace("✅", "DONE")
content = content.replace("⚡", "FLASH")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Emojis removed.")
