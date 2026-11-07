"""Offline coordinate check. Does not open input devices or send input."""
import argparse
import json


def coordinates(x, y, bounds, width=1080, height=2340):
    xmin, xmax, ymin, ymax = bounds
    if xmax <= xmin or ymax <= ymin or width < 2 or height < 2:
        raise ValueError("Invalid measured ABS bounds or output dimensions")
    if not xmin <= x <= xmax or not ymin <= y <= ymax:
        raise ValueError("Touch outside measured ABS bounds")
    return round((x-xmin)*(width-1)/(xmax-xmin)), round((y-ymin)*(height-1)/(ymax-ymin))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bounds", type=int, nargs=4, required=True,
                        metavar=("XMIN", "XMAX", "YMIN", "YMAX"))
    parser.add_argument("--point", type=int, nargs=2, required=True)
    args = parser.parse_args()
    print(json.dumps({"output": "1080x2340", "rotation": 0,
                      "point": coordinates(*args.point, args.bounds),
                      "warning": "Measured axis orientation is required; identity is only a candidate"}))
