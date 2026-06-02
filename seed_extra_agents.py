import db

new_agents = [
    ("BaseGenerator", "基础生成器", "执行标准的极速生成任务", "#00c853", "zap"),
    ("DraftGenerator", "初稿生成器", "负责生成初始方案初稿", "#2979ff", "file-text"),
    ("SecurityReviewer", "安全与性能审查", "严格审查方案中的安全漏洞与性能瓶颈", "#d50000", "shield"),
    ("ArchitectureReviewer", "架构审查", "从宏观架构层面审视设计合理性", "#ff9100", "layers"),
    ("ReverseThinker", "逆向思维", "打破常规，从反面论证方案的脆弱性", "#ff4081", "refresh-cw"),
    ("CrossBorderThinker", "跨界思维", "引入其他领域的模式寻找创新解法", "#ff4081", "globe"),
    ("ExtremeDeducer", "极限推演", "在极端压力场景下推演方案的稳定性", "#ff4081", "trending-up"),
    ("Synthesizer", "多维融合输出", "综合多种思维结果，融合生成最终答案", "#00e5ff", "check-circle"),
    ("FinalOutput", "定稿输出", "经过多轮专家审查后的最终定稿", "#00c853", "check"),
]

with db.get_connection() as conn:
    with conn.cursor() as cursor:
        for agent in new_agents:
            cursor.execute("""
                INSERT IGNORE INTO agents (agent_id, name, description, color, icon)
                VALUES (%s, %s, %s, %s, %s)
            """, agent)
            
print("Extra agents seeded successfully!")
