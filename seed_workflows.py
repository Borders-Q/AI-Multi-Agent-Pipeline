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
                    "data": {"label": "User Input", "name": "用户输入"}
                },
                {
                    "id": "node_core",
                    "type": "default",
                    "position": {"x": 100, "y": 250},
                    "data": {"label": "LLM Core", "name": "基础生成器"},
                    "style": {"border": "2px solid #00c853"}
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
                    "position": {"x": 100, "y": 100},
                    "data": {"label": "User Input", "name": "用户输入"}
                },
                {
                    "id": "node_draft",
                    "type": "default",
                    "position": {"x": 100, "y": 250},
                    "data": {"label": "Draft Generator", "name": "初稿生成器"},
                    "style": {"border": "2px solid #2979ff"}
                },
                {
                    "id": "node_review_1",
                    "type": "default",
                    "position": {"x": 300, "y": 250},
                    "data": {"label": "Security Review", "name": "安全与性能审查"},
                    "style": {"border": "2px solid #d50000"}
                },
                {
                    "id": "node_review_2",
                    "type": "default",
                    "position": {"x": 500, "y": 250},
                    "data": {"label": "Architecture Review", "name": "架构审查"},
                    "style": {"border": "2px solid #ff9100"}
                },
                {
                    "id": "node_final",
                    "type": "output",
                    "position": {"x": 300, "y": 400},
                    "data": {"label": "Final Output", "name": "定稿输出"},
                    "style": {"border": "2px solid #00c853"}
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
                    "position": {"x": 250, "y": 100},
                    "data": {"label": "User Input", "name": "创意原点"}
                },
                {
                    "id": "node_diverge_1",
                    "type": "default",
                    "position": {"x": 50, "y": 250},
                    "data": {"label": "Perspective A", "name": "逆向思维"},
                    "style": {"border": "2px solid #ff4081"}
                },
                {
                    "id": "node_diverge_2",
                    "type": "default",
                    "position": {"x": 250, "y": 250},
                    "data": {"label": "Perspective B", "name": "跨界思维"},
                    "style": {"border": "2px solid #ff4081"}
                },
                {
                    "id": "node_diverge_3",
                    "type": "default",
                    "position": {"x": 450, "y": 250},
                    "data": {"label": "Perspective C", "name": "极限推演"},
                    "style": {"border": "2px solid #ff4081"}
                },
                {
                    "id": "node_converge",
                    "type": "output",
                    "position": {"x": 250, "y": 400},
                    "data": {"label": "Synthesis", "name": "多维融合输出"},
                    "style": {"border": "2px solid #00e5ff"}
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

for t in templates:
    db.save_workflow_template(
        t["template_id"],
        t["title"],
        t["description"],
        t["stage"],
        t["tags"],
        t["author"],
        t["workflow_json"]
    )
    print(f"Saved template: {t['title']}")
