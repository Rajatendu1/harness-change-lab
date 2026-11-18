"""Prepare-only text request admission, not a provider quota or grant check.

The controller supplies a reviewed tokenizer for the exact model/template.
No tokenizer is guessed here. This module performs no network or credential IO.
Counts are local estimates unless the selected provider's framing is verified.
"""
from dataclasses import dataclass
import json


@dataclass(frozen=True)
class TextRequestPolicy:
    model: str
    max_input_tokens: int
    max_output_tokens: int
    max_body_bytes: int = 32768
    max_messages: int = 16

    def __post_init__(self):
        if not isinstance(self.model, str) or not self.model:
            raise ValueError('Fixed model required')
        for value in (self.max_input_tokens, self.max_output_tokens,
                      self.max_body_bytes, self.max_messages):
            if type(value) is not int or value <= 0:
                raise ValueError('Positive integer bounds required')

    def admit(self, payload, *, count_tokens):
        """Return canonical bounded bytes only after explicit token accounting.

        count_tokens takes an immutable tuple of (role, text) pairs, including
        the system prompt. It must include template framing overhead. It never
        sees a credential. A missing/failing/invalid counter refuses admission.
        This is a local planning bound, not a guarantee against provider 429s.
        """
        if not isinstance(payload, dict) or set(payload) - {
                'model', 'messages', 'stream', 'max_tokens', 'temperature',
                'top_p', 'stop', 'seed'}:
            raise ValueError('Unsupported request field')
        if payload.get('model') != self.model or payload.get('stream', False) is not False:
            raise ValueError('Fixed nonstreaming model required')
        cap = payload.get('max_tokens')
        if type(cap) is not int or not 0 < cap <= self.max_output_tokens:
            raise ValueError('Explicit bounded output required')
        messages = payload.get('messages')
        if not isinstance(messages, list) or not 0 < len(messages) <= self.max_messages:
            raise ValueError('Bounded text messages required')
        pairs = []
        for message in messages:
            if (not isinstance(message, dict) or set(message) != {'role', 'content'}
                    or message['role'] not in ('system', 'user', 'assistant')
                    or not isinstance(message['content'], str)):
                raise ValueError('Only plain text message content is accepted')
            pairs.append((message['role'], message['content']))
        # Bound serialization before invoking a potentially expensive tokenizer.
        try:
            raw = json.dumps(payload, ensure_ascii=False, allow_nan=False,
                             separators=(',', ':')).encode('utf-8')
        except (ValueError, TypeError, UnicodeError):
            raise ValueError('Invalid JSON request') from None
        if len(raw) > self.max_body_bytes:
            raise ValueError('Input byte bound exceeded')
        try:
            count = count_tokens(tuple(pairs))
        except Exception:
            raise ValueError('Reviewed token accounting unavailable') from None
        if type(count) is not int or not 0 <= count <= self.max_input_tokens:
            raise ValueError('Input token bound exceeded or unverifiable')
        return raw
