import sys
import urllib.parse
import os
from os import path
import json
import argparse
import logging
import dataclasses
from typing import List

from models import GoExample, GoVetResult
from validate import GoVet


script_path: str = '.'
tmp_path: str

original_file_key = '// x-ms-original-file: '


@dataclasses.dataclass(eq=True, frozen=True)
class Release:
    tag: str
    package: str
    version: str


@dataclasses.dataclass(eq=True)
class GoExampleMethodContent:
    example_relative_path: str = None
    content: List[str] = None
    line_start: int = None
    line_end: int = None

    def is_valid(self) -> bool:
        return self.example_relative_path is not None


@dataclasses.dataclass(eq=True)
class AggregatedGoExample:
    methods: List[GoExampleMethodContent]
    class_opening: List[str] = None


def format_markdown(doc_reference: str, lines: List[str]) -> str:
    # format markdown

    md_lines = [doc_reference + '\n',
                '\n',
                '```go\n']
    md_lines += lines
    md_lines.append('```\n')
    return ''.join(md_lines)


def is_aggregated_go_example(lines: List[str]) -> bool:
    # check metadata to see if the sample file is a candidate for example extraction

    for line in lines:
        if line.strip().startswith(original_file_key):
            return True
    return False


def get_go_example_method(lines: List[str], start: int) -> GoExampleMethodContent:
    # extract one example method, start from certain line number

    original_file = None
    go_example_method = GoExampleMethodContent()
    for index in range(len(lines)):
        if index < start:
            continue

        line = lines[index]
        if line.strip().startswith(original_file_key):
            original_file = line.strip()[len(original_file_key):]
        elif line.startswith('func '):
            # begin of method
            go_example_method.example_relative_path = original_file
            go_example_method.line_start = index
        elif line.startswith('}'):
            # end of method
            go_example_method.line_end = index + 1
            break

    if go_example_method.is_valid():
        # backtrace to include comments before the method declaration
        for index in range(go_example_method.line_start - 1, start - 1, -1):
            line = lines[index]
            if line.strip().startswith('//'):
                go_example_method.line_start = index
            else:
                break
        go_example_method.content = lines[go_example_method.line_start:go_example_method.line_end]

    return go_example_method


def break_down_aggregated_go_example(lines: List[str]) -> AggregatedGoExample:
    # break down sample Go to multiple examples

    aggregated_go_example = AggregatedGoExample([])
    go_example_method = get_go_example_method(lines, 0)
    line_start = go_example_method.line_start
    line_end = go_example_method.line_end
    while go_example_method.is_valid():
        aggregated_go_example.methods.append(go_example_method)
        line_end = go_example_method.line_end
        go_example_method = get_go_example_method(lines, go_example_method.line_end)
    aggregated_go_example.class_opening = lines[0:line_start]
    aggregated_go_example.class_closing = lines[line_end:]
    return aggregated_go_example


def format_go(lines: List[str]) -> List[str]:
    # format example as Go code

    new_lines = []
    skip_head = True
    for line in lines:
        if not skip_head:
            # use new class name
            new_lines.append(line)

        # remove package
        if line.startswith('package'):
            new_lines.append(line)
            skip_head = False

    return new_lines


def process_go_example(release: Release, sdk_examples_path: str, filepath: str) -> List[GoExample]:
    # process aggregated Go sample to examples

    filename = path.basename(filepath)
    logging.info(f'Processing Go aggregated sample: {filename}')

    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    go_examples = []
    if is_aggregated_go_example(lines):
        aggregated_go_example = break_down_aggregated_go_example(lines)
        for go_example_method in aggregated_go_example.methods:
            if go_example_method.is_valid():
                logging.info(f'Processing go example: {go_example_method.example_relative_path}')

                # re-construct the example class, from example method
                example_lines = aggregated_go_example.class_opening + go_example_method.content

                example_filepath = go_example_method.example_relative_path
                example_dir, example_filename = path.split(example_filepath)

                example_lines = format_go(example_lines)

                filename = example_filename.split('.')[0]
                # use the examples-go folder for Go example
                md_dir = (example_dir + '-go') if example_dir.endswith('/examples') \
                    else example_dir.replace('/examples/', '/examples-go/')

                go_example = GoExample(filename, md_dir, ''.join(example_lines))
                go_examples.append(go_example)

    return go_examples


def validate_go_examples(go_module: str, go_mod_filepath: str, go_examples: List[GoExample]) -> GoVetResult:
    # batch validate Go examples

    go_mod = None
    if path.isfile(go_mod_filepath):
        with open(go_mod_filepath, encoding='utf-8') as f:
            go_mod = f.read()

    go_vet = GoVet(tmp_path, go_module, go_mod, go_examples)
    go_vet_result = go_vet.vet()

    return go_vet_result


def generate_markdowns(release: Release, sdk_examples_path: str, go_examples: List[GoExample]):
    # generate markdowns from Go examples

    for go_example in go_examples:
        md_dir = go_example.target_dir
        md_filename = go_example.target_filename + '.md'

        # add doc reference to markdown, as guidance for user to configure project and authenticate
        escaped_release_tag = urllib.parse.quote(release.tag, safe='')
        doc_link = f'https://github.com/Azure/azure-sdk-for-go/blob/{escaped_release_tag}/' \
                   f'{release.package}/README.md'
        doc_reference = f'Read the [SDK documentation]({doc_link}) on how to add the SDK ' \
                        f'to your project and authenticate.'
        md_str = format_markdown(doc_reference, go_example.content.splitlines(keepends=True))

        md_dir_path = path.join(sdk_examples_path, md_dir)
        os.makedirs(md_dir_path, exist_ok=True)

        md_file_path = path.join(md_dir_path, md_filename)
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(md_str)
        logging.info(f'Markdown written to file: {md_file_path}')


def create_go_examples(release: Release,
                       go_module: str, go_mod_filepath: str,
                       sdk_examples_path: str, go_examples_path: str) -> bool:
    go_paths = []
    for root, dirs, files in os.walk(go_examples_path):
        for name in files:
            filepath = path.join(root, name)
            if path.splitext(filepath)[1] == '.go' and filepath.endswith('_test.go'):
                go_paths.append(filepath)

    go_examples = []
    for filepath in go_paths:
        go_examples += process_go_example(release, sdk_examples_path, filepath)

    if go_examples:
        go_vet_result = validate_go_examples(go_module, go_mod_filepath, go_examples)

        if go_vet_result.succeeded:
            generate_markdowns(release, sdk_examples_path, go_vet_result.examples)

        return go_vet_result.succeeded
    else:
        # examples not found
        return True


def main():
    global script_path
    global tmp_path

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %X')

    script_path = path.abspath(path.dirname(sys.argv[0]))

    parser = argparse.ArgumentParser(description='Requires 2 arguments, path of "input.json" and "output.json".')
    parser.add_argument('paths', metavar='path', type=str, nargs=2,
                        help='path of "input.json" or "output.json"')
    args = parser.parse_args()
    input_json_path = args.paths[0]
    output_json_path = args.paths[1]
    with open(input_json_path, 'r', encoding='utf-8') as f_in:
        config = json.load(f_in)

    sdk_path = config['sdkPath']
    sdk_examples_path = config['sdkExamplesPath']
    tmp_path = config['tempPath']

    release = Release(config['release']['tag'],
                      config['release']['package'],
                      config['release']['version'])

    go_module = f'github.com/Azure/azure-sdk-for-go/{release.package}@{release.version}'

    go_examples_relative_path = release.package
    go_examples_path = path.join(sdk_path, go_examples_relative_path)
    go_mod_filepath = path.join(sdk_path, release.package, 'go.mod')

    succeeded = create_go_examples(release, go_module, go_mod_filepath, sdk_examples_path, go_examples_path)

    with open(output_json_path, 'w', encoding='utf-8') as f_out:
        output = {
            'status': 'succeeded' if succeeded else 'failed',
            'name': go_module
        }
        json.dump(output, f_out, indent=2)


if __name__ == '__main__':
    main()
