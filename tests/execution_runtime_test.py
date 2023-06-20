from json import JSONDecodeError
import pytest
from lynx.common.scene import Scene
from lynx.common.object import Object


class TestExecutionRuntime:
    def test_sequential_code(self):
        from src.app import execution_runtime

        scene = Scene()
        object = Object(id=0, tick="move(Vector(0,1))\nmove(Vector(-1,0))")
        scene.add_entity(object)

        received_actions = []

        class MockedPipe:
            def __init__(self) -> None:
                self.recv_done = 0
                self.recv_count = 2

            def send(self, action):
                received_actions.append(action)

            def recv(self) -> str:
                if self.recv_done < self.recv_count:
                    self.recv_done += 1
                    return scene.serialize()
                else:
                    # This return will break execution runtime
                    return ""

        pipe = MockedPipe()
        try:
            execution_runtime(pipe, 0)
        except JSONDecodeError:
            pass

        assert received_actions == ['{"type": "Move", "attributes": {"object_id": 0, "direction": {"x": 0, "y": 1}}}',
                                    '{"type": "Move", "attributes": {"object_id": 0, "direction": {"x": -1, "y": 0}}}',
                                    '{"type": "ErrorLog", "attributes": {"text": "Expecting value: line 1 column 1 (char 0)"}}']
