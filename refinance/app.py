from fastapi import FastAPI

from refinance.routes.entity import entity_router

app = FastAPI()
app.include_router(entity_router)
