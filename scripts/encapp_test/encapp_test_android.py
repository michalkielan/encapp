"""Android implementation of encapp operations"""

import os
import re
import time
import datetime
import shutil

from encapp_test.encapp_test import EncappTest
from encapp_tool.app_utils import (
    APPNAME_MAIN, ACTIVITY,
    install_app, uninstall_app, install_ok)
from encapp_tool.adb_cmds import (
    run_cmd, ENCAPP_OUTPUT_FILE_NAME_RE,
    remove_files_using_regex, get_app_pid)
from utils.utils import convert_to_bps, video_is_raw

import proto.tests_pb2 as tests_definitions  # noqa: E402


class EncappTestAndroid(EncappTest):
    """Android encapp operations"""

    def __init__(self, serial, model, script_dir):
        self.serial = serial
        self.model = model
        self.script_dir = script_dir

    def remove_encapp_gen_files(self, debug=0):
        """ Remove any files that are generated in previous runs. """
        regex_str = ENCAPP_OUTPUT_FILE_NAME_RE
        location = '/sdcard/'
        remove_files_using_regex(self.serial, regex_str, location, debug)

    def abort_test(self, workdir, message):
        print('\n*** Test failed ***')
        print(message)
        shutil.rmtree(workdir)
        exit(0)

    def wait_for_exit(self, debug=0):
        pid = -1
        current = 1
        while current != -1:
            current = get_app_pid(self.serial, APPNAME_MAIN, debug)
            if current > 0:
                pid = current
            time.sleep(1)
        if pid != -1:
            print(f'Exit from {pid}')
        else:
            print(f'{APPNAME_MAIN} was not active')

    def collect_result(self, workdir, test_name):
        print(f'Collect_result: {test_name}')
        run_cmd(f'adb -s {self.serial} shell am start -W -e test '
                f'/sdcard/{test_name} {ACTIVITY}')
        self.wait_for_exit()
        adb_cmd = 'adb -s ' + self.serial + ' shell ls /sdcard/'
        ret, stdout, stderr = run_cmd(adb_cmd, True)
        output_files = re.findall(ENCAPP_OUTPUT_FILE_NAME_RE, stdout,
                                  re.MULTILINE)
        base_file_name = os.path.basename(test_name).rsplit('.run.bin', 1)[0]
        sub_dir = '_'.join([base_file_name, 'files'])
        output_dir = f'{workdir}/{sub_dir}/'
        run_cmd(f'mkdir {output_dir}')
        result_json = []
        for file in output_files:
            if file == '':
                print('No file found')
                continue
            # pull the output file
            print(f'pull {file} to {output_dir}')

            adb_cmd = f'adb -s {self.serial} pull /sdcard/{file} {output_dir}'
            run_cmd(adb_cmd)

            # remove the json file on the device too
            adb_cmd = f'adb -s {self.serial} shell rm /sdcard/{file}'
            run_cmd(adb_cmd)
            if file.endswith('.json'):
                path, tmpname = os.path.split(file)
                result_json.append(f'{output_dir}/{tmpname}')

        adb_cmd = f'adb -s {self.serial} shell rm /sdcard/{test_name}'
        run_cmd(adb_cmd)
        print(f'results collect: {result_json}')
        return result_json

    def run_codec_tests_file(self, test_def, workdir, settings):
        print(f'run test: {test_def}')
        tests = tests_definitions.Tests()
        with open(test_def, 'rb') as fd:
            tests.ParseFromString(fd.read())
        return self.run_codec_tests(tests, workdir, settings)

    def update_file_paths(self, test, new_name):
        path = test.input.filepath
        for para in test.parallel.test:
            self.update_file_paths(para, new_name)

        if path == 'camera':
            return

        if new_name is not None:
            path = new_name

        test.input.filepath = f'/sdcard/{os.path.basename(path)}'
        path = test.input.filepath

    def add_files(self, test, files_to_push):
        if test.input.filepath != 'camera':
            if not (test.input.filepath in files_to_push):
                files_to_push.append(test.input.filepath)
        for para in test.parallel.test:
            if para.input.filepath != 'camera':
                files_to_push = self.add_files(para, files_to_push)
        return files_to_push

    def run_codec_tests(self, tests, workdir, settings):
        test_def = settings['configfile']  # todo: check
        print(f'Run test: {test_def}')
        fresh = tests_definitions.Tests()
        files_to_push = []
        for test in tests.test:
            if settings['encoder'] is not None and len(settings['encoder']) > 0:
                test.configure.codec = settings['encoder']
            if (settings['inp_resolution'] is not None and
                    len(settings['inp_resolution']) > 0):
                test.input.resolution = settings['inp_resolution']
            if (settings['out_resolution'] is not None and
                    len(settings['out_resolution']) > 0):
                test.configure.resolution = settings['out_resolution']
            if settings['inp_framerate'] is not None:
                test.input.framerate = settings['inp_framerate']
            if settings['out_framerate'] is not None:
                test.configure.framerate = settings['out_framerate']

            videofile = settings['videofile']
            if videofile is not None and len(videofile) > 0:
                files_to_push.append(videofile)
                # verify video and resolution
                if not self.verify_video_size(videofile, test.input.resolution):
                    self.abort_test(workdir, 'Video size is not matching the raw '
                                    'file size')
            else:
                # check for possible parallel files
                files_to_push = self.add_files(test, files_to_push)

            self.update_file_paths(test, videofile)

            print(f'files to push: {files_to_push}')
            if settings['bitrate'] is not None and len(settings['bitrate']) > 0:
                # defult is serial calls
                split = settings['bitrate'].split('-')
                if len(split) != 3:
                    split = settings['bitrate'].split(',')
                    if len(split) != 3:
                        # Single bitrate
                        test.configure.bitrate = str(
                            convert_to_bps(settings['bitrate']))
                        fresh.test.extend([test])
                    else:
                        for bitrate in split:
                            ntest = tests_definitions.Test()
                            ntest.CopyFrom(test)
                            ntest.configure.bitrate = str(convert_to_bps(bitrate))
                            fresh.test.extend([ntest])
                else:
                    fval = convert_to_bps(split[0])
                    tval = convert_to_bps(split[1])
                    sval = convert_to_bps(split[2])
                    for bitrate in range(fval, tval, sval):
                        ntest = tests_definitions.Test()
                        ntest.CopyFrom(test)
                        ntest.configure.bitrate = str(bitrate)
                        fresh.test.extend([ntest])
            else:
                fresh.test.extend([test])

        print(fresh)
        if test_def is None:
            self.abort_test(workdir, 'ERROR: no test file name')

        test_file = os.path.basename(test_def)
        testname = f"{test_file[0:test_file.rindex('.')]}.run.bin"
        output = f'{workdir}/{testname}'
        os.system('mkdir -p ' + workdir)
        with open(output, 'wb') as binfile:
            binfile.write(fresh.SerializeToString())
            files_to_push.append(output)

        ok = True
        for filepath in files_to_push:
            if os.path.exists(filepath):
                run_cmd(f'adb -s {self.serial} push {filepath} /sdcard/')
            else:
                ok = False
                print(f'File: "{filepath}" does not exist, check path')

        if not ok:
            self.abort_test(workdir, 'Check file paths and try again')

        return self.collect_result(workdir, testname)

    def list_codecs(self, debug=0):
        adb_cmd = f'adb -s {self.serial} shell am start ' \
                  f'-e ui_hold_sec 3 ' \
                  f'-e list_codecs a {ACTIVITY}'

        run_cmd(adb_cmd, debug)
        self.wait_for_exit(debug)
        filename = f'codecs_{self.model}.txt'
        adb_cmd = f'adb -s {self.serial} pull /sdcard/codecs.txt {filename}'
        ret, stdout, stderr = run_cmd(adb_cmd, debug)
        assert ret, 'error getting codec list: "%s"' % stdout

        with open(filename, 'r') as codec_file:
            lines = codec_file.readlines()
            for line in lines:
                print(line.split('\n')[0])
            print(f'File is available in current dir as {filename}')

    def convert_test(self, path):
        output = f"{path[0:path.rindex('.')]}.bin"
        root = f"{self.script_dir[0:self.script_dir.rindex('/')]}"
        cmd = (f'protoc -I / --encode="Tests" {root}/proto/tests.proto '
               f'< {path} > {output}')
        print(f'cmd: {cmd}')
        run_cmd(cmd)
        return output

    def codec_test(self, settings):
        print(f'codec test: {settings}')
        # convert the human-friendly input into a valid apk input
        test_config = self.convert_test(settings['configfile'])

        # get date and time and format it
        now = datetime.datetime.now()
        dt_string = now.strftime('%Y-%m-%d_%H_%M')

        # get working directory at the host
        if settings['output'] is not None:
            workdir = settings['output']
        else:
            workdir = f"{settings['desc'].replace(' ', '_')}_{self.model}_{dt_string}"

        # run the codec test
        return self.run_codec_tests_file(test_config,
                                         workdir,
                                         settings)

    def install_app(self, debug):
        return install_app(self.serial, debug)

    def uninstall_app(self, debug):
        return uninstall_app(self.serial, debug)

    def install_ok(self, debug):
        return install_ok(self.serial, debug)

    def verify_video_size(videofile, resolution):
        if not os.path.exists(videofile):
            return False

        if video_is_raw(videofile):
            file_size = os.path.getsize(videofile)
            if resolution is not None:
                framesize = (int(resolution.split('x')[0]) *
                             int(resolution.split('x')[1]) * 1.5)
                if file_size % framesize == 0:
                    return True
            return False
        else:
            # in this case the actual encoded size is used.
            return True
