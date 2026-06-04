import os
from jinja2 import Environment, FileSystemLoader

class ContextBuilder:
    def __init__(self, workspace_dir="."):
        self.templates_dir = os.path.join(workspace_dir, "templates")
        self.env = Environment(loader=FileSystemLoader(self.templates_dir))
        
    def build_system_prompt(self, agent_identity="agent/identity.md", additional_context=None):
        """
        Builds the system prompt by combining SOUL.md, USER.md, identity.md, 
        skills_section.md and Long-Term Memory.
        """
        soul = self._render_template("SOUL.md", optional=True)
        user_pref = self._render_template("USER.md", optional=True)
        identity = self._render_template(agent_identity, optional=True, **(additional_context or {}))
        
        # Load skills if present
        skills = self._render_template("agent/skills_section.md", optional=True)
        
        prompt_parts = []
        if soul: prompt_parts.append(f"## SOUL\n{soul}")
        if user_pref: prompt_parts.append(f"## USER PREFERENCES\n{user_pref}")
        if identity: prompt_parts.append(f"## IDENTITY\n{identity}")
        if skills: prompt_parts.append(f"## AVAILABLE SKILLS\n{skills}")
        
        return "\n\n".join(prompt_parts)

    def get_subagent_prompt(self, subagent_name: str):
        """Loads a subagent template from templates/subagents/"""
        # Resolve aliases
        aliases = {
            "general": "neiguan_yingzao",
            "researcher": "dongchang_tanshi"
        }
        actual_name = aliases.get(subagent_name, subagent_name)
        return self._render_template(f"subagents/{actual_name}.md")

    def _render_template(self, template_name, optional=False, **kwargs):
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            if optional:
                return ""
            raise e
