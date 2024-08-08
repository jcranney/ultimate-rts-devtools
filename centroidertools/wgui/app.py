#!/usr/bin/env python
from flask import Flask, render_template, Response, request
from pyMilk.interfacing.isio_shmlib import SHM
from PIL import Image
import io
import matplotlib as mpl
import numpy as np
from matplotlib import cm


SUCCESS = 0
FILENOTEFOUND = 1

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


def get_shm_wrapper(shm_name):
    try:
        shm = SHM(shm_name)
    except FileNotFoundError:
        return None
    return shm


def read_stacked_shms(*, prefix="", suffix=""):
    shms = []
    blank_dims = None
    for i in range(5):
        # get as many shms as there are
        shm = get_shm_wrapper(f"{prefix}{i:01d}{suffix}")
        if shm:
            shms += [shm]
            if blank_dims is None:
                blank_dims = shm.get_data().shape
    if len(shms) == 0:
        yield False
        return
    yield True
    blank_xx = np.linspace(0, 4*np.pi, blank_dims[1])[None, :]
    blank = np.cos(np.abs(blank_xx), dtype=np.float32)*np.ones(blank_dims)
    cmap = cm.turbo
    norm = mpl.colors.Normalize()
    while True:
        ims = [shm.get_data() if shm else blank for shm in shms]
        ims = [im-im.min() for im in ims]
        ims = [im/im.max() for im in ims]
        im = np.concatenate(ims, axis=1)
        frame = Image.fromarray(np.uint8(cmap(norm(im))*255))
        file = io.BytesIO()
        frame.convert("RGB").save(file, format="png")
        file.seek(0)
        yield (b'--frame\r\n'
               b'Content-Type: image/png\r\n\r\n' + file.read() + b'\r\n')


def read_single_shm(name):
    shm = get_shm_wrapper(name)
    if shm is None:
        yield False
        return
    yield True
    cmap = cm.turbo
    norm = mpl.colors.Normalize()
    while True:
        im = shm.get_data()
        im -= im.min()
        im /= im.max()
        frame = Image.fromarray(np.uint8(cmap(norm(im))*255))
        file = io.BytesIO()
        frame.convert("RGB").save(file, format="png")
        file.seek(0)
        yield (b'--frame\r\n'
               b'Content-Type: image/png\r\n\r\n' + file.read() + b'\r\n')


@app.route('/stream', methods=["GET"])
def stream():
    prefix = request.args.get("prefix")
    suffix = request.args.get("suffix")
    name = request.args.get("name")
    if name is not None:
        response = read_single_shm(name)
    else:
        if prefix is None:
            prefix = ""
        if suffix is None:
            suffix = ""
        response = read_stacked_shms(prefix=prefix, suffix=suffix)
    success = next(response)
    if success:
        return Response(
            response,
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    return "shm stream not found"


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port="7474")
