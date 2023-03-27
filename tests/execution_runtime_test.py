from json import JSONDecodeError
import pytest
from lynx.common.scene import Scene
from lynx.common.object import Object

class TestExecutionRuntime:
    def test_sequential_code(self):
        from src.scene_server import execution_runtime

        scene = Scene()
        object = Object(id=0, tick="move(Vector(0,10))\nmove(Vector(-20,0))")
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

        assert received_actions == ['{"type": "Move", "attributes": "{\\"object_id\\": 0, \\"vector\\": {\\"x\\": 0, \\"y\\": 10}}"}', '{"type": "Move", "attributes": "{\\"object_id\\": 0, \\"vector\\": {\\"x\\": -20, \\"y\\": 0}}"}']