import json
from rest_framework.renderers import BaseRenderer


class EventStreamRenderer(BaseRenderer):
    """Renderer for Server-Sent Events (text/event-stream).

    For non-streaming responses DRF will call `render` and this returns a
    properly formatted SSE payload (single event). For streaming responses
    the view should return a `StreamingHttpResponse` directly but still set
    `request.accepted_renderer` to an instance of this renderer to satisfy
    DRF's exception handling.
    """
    media_type = 'text/event-stream'
    format = 'event-stream'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b''
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        text = data if isinstance(data, str) else json.dumps(data)
        # Prefix with 'data:' and terminate with two newlines per SSE spec
        return ('data: ' + text + '\n\n').encode(self.charset)
