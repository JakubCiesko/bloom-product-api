from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    now = datetime.now()
    return templates.TemplateResponse(
        request=request, name="index.html", context={"now": now}
    )

@app.get("/products", response_class=JSONResponse)
async def get_products():
    return JSONResponse({"message": "OK"}, 200)



