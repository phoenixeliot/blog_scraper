import os
import re
import subprocess

filenames = os.listdir(os.path.join(os.path.dirname(__file__), f"../blog_configs"))
yml_filenames = list(filter(lambda f: re.match('^[^_].*\.yml', f), filenames))

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline().decode('utf8')
        if output == '' and process.poll() is not None:
            break
        if output:
            print('  ' + output.strip())
    rc = process.poll()
    return rc

for yml_filename in yml_filenames:
    # config_name = re.match('(.*)\.yml', yml_filename)[1]

    scrape_args = [
        'python3',
        os.path.join(os.path.dirname(__file__), f"scrape.py"),
        yml_filename,
        '--format=epub,mobi',
    ]
    print(' '.join(scrape_args))
    run_command(scrape_args)

