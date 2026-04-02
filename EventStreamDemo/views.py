from django.shortcuts import render

def render_event_stream(request):
    import os
    import time
    from django.http import StreamingHttpResponse, HttpResponseNotFound

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    file_path = os.path.join(project_root, 'loremtxt.txt')

    def _stream_sse(chunk_size=1024, interval=1.0):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    # SSE event format
                    yield f"data: {chunk}\n\n"
                    time.sleep(interval)
            # After file ends, keep the connection alive with periodic heartbeats

        except FileNotFoundError:
            # Let caller handle by raising; generator should stop
            return

    if not os.path.exists(file_path):
        return HttpResponseNotFound('loremtxt.txt not found')

    resp = StreamingHttpResponse(_stream_sse(), content_type='text/event-stream')
    resp['Cache-Control'] = 'no-cache'
    resp['X-Accel-Buffering'] = 'no'
    return resp

# Create your views here.
