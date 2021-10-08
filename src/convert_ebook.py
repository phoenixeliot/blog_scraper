"""
Converts HTML to ebook files.
"""
import os
import subprocess

from src.read_config import read_config


def convert_ebook(config, book_base_name, output_format):
    """
    Given a config and names, generates the epub and mobi files
    """
    print("Converting...")
    convert_args = [
        "/Applications/calibre.app/Contents/MacOS/ebook-convert",
        # f'"{os.path.realpath(os.path.join(os.path.dirname(__file__), f"../books/{book_base_name}.html"))}"',
        os.path.realpath(
            os.path.join(os.path.dirname(__file__), f"../books/{book_base_name}.html")
        ),
        # f'"{os.path.realpath(os.path.join(os.path.dirname(__file__), f"../books/{book_base_name}.{output_format}"))}"',
        os.path.realpath(
            os.path.join(
                os.path.dirname(__file__), f"../books/{book_base_name}.{output_format}"
            )
        ),
        "--chapter",
        "/",
        "--page-breaks-before",
        "//*[name()='h1']", # default is "//*[name()='h1' or name()='h2']"
        "--max-toc-links",
        "194",
        "--cover",
        f'{os.path.join(os.path.dirname(__file__), "blank_cover_1x1.png")}',
    ]
    if config["book_title"]:
        convert_args += ["--title", f'{config["book_title"]}']
    if config["book_author"]:
        convert_args += ["--authors", f'{config["book_author"]}']
    if config["convert_options"]:
        convert_args += config["convert_options"]

    print(f"Running command: {convert_args}")
    run_command(convert_args)
    # subprocess.run(convert_args)
    print("Done converting.")


def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline().decode("utf8")
        if output == "" and process.poll() is not None:
            break
        if output:
            print("  " + output.strip())
    rc = process.poll()
    return rc


if __name__ == "__main__":
    convert_ebook(read_config("ward.yml"), "ward", "mobi")
