#!/usr/bin/env python
from flask import Flask, render_template, Response, request
from pyMilk.interfacing.isio_shmlib import SHM
from PIL import Image
import io
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from PIL import Image

SUCCESS = 0
FILENOTEFOUND = 1

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def gen(prefix="default"):
    shms = None
    try:
        shms = [SHM(f"{prefix}{i+1:02d}") for i in range(5)]
    except FileNotFoundError:
        print(f"No streams with prefix: {prefix}")
    if shms is None:
        yield False
    else:
        yield True
        cmap = cm.turbo
        norm = mpl.colors.Normalize()
        while True:
            ims = [shm.get_data() for shm in shms]
            ims = [im-im.min() for im in ims]
            ims = [im/im.max() for im in ims]
            im = np.concatenate(ims,axis=1)
            frame = Image.fromarray(np.uint8(cmap(norm(im))*255))
            file = io.BytesIO()
            frame.convert("RGB").save(file, format="png")
            file.seek(0)
            yield (b'--frame\r\n'
                    b'Content-Type: image/png\r\n\r\n' + file.read() + b'\r\n')

@app.route('/stream', methods=["GET"])
def stream():
    name = request.args.get("prefix")
    if name is None:
        return f"invalid request"
    response = gen(name)
    success = next(response)
    if success:
        return Response(response,
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    return f"shm stream: {name} not found"

def create_app():
    return app