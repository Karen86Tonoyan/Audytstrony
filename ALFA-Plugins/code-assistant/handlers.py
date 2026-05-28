"""Code Assistant Plugin

AI-powered code generation and analysis using Ollama.
"""

from typing import Any, Dict, List, Optional
import asyncio
import re


class CodeAssistantHandler:
    """Handler for code assistant operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.preferred_language = config.get('preferred_language', 'python')
        self.code_style = config.get('code_style', 'pep8')
        self.ollama_client = None
        
    async def initialize(self, agent):
        """Initialize plugin with agent reference"""
        self.ollama_client = agent.ollama
        print("Code Assistant Plugin initialized")
        
    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute plugin action"""
        actions = {
            'generate_code': self._generate_code,
            'analyze_code': self._analyze_code,
            'review_code': self._review_code,
            'refactor_code': self._refactor_code,
            'explain_code': self._explain_code,
        }
        
        handler = actions.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
            
        return await handler(params)
        
    async def _generate_code(self, params: Dict[str, Any]) -> str:
        """Generate code from description"""
        description = params.get('description', '')
        language = params.get('language', self.preferred_language)
        
        prompt = f"""Generate {language} code that {description}.

Requirements:
- Follow {self.code_style} style guide
- Include type hints
- Add docstrings
- Handle errors appropriately
- Write clean, maintainable code

Code:"""
        
        response = await self.ollama_client.generate(
            model="codellama",
            prompt=prompt,
            temperature=0.3
        )
        
        return self._extract_code(response)
        
    async def _analyze_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code quality and complexity"""
        code = params.get('code', '')
        
        prompt = f"""Analyze this code and provide:
1. Complexity score (1-10)
2. Code quality issues
3. Security concerns
4. Performance issues
5. Best practice violations

Code:
{code}

Analysis:"""
        
        response = await self.ollama_client.generate(
            model="llama3.2",
            prompt=prompt,
            temperature=0.5
        )
        
        return {
            'analysis': response,
            'code': code
        }
        
    async def _review_code(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform code review"""
        code = params.get('code', '')
        
        prompt = f"""Review this code and provide specific feedback:

Code:
{code}

Review (list issues line by line):"""
        
        response = await self.ollama_client.generate(
            model="codellama",
            prompt=prompt,
            temperature=0.4
        )
        
        return self._parse_review_comments(response)
        
    async def _refactor_code(self, params: Dict[str, Any]) -> str:
        """Suggest code refactoring"""
        code = params.get('code', '')
        
        prompt = f"""Refactor this code to improve:
- Readability
- Performance
- Maintainability
- Best practices

Original code:
{code}

Refactored code:"""
        
        response = await self.ollama_client.generate(
            model="codellama",
            prompt=prompt,
            temperature=0.3
        )
        
        return self._extract_code(response)
        
    async def _explain_code(self, params: Dict[str, Any]) -> str:
        """Explain what code does"""
        code = params.get('code', '')
        
        prompt = f"""Explain what this code does in simple terms:

{code}

Explanation:"""
        
        response = await self.ollama_client.generate(
            model="llama3.2",
            prompt=prompt,
            temperature=0.6
        )
        
        return response
        
    def _extract_code(self, text: str) -> str:
        """Extract code from response"""
        # Look for code blocks
        code_block = re.search(r'```(?:\w+)?\n(.*?)```', text, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()
        return text.strip()
        
    def _parse_review_comments(self, text: str) -> List[Dict[str, Any]]:
        """Parse review comments into structured format"""
        comments = []
        lines = text.split('\n')
        
        for line in lines:
            if line.strip() and (
                line.startswith('-') or 
                line.startswith('*') or 
                any(word in line.lower() for word in ['issue', 'problem', 'warning', 'error'])
            ):
                comments.append({
                    'type': 'suggestion',
                    'message': line.strip('- *').strip()
                })
                
        return comments
        
    async def shutdown(self):
        """Clean up resources"""
        print("Code Assistant Plugin shutting down")


__version__ = "1.0.0"
__plugin__ = CodeAssistantHandler
