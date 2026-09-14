from copy import deepcopy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import validate_document

base = {
    "objects": {
        "title": {
            "type": "text",
            "left": "10%", "top": "10%", "width": "80%", "height": "100px",
            "fontSize": 48, "textAlign": "center", "textVerticalAlign": "middle", "textPadding": 8, "fontWeight": "700", "fontStyle": "normal",
            "letterSpacing": 1, "lineHeight": 1.2, "shapeKind": "rectangle", "opacity": 1,
            "borderWidth": 0, "borderRadius": 20, "shadowBlur": 10,
            "borderColor": "#ffffff", "shadowColor": "#000000", "fillColor": "#d9a6ad",
            "backgroundEnabled": True, "backgroundColor": "#ffffff", "backgroundOpacity": 45,
            "blendMode": "soft-light", "fillMode": "gradient", "gradientStart": "#9d4555",
            "gradientEnd": "#b58a3a", "gradientAngle": 135, "textGradientEnabled": True,
            "textGradientStart": "#9d4555", "textGradientEnd": "#e9c86e", "textGradientAngle": 90,
            "textStrokeWidth": 1.5, "textStrokeColor": "#ffffff", "textShadowBlur": 12,
            "textShadowColor": "#000000", "textTransform": "uppercase", "animation": "fade-up",
            "duration": 900, "animationDelay": 350, "rotation": 0, "imagePositionX": 50,
            "imagePositionY": 50, "imageMask": "none", "imageFrame": "none",
            "imageBrightness": 100, "imageContrast": 100, "imageSaturation": 100,
            "imageGrayscale": 0, "imageSepia": 0, "imageBlur": 0, "imageHue": 0,
            "imageFlipX": False, "imageFlipY": False,
            "visible": True, "layerName": "Hero title",
        }
    },
    "designPages": [],
    "sectionOrder": [],
    "masterPageStyle": {"enabled": False, "background": "#fffaf6", "backgroundImage": "", "backgroundSize": "cover", "backgroundOverlay": 0},
    "backgroundEffects": {"mode": "gradient", "start": "#fff8f2", "end": "#ead8d0", "angle": 135, "texture": "paper", "textureOpacity": 18},
}

validate_document(deepcopy(base))

for key, value in [("blendMode", "difference"), ("gradientAngle", 500), ("textStrokeWidth", 20), ("animationDelay", 9999), ("visible", "yes"), ("layerName", "x"*81), ("imageHue", 400), ("imageFlipX", "yes"), ("textVerticalAlign", "sideways"), ("textPadding", 100)]:
    bad = deepcopy(base)
    bad["objects"]["title"][key] = value
    try:
        validate_document(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Expected invalid {key} to be rejected")

for key, value in [("mode", "radial"), ("texture", "noise"), ("angle", 500), ("textureOpacity", 90)]:
    bad = deepcopy(base)
    bad["backgroundEffects"][key] = value
    try:
        validate_document(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Expected invalid background effect {key} to be rejected")

print("FINAL_FEATURES_TEST_PASSED")
