from fastapi import FastAPI
from lynx.common.scene import Scene
import src.router

app = FastAPI()
scene = Scene()
processes = {}
tick_number = 0
# each element represents actions applied in a consecutive tick
# TODO change to states = {self.scene.hash(): [None]}
applied_actions = [[]]
