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
    
    try:
        content = await file.read()
        with open(input_path, "wb") as f:
            f.write(content)

        pattern = pyembroidery.read(input_path)
        new_pattern = pyembroidery.EmbPattern()
        
        # 1. COLOR LOGIC: Professional Neutral Fallback
        colors = []
        if pattern.threadlist:
            for thread in pattern.threadlist:
                colors.append(f"#{thread.red:02x}{thread.green:02x}{thread.blue:02x}")
        else:
            # If no colors (DST), send 'blueprint' flag
            colors = ["BLUEPRINT"] 

        # 2. ADAPTIVE SCALING LOGIC
        MAX_STITCH_LENGTH = 3.2
        last_x, last_y = 0, 0
        for x, y, cmd in pattern.stitches:
            tx, ty = x * scale, y * scale
            dx, dy = tx - last_x, ty - last_y
            dist = (dx**2 + dy**2)**0.5
            
            if cmd == pyembroidery.STITCH and dist > MAX_STITCH_LENGTH:
                steps = int(dist // MAX_STITCH_LENGTH)
                for i in range(1, steps + 1):
                    f_val = i / (steps + 1)
                    new_pattern.add_stitch_absolute(pyembroidery.STITCH, last_x + dx*f_val, last_y + dy*f_val)
            
            new_pattern.add_stitch_absolute(cmd, tx, ty)
            last_x, last_y = tx, ty

        pyembroidery.write(new_pattern, output_path)

        with open(output_path, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode('utf-8')

        return JSONResponse({
            "status": "success",
            "new_stitch_count": len(new_pattern.stitches),
            "colors": colors,
            "base64_file": encoded_file,
            "filename": f"scaled_{file.filename}"
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
