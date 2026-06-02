import codecs
import re

with codecs.open('g:/Ai Multi Agent/frontend/src/App.jsx', 'r', 'utf-8', errors='ignore') as f:
    content = f.read()

# Using regex to find the broken welcome message strings that end with a ? instead of ?'
# The broken string is something like "娆㈣繋浣跨敤 Ai Multi Agent 鏅鸿兘鎺у埗鍙般€傜郴缁熷凡灏辩华锛岃杈撳叆鎮ㄧ殑闇€姹傘€? "
# We can just match the prefix "content: '" and any non-quote characters followed by "? " or "? }"
pattern = r"content:\s*'娆㈣繋浣跨敤.*?(\?.*?)(?=[,}])"

def repl(match):
    return "content: '欢迎使用 Ai Multi Agent 智能控制台。系统已就绪，请输入您的需求？'"

new_content = re.sub(pattern, repl, content)

# Also let's do a brute force replace for the exact strings
new_content = new_content.replace("content: '娆㈣繋浣跨敤 Ai Multi Agent 鏅鸿兘鎺у埗鍙般€傜郴缁熷凡灏辩华锛岃杈撳叆鎮ㄧ殑闇€姹傘€? }", "content: '欢迎使用 Ai Multi Agent 智能控制台。系统已就绪，请输入您的需求？' }")
new_content = new_content.replace("content: '娆㈣繋浣跨敤 Ai Multi Agent 鏅鸿兘鎺у埗鍙般€傜郴缁熷凡灏辩华锛岃杈撳叆鎮ㄧ殑闇€姹傘€? ,", "content: '欢迎使用 Ai Multi Agent 智能控制台。系统已就绪，请输入您的需求？' ,")
new_content = new_content.replace("content: '娆㈣繋浣跨敤 Ai Multi Agent 鏅鸿兘鎺у埗鍙般€傜郴缁熷凡灏辩华锛岃杈撳叆鎮ㄧ殑闇€姹傘€? ]", "content: '欢迎使用 Ai Multi Agent 智能控制台。系统已就绪，请输入您的需求？' ]")

with codecs.open('g:/Ai Multi Agent/frontend/src/App.jsx', 'w', 'utf-8') as f:
    f.write(new_content)
    
print("Replaced all welcome messages!")
