from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pyembroidery
import os
import shutil
import uuid

app = FastAPI()

# IMPORTANT: This allows your Google AI Studio app to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/scale")
async def scale_embroidery(file: UploadFile = File(...), scale: float = Form(...)):
    # 1. Save uploaded file temporarily
    temp_id = str(uuid.uuid4())
    input_path = f"temp_{temp_id}_{file.filename}"
    output_path = f"scaled_{temp_id}_{file.filename}"
    
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Run your 'Perfect Scale' Logic
    pattern = pyembroidery.read(input_path)
    new_pattern = pyembroidery.EmbPattern()
    
    MAX_STITCH_LENGTH = 3.2
    last_x, last_y = 0, 0
    
    for x, y, cmd in pattern.stitches:
        tx, ty = x * scale, y * scale
        dist = ((tx - last_x)**2 + (ty - last_y)**2)**0.5
        
        if cmd == pyembroidery.STITCH and dist > MAX_STITCH_LENGTH:
            steps = int(dist // MAX_STITCH_LENGTH)
            for i in range(1, steps + 1):
                fraction = i / (steps + 1)
                new_pattern.add_stitch_absolute(pyembroidery.STITCH, last_x + (tx-last_x)*fraction, last_y + (ty-last_y)*fraction)
        
        new_pattern.add_stitch_absolute(cmd, tx, ty)
        last_x, last_y = tx, ty

    pyembroidery.write(new_pattern, output_path)

    # 3. Return the new file to the user
    return FileResponse(output_path, filename=f"scaled_{file.filename}")