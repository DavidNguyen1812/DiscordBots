import os
from PIL import Image, ImageSequence


GifDirectory = "/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/DavidKnights/KnightSamson/PythonScripts/Cooked"
gif_name = "BigBoyRugby"
if os.listdir(GifDirectory):
    GifFrames = []
    for dirpath, dirnames, filenames in os.walk(GifDirectory):
        for filename in filenames:
            framepath = os.path.join(dirpath, filename)
            GifFrames.append(framepath)
    GifFrames.sort()
    print(GifFrames)
    NewResizeFrames = []
    for frame in GifFrames:
        img = Image.open(frame)
        img = img.convert("RGBA")
        resized = img.resize(size=(int(img.width * 0.25), int(img.height * 0.25)))
        NewResizeFrames.append(resized)

    NewResizeFrames[0].save(
        f'{GifDirectory}/{gif_name}.gif',
        save_all=True,
        append_images=NewResizeFrames[1:],
        optimize=True,
        duration=100,
        loop=0,
        disposal=2
    )