from aioprocessing.connection import AioConnection

from src.algorithms import AStarAlgorithm
from src.utils.logger import get_logger

logger = get_logger()


def execution_runtime(pipe: AioConnection, object_id: int):
    from time import sleep

    from lynx.common.actions.action import Action
    from lynx.common.actions.chop import Chop
    from lynx.common.actions.mine import Mine
    from lynx.common.actions.error_log import ErrorLog
    from lynx.common.scene import Scene
    from lynx.common.actions.move import Move
    from lynx.common.actions.push import Push
    from lynx.common.actions.message_log import MessageLog
    from lynx.common.vector import Vector
    from lynx.common.enums import Direction

    logger.info("Starting execution runtime for object with id: " + str(object_id))
    logger.info("Waiting for scene to be sent")
    scene_serialized = pipe.recv()
    logger.info("Scene has been successfully received")
    logger.info("Starting to deserialize scene")
    scene: Scene = Scene.deserialize(scene_serialized)
    logger.info("Scene has been successfully deserialized")

    def send(action: Action):
        logger.debug(f"Sending action: {action.serialize()}")
        nonlocal scene
        pipe.send(action.serialize())
        logger.debug(f"Action has been successfully sent")
        logger.debug(f"Waiting for scene to be sent")
        scene_serialized = pipe.recv()
        logger.debug(f"Scene has been successfully received")
        logger.debug(f"Starting to deserialize scene")
        scene = Scene.deserialize(scene_serialized)
        logger.debug(f"Scene has been successfully deserialized")
        return scene

    def goto(target_position: Vector):
        nonlocal scene

        agent = scene.get_object_by_id(object_id)
        if agent.position == target_position:
            send(MessageLog(object_id, f"I am already on target position"))

        objects_on_target_position = scene.get_objects_by_position(target_position)
        for object in objects_on_target_position:
            if 'walkable' not in object.tags:
                send(MessageLog(object_id, f"Target position: {target_position} is not walkable"))

        path = AStarAlgorithm(agent.position, target_position).get_path(scene)
        for vector in path:
            scene = send(Move(object_id, vector))

    builtins = {
        'agent': scene.get_object_by_id(object_id),
        'chop': lambda vector: send(Chop(object_id, vector)),
        'move': lambda vector: send(Move(object_id, vector)),
        'push': lambda vector: send(Push(object_id, vector)),
        'mine': lambda vector: send(Mine(object_id, vector)),
        'log': lambda text: send(MessageLog(object_id, text)),
        'goto': lambda target_position: goto(target_position),
        'NORTH': Direction.NORTH.value,
        'SOUTH': Direction.SOUTH.value,
        'EAST': Direction.EAST.value,
        'WEST': Direction.WEST.value,
        'sleep': sleep,
        'Vector': Vector,
        'str': str,
        'range': range,
        'len': len,
    }

    try:
        while (True):
            exec(
                scene.get_object_by_id(object_id).tick,
                {'__builtins__': builtins},
            )
    except Exception as e:
        send(ErrorLog(text=str(e)))
