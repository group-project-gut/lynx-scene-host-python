from typing import NoReturn

from lynx.common.actions.move import Move
from lynx.common.enums import Direction

from src.app import calculate_deltas


class TestCalculateDeltas:
    applied_actions = [
        [],
        [Move(object_id=123, direction=Direction.NORTH.value).serialize(), Move(object_id=124, direction=Direction.WEST.value).serialize()],
        [Move(object_id=123, direction=Direction.SOUTH.value).serialize()],
        [Move(object_id=345, direction=Direction.EAST.value).serialize(), Move(object_id=124, direction=Direction.EAST.value).serialize()],
        [],
        [Move(object_id=124, direction=Direction.NORTH.value).serialize(), Move(object_id=123, direction=Direction.WEST.value).serialize()]
    ]
    expected_deltas = [applied_actions[1][0], applied_actions[1][1], applied_actions[2][0], applied_actions[3][0], applied_actions[3][1]]

    def test_success(self) -> NoReturn:
        deltas = calculate_deltas(0, 3, self.applied_actions)
        assert deltas == self.expected_deltas

    def test_failure(self) -> NoReturn:
        deltas = calculate_deltas(2, 4, self.applied_actions)
        assert deltas != self.expected_deltas
