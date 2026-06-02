import codecs
import re

with codecs.open('g:/Ai Multi Agent/frontend/src/App.jsx', 'r', 'utf-8', errors='ignore') as f:
    content = f.read()

def recover_mojibake(match):
    text = match.group(0)
    try:
        # The text was UTF-8 bytes that were interpreted as GBK
        # So we encode to GBK to get the original UTF-8 bytes back
        original_bytes = text.encode('gbk')
        # Then decode the UTF-8 bytes to get the real characters
        recovered_text = original_bytes.decode('utf-8')
        
        # Basic heuristic: if it decodes to UTF-8 without errors, and it contains
        # Chinese characters, it's very likely a successful recovery.
        # But wait, there are also things like ? that we already replaced,
        # but those are just ASCII so they won't be matched by the regex below (which only matches non-ASCII).
        return recovered_text
    except Exception:
        # If it fails to encode to GBK or decode to UTF-8, it's not our specific mojibake
        return text

# Match sequences of non-ASCII characters. 
# We include some common symbols that might have been mapped in GBK.
# Actually, anything that is \x80 or higher
pattern = re.compile(r'[^\x00-\x7F]+')

new_content = pattern.sub(recover_mojibake, content)

with codecs.open('g:/Ai Multi Agent/frontend/src/App_recovered.jsx', 'w', 'utf-8') as f:
    f.write(new_content)

print("Recovery attempted and saved to App_recovered.jsx")
