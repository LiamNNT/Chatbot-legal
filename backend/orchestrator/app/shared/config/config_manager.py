import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelConfig:
    name: str
    temperature: float
    max_tokens: Optional[int]
    timeout: Optional[int]


@dataclass
class AgentConfiguration:
    agent_type: str
    model_config: str
    system_prompt: str
    parameters: Dict[str, Any]


@dataclass
class SystemConfig:
    default_timeout: int
    default_max_retries: int
    enable_verification: bool
    enable_planning: bool


class ConfigurationManager:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Check environment variable first
            import os
            env_config = os.getenv("AGENT_CONFIG_FILE", "agents_config_optimized.yaml")
            
            # Default to config directory relative to project root
            # app/core/config_manager.py -> ../../config/agents_config_optimized.yaml
            current_dir = Path(__file__).parent
            config_path = current_dir.parent.parent / "config" / env_config
        
        self.config_path = Path(config_path)
        self._config_data: Optional[Dict[str, Any]] = None
        self._models: Dict[str, ModelConfig] = {}
        self._agents: Dict[str, AgentConfiguration] = {}
        self._system_config: Optional[SystemConfig] = None
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config_data = yaml.safe_load(file)
            
            self._parse_configuration()
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def _parse_configuration(self) -> None:
        if not self._config_data:
            raise ValueError("No configuration data loaded")
        
        # Parse system configuration
        system_data = self._config_data.get("system", {})
        self._system_config = SystemConfig(
            default_timeout=system_data.get("default_timeout", 30),
            default_max_retries=system_data.get("default_max_retries", 3),
            enable_verification=system_data.get("enable_verification", True),
            enable_planning=system_data.get("enable_planning", True)
        )
        
        # Parse model configurations
        models_data = self._config_data.get("models", {})
        for model_id, model_data in models_data.items():
            self._models[model_id] = ModelConfig(
                name=model_data.get("name", ""),
                temperature=model_data.get("temperature", 0.7),
                max_tokens=model_data.get("max_tokens"),
                timeout=model_data.get("timeout")
            )
        
        # Parse agent configurations
        agents_data = self._config_data.get("agents", {})
        for agent_id, agent_data in agents_data.items():
            self._agents[agent_id] = AgentConfiguration(
                agent_type=agent_data.get("agent_type", agent_id),
                model_config=agent_data.get("model_config", ""),
                system_prompt=agent_data.get("system_prompt", ""),
                parameters=agent_data.get("parameters", {})
            )
    
    def get_system_config(self) -> SystemConfig:
        if not self._system_config:
            raise RuntimeError("System configuration not loaded")
        return self._system_config
    
    def get_model_config(self, model_id: str) -> ModelConfig:
        if model_id not in self._models:
            raise KeyError(f"Model configuration '{model_id}' not found")
        return self._models[model_id]
    
    def get_agent_config(self, agent_id: str) -> AgentConfiguration:
        if agent_id not in self._agents:
            raise KeyError(f"Agent configuration '{agent_id}' not found")
        return self._agents[agent_id]
    
    def get_agent_full_config(self, agent_id: str) -> Dict[str, Any]:
        agent_config = self.get_agent_config(agent_id)
        model_config = self.get_model_config(agent_config.model_config)
        
        return {
            "agent_type": agent_config.agent_type,
            "model": model_config.name,
            "system_prompt": agent_config.system_prompt,
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens,
            "timeout": model_config.timeout or self._system_config.default_timeout,
            "max_retries": self._system_config.default_max_retries,
            "parameters": agent_config.parameters
        }
    
    def list_available_agents(self) -> List[str]:
        return list(self._agents.keys())
    
    def list_available_models(self) -> List[str]:
        return list(self._models.keys())
    
    def reload_configuration(self) -> None:
        self._config_data = None
        self._models.clear()
        self._agents.clear()
        self._system_config = None
        self._load_configuration()
    
    def override_agent_config(self, agent_id: str, overrides: Dict[str, Any]) -> None:
        if agent_id not in self._agents:
            raise KeyError(f"Agent configuration '{agent_id}' not found")
        
        agent_config = self._agents[agent_id]
        
        # Update agent configuration fields
        if "system_prompt" in overrides:
            agent_config.system_prompt = overrides["system_prompt"]
        
        if "parameters" in overrides:
            agent_config.parameters.update(overrides["parameters"])
        
        # Update model configuration if specified
        if "model_config" in overrides and overrides["model_config"] in self._models:
            agent_config.model_config = overrides["model_config"]
    
    def override_model_config(self, model_id: str, overrides: Dict[str, Any]) -> None:
        """
        Override specific model configuration values.
        
        Args:
            model_id: Model configuration ID  
            overrides: Dictionary of values to override
        """
        if model_id not in self._models:
            raise KeyError(f"Model configuration '{model_id}' not found")
        
        model_config = self._models[model_id]
        
        if "name" in overrides:
            model_config.name = overrides["name"]
        if "temperature" in overrides:
            model_config.temperature = overrides["temperature"]
        if "max_tokens" in overrides:
            model_config.max_tokens = overrides["max_tokens"]
        if "timeout" in overrides:
            model_config.timeout = overrides["timeout"]


_config_manager: Optional[ConfigurationManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigurationManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(config_path)
    return _config_manager


def reload_global_config() -> None:
    global _config_manager
    if _config_manager:
        _config_manager.reload_configuration()