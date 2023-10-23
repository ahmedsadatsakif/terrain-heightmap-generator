import math
import itertools
import os.path
import urllib3
import utm
from PIL import Image



BASE_URL = 'https://tile.nextzen.org/tilezen/terrain/v1/512/terrarium/{z}/{x}/{y}.png?api_key={api}'


# Latitude: 1 deg = 110.574 km
# Longitude: 1 deg = 111.320*cos(latitude) km

def create_rectangular_bounds(c_lat, c_lng, distance_km, zoom):
    lat_dist = distance_km / 110.574
    tl_lat, br_lat = c_lat - lat_dist,  c_lat + lat_dist
    lng_dist = distance_km / (111.320 * math.cos(c_lat * math.pi / 180.))

    print(lat_dist, lng_dist)
    tl_lng, br_lng = c_lng - lng_dist, c_lng + lng_dist
    return zoom, tl_lat, tl_lng, br_lat, br_lng


def create_mercator_coords(lat, lng, zoom):
    x, y = lng * math.pi / 180, lat * math.pi / 180 # Convert to radians
    x, y = x, math.log(math.tan(0.25 * math.pi + 0.5 * y)) # Convert to mercator values
    print(x, y)
    # Transform values to tilespace
    tiles, diameter = 2 ** zoom, 2 * math.pi
    x, y = round(tiles * (x + math.pi) / diameter), round(tiles * (math.pi - y) / diameter)

    return x, y, zoom


def generate_tilelist(zoom, lat_a, lng_a, lat_b, lng_b):
    # Find min and max coords
    min_lat, min_lng = min(lat_a, lat_b), min(lng_a, lng_b)
    max_lat, max_lng = max(lat_a, lat_b), max(lng_a, lng_b)
    min_x, min_y, zoom = create_mercator_coords(max_lat, min_lng, zoom)
    max_x, max_y, zoom = create_mercator_coords(min_lat, max_lng, zoom)

    print(max_x - min_x, max_y - min_y)

    range_x = [x for x in range(min_x, max_x + 1)]
    range_y = [y for y in range(min_y, max_y + 1)]

    tiles = [(zoom, x, y) for (x, y) in itertools.product(range_x, range_y)]

    return tiles, (min_x, min_y, max_x, max_y)


def get_tile_image(request_pool, z, x, y, api):
    tile_url = BASE_URL.format(**dict(z=z, x=x, y=y, api=api))
    response = request_pool.request('GET', tile_url)
    return response.data


def create_heightmap(outd, bounds, api):
    tiles, pos = generate_tilelist(*bounds)
    http = urllib3.PoolManager()
    if not os.path.exists(outd):
        os.mkdir(outd)

    curr = 1
    for z, x, y in tiles:
        file_name ='tile_{x}_{y}_{z}.png'.format(z=z, x=x, y=y)
        file_path = os.path.join(outd, file_name)
        if os.path.exists(file_path):
            print('Skipping %s / %s as file %s already exists' % (curr, len(tiles), file_name))
            curr += 1
            continue
        print('Downloading %s / %s tiles' % (curr, len(tiles)))
        data = get_tile_image(http, z, x, y, api)
        with open(file_path, 'wb') as tile_file:
            tile_file.write(data)
        curr += 1

    return tiles, pos


def stitch_maps(tiles, pos, outdir):
    img_grid = []
    min_x, min_y, max_x, max_y = pos

    width = max_x - min_x
    height = max_y - min_y

    canvas = Image.new('RGB', (width*512, height*512), (0, 0, 0))

    for z, x, y in tiles:
        data = Image.open(
            os.path.join(outdir, 'tile_{x}_{y}_{z}.png'.format(**dict(z=z, x=x, y=y)))
        )
        img_grid.append((x-min_x, y-min_y, data))

    for x, y, img in img_grid:
        canvas.paste(img, (x*512, y*512))
    canvas.save('merged_full.png')


def extract_heightmap():
    merged = Image.open('merged_full.png', 'r')
    heightmap = Image.new('I', merged.size)
    raw_heights = []
    min_h = 99999999
    max_h = -99999999
    for x in range(merged.size[0]):
        for y in range(merged.size[1]):
            raw_color = merged.getpixel((x, y))
            color = dict()
            color['r'] = raw_color[0]
            color['g'] = raw_color[1]
            color['b'] = raw_color[2]
            if color['r'] == 0. and color['g'] == 0.:
                raw_height = -256.
            else:
                raw_height = (color['r'] * 256. + color['g'] + color['b'] / 256.) - 32768
            raw_heights.append((x, y, raw_height))
            min_h = min(min_h, raw_height)
            max_h = max(max_h, raw_height)

    print(min_h, max_h, sep='\n')
    median_h = (max_h - min_h) / (max_h + min_h)
    range_h = max_h - min_h
    print(raw_heights)
    for x, y, height in raw_heights:
        new_height = (((height - min_h)) / range_h)

        # enc_height = (height + abs(min_h)) / range_h
        if new_height > 1.0 or new_height < 0.0:
            print(new_height)
        heightmap.putpixel((x, y), round(new_height *  256. * 256.))
    heightmap.save('heightmap_converted.png')


if __name__ == '__main__':
    outdir = './collected/'



    # bounds = create_rectangular_bounds(22.651086, 92.177181, 30, 12)

    # 45.5130109012046, -73.71206133766415
    # 45.513083,-73.7120703

    bounds = create_rectangular_bounds(45.514248331889476, -73.7115938964162, 2, 17)
    print(bounds)
    # bounds = (11, 23.0317, 91.9885, 22.4313, 92.3895)
    api_key = 'random_secret_key_you_get'
    tiles, pos = create_heightmap(outdir, bounds, api_key)
    print(pos)
    stitch_maps(tiles, pos, outdir)
    extract_heightmap()
