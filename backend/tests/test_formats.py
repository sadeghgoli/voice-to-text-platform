from app.stt.formats import segments_to_srt, segments_to_text, segments_to_vtt

SEGMENTS = [
    {"start": 0.0, "end": 3.2, "text": "سلام وقت بخیر"},
    {"start": 3.2, "end": 7.5, "text": "به سرویس تبدیل صوت به متن خوش آمدید"},
]


def test_plain_text_joins_segments():
    assert segments_to_text(SEGMENTS) == "سلام وقت بخیر به سرویس تبدیل صوت به متن خوش آمدید"


def test_srt_timestamps_and_indexes():
    body = segments_to_srt(SEGMENTS)
    assert body.startswith("1\n00:00:00,000 --> 00:00:03,200\nسلام وقت بخیر")
    assert "2\n00:00:03,200 --> 00:00:07,500" in body


def test_vtt_header():
    body = segments_to_vtt(SEGMENTS)
    assert body.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:03.200" in body
    assert "خوش آمدید" in body
