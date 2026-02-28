import httpx
from config import Config

class ClaudeClient:
    """
    Claude API Client with vision support
    Replaces legacy DeepSeek client
    """
    def __init__(self):
        self.api_key = Config.CLAUDE_API_KEY
        if not self.api_key:
            raise ValueError('⚠ ANTHROPIC_API_KEY is required!')

        self.api_url = Config.CLAUDE_API_URL
        self.model = Config.CLAUDE_MODEL

    async def call_claude(self, message, history=None, image_data=None):
        """
        Send message to Claude API

        Args:
            message: User message text
            history: Previous conversation history
            image_data: Optional base64 encoded image for vision analysis

        Returns:
            dict with 'reply' and 'model' fields
        """
        messages = []

        # Historia - last 10 messages
        if history:
            recent_history = history[-10:] if len(history) > 10 else history
            messages.extend(recent_history)

        # Current message - with optional image
        content = []

        if image_data:
            # Vision mode - image + text
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data
                }
            })

        content.append({
            "type": "text",
            "text": message
        })

        messages.append({
            'role': 'user',
            'content': content if len(content) > 1 else message
        })

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        'x-api-key': self.api_key,
                        'anthropic-version': '2023-06-01',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': self.model,
                        'messages': messages,
                        'system': 'Jesteś pomocnym asystentem AI. Odpowiadaj zwięźle i na temat.',
                        'max_tokens': 4096,
                        'temperature': 0.7
                    },
                    timeout=60.0
                )

                response.raise_for_status()
                data = response.json()
                reply = data['content'][0]['text']

                return {
                    'reply': reply,
                    'model': data.get('model', self.model),
                    'stop_reason': data.get('stop_reason')
                }

        except Exception as e:
            return {'reply': f'⚠ Błąd Claude API: {str(e)}', 'error': True}

# Global instance
claude_client = ClaudeClient()
