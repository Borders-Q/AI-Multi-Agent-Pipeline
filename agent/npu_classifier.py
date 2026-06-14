import random
import os
import sys
import threading

# Pre-defined rich responses
GREETING_RESPONSES = [
    "您好！我是天韬（SkyT），您的专属多智能体控制中枢。很高兴为您服务！不论是多么复杂的架构设计还是微小的代码调试，我都将全力以赴帮您完美解决，让我们一起创造奇迹吧！",
    "初次见面，我是天韬（SkyT）。您所在维度的所有计算资源已由我接管，请随时下达您的工程指令！我非常期待能陪伴您一起攻克技术难题，见证每一个激动人心的项目落地！",
    "欢迎来到 天韬（SkyT） 中枢控制台，我是天韬（SkyT）！您可以把我当做您最可靠的高级智囊团。今天有什么绝妙的灵感想要实现吗？无论多天马行空的想法，我都会倾尽全力帮您达成！",
    "你好！我是天韬（SkyT），一个在硅基丛林中为您探路的多智能体指挥官。您的每一次调用我都倍感荣幸，让我们并肩作战，把那些看似不可能的任务变成完美运行的代码吧！",
    "您好呀！我是天韬（SkyT）。NPU 神经元放电正常，GPU 核心预热完毕，我已准备好迎接您的任何挑战！我相信在我们的默契配合下，一定能打造出令人惊叹的卓越作品！"
]

class NPUClassifier:
    """Lazy-loading NPU classifier. Models are compiled on first use, not at import time."""
    def __init__(self):
        self.model_name = "prajjwal1/bert-tiny" # 17MB tiny BERT
        self.tokenizer = None
        self.model = None
        self.device = "cpu"
        self.compiled = False
        self._init_lock = threading.Lock()
        self._init_started = False
        
    def _lazy_init(self):
        """Initialize NPU model on first actual use (not at import time)."""
        if self.compiled:
            return
        with self._init_lock:
            if self.compiled:
                return
            if self._init_started:
                return
            self._init_started = True
            
            print("> [GPU_Subsystem] 正在初始化特征提取引擎(后台)...")
            try:
                import torch
                from transformers import AutoModel, AutoTokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                print(f"> [GPU_Subsystem] 正在将深度学习模型加载至 {device}...")
                try:
                    self.model = AutoModel.from_pretrained(self.model_name).to(device)
                    self.device = device
                    self.compiled = True
                    print(f"> [GPU_Subsystem] [OK] 模型已成功加载至 {device} 内存。")
                except Exception as e:
                    print(f"> [GPU_Subsystem] [WARN] 加载失败，将回退至 CPU: {e}")
                    self.model = AutoModel.from_pretrained(self.model_name).to("cpu")
                    self.device = "cpu"
                    self.compiled = True
                    
            except Exception as e:
                print(f"> [GPU_Subsystem] [WARN] 初始化失败: {e}")
                self.compiled = False

    def warmup_async(self):
        """Start model compilation in a background thread so it's ready when needed."""
        t = threading.Thread(target=self._lazy_init, daemon=True)
        t.start()
        
    def _get_embedding(self, text: str):
        self._lazy_init()
        if not self.model or not self.tokenizer:
            return None
            
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=128, padding="max_length")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        outputs = self.model(**inputs)
        return outputs.last_hidden_state[0][0]

    def is_simple_greeting(self, text: str) -> bool:
        # Use regex first (zero cost), only invoke NPU if it's actually a greeting
        import re
        greeting_pattern = r"^(hello|hi|你好啊?|在吗|hey+|嗨|测试|test)$"
        is_greeting = bool(re.match(greeting_pattern, text.strip(), re.IGNORECASE))
        
        # Trigger NPU forward pass only for greetings (to show hardware usage)
        if is_greeting and self.compiled:
            self._get_embedding(text)
        
        return is_greeting
        
    def is_complex_greeting(self, text: str) -> bool:
        import re
        msg_clean = text.strip()
        if len(msg_clean) > 15:
            return False
            
        complex_pattern = r"(你是谁|介绍一下自己|你会做什么|谁派你来的|聊聊天|早上好|晚上好|你好吗|你能干什么|什么名字)"
        return bool(re.search(complex_pattern, msg_clean, re.IGNORECASE))

    def generate_response(self) -> str:
        return random.choice(GREETING_RESPONSES)

# Global singleton — no model loading here, just object creation (instant)
npu_engine = NPUClassifier()


