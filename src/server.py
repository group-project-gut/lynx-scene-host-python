from fastapi import FastAPI
import uvicorn

class Server():
    def __init__(self, host: str = "0.0.0.0", port: int = 8555) -> None:
        self.host = host
        self.port = port
        
    def run(self) -> None:
        app = FastAPI()
        context = {'num': 1}

        @app.get("/get")
        async def get():
            return {"message": context['num']}
        
        @app.get("/add")
        async def add():
            context['num'] = context['num'] + 1
            return {"message": context['num']}
        
        uvicorn.run(app, host=self.host, port=self.port, workers=1)