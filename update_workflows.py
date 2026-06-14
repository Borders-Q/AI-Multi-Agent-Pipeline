import db
import json

templates = [
    {
        "template_id": "tmpl_standard_fast",
        "title": "⚡ 标准极速流",
        "description": "极速直接回答，跳过反思和校验，适合简单问题。",
        "stage": "Published",
        "tags": "Official,Fast",
        "author": "天韬（SkyT） System",
        "workflow_json": json.dumps({
            "nodes": [
                {
                    "id": "node_input",
                    "type": "input",
                    "position": {"x": 100, "y": 100},
                    "data": {"label": "用户输入"}
                },
                {
                    "id": "node_core",
                    "type": "customAgent",
                    "position": {"x": 100, "y": 250},
                    "data": {"label": "基础生成器", "agentId": "BaseGenerator", "color": "#00c853", "icon": "zap"}
                }
            ],
            "edges": [
                {
                    "id": "e_input_core",
                    "source": "node_input",
                    "target": "node_core",
                    "animated": True
                }
            ]
        }, ensure_ascii=False)
    },
    {
        "template_id": "tmpl_expert_review",
        "title": "🧐 专家审查流",
        "description": "最严苛的业界顶尖视角审查自身代码或方案，确保性能和扩展性没有死角，多轮深度自反思循环。",
        "stage": "Published",
        "tags": "Official,Expert,Rigorous",
        "author": "天韬（SkyT） System",
        "workflow_json": json.dumps({
            "nodes": [
                {
                    "id": "node_input",
                    "type": "input",
                    "position": {"x": 300, "y": 50},
                    "data": {"label": "用户输入"}
                },
                {
                    "id": "node_draft",
                    "type": "customAgent",
                    "position": {"x": 300, "y": 200},
                    "data": {"label": "初稿生成器", "agentId": "DraftGenerator", "color": "#2979ff", "icon": "file-text"}
                },
                {
                    "id": "node_review_1",
                    "type": "customAgent",
                    "position": {"x": 100, "y": 400},
                    "data": {"label": "安全与性能审查", "agentId": "SecurityReviewer", "color": "#d50000", "icon": "shield"}
                },
                {
                    "id": "node_review_2",
                    "type": "customAgent",
                    "position": {"x": 500, "y": 400},
                    "data": {"label": "架构审查", "agentId": "ArchitectureReviewer", "color": "#ff9100", "icon": "layers"}
                },
                {
                    "id": "node_final",
                    "type": "customAgent",
                    "position": {"x": 300, "y": 600},
                    "data": {"label": "定稿输出", "agentId": "FinalOutput", "color": "#00c853", "icon": "check"}
                }
            ],
            "edges": [
                {"id": "e_input_draft", "source": "node_input", "target": "node_draft", "animated": True},
                {"id": "e_draft_r1", "source": "node_draft", "target": "node_review_1", "animated": True},
                {"id": "e_draft_r2", "source": "node_draft", "target": "node_review_2", "animated": True},
                {"id": "e_r1_final", "source": "node_review_1", "target": "node_final", "animated": True},
                {"id": "e_r2_final", "source": "node_review_2", "target": "node_final", "animated": True}
            ]
        }, ensure_ascii=False)
    },
    {
        "template_id": "tmpl_creative_brainstorm",
        "title": "💡 发散风暴流",
        "description": "突破常规逻辑束缚，使用多角度思维和图表输出，给出更具创意的替代方案。",
        "stage": "Published",
        "tags": "Official,Creative",
        "author": "天韬（SkyT） System",
        "workflow_json": json.dumps({
            "nodes": [
                {
                    "id": "node_input",
                    "type": "input",
                    "position": {"x": 250, "y": 50},
                    "data": {"label": "创意原点"}
                },
                {
                    "id": "node_diverge_1",
                    "type": "customAgent",
                    "position": {"x": -50, "y": 250},
                    "data": {"label": "逆向思维", "agentId": "ReverseThinker", "color": "#ff4081", "icon": "refresh-cw"}
                },
                {
                    "id": "node_diverge_2",
                    "type": "customAgent",
                    "position": {"x": 250, "y": 250},
                    "data": {"label": "跨界思维", "agentId": "CrossBorderThinker", "color": "#ff4081", "icon": "globe"}
                },
                {
                    "id": "node_diverge_3",
                    "type": "customAgent",
                    "position": {"x": 550, "y": 250},
                    "data": {"label": "极限推演", "agentId": "ExtremeDeducer", "color": "#ff4081", "icon": "trending-up"}
                },
                {
                    "id": "node_converge",
                    "type": "customAgent",
                    "position": {"x": 250, "y": 450},
                    "data": {"label": "多维融合输出", "agentId": "Synthesizer", "color": "#00e5ff", "icon": "check-circle"}
                }
            ],
            "edges": [
                {"id": "e_in_d1", "source": "node_input", "target": "node_diverge_1", "animated": True},
                {"id": "e_in_d2", "source": "node_input", "target": "node_diverge_2", "animated": True},
                {"id": "e_in_d3", "source": "node_input", "target": "node_diverge_3", "animated": True},
                {"id": "e_d1_out", "source": "node_diverge_1", "target": "node_converge", "animated": True},
                {"id": "e_d2_out", "source": "node_diverge_2", "target": "node_converge", "animated": True},
                {"id": "e_d3_out", "source": "node_diverge_3", "target": "node_converge", "animated": True}
            ]
        }, ensure_ascii=False)
    }
]

with db.get_connection() as conn:
    with conn.cursor() as cursor:
        for t in templates:
            cursor.execute("""
                UPDATE workflow_templates 
                SET workflow_json = %s 
                WHERE template_id = %s
            """, (t["workflow_json"], t["template_id"]))
            
print("Templates updated successfully!")
