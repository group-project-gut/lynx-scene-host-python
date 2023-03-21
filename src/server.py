from fastapi import FastAPI

class Server():
    def __init__(self) -> None:
        self.app = FastAPI()
        context = {'num': 1}

        @self.app.get("/get")
        async def get():
            return {"message": context['num']}
        
        @self.app.get("/add")
        async def add():
            context['num'] = context['num'] + 1
            return {"message": context['num']}
   