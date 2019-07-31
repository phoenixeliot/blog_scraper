import os
import subprocess

from src.read_config import read_config


def convert_ebook(config, book_base_name, output_format):
    print('Converting...')
    convert_args = [
        '/Applications/calibre.app/Contents/MacOS/ebook-convert',
        os.path.join(os.path.dirname(__file__), f"../books/{book_base_name}.html"),
        os.path.join(os.path.dirname(__file__), f"../books/{book_base_name}.{output_format}"),
        '--max-toc-links', '194',
        '--cover', os.path.join(os.path.dirname(__file__), "blank_cover_1x1.png"),
    ]
    if config['book_title']:
        convert_args += ['--title', config['book_title']]
    if config['book_author']:
        convert_args += ['--authors', config['book_author']]
    if config['convert_options']:
        convert_args += config['convert_options']

    print(' '.join(convert_args))
    run_command(convert_args)
    # subprocess.run(convert_args)
    print('Done converting.')

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

if __name__ == '__main__':
    convert_ebook(read_config('ward.yml'), 'ward', 'mobi')
