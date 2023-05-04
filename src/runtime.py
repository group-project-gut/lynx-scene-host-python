from aioprocessing.connection import AioConnection
from lynx.common.scene import Scene


def execution_runtime(pipe: AioConnection, object_id: int):
    from time import sleep

    from lynx.common.actions.action import Action
    from lynx.common.actions.chop import Chop
    from lynx.common.actions.move import Move
    from lynx.common.actions.push import Push
    from lynx.common.actions.message_log import MessageLog
    from lynx.common.enums import Direction
    from lynx.common.vector import Vector

    scene_serialized = pipe.recv()
    scene: Scene = Scene.deserialize(scene_serialized)

    def send(action: Action):
        pipe.send(action.serialize())
        scene_serialized = pipe.recv()
        scene = Scene.deserialize(scene_serialized)

    builtins = {
        'agent': scene.get_object_by_id(object_id),
        'chop': lambda vector: send(Chop(object_id, vector)),
        'move': lambda vector: send(Move(object_id, vector)),
        'push': lambda vector: send(Push(object_id, vector)),
        'log': lambda text: send(MessageLog(object_id, text)),
        'sleep': sleep,
        'Vector': Vector,
        'str': str,
        'range': range,
        'len': len,
    }

    while (True):
        # Sure, I know exec bad
        # pylint: disable=exec-used
        exec(
            scene.get_object_by_id(object_id).tick,
            {'__builtins__': builtins},
        )
