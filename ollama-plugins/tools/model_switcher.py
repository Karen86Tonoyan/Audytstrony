"""Model Switcher - Intelligent model selection based on task type"""

from typing import Dict, List, Optional
import json
from pathlib import Path


class ModelSwitcher:
    """Automatically selects the best Ollama model for a given task"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize model switcher
        
        Args:
            config_dir: Directory containing model configurations
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "models"
        
        self.config_dir = Path(config_dir)
        self.model_configs = self._load_model_configs()
        
        # Task to use case mapping
        self.task_mapping = {
            'code_generation': 'code_generation',
            'code_review': 'code_review',
            'refactoring': 'refactoring',
            'debugging': 'debugging',
            'conversation': 'conversation',
            'general': 'general',
            'analysis': 'analysis',
            'explanation': 'explanation',
        }
        
    def _load_model_configs(self) -> Dict[str, dict]:
        """Load all model configurations"""
        configs = {}
        
        if not self.config_dir.exists():
            return configs
            
        for model_dir in self.config_dir.iterdir():
            if model_dir.is_dir():
                config_file = model_dir / "config.json"
                if config_file.exists():
                    with open(config_file) as f:
                        configs[model_dir.name] = json.load(f)
                        
        return configs
        
    def select_for_task(self, task: str) -> str:
        """Select the best model for a given task
        
        Args:
            task: Task type (e.g., 'code_generation', 'conversation')
            
        Returns:
            Model name to use
        """
        use_case = self.task_mapping.get(task, 'general')
        
        # Find models that support this use case
        candidates = []
        for model_name, config in self.model_configs.items():
            if use_case in config.get('use_cases', []):
                candidates.append((
                    model_name,
                    config.get('priority', 999)
                ))
                
        if not candidates:
            # Fallback to default model
            return "llama3.2"
            
        # Sort by priority (lower is better)
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
        
    def get_model_config(self, model_name: str) -> Optional[dict]:
        """Get configuration for a specific model
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model configuration or None if not found
        """
        return self.model_configs.get(model_name)
        
    def list_models(self) -> List[str]:
        """Get list of available models"""
        return list(self.model_configs.keys())
        
    def list_use_cases(self) -> List[str]:
        """Get list of all supported use cases"""
        use_cases = set()
        for config in self.model_configs.values():
            use_cases.update(config.get('use_cases', []))
        return sorted(list(use_cases))


if __name__ == "__main__":
    # Example usage
    switcher = ModelSwitcher()
    
    print("Available models:")
    for model in switcher.list_models():
        print(f"  - {model}")
        
    print("\nSupported use cases:")
    for use_case in switcher.list_use_cases():
        print(f"  - {use_case}")
        
    print("\nModel selection examples:")
    tasks = ['code_generation', 'conversation', 'analysis']
    for task in tasks:
        model = switcher.select_for_task(task)
        print(f"  {task} -> {model}")
