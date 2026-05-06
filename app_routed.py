from fastapi import FastAPI
from chainlit.utils import mount_chainlit

app = FastAPI()

# Your main app routes
@app.get("/health")
async def read_main():
    return {"message": "Welcome to the main app"}

# Mount Chainlit on the /chat route
mount_chainlit(app=app, target="app.py", path="/content-generator")
