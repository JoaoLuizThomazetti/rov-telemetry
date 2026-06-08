import argparse
from roboflow import Roboflow
from ultralytics import YOLO
import shutil
from pathlib import Path


WORKSPACE = "california-state-university-east-bay-wkf0d"
PROJECT = "underwater-marine-species"
VERSION = 6


def main(api_key: str, output: str, epochs: int, batch: int):
    rf = Roboflow(api_key=api_key)
    dataset = rf.workspace(WORKSPACE).project(PROJECT).version(VERSION).download("yolov8")
    model = YOLO("yolov8n.pt")
    model.train(
        data=f"{dataset.location}/data.yaml",
        epochs=epochs,
        imgsz=640,
        batch=batch,
        workers=8,
        device=0,
    )
    best = Path("runs/detect/train/weights/best.pt")
    shutil.copy(best, output)
    print(f"Model saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", default="../marine.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch",  type=int, default=32)
    args = parser.parse_args()
    main(args.api_key, args.output, args.epochs, args.batch)
