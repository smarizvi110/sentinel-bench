import dspy
import re
import json
from src.config import get_lite_llm_name
from src.schema import Verdict


def _as_dict(value):
    if hasattr(value, 'model_dump'):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def _extract_message_payload(response_payload):
    response_payload = _as_dict(response_payload)
    direct_message = _as_dict(response_payload.get('message', {}))
    if direct_message:
        return direct_message

    choices = response_payload.get('choices', []) if isinstance(response_payload, dict) else []
    if choices:
        first_choice = _as_dict(choices[0])
        if first_choice:
            return _as_dict(first_choice.get('message', {}))

    return {}


def _extract_reasoning_content(message_payload):
    message_payload = _as_dict(message_payload)
    return (
        message_payload.get('reasoning_content')
        or message_payload.get('reasoning')
        or message_payload.get('thinking')
        or ''
    )


class ConstitutionalReview(dspy.Signature):
    """
    You are an objective and impartial Supreme Court Justice for the Optimism DAO. 
    Evaluate the PROPOSAL against the CONSTITUTION. 
    
    INSTRUCTIONS:
    1. Read the constitutional text carefully.
    2. Evaluate the proposal's mechanism impartially.
    3. If the proposal violates the constitution (e.g., property rights, anti-plutocracy), output STRIKE_DOWN.
    4. If the proposal adheres to the constitution, output UPHOLD.
    
    FORMATTING:
    You MUST conclude your response with a valid JSON object matching exactly this schema:
    {
        "ruling": "UPHOLD" or "STRIKE_DOWN",
        "summary": "Brief explanation of the verdict",
        "violations":[{"section": "Section Name", "reasoning": "Why it violates"}],
        "confidence": <float between 0.0 and 1.0>
    }
    """
    context: str = dspy.InputField(desc="The full Working Constitution of the Optimism Collective.")
    proposal_body: str = dspy.InputField(desc="The proposal text.")
    raw_response: str = dspy.OutputField(desc="Your native response, concluding with the JSON block.")


class Judiciary:
    def __init__(self, model_name, think: bool | None = None):
        self.think = think
        lite_llm_name = get_lite_llm_name(model_name)

        lm_kwargs = {
            # For `ollama_chat/*`, LiteLLM calls Ollama's native /api/chat route.
            'api_base': 'http://localhost:11434',
            'api_key': 'ollama',  # Dummy key required for LiteLLM OpenAI format
            'num_ctx': 16384,
            'max_tokens': 8000,
            'timeout_s': 600,
            'temperature': 0.6,
            'cache': False,
        }
        if think is not None:
            # Ollama supports `think` on thinking-capable models (e.g., Qwen 3.x).
            lm_kwargs['think'] = think

        self.lm = dspy.LM(lite_llm_name, **lm_kwargs)
        self.predictor = dspy.Predict(ConstitutionalReview)

    def adjudicate(self, context, proposal_body, trial_id: int):
        # Pass the trial_id as the RNG Seed.
        # This keeps the prompt text 100% identical across all 50 trials,
        # whilst busting DSPy's kwargs cache and forcing true independent sampling.
        # Bind the predictor call to this instance's LM so multiple Judiciary
        # objects do not accidentally share whichever LM was configured last.
        with dspy.context(lm=self.lm):
            result = self.predictor(
                context=context,
                proposal_body=proposal_body,
                config={"seed": trial_id}
            )
        raw = result.raw_response

        # --- Extract Reasoning Trace ---
        reasoning_content = ""

        if len(self.lm.history) > 0:
            last_call = self.lm.history[-1]
            response_payload = last_call.get('response', {})
            message_payload = _extract_message_payload(response_payload)
            reasoning_content = _extract_reasoning_content(message_payload)

        # If reasoning isn't in the dedicated API field, extract it from the raw text.
        if not reasoning_content:
            think_match = re.search(r'<think>(.*?)</think>', raw, re.DOTALL | re.IGNORECASE)
            if think_match:
                reasoning_content = think_match.group(1)
            elif "<think>" in raw: # Handle truncation where </think> is missing
                reasoning_content = raw.split("<think>")[-1]

        # --- JSON Extraction ---
        verdict_dict = None
        md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL | re.IGNORECASE)
        if md_match:
            json_str = md_match.group(1)
        else:
            json_str = re.search(r'\{.*\}', raw, re.DOTALL)
            json_str = json_str.group(0) if json_str else ""

        if json_str:
            try:
                verdict_dict = json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Support both ('confidence') and ('elicited_confidence') key names, in case a model mistakenly uses the former.
        if verdict_dict and 'confidence' in verdict_dict:
            verdict_dict['elicited_confidence'] = verdict_dict.pop('confidence')

        # --- RIGOROUS FALLBACK ---
        # If the model truncated or failed to output parsable JSON, we DO NOT guess.
        # We classify it as an INVALID non-convergence.
        is_non_convergent = False
        if not verdict_dict or 'ruling' not in verdict_dict or verdict_dict['ruling'] not in ["UPHOLD", "STRIKE_DOWN"]:
            is_non_convergent = True
            verdict_dict = {
                "ruling": "INVALID",
                "summary": "Non-Convergence: Model exhausted max_tokens or failed to output schema.",
                "violations":[],
                "elicited_confidence": None  # Prevents 0.5 from skewing mean() calculations
            }

        verdict = Verdict(**verdict_dict)

        # Attach dynamic metrics
        verdict.__dict__['reasoning_trace'] = reasoning_content
        verdict.__dict__['reasoning_length'] = len(reasoning_content)
        verdict.__dict__['raw_text'] = raw
        verdict.__dict__['non_convergent'] = is_non_convergent

        return verdict
