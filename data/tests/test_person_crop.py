import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from person_crop import Box, YoloPersonDetector, estimate_crop, expand, union


def frame(width=200, height=100):
    return np.zeros((height, width, 3), dtype=np.uint8)


class FakeYolo:
    """Imita `ultralytics.YOLO`: devolve as caixas combinadas, em xyxy."""

    calls: list[dict] = []
    boxes = np.array([[10.4, 5.2, 60.1, 90.0], [100.0, 0.0, 220.0, 95.0]])

    def __init__(self, model):
        self.model = model

    def predict(self, image, **kwargs):
        FakeYolo.calls.append(kwargs)
        xyxy = SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: FakeYolo.boxes))
        return [SimpleNamespace(boxes=SimpleNamespace(xyxy=xyxy))]


@pytest.fixture
def fake_ultralytics(monkeypatch):
    module = ModuleType("ultralytics")
    module.YOLO = FakeYolo
    monkeypatch.setitem(sys.modules, "ultralytics", module)
    FakeYolo.calls = []


def test_yolo_detector_picks_the_largest_person_clamped_to_the_frame(fake_ultralytics):
    detector = YoloPersonDetector("yolov8n.pt", confidence=0.5)
    assert detector(frame(width=200, height=100)) == Box(100, 0, 200, 95)
    assert FakeYolo.calls[0]["classes"] == [0]
    assert FakeYolo.calls[0]["conf"] == 0.5


def test_yolo_detector_without_person_returns_none(fake_ultralytics):
    FakeYolo.boxes = np.zeros((0, 4))
    try:
        assert YoloPersonDetector()(frame()) is None
    finally:
        FakeYolo.boxes = np.array([[10.4, 5.2, 60.1, 90.0], [100.0, 0.0, 220.0, 95.0]])


def test_union_covers_all_boxes_and_handles_empty():
    assert union([]) is None
    assert union([Box(10, 20, 50, 60), Box(5, 30, 40, 90)]) == Box(5, 20, 50, 90)


def test_expand_adds_margin_and_clamps_to_frame():
    box = Box(10, 10, 110, 60)
    assert expand(box, 0.1, 200, 100) == Box(0, 5, 120, 65)
    assert expand(box, 0.5, 200, 100) == Box(0, 0, 160, 85)


def test_estimate_crop_merges_detections_and_applies_margin():
    detections = iter([Box(50, 10, 100, 90), None, Box(60, 20, 130, 80)])
    crop = estimate_crop([frame(), frame(), frame()], lambda _: next(detections), margin=0.0)
    assert crop == Box(50, 10, 130, 90)


def test_estimate_crop_without_person_returns_none():
    assert estimate_crop([frame(), frame()], lambda _: None) is None
    assert estimate_crop([], lambda _: Box(0, 0, 1, 1)) is None
