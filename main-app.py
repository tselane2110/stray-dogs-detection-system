from flask import Flask, flash, render_template, url_for, redirect, request
import torch
import filetype
import argparse, datetime
from PIL import Image
import cv2
import numpy as np
from glob import glob
from tqdm.notebook import tqdm


# cmd commands :
# 1. activate the virtual env by running the activate.ps file from the virtual/scripts folder
# 2. !git clone https://github.com/ultralytics/yolov5
# 3. cd yolov5
# 4. install the required libraries by using "pip install -r requirements.txt"

# function to check file type


def check_file_type(file_path):
    kind = filetype.guess(file_path)
    if kind is None:
        return "Cannot determine file type."
    else:
        return kind.mime


# function to apply model to a video  file


def detect_video(input_file, output_file):
    fourcc_mp4v = cv2.VideoWriter_fourcc(*"mp4v")
    # load the video capture
    cap = cv2.VideoCapture(input_file)
    # Total number of frames in video
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # height of video frame
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # width of video frame
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    # frames per second
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    out = cv2.VideoWriter(output_file, fourcc_mp4v, fps, (width, height))

    for frame in tqdm(range(n_frames), total=n_frames):
        ret, img = cap.read()
        if ret == False:
            break
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # image = Image.fromarray(img)
        return_img = model([img])

        # updates results.imgs with boxes and labels
        return_img.render()

        # converting img to an array
        image = Image.fromarray(return_img.ims[0])

        # Convert the PIL Image to a NumPy array
        image = np.array(image)

        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        out.write(image)

    out.release()
    cap.release()


app = Flask(__name__)

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"


@app.route("/")
def index():
    css_url = url_for("static", filename="css/style.css")
    js_url = url_for("static", filename="js/script.js")
    return render_template("index.html", css_url=css_url, js_url=js_url)


@app.route("/model_prediction", methods=["GET", "POST"])
def model_prediction():
    if request.method == "POST":
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if not file:
            return

        # checking file type
        file_type = check_file_type(file)[0:5]  # applied python slicing

        if file_type == "image":
            # Save the file to a desired location on the server
            filepath = "static/images/" + file.filename
            file.save(filepath)

            # reading image file and applying model on it
            img = Image.open(filepath)
            results = model([img])

            # updates results.imgs with boxes and labels
            results.render()

            # saving image
            now_time = datetime.datetime.now().strftime(DATETIME_FORMAT)
            img_savename = f"static/predicted_images/{now_time}.png"
            Image.fromarray(results.ims[0]).save(img_savename)

            # returning output
            return redirect(img_savename)

        elif file_type == "video":
            # Save the file to a desired location on the server
            filepath = "static/videos/" + file.filename
            file.save(filepath)

            predicted_filepath = "static/predicted_videos/" + file.filename

            detect_video(filepath, predicted_filepath)

            # returning output
            return redirect(predicted_filepath)


# main function

if __name__ == "__main__":
    app.jinja_env.auto_reload = True
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    parser = argparse.ArgumentParser(description="Flask app exposing yolov5 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()

    model = torch.hub.load("ultralytics/yolov5", "custom", path="best.pt")
    """model = torch.hub.load(
        "ultralytics/yolov5", "yolov5s", pretrained=True
    )  # force_reload = recache latest code"""
    model.eval()
    app.run(host="0.0.0.0", port=args.port)  # debug=True causes Restarting with stat
