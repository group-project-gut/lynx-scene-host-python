#!/usr/bin/env python3

def main():
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI()
    context = {'num': 1}


    @app.get("/get")
    async def get():
        return {"message": context['num']}
    
    @app.get("/add")
    async def add():
        context['num'] = context['num'] + 1
        return {"message": context['num']}
    
    uvicorn.run(app, host="0.0.0.0", port=8555, workers=1)

if __name__ == '__main__':
    main()