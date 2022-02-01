#!/usr/bin/python3
import json
import argparse
import pandas as pd
import seaborn as sb
import matplotlib.pyplot as plt
import numpy as np

# pd.options.mode.chained_assignment = 'raise'

# "id": "encapp_3d989dae-2218-43a8-a96c-c4856f362c4b",
# "description": "surface encoder",
# "date": "Mon Jul 20 15:18:35 PDT 2020",
# "proctime": 842594344696070,
# "framecount": 294,
# "encodedfile": "encapp_3d989dae-2218-43a8-a96c-c4856f362c4b.mp4",
# "settings": {
#   "codec": "video/hevc",
#   "gop": 10,
#   "fps": 30,
#   "bitrate": 2000000,
#   "meanbitrate": 1905177,
#   "width": 1280,
#   "height": 720,
#   "encmode": "BITRATE_MODE_CBR",
#   "keyrate": 10,
#   "iframepreset": "UNLIMITED",
#   "colorformat": 2135033992,
#   "colorrange": 2,
#   "colorstandard": 4,
#   "colortransfer": 3,
#   "hierplayers": 0,
#   "ltrcount": 1
# },
# "frames": [
#   {
#   "frame": 0,
#   "iframe": 1,
#   "size": 31568,
#   "pts": 66666,
#   "proctime": 74273281
#   },


def plot_framesize(data, variant, description, options):
    print('Plot frame sizes')
    fig, axs = plt.subplots(nrows=1, figsize=(12, 9), dpi=200)
    axs.legend(loc='best', fancybox=True, framealpha=0.5)
    axs.set_title('Frame sizes in bytes')

    p = sb.lineplot(x=data['pts']/1000000,
                    y='size',
                    ci='sd',
                    data=data,
                    hue=variant,
                    ax=axs)
    p.set_xlabel('Presentation time in sec')
    p.set_ylabel('Frame size in bytes')
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.suptitle(f'{options.label} - {description}')

    name = options.label + '_framesizes_' + description + '.png'
    plt.savefig(name.replace(' ', '_'), format='png')


def plot_bitrate(data, variant, description, options):
    print('Plot bitrate')
    print(f'{data}')
    fig, axs = plt.subplots(nrows=1, figsize=(12, 9), dpi=200)
    axs.legend(loc='best', fancybox=True, framealpha=0.5)
    axs.set_title('Bitrate in kbps')
    # bytes/msec = kbytes/sec
    data['target in kbps'] = ((data['bitrate']/1000).astype(int)).astype(str)
    data['kbps'] = (round(
        (8 * data['size']/(data['duration_ms'])), 0)).astype(int)
    mean = np.mean(data['kbps'])
    data['kbps'] = data['kbps'].where(data['kbps'] < mean * 20, other=0)
    print(f'mean br = {mean}')
    fps = int(np.mean(data['fps']))
    print(f'fps = {fps}')
    p = sb.lineplot(x=data['pts']/1000000,
                    y='kbps',
                    ci='sd',
                    data=data,
                    hue=variant,
                    ax=axs)
    p.set_xlabel('Presentation time in sec')
    p.set_ylabel('Bitrate in kbps')
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.suptitle(f'{options.label} - {description}')

    name = options.label + '_bitrate_' + description + '.png'
    plt.savefig(name.replace(' ', '_'), format='png')

    # vs target
    heights = np.unique(data['height'])
    for height in heights:
        fig, axs = plt.subplots(nrows=1, figsize=(12, 9), dpi=200)
        axs.legend(loc='best', fancybox=True, framealpha=0.5)
        axs.set_title(f'Bitrate in kbps as function of target, {height}p')
        filtered = data.loc[data['height'] == height]
        filtered['sm_kbps'] = filtered['kbps'].rolling(
            fps,  min_periods=1, win_type=None).sum()/fps
        p = sb.lineplot(x=filtered['pts']/1000000,
                        y='sm_kbps',
                        ci='sd',
                        data=filtered,
                        hue='target in kbps',
                        style='codec',
                        ax=axs)
        p.set_xlabel('Presentation time in sec')
        p.set_ylabel('Bitrate in kbps')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.suptitle(f'{options.label} - {description}')

        name = (options.label + f'_target-bitrate_{height}_' + description +
                '.png')
        plt.savefig(name.replace(' ', '_'), format='png')


def plot_processingtime(data, variant, description, options):
    print('Plot processing time, latency and average per frame processing')
    fig, axs = plt.subplots(nrows=1, figsize=(12, 9), dpi=200)
    p = sb.lineplot(x=data['pts']/1000000,
                    y=data['proctime']/1000000,
                    ci='sd', data=data,
                    hue=variant,
                    ax=axs)

    axs.set_title('Proc time in ms')
    axs.legend(loc='best', fancybox=True, framealpha=0.5)

    p.set_xlabel('Presentation time in sec')
    p.set_ylabel('Time in ms')
    plt.suptitle(f'{options.label} - {description}')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    name = options.label + '_proc-time_' + description + '.png'
    plt.savefig(name.replace(' ', '_'), format='png')


def plot_times(data, variant, description, options):
    print('Plot times')
    fig, axs = plt.subplots(nrows=1, figsize=(12, 9), dpi=200)
    sb.lineplot(x=data.index,
                y=data['starttime']/1000000,
                ci='sd', data=data, hue=variant,
                ax=axs)
    p = sb.lineplot(x=data.index,
                    y=data['stoptime']/1000000,
                    ci='sd', data=data, hue=variant,
                    ax=axs)

    axs.set_title('starttime vs stoptime')
    axs.legend(loc='best', fancybox=True, framealpha=0.5)

    p.set_xlabel('Presentation time in sec')
    p.set_ylabel('Time in ms')
    plt.suptitle(f'{options.label} - {description}')


def plot_concurrency(data, description, options):
    print('Plot concurrency')
    fig, axs = plt.subplots(figsize=(12, 9), dpi=200)
    data['simple'] = round(data['starttime']/1000000)
    p = sb.barplot(x=data['simple'],
                   y=data['conc'],
                   ci='sd', data=data,
                   ax=axs)

    axs.set_title('Concurrent codecs')
    axs.legend(loc='best', fancybox=True, framealpha=0.5)

    p.set_ylabel('Number codecs')
    p.set_xlabel('Start time of encoding in sec')
    plt.suptitle(f'{options.label} - {description}')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    name = options.label + '_concurrent_' + description + '.png'
    plt.savefig(name.replace(' ', '_'), format='png')


def plot_inflight_data(data, variant, description, options):
    print('Plot inflight data')
    fig, axs = plt.subplots(nrows=1, figsize=(12, 9), dpi=200)
    p = sb.lineplot(x=data['pts']/1000000,
                    y=data['inflight'],
                    ci='sd', data=data, hue=variant,
                    ax=axs)

    axs.set_title('Frames in flight')
    axs.legend(loc='best', fancybox=True, framealpha=0.5)

    p.set_ylabel('Number of frames in codec at the same time')
    p.set_xlabel('Time in sec')
    plt.suptitle(f'{options.label} - {description}')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    name = options.label + '_inflight_' + description + '.png'
    plt.savefig(name.replace(' ', '_'), format='png')

    # "gpu_model": "Adreno615v2",
    # "gpu_max_clock": "180",
    # "gpu_min_clock": "780",
    # {
    #  "time_sec": 3.7,
    #  "load_percentage": 38
    # },
    # {
    #  "time_sec": 3.8,
    #  "load_percentage": 38
    # },
    # {
    #  "time_sec": 0,
    #  "clock_MHz": "180"
    # },


def plot_gpuprocessing(gpuload, description, options):
    print('Plot gpu processing')
    maxclock = gpuload['gpu_max_clock'].values[0]
    gpumodel = gpuload['gpu_model'].values[0]

    fig, axs = plt.subplots(nrows=1, figsize=(12, 9), dpi=200)
    sb.lineplot(x=gpuload['time_sec'],
                y=gpuload['clock_perc'],
                ci='sd', data=gpuload,
                ax=axs, label=f'GPU clock percentage (max: {maxclock} MHz)')
    p = sb.lineplot(x=gpuload['time_sec'],
                    y=gpuload['load_percentage'],
                    ci='sd', data=gpuload,
                    ax=axs, label='GPU load percentage')

    p.set_xlabel('Time in sec')
    p.set_ylabel('Percentage')

    axs.set_title(f'Gpu load ({gpumodel})')
    axs.legend(loc='best', fancybox=True, framealpha=0.5)
    plt.suptitle(f'{options.label} - {description}')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    name = options.label + '_gpu-load_' + description + '.png'
    plt.savefig(name.replace(' ', '_'), format='png')


def parse_encoding_data(json, inputfile):
    print('Parse encoding data')
    try:
        data = pd.DataFrame(json['frames'])
        data['source'] = inputfile
        data['codec'] = json['settings']['codec']
        data['description'] = json['description']
        data['test'] = json['test']
        data['bitrate'] = json['settings']['bitrate']
        data['height'] = json['settings']['height']
        data['duration_ms'] = round((data['pts'].shift(-1, axis='index',
                                     fill_value=0) - data['pts']) / 1000, 2)
        data['fps'] = round(1000.0/(data['duration_ms']), 2)
        data.fillna(0)
    except Exception:
        return None
    return data


def parse_decoding_data(json, inputfile):
    print('Parse decoding data')
    decoded_data = None
    try:
        decoded_data = pd.DataFrame(json['decoded_frames'])
        decoded_data['source'] = inputfile
        if (len(decoded_data) > 0):
            try:
                decoded_data['codec'] = json['decoder_media_format']['mime']
            except Exception:
                print('Failed to read decoder data')
                decoded_data['codec'] = 'unknown codec'
            try:
                decoded_data['height'] = json['decoder_media_format']['height']
            except Exception:
                print('Failed to read decoder data')
                decoded_data['height'] = 'unknown height'

            decoded_data = decoded_data.loc[decoded_data['proctime'] >= 0]
            decoded_data.fillna(0)
    except Exception as ex:
        print(f'Filed to parse decode data for {inputfile}: {ex}')
        decoded_data = None

    return decoded_data


def parse_gpu_data(json, inputfile):
    print('Parse gpu data')
    gpu_data = None
    try:
        gpu_data = pd.DataFrame(json['gpu_data']['gpu_load_percentage'])
        if len(gpu_data) > 0:
            gpuclock_data = pd.DataFrame(json['gpu_data']['gpu_clock_freq'])
            gpu_max_clock = int(json['gpu_data']['gpu_max_clock'])
            gpu_data['clock_perc'] = (
                 100.0 * gpuclock_data['clock_MHz'].astype(float) /
                 gpu_max_clock)
            gpu_data = gpu_data.merge(gpuclock_data)
            gpu_model = json['gpu_data']['gpu_model']
            gpu_data['source'] = inputfile
            gpu_data['gpu_max_clock'] = gpu_max_clock
            gpu_data['gpu_model'] = gpu_model
            gpu_data.fillna(0)
    except Exception as ex:
        print(f'GPU parsing failed: {ex}')
        pass
    return gpu_data


def calc_infligh(frames, time_ref):
    sources = pd.unique(frames['source'])
    coding = []
    for source in sources:
        # Calculate how many frames starts encoding before a frame has finished
        # relying on the accurace of the System.nanoTime()
        inflight = []
        filtered = frames.loc[frames['source'] == source]
        start = np.min(filtered['starttime'])
        stop = np.max(filtered['stoptime'])
        # Calculate a time where the start offset (if existing) does not
        # blur the numbers
        coding.append([source, start - time_ref, stop - time_ref])
        for row in filtered.iterrows():
            start = row[1]['starttime']
            stop = row[1]['stoptime']
            intime = (filtered.loc[(filtered['stoptime'] > start) &
                                   (filtered['starttime'] < stop)])
            count = len(intime)
            inflight.append(count)
        frames.loc[frames['source'] == source, 'inflight'] = inflight

    labels = ['source', 'starttime', 'stoptime']
    concurrent = pd.DataFrame.from_records(coding, columns=labels,
                                           coerce_float=True)

    # calculate how many new encoding are started before stoptime
    inflight = []
    for row in concurrent.iterrows():
        start = row[1]['starttime']
        stop = row[1]['stoptime']
        count = (len(concurrent.loc[(concurrent['stoptime'] > start) &
                                    (concurrent['starttime'] < stop)]))
        inflight.append(count)
    concurrent['conc'] = inflight
    return frames, concurrent


def parse_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('files', nargs='+', help='file to analyze')
    parser.add_argument('--label', default='')
    parser.add_argument('-c', '--concurrency', action='store_true',
                        help='plot encodings overlapping in time')
    parser.add_argument('-pt', '--proctime', action='store_true',
                        help='plot processing time per frame for a codec')
    parser.add_argument('-br', '--bitrate', action='store_true')
    parser.add_argument('-fs', '--framesize', action='store_true')
    parser.add_argument('-if', '--inflight', action='store_true',
                        help='plot number of frames in the codec '
                             'simultanously')
    parser.add_argument('-dd', '--decode_data', action='store_true',
                        help='plot data for decoder')
    parser.add_argument('-gd', '--gpu_data', action='store_true',
                        help='plot performance data for the gpu')
    options = parser.parse_args()

    return options


def main():
    """
        Calculate stats for videos based on parsing individual frames
        with ffprobe frame parser.
        Can output data for a single file or aggregated data for several files.
    """
    options = parse_args()

    accum_data = None
    accum_dec_data = None
    accum_gpu_data = None
    pts_mult = 1000000

    for inputfile in options.files:
        if options.files == 1 and len(options.label) == 0:
            splits = inputfile.rsplit('/')
            filename = splits[len(splits)-1]
            options.label = filename

        with open(inputfile) as json_file:
            alldata = json.load(json_file)

            video_length = 0
            first_frame = 0
            last_frame = 0
            encoding_data = parse_encoding_data(alldata, inputfile)
            first_frame_start = -1
            last_frame_end = -1
            if not isinstance(encoding_data, type(None)):
                # pts is in microsec
                first_frame = np.min(encoding_data['pts'])
                # approx.
                last_frame = np.max(encoding_data['pts'])
                first_frame_start = np.min(encoding_data['starttime'])
                last_frame_end = np.max(encoding_data['stoptime'])
                video_length = (last_frame - first_frame)/pts_mult

            decoded_data = parse_decoding_data(alldata, inputfile)
            print(f'{type(decoded_data)}')
            gpu_data = parse_gpu_data(alldata, inputfile)

            proctime_sec = round((last_frame_end-first_frame_start) /
                                 1000000000.0, 2)
            framecount = alldata['framecount']

            print('__')
            print('Media = {:s}'.format(alldata['encodedfile']))
            print('Test run = {:s}'.format(alldata['test']))
            print('Description = {:s}'.format(alldata['description']))
            print('Video length = {:.2f}'.format(video_length))
            print(f'Framecount = {framecount}')
            print(f'Proctime {proctime_sec} sec')
            print(f'Total time = {proctime_sec} sec')
            print('Codec = {:s}'.format(alldata['settings']['codec']))
            print('Nitrate = {:d}'.format(alldata['settings']['bitrate']))
            print('Height = {:d}'.format(alldata['settings']['height']))
            # Mean processing incuded file reading and format changes etc.
            print('Mean processing time = {:.2f} ms'.
                  format(1000 * proctime_sec/framecount))
            if not isinstance(encoding_data, type(None)):
                # Latency is the time it takes for the
                # frame to pass the encoder
                mean_latency = np.mean(encoding_data.
                                       loc[encoding_data['proctime'] > 0,
                                           'proctime'])/1000000
                print('Mean frame latency = {:.2f} ms'.format(mean_latency))
            print('Encoding speed = {:.2f} times'.format(
                (video_length/proctime_sec)))
            print('__')

        if isinstance(accum_data, type(None)):
            accum_data = encoding_data
        elif not isinstance(encoding_data, type(None)):
            accum_data = accum_data.append(encoding_data)

        if isinstance(accum_dec_data, type(None)):
            accum_dec_data = decoded_data
        elif not isinstance(decoded_data, type(None)):
            accum_dec_data = accum_dec_data.append(decoded_data)

        if isinstance(accum_gpu_data, type(None)):
            accum_gpu_data = gpu_data
        elif not isinstance(gpu_data, type(None)):
            accum_gpu_data = accum_gpu_data.append(gpu_data)
    concurrency = None
    frames = None
    if not isinstance(encoding_data, type(None)):
        frames = accum_data.loc[accum_data['size'] > 0]
        sb.set(style='whitegrid', color_codes=True)
        # codecs = pd.unique(frames['codec'])
        # sources = pd.unique(frames['source'])
        first = np.min(frames['starttime'])

        frames, concurrency = calc_infligh(frames, first)

    if options.inflight:
        plot_inflight_data(frames, 'codec', 'encoding pipeline', options)

    if (options.concurrency and concurrency is not None and
            len(concurrency) > 1):
        plot_concurrency(concurrency, 'conc', options)

    if frames is not None:
        if options.framesize:
            plot_framesize(frames, 'test', 'encoder', options)

        if options.bitrate:
            plot_bitrate(frames, 'test', 'encoder', options)

        if options.proctime:
            plot_processingtime(frames, 'test', 'encoder', options)

    if (options.decode_data and not isinstance(accum_dec_data, type(None)) and
            len(accum_dec_data) > 0):
        first = np.min(accum_dec_data['starttime'])
        accum_dec_data, concurrency = calc_infligh(accum_dec_data, first)
        plot_inflight_data(accum_dec_data, 'codec', 'decoding pipeline',
                           options)
        plot_processingtime(accum_dec_data, 'codec', 'decoder', options)

    if (options.gpu_data and accum_gpu_data is not None and
            len(accum_gpu_data) > 0):
        plot_gpuprocessing(accum_gpu_data, 'gpu load', options)

    sb.set(style='whitegrid', color_codes=True)
    plt.show()


if __name__ == '__main__':
    main()
