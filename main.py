from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
import shutil
import os

'''
Executar no terminal para instalar as dependências:
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

Executar para iniciar o servidor:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
'''


UPLOAD_DIR = "static"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Image Map Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajustar em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# monta static (serve a imagem e tiles)
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")


class ImageInfo(BaseModel):
    filename: str
    width: int
    height: int
    bounds: list  # [[southWest_x, southWest_y], [northEast_x, northEast_y]]
    mode: str


@app.post("/api/upload", response_model=ImageInfo)
async def upload_image(file: UploadFile = File(...)):
    # salva o arquivo em static/
    dest = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # pega metadata com Pillow
    try:
        im = Image.open(dest)
        width, height = im.size
        mode = im.mode
        # Para Leaflet ImageOverlay usaremos coordenadas simples: [0,0] -> top-left e [width, height] -> bottom-right
        # Mas vamos normalizar para um sistema em que Y aumenta para baixo (Leaflet usa lat/lng; usaremos CRS.Simple)
        bounds = [
            [0, 0],
            [height, width],
        ]  # note: we'll swap when using in frontend with CRS.Simple
        return ImageInfo(
            filename=file.filename, width=width, height=height, bounds=bounds, mode=mode
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/image-info/{filename}", response_model=ImageInfo)
def image_info(filename: str):
    dest = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(dest):
        raise HTTPException(status_code=404, detail="File not found")
    im = Image.open(dest)
    w, h = im.size
    mode = im.mode
    bounds = [[0, 0], [h, w]]
    return ImageInfo(filename=filename, width=w, height=h, bounds=bounds, mode=mode)
