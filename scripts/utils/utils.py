""" Utils """

import os

RAW_EXTENSION_LIST = ('.yuv', '.rgb', '.raw')


def video_is_raw(videofile):
    extension = os.path.splitext(videofile)[1]
    return extension in RAW_EXTENSION_LIST


def convert_to_bps(value):
    if isinstance(value, str):
        mul = 1
        index = value.rfind('k')
        if index == -1:
            index = value.rfind('M')
            if index > 0:
                mul = 1000000
        elif index > 0:
            mul = 1000
        return int(value[0:index]) * mul
    else:
        return int(value)
