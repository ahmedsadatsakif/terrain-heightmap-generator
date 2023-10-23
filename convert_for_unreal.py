import math

from PIL import Image


def upscale_heightmap(file_name, output_size):
    src = Image.open(file_name, 'r')

    img_side = min(src.size[0], src.size[1]) / 2
    sx, sy = src.size[0]/2 - img_side, src.size[1]/2 - img_side
    ex, ey = src.size[0]/2 + img_side, src.size[1]/2 + img_side
    dest = src.resize((output_size+2, output_size+2), Image.HAMMING, box=(sx+1, sy+1, ex-1, ey-1), reducing_gap=3)

    max_val = -9999999
    min_val = 9999999
    for x in range(dest.size[0]):
        for y in range(dest.size[1]):
            max_val = max(dest.getpixel((x, y)), max_val)
            min_val = min(dest.getpixel((x, y)), min_val)

    dest = dest.convert('I')

    val_range = abs(max_val) + abs(min_val)
    print(max_val, min_val, val_range)
    for x in range(1, dest.size[0]-1):
        for y in range(1, dest.size[1]-1):
            curr_value = (dest.getpixel((x, y)) / 256.0) + \
                         (dest.getpixel((x - 1, y - 0)) / 256.0) + \
                         (dest.getpixel((x - 1, y - 1)) / 256.0) + \
                         (dest.getpixel((x - 1, y + 1)) / 256.0) + \
                         (dest.getpixel((x + 1, y + 0)) / 256.0) + \
                         (dest.getpixel((x + 1, y - 1)) / 256.0) + \
                         (dest.getpixel((x + 1, y + 1)) / 256.0) + \
                         (dest.getpixel((x + 0, y - 1)) / 256.0) + \
                         (dest.getpixel((x + 0, y + 1)) / 256.0)
            curr_value = curr_value / 9.0
            dest.putpixel((x, y), round(curr_value * 255.992))
    dest.save('montreal.png')


if __name__ == '__main__':

    inp_file = 'heightmap_converted.png'
    upscale_heightmap(inp_file, 2017)
