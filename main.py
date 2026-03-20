from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pyembroidery
import os
import uuid
import base64

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/scale")
async def scale_embroidery(file: UploadFile = File(...), scale: float = Form(...)):
    temp_id = str(uuid.uuid4())
    input_path = f"temp_{temp_id}_{file.filename}"
    output_path = f"scaled_{temp_id}_{file.filename}"
    
    with open(input_path, "wb") as f:
        f.write(await file.read())

    pattern = pyembroidery.read(input_path)
    new_pattern = pyembroidery.EmbPattern()
    
    # --- COLOR EXTRACTION ---
    colors = []
    for thread in pattern.threadlist:
        hex_color = f"#{thread.red:02x}{thread.green:02x}{thread.blue:02x}"
        colors.append(hex_color)
    
    # If no colors found (common in DST), provide a default bee palette
    if not colors:
        colors = ["#000000", "#FFD700", "#FFFFFF"]

    # --- PERFECT SCALING LOGIC ---
    MAX_STITCH_LENGTH = 3.2
    last_x, last_y = 0, 0
    for x, y, cmd in pattern.stitches:
        tx, ty = x * scale, y * scale
        dist = ((tx - last_x)**2 + (ty - last_y)**2)**0.5
        
        if cmd == pyembroidery.STITCH and dist > MAX_STITCH_LENGTH:
            steps = int(dist // MAX_STITCH_LENGTH)
            for i in range(1, steps + 1):
                f = i / (steps + 1)
                new_pattern.add_stitch_absolute(pyembroidery.STITCH, last_x + (tx-last_x)*f, last_y + (ty-last_y)*f)
        
        new_pattern.add_stitch_absolute(cmd, tx, ty)
        last_x, last_y = tx, ty

    pyembroidery.write(new_pattern, output_path)

    # --- ENCODE FILE FOR JSON ---
    with open(output_path, "rb") as f:
        encoded_file = base64.b64encode(f.read()).decode('utf-8')

    # Cleanup
    os.remove(input_path)
    os.remove(output_path)

    return JSONResponse({
        "status": "success",
        "new_stitch_count": len(new_pattern.stitches),
        "colors": colors,
        "base64_file": encoded_file,
        "filename": f"scaled_{file.filename}"
    })
