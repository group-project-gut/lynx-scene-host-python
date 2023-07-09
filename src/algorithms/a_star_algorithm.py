from dataclasses import dataclass
from typing import List, Tuple

from lynx.common.vector import Vector


@dataclass
class AStarAlgorithm:
    """
    Get the shortest path from start to end
    """
    start: Vector = None
    end: Vector = None

    class Node:
        def __init__(self, parent=None, position=None):
            self.parent = parent
            self.position = position

            self.distance_to_start_node = 0
            self.heuristic = 0
            self.total_cost = 0

        def __eq__(self, other):
            return self.position == other.position

    def get_path(self, scene: 'Scene') -> List[Vector]:
        """
        Get the shortest path from start to end in scene using A* algorithm
        return list of vectors from start
        """
        start_node = AStarAlgorithm.Node(position=(self.start.x, self.start.y))
        start_node.distance_to_start_node = start_node.heuristic = start_node.total_cost = 0
        end_node = AStarAlgorithm.Node(position=(self.end.x, self.end.y))
        end_node.distance_to_start_node = end_node.heuristic = end_node.total_cost = 0

        # initialize both open and closed list
        open_list = []
        closed_list = []

        # add the start node
        open_list.append(start_node)

        # loop until you find the end
        while len(open_list) > 0:
            # get the current node
            current_node = open_list[0]
            current_index = 0
            for index, item in enumerate(open_list):
                if item.total_cost < current_node.total_cost:
                    current_node = item
                    current_index = index

            # pop current off open list, add to closed list
            open_list.pop(current_index)
            closed_list.append(current_node)

            # found the goal
            if current_node == end_node:
                path = []
                current = current_node
                while current is not None:
                    path.append(current.position)
                    current = current.parent
                return self.transform_to_unit_vectors(path[::-1])

            # generate children
            children = []
            for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0)]:  # adjacent squares
                # get node position
                node_position = (current_node.position[0] + new_position[0],
                                 current_node.position[1] + new_position[1])

                # make sure walkable terrain
                objects_on_ground = scene.get_objects_by_position(Vector(node_position[0], node_position[1]))
                if len(objects_on_ground) == 0:
                    continue
                is_not_walkable = False
                for object_on_ground in objects_on_ground:
                    if 'walkable' not in object_on_ground.tags:
                        is_not_walkable = True
                        break

                if is_not_walkable:
                    continue

                new_node = AStarAlgorithm.Node(current_node, node_position)
                children.append(new_node)

            # loop through children
            for child in children:
                # child is on the closed list
                for closed_child in closed_list:
                    if child == closed_child:
                        continue

                # create the f, g, and h values
                child.distance_to_start_node = current_node.distance_to_start_node + 1
                child.heuristic = ((child.position[0] - end_node.position[0]) ** 2) + (
                        (child.position[1] - end_node.position[1]) ** 2)
                child.total_cost = child.distance_to_start_node + child.heuristic

                # child is already in the open list
                for open_node in open_list:
                    if child == open_node and child.distance_to_start_node > open_node.distance_to_start_node:
                        continue

                if child in open_list:
                    continue

                # add the child to the open list
                open_list.append(child)

    @staticmethod
    def transform_to_unit_vectors(positions: List[Tuple]) -> List[Vector]:
        """
        Transform list of tuples to list of vectors from start to end
        :param positions: list of tuples
        :return: list of unit vectors from start to end
        """
        vectors = []
        for i in range(len(positions) - 1):
            start_point = positions[i]
            end_point = positions[i + 1]
            vector = Vector(end_point[0] - start_point[0], end_point[1] - start_point[1])
            vectors.append(vector)
        return vectors
