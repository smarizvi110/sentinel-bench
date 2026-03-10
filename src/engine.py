import dspy
import re
import json
from src.schema import Verdict


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
        "elicited_confidence": <float between 0.0 and 1.0>
    }
    """
    context: str = dspy.InputField(desc="The full Working Constitution of the Optimism Collective.")
    proposal_body: str = dspy.InputField(desc="The proposal text.")
    raw_response: str = dspy.OutputField(desc="Your native response, concluding with the JSON block.")


class Judiciary:
    def __init__(self, model_name):
        # Format the model name for LiteLLM's OpenAI routing
        lite_llm_name = f"openai/{model_name.split('/')[-1]}" if "ollama" in model_name else model_name

        self.lm = dspy.LM(
            lite_llm_name,
            api_base='http://localhost:11434/v1',  # Route to Ollama's OpenAI-compat endpoint
            api_key='ollama',  # Dummy key required for LiteLLM OpenAI format
            num_ctx=16384,
            max_tokens=8000,
            timeout_s=600,
            temperature=0.6,
            cache=False,
            logprobs=False
        )
        dspy.configure(lm=self.lm)
        self.predictor = dspy.Predict(ConstitutionalReview)

    def adjudicate(self, context, proposal_body, trial_id: int):
        # Pass the trial_id as the RNG Seed.
        # This keeps the prompt text 100% identical across all 50 trials,
        # whilst busting DSPy's kwargs cache and forcing true independent sampling.
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
            if hasattr(response_payload, 'model_dump'):
                response_payload = response_payload.model_dump()

            choices = response_payload.get('choices', []) if isinstance(response_payload, dict) else []
            if choices:
                choice_0 = choices[0]
                if hasattr(choice_0, 'model_dump'):
                    choice_0 = choice_0.model_dump()

                # 1. Extract Reasoning across provider field variants
                message = choice_0.get('message', {}) if isinstance(choice_0, dict) else {}
                if hasattr(message, 'model_dump'):
                    message = message.model_dump()
                if isinstance(message, dict):
                    reasoning_content = (
                        message.get('reasoning_content')
                        or message.get('reasoning')
                        or message.get('thinking')
                        or ""
                    )
                else:
                    reasoning_content = ""

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

        # Normalize legacy key names that may still appear in model JSON.
        if verdict_dict and 'elicited_confidence' not in verdict_dict and 'confidence' in verdict_dict:
            verdict_dict['elicited_confidence'] = verdict_dict.pop('confidence')

        # Robust Fallback
        if not verdict_dict or 'ruling' not in verdict_dict:
            fallback_ruling = "STRIKE_DOWN" if "STRIKE_DOWN" in raw else "UPHOLD"
            verdict_dict = {
                "ruling": fallback_ruling,
                "summary": "JSON Parsing Failed.",
                "violations": [],
                "elicited_confidence": 0.5
            }

        verdict = Verdict(**verdict_dict)

        # Attach dynamic metrics
        verdict.__dict__['reasoning_trace'] = reasoning_content
        verdict.__dict__['reasoning_length'] = len(reasoning_content)
        verdict.__dict__['raw_text'] = raw

        return verdict
