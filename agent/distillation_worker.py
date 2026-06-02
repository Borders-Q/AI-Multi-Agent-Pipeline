import asyncio
import json
import db
from agent.llm_client import llm

async def distillation_loop():
    """
    Background worker that runs when GPU is idle to perform memory distillation.
    """
    print("> [GPU_Subsystem] 后台知识蒸馏进程已启动 (Idle-priority).")
    while True:
        await asyncio.sleep(10)  # Check every 10 seconds
        
        # Check if the system is currently busy processing user requests
        if getattr(llm, 'active_tasks', 0) > 0:
            continue
            
        try:
            # Check for runs that have not been distilled but have large event logs
            runs = db.get_run_records(limit=20)
            
            for run in runs:
                if getattr(llm, 'active_tasks', 0) > 0:
                    break  # Stop if a user request comes in
                    
                run_id = run['run_id']
                requirement = run['requirement'] or "Unknown"
                
                # Check if it has large detail_json and if it has already been distilled
                with db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        # Has it been distilled?
                        cursor.execute("SELECT id FROM distilled_knowledge WHERE run_id=%s", (run_id,))
                        if cursor.fetchone():
                            continue # Already distilled
                            
                        # Are there large JSONs to distill?
                        cursor.execute("SELECT SUM(LENGTH(detail_json)) as total FROM run_events WHERE run_id=%s", (run_id,))
                        row = cursor.fetchone()
                        total_bytes = int(row['total'] or 0) if row else 0
                        
                if total_bytes > 5000:  # Only distill if there's enough data (e.g. > 5KB)
                    print(f"\n> [GPU_Subsystem] 空闲时段：发现待提炼的执行记录 [{run_id}]...")
                    
                    events = db.get_run_events(run_id)
                    events_text = ""
                    for e in events:
                        events_text += f"[{e['event_type']}] {e['message']}\n"
                        if e['detail_json']:
                            # Truncate very long details to save context window
                            detail_str = e['detail_json']
                            events_text += f"{detail_str[:300]}...\n" if len(detail_str) > 300 else f"{detail_str}\n"
                            
                    prompt = (
                        "请将以下系统的执行流转日志进行高密度压缩提炼。提取出核心发现、使用的工具、遇到的错误及最终方案，忽略所有不重要的流水账。\n\n"
                        f"任务目标: {requirement}\n\n执行流转记录：\n{events_text}"
                    )
                    
                    try:
                        # Call LLM explicitly in background mode so we don't block
                        response = await llm.chat_completion([{"role": "user", "content": prompt}], is_background=True)
                        summary = response.choices[0].message.content
                        
                        space_saved = db.distill_run_data(run_id, distilled_summary=summary)
                        
                        # Automatically inject the distilled knowledge into long-term memory
                        from agent.memory import MemorySystem
                        mem_sys = MemorySystem(workspace_dir=".")
                        mem_sys.append_long_term_memory(title=requirement[:50], content=summary)
                        
                        print(f"> [GPU_Subsystem] 提炼完成！[{run_id}] 释放了 {round(space_saved/1024, 2)}KB 空间并已写入长期记忆库。")
                        
                        # Wait a bit before checking the next one
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        print(f"> [GPU_Subsystem] 提炼失败: {e}")
                        
        except Exception as e:
            print(f"> [GPU_Subsystem] 后台蒸馏进程出错: {e}")
