# Model Configuration Update Summary

## Overview
This document summarizes the model configuration updates made to optimize the multi-agent system for better performance and cost-effectiveness using free/affordable models.

## Updated Model Configurations

### Agent Model Assignments

| Agent | Previous Model | Updated Model | Provider | Pricing |
|-------|---------------|---------------|----------|---------|
| **PlannerAgent** | deepseek/deepseek-chat | deepseek/deepseek-chat | DeepSeek | Paid |
| **QueryRewriterAgent** | openai/gpt-3.5-turbo | mistralai/mistral-7b-instruct:free | Mistral AI | Free |
| **AnswerAgent** | openai/gpt-4o-mini | google/gemma-3-27b-it:free | Google | Free |
| **VerifierAgent** | google/gemini-flash-1.5 | google/gemini-flash-1.5 | Google | Free |
| **ResponseAgent** | openai/gpt-3.5-turbo | meituan/longcat-flash-chat:free | Meituan | Free |

### Key Changes Made

#### 1. Timeout Configuration Updates
- **Previous**: Fixed timeout of 30 seconds for all agents
- **Updated**: Timeout set to `None` for all agents using free models
- **Rationale**: Free models often have longer response times and queue delays

#### 2. Model Selection Rationale

**AnswerAgent - Google Gemma-3 27B IT Free**
- **Task**: Generate comprehensive answers from RAG context
- **Why Gemma**: Excellent instruction following and reasoning capabilities
- **Benefits**: Good performance on Vietnamese text, free tier availability

**QueryRewriterAgent - Mistral 7B Instruct Free**
- **Task**: Reformulate and optimize user queries
- **Why Mistral**: Strong text transformation and rewriting capabilities
- **Benefits**: Fast inference, good multilingual support

**ResponseAgent - LongCat Flash Chat Free**
- **Task**: Format final responses for user presentation
- **Why LongCat**: Optimized for chat responses, good formatting
- **Benefits**: Fast response times, conversational tone

**VerifierAgent - Gemini Flash 1.5**
- **Task**: Verify answer accuracy and relevance
- **Why Gemini**: Advanced reasoning and verification capabilities
- **Benefits**: Free tier, excellent fact-checking abilities

**PlannerAgent - DeepSeek Chat**
- **Task**: Create execution plans and coordinate workflow
- **Why DeepSeek**: Superior planning and reasoning capabilities
- **Benefits**: Cost-effective, excellent JSON formatting

### Technical Implementation Changes

#### OpenRouter Adapter Updates
```python
# Updated timeout handling
timeout: Optional[int] = 30  # Now accepts None
timeout_config = aiohttp.ClientTimeout(total=self.timeout) if self.timeout else None
```

#### Agent Configuration Pattern
```python
class AgentConfig:
    model: str = "model-name"
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout: Optional[int] = None  # No timeout for free models
```

## Performance Considerations

### Expected Benefits
1. **Cost Reduction**: Majority of agents now use free models
2. **Improved Reliability**: No timeout constraints for slow free models
3. **Better Task Alignment**: Models selected based on specific capabilities

### Potential Trade-offs
1. **Response Time**: Free models may have longer latency
2. **Rate Limits**: Free tiers have usage restrictions
3. **Availability**: Free models may have queue delays during peak hours

## Testing Strategy

### Verification Steps
1. Individual agent testing with new models
2. Full pipeline testing with realistic queries
3. Performance benchmarking against previous configuration
4. Error handling validation for timeout scenarios

### Success Metrics
- Response accuracy maintained or improved
- System stability with timeout removal
- Cost reduction achieved
- User experience quality preserved

## Deployment Notes

### Environment Requirements
- OpenRouter API key with access to specified models
- Proper error handling for model unavailability
- Monitoring for free tier usage limits

### Rollback Plan
If issues arise, previous model configuration can be restored by:
1. Reverting model names in agent configurations
2. Restoring timeout values to 30 seconds
3. Testing system stability

## Future Optimizations

### Potential Improvements
1. **Dynamic Model Selection**: Switch between free/paid based on load
2. **Fallback Chains**: Secondary models for high availability
3. **Caching Strategy**: Reduce API calls for similar queries
4. **Load Balancing**: Distribute requests across multiple free models

### Monitoring Requirements
- Track model response times and success rates
- Monitor free tier usage limits
- Alert on model availability issues
- Performance metrics collection

## Configuration Files Updated

1. `/services/orchestrator/app/agents/planner_agent.py`
2. `/services/orchestrator/app/agents/query_rewriter_agent.py`
3. `/services/orchestrator/app/agents/answer_agent.py`
4. `/services/orchestrator/app/agents/verifier_agent.py`
5. `/services/orchestrator/app/agents/response_agent.py`
6. `/services/orchestrator/app/adapters/openrouter_adapter.py`

---

**Date**: October 2024  
**Version**: 2.0  
**Status**: Implemented and Ready for Testing