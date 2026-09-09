"""SSE contract cho chart — backward compatible với parser cũ."""

from interfaces.api.app import _sse_chart_error_event, _sse_chart_spec_event


def test_chart_spec_event_shape():
    import json

    evt = _sse_chart_spec_event('{"chart_type":"line"}', "rid-1")
    assert evt.startswith("event: chart_spec\n")
    assert evt.endswith("\n\n")
    data_line = evt.split("data: ", 1)[1].rsplit("\n", 2)[0]
    outer = json.loads(data_line)
    assert outer["request_id"] == "rid-1"
    assert json.loads(outer["spec"])["chart_type"] == "line"


def test_chart_error_event_shape():
    evt = _sse_chart_error_event("bad spec", "rid-2")
    assert evt.startswith("event: chart_error\n")
    assert "bad spec" in evt
