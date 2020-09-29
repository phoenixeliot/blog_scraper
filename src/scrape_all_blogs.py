import os
import re
import subprocess

filenames = os.listdir(os.path.realpath(os.path.join(
    os.path.dirname(__file__), f"../blog_configs")))
yml_filenames = list(filter(lambda f: re.match('^[^_].*\.yml', f), filenames))


def run_command(command, log_filename):
    with open(log_filename, 'wb') as logfile:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            output = process.stdout.readline().decode('utf8')
            if output == '' and process.poll() is not None:
                break
            if output:
                logfile.write(output.encode('utf-8'))
                print('  ' + output.strip())

        rc = process.poll()
        return rc


for yml_filename in yml_filenames:
    filename_root = yml_filename.replace('.yml', '')
    # config_name = re.match('(.*)\.yml', yml_filename)[1]

    scrape_args = [
        'python3',
        os.path.join(os.path.dirname(__file__), f"scrape.py"),
        yml_filename,
        '--format=epub,mobi',
    ]
    print(' '.join(scrape_args))

    # TODO: Have scrape.py log its own things so scraping individual blogs does this right
    log_filename = os.path.realpath(os.path.join(
        os.path.dirname(__file__), f"../logs", f'{filename_root}.log'))
    run_command(scrape_args, log_filename)
