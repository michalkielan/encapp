#!/usr/bin/env python3

"""Python script to run ENCAPP tests on Android and collect results.
The script will create a directory based on device model and date,
and save encoded video and rate distortion results in the directory
"""

import os
import humanfriendly
import json
import sys
import argparse

from encapp_tool import __version__
from encapp_tool.app_utils import SCRIPT_DIR
from encapp_tool.adb_cmds import (
    run_cmd, get_device_info)
from encapp_test.encapp_test_android import EncappTestAndroid
from utils.utils import video_is_raw

SCRIPT_ROOT_DIR = os.path.join(SCRIPT_DIR, '..')
sys.path.append(SCRIPT_ROOT_DIR)


RD_RESULT_FILE_NAME = 'rd_results.json'

DEBUG = False

FUNC_CHOICES = {
    'help': 'show help options',
    'install': 'install apks',
    'uninstall': 'uninstall apks',
    'list': 'list codecs and devices supported',
    'run': 'run codec test case',
}

default_values = {
    'debug': 0,
    'func': 'help',
    'install': False,
    'videofile': None,
    'configfile': None,
    'encoder': None,
    'output': None,
    'bps': None,
}

extra_settings = {
    'videofile': None,
    'configfile': None,
    'encoder': None,
    'output': None,
    'bitrate': None,
    'desc': 'encapp',
    'inp_resolution': None,
    'out_resolution': None,
    'inp_framerate': None,
    'out_framerate': None,
}

OPERATION_TYPES = ('batch', 'realtime')
PIX_FMT_TYPES = ('yuv420p', 'nv12')
KNOWN_CONFIGURE_TYPES = {
    'codec': str,
    'encode': bool,
    'surface': bool,
    'mime': str,
    'bitrate': int,
    'bitrate-mode': int,
    'durationUs': int,
    'resolution': str,
    'width': int,
    'height': int,
    'color-format': int,
    'color-standard': int,
    'color-range': int,
    'color-transfer': int,
    'color-transfer-request': int,
    'frame-rate': int,
    'i-frame-interval': int,
    'intra-refresh-period': int,
    'latency': int,
    'repeat-previous-frame-after': int,
    'ts-schema': str,
}
KNOWN_RUNTIME_TYPES = {
    'video-bitrate': int,
    'request-sync': None,
    'drop': None,
    'dynamic-framerate': int,
}
TYPE_LIST = (
    'int', 'float', 'str', 'bool', 'null',
)
BITRATE_MODE_VALUES = {
    'cq': 0,
    'vbr': 1,
    'cbr': 2,
    'cbr_fd': 3,
}
FFPROBE_FIELDS = {
    'codec_name': 'codec-name',
    'width': 'width',
    'height': 'height',
    'pix_fmt': 'pix-fmt',
    'color_range': 'color-range',
    'color_space': 'color-space',
    'color_transfer': 'color-transfer',
    'color_primaries': 'color-primaries',
    'r_frame_rate': 'framerate',
    'duration': 'duration',
}
R_FRAME_RATE_MAP = {
    '30/1': 30,
}


def read_json_file(configfile, debug):
    # read input file
    with open(configfile, 'r') as fp:
        if debug > 0:
            print(f'configfile: {configfile}')
        input_config = json.load(fp)
    return input_config


def is_int(s):
    if isinstance(s, int):
        return True
    return (s[1:].isdigit() if s[0] in ('-', '+') else s.isdigit())


# convert a value (in either time or frame units) into frame units
def convert_to_frames(value, fps=30):
    if is_int(value):
        # value is already fps
        return int(value)
    # check if it can be parsed as a duration (time)
    try:
        sec = humanfriendly.parse_timespan(value)
    except humanfriendly.InvalidTimespan:
        print('error: invalid frame value "%s"' % value)
        sys.exit(-1)
    return int(sec * fps)


def get_options(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-v', '--version', action='store_true',
        dest='version', default=False,
        help='Print version',)
    parser.add_argument(
        '-d', '--debug', action='count',
        dest='debug', default=default_values['debug'],
        help='Increase verbosity (use multiple times for more)',)
    parser.add_argument(
        '--quiet', action='store_const',
        dest='debug', const=-1,
        help='Zero verbosity',)
    parser.add_argument('--serial', help='Android device serial number')
    parser.add_argument(
        '--install', action='store_const',
        dest='install', const=True,
        default=default_values['install'],
        help='Do install apk',)
    parser.add_argument(
        '--no-install', action='store_const',
        dest='install', const=False,
        help='Do not install apk',)
    parser.add_argument(
        'func', type=str, nargs='?',
        default=default_values['func'],
        choices=FUNC_CHOICES.keys(),
        metavar='%s' % (' | '.join('{}: {}'.format(k, v) for k, v in
                                   FUNC_CHOICES.items())),
        help='function arg',)
    parser.add_argument(
        '-i', type=str, dest='videofile',
        default=default_values['videofile'],
        metavar='input-video-file',
        help='input video file',)
    parser.add_argument(
        '-c', '--codec', type=str, dest='codec',
        default=default_values['encoder'],
        metavar='encoder',
        help='override encoder in config',)
    parser.add_argument(
        '-r', '--bitrate', type=str, dest='bitrate',
        default=default_values['bps'],
        metavar='input-video-bitrate',
        help='input video bitrate, either as a single number, '
        '"100 kbps" or a lst 100kbps,200kbps or a range '
        '100k-1M-100k (start-stop-step)',)
    parser.add_argument(
        'configfile', type=str, nargs='?',
        default=default_values['configfile'],
        metavar='input-config-file',
        help='input configuration file',)
    parser.add_argument(
        'output', type=str, nargs='?',
        default=default_values['output'],
        metavar='output',
        help='output dir or file',)

    options = parser.parse_args(argv[1:])
    options.desc = 'testing'
    if options.version:
        return options

    # implement help
    if options.func == 'help':
        parser.print_help()
        sys.exit(0)

    if options.serial is None and 'ANDROID_SERIAL' in os.environ:
        # read serial number from ANDROID_SERIAL env variable
        options.serial = os.environ['ANDROID_SERIAL']

    global DEBUG
    DEBUG = options.debug > 0
    return options


def parse_ffprobe_output(stdout):
    videofile_config = {}
    for line in stdout.split('\n'):
        if not line:
            # ignore empty lines
            continue
        if line in ('[STREAM]', '[/STREAM]'):
            # ignore start/end of stream
            continue
        key, value = line.split('=')
        # store interesting fields
        if key in FFPROBE_FIELDS.keys():
            # process some values
            if key == 'r_frame_rate':
                value = R_FRAME_RATE_MAP[value]
            elif key == 'width' or key == 'height':
                value = int(value)
            elif key == 'duration':
                value = float(value)
            key = FFPROBE_FIELDS[key]
            videofile_config[key] = value
    return videofile_config


def get_video_info(videofile, debug=0):
    assert os.path.exists(videofile), (
        'input video file (%s) does not exist' % videofile)
    assert os.path.isfile(videofile), (
        'input video file (%s) is not a file' % videofile)
    assert os.access(videofile, os.R_OK), (
        'input video file (%s) is not readable' % videofile)
    if video_is_raw(videofile):
        return {}
    # check using ffprobe
    cmd = f'ffprobe -v quiet -select_streams v -show_streams {videofile}'
    ret, stdout, stderr = run_cmd(cmd, debug)
    assert ret, f'error: failed to analyze file {videofile}'
    videofile_config = parse_ffprobe_output(stdout)
    videofile_config['filepath'] = videofile
    return videofile_config


def verify_app_version(json_files):
    for fl in json_files:
        with open(fl) as f:
            data = json.load(f)
            version = data['encapp_version']
            if __version__ != version:
                print(f'Warning, version missmatch between script '
                      f'({__version__}) and application ({version})')


def main(argv):
    options = get_options(argv)
    if options.version:
        print('version: %s' % __version__)
        sys.exit(0)

    videofile_config = {}
    if (options.videofile is not None and
            options.videofile != 'camera'):
        videofile_config = get_video_info(options.videofile)  # noqa: F841

    # get model and serial number
    model, serial = get_device_info(options.serial, options.debug)

    # TODO(chema): fix this
    if type(model) is dict:
        if 'model' in model:
            model = model.get('model')
        else:
            model = list(model.values())[0]
    if options.debug > 0:
        print(f'model = {model}')

    encapp_android = EncappTestAndroid(serial, model, SCRIPT_DIR)
    encapp_android.remove_encapp_gen_files(options.debug)

    # install app
    if options.func == 'install' or options.install:
        encapp_android.install_app(options.debug)

    # uninstall app
    if options.func == 'uninstall':
        encapp_android.uninstall_app(options.debug)
        sys.exit(0)

    # ensure the app is correctly installed
    assert encapp_android.install_ok(options.debug), (
        'Apps not installed in %s' % serial)

    # run function
    if options.func == 'list':
        encapp_android.list_codecs(options.debug)

    elif options.func == 'run':
        # ensure there is an input configuration
        assert options.configfile is not None, (
            'error: need a valid input configuration file')

        settings = extra_settings
        settings['configfile'] = options.configfile
        settings['videofile'] = options.videofile
        settings['encoder'] = options.codec
        settings['encoder'] = options.codec
        settings['output'] = options.output
        settings['bitrate'] = options.bitrate
        settings['desc'] = options.desc

        result = encapp_android.codec_test(settings)
        verify_app_version(result)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except AssertionError as ae:
        print(ae, file=sys.stderr)
        if DEBUG:
            raise
        sys.exit(1)
