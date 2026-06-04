import codecs

replacements = {
    806: '                ▶              </button>',
    1165: '                  <Sparkles size={24} color="var(--sys-color-primary)" /> 导入自定义技能              </h2>',
    1167: '                  在此粘贴您自己编写的 Python 工具脚本。必须包含执行函数和符合 OpenAI Tool Call 规范的 schema 字典。系统将动态编译并注入，无需重启。              </p>',
    1195: '                  🚀 编译并加载                </button>',
    1281: '                  系统将根据 API Key 的格式自动识别所属平台 (支持 OpenAI, Gemini, DeepSeek, Zhipu 等)。                </p>'
}

with codecs.open('g:/Ai Multi Agent/frontend/src/App.jsx', 'r', 'utf-8', errors='ignore') as f:
    lines = f.readlines()

for num, text in replacements.items():
    lines[num-1] = text + '\n'

with codecs.open('g:/Ai Multi Agent/frontend/src/App.jsx', 'w', 'utf-8') as f:
    f.writelines(lines)
    
print('Restored missing JSX closing tags!')
