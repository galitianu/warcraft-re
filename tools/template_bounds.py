#!/usr/bin/env python3
"""Read the oracle template bounds once through mpyq (authoring dependency only).

The committed report binds the decoded w3i/w3e fields to the exact template. CI
checks that template digest without importing mpyq. No MPQ writing is performed.
"""
import argparse
import hashlib
import struct
from check_map import read_map
from trace_contract import write_json


def bounds(path):
    raw, files = read_map(path, ('war3map.w3i', 'war3map.w3e'))
    info, terrain = files['war3map.w3i'], files['war3map.w3e']
    if struct.unpack_from('<i', info)[0] != 18:
        raise ValueError('only the retained RoC w3i format 18 is supported')
    offset = 12
    for _ in range(4):
        offset = info.index(b'\0', offset) + 1
    camera = list(struct.unpack_from('<8f', info, offset))
    left, right, bottom, top = struct.unpack_from('<4i', info, offset + 32)
    width, height = struct.unpack_from('<2i', info, offset + 48)
    if terrain[:4] != b'W3E!' or struct.unpack_from('<i', terrain, 4)[0] != 11:
        raise ValueError('unsupported terrain format')
    offset = 13  # magic, version, tileset byte, custom-tileset flag
    for _ in range(2):  # ground and cliff tile-id lists
        count, = struct.unpack_from('<i', terrain, offset)
        if not 0 <= count <= 100:
            raise ValueError('invalid tile list')
        offset += 4 + count * 4
    vertices_x, vertices_y, origin_x, origin_y = struct.unpack_from('<2i2f', terrain, offset)
    if width + left + right != vertices_x - 1 or height + bottom + top != vertices_y - 1:
        raise ValueError('w3i complements/dimensions disagree with terrain vertices')
    playable = [origin_x + left * 128, origin_x + (vertices_x - 1 - right) * 128,
                origin_y + bottom * 128, origin_y + (vertices_y - 1 - top) * 128]
    return dict(template=dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()),
                files={name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
                w3i_format=18, camera_bounds=camera,
                complements=dict(left=left, right=right, bottom=bottom, top=top),
                playable_tiles=[width, height], terrain_vertices=[vertices_x, vertices_y],
                terrain_origin=[origin_x, origin_y], tile_world_units=128,
                playable_bounds=dict(zip(('min_x', 'max_x', 'min_y', 'max_y'), playable)),
                method='terrain origin + w3i edge complements * 128; far edge from terrain vertices - 1',
                clamping='UNOBSERVED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    write_json(args.out, bounds(args.map))


if __name__ == '__main__':
    main()
