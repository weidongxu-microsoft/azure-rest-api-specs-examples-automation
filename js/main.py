import sys
import urllib.parse
import os
from os import path
import json
import argparse
import logging
import dataclasses
from typing import List


script_path: str = '.'
tmp_path: str

original_file_key = '* x-ms-original-file: '


@dataclasses.dataclass(eq=True, frozen=True)
class Release:
    tag: str
    package: str
    version: str
    sdk_name: str


@dataclasses.dataclass(eq=True)
class JsExampleMethodContent:
    example_relative_path: str = None
    content: List[str] = None
    line_start: int = None
    line_end: int = None

    def is_valid(self) -> bool:
        return self.example_relative_path is not None


@dataclasses.dataclass(eq=True)
class AggregatedJsExample:
    methods: List[JsExampleMethodContent]
    class_opening: List[str] = None


@dataclasses.dataclass(eq=True)
class JsExample:
    target_filename: str
    target_dir: str
    content: str


def format_markdown(doc_reference: str, lines: List[str]) -> str:
    # format markdown

    md_lines = [doc_reference + '\n',
                '\n',
                '```javascript\n']
    md_lines += lines
    md_lines.append('```\n')
    return ''.join(md_lines)


def is_aggregated_js_example(lines: List[str]) -> bool:
    # check metadata to see if the sample file is a candidate for example extraction

    for line in lines:
        if line.strip().startswith(original_file_key):
            return True
    return False


def get_js_example_method(lines: List[str], start: int) -> JsExampleMethodContent:
    # extract one example method, start from certain line number

    original_file = None
    js_example_method = JsExampleMethodContent()
    for index in range(len(lines)):
        if index < start:
            continue

        line = lines[index]
        if line.strip().startswith(original_file_key):
            original_file = line.strip()[len(original_file_key):]
        elif line.startswith('async function '):
            # begin of method
            js_example_method.example_relative_path = original_file
            js_example_method.line_start = index
        elif '.catch(console.error);' in line:
            # end of method
            js_example_method.line_end = index + 1
            break

    if js_example_method.is_valid():
        # backtrace to include comments before the method declaration
        for index in range(js_example_method.line_start - 1, start - 1, -1):
            line = lines[index]
            if line.strip().startswith('*') or line.strip().startswith('/*') or line.strip().startswith('*/') \
                    or line.strip().startswith('//'):
                js_example_method.line_start = index
            else:
                break
        js_example_method.content = lines[js_example_method.line_start:js_example_method.line_end]

    return js_example_method


def break_down_aggregated_js_example(lines: List[str]) -> AggregatedJsExample:
    # break down sample Js to multiple examples

    aggregated_js_example = AggregatedJsExample([])
    js_example_method = get_js_example_method(lines, 0)
    line_start = js_example_method.line_start
    line_end = js_example_method.line_end
    while js_example_method.is_valid():
        aggregated_js_example.methods.append(js_example_method)
        line_end = js_example_method.line_end
        js_example_method = get_js_example_method(lines, js_example_method.line_end)
    aggregated_js_example.class_opening = lines[0:line_start]
    aggregated_js_example.class_closing = lines[line_end:]
    return aggregated_js_example


def format_js(lines: List[str]) -> List[str]:
    # format example as Js code

    new_lines = []
    skip_head = True
    for line in lines:
        if not skip_head:
            # use new class name
            new_lines.append(line)
        else:
            # remove comments before "require", which should be empty or comments
            if line.strip() and not (line.strip().startswith('/*') or line.strip().startswith('*')
                                     or line.strip().startswith('*/') or line.strip().startswith('//')):
                new_lines.append(line)
                skip_head = False

    return new_lines


def process_js_example(filepath: str) -> List[JsExample]:
    # process aggregated Js sample to examples

    filename = path.basename(filepath)
    logging.info(f'Processing Js aggregated sample: {filename}')

    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    js_examples = []
    if is_aggregated_js_example(lines):
        aggregated_js_example = break_down_aggregated_js_example(lines)
        for js_example_method in aggregated_js_example.methods:
            if js_example_method.is_valid():
                logging.info(f'Processing Js example: {js_example_method.example_relative_path}')

                # re-construct the example class, from example method
                example_lines = aggregated_js_example.class_opening + js_example_method.content

                example_filepath = js_example_method.example_relative_path
                example_dir, example_filename = path.split(example_filepath)

                example_lines = format_js(example_lines)

                filename = example_filename.split('.')[0]
                # use the examples-js folder for Js example
                md_dir = (example_dir + '-js') if example_dir.endswith('/examples') \
                    else example_dir.replace('/examples/', '/examples-js/')

                js_example = JsExample(filename, md_dir, ''.join(example_lines))
                js_examples.append(js_example)

    return js_examples


# def validate_go_examples(go_module: str, go_mod_filepath: str, go_examples: List[GoExample]) -> GoVetResult:
#     # batch validate Go examples
#
#     go_mod = None
#     if path.isfile(go_mod_filepath):
#         with open(go_mod_filepath, encoding='utf-8') as f:
#             go_mod = f.read()
#
#     go_vet = GoVet(tmp_path, go_module, go_mod, go_examples)
#     go_vet_result = go_vet.vet()
#
#     return go_vet_result


def generate_markdowns(release: Release, sdk_examples_path: str, js_examples: List[JsExample]):
    # generate markdowns from Js examples

    for js_example in js_examples:
        md_dir = js_example.target_dir
        md_filename = js_example.target_filename + '.md'

        # add doc reference to markdown, as guidance for user to configure project and authenticate
        escaped_release_tag = urllib.parse.quote(release.tag, safe='')
        doc_link = f'https://github.com/Azure/azure-sdk-for-js/blob/{escaped_release_tag}/' \
                   f'{get_module_relative_path(release.sdk_name)}/README.md'
        doc_reference = f'Read the [SDK documentation]({doc_link}) on how to add the SDK ' \
                        f'to your project and authenticate.'
        md_str = format_markdown(doc_reference, js_example.content.splitlines(keepends=True))

        md_dir_path = path.join(sdk_examples_path, md_dir)
        os.makedirs(md_dir_path, exist_ok=True)

        md_file_path = path.join(md_dir_path, md_filename)
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(md_str)
        logging.info(f'Markdown written to file: {md_file_path}')


def create_js_examples(release: Release,
                       js_module: str,
                       sdk_examples_path: str, js_examples_path: str) -> bool:
    js_paths = []
    for root, dirs, files in os.walk(js_examples_path):
        for name in files:
            filepath = path.join(root, name)
            if path.splitext(filepath)[1] == '.js':
                js_paths.append(filepath)

    logging.info(f'Processing SDK examples: {release.package}')
    js_examples = []
    for filepath in js_paths:
        js_examples += process_js_example(filepath)

    if js_examples:
        logging.info('Validating SDK examples')
        generate_markdowns(release, sdk_examples_path, js_examples)
        # go_vet_result = validate_go_examples(go_module, go_mod_filepath, js_examples)
        #
        # if go_vet_result.succeeded:
        #     generate_markdowns(release, sdk_examples_path, go_vet_result.examples)
        # else:
        #     logging.error('Validation failed')
        #
        # return go_vet_result.succeeded
        return True
    else:
        logging.info('SDK examples not found')
        return True


def get_module_relative_path(sdk_name: str) -> str:
    return path.join('sdk', sdk_name, 'arm-' + sdk_name)


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
                      config['release']['version'],
                      config['release']['package'][len('@azure/arm-'):])

    js_module = '{release.package}@{release.version}'
    sample_version = 'v' + release.version.split('.')[0]

    js_examples_relative_path = path.join(get_module_relative_path(release.sdk_name),
                                          'samples', sample_version, 'javascript')
    js_examples_path = path.join(sdk_path, js_examples_relative_path)

    succeeded = create_js_examples(release, js_module, sdk_examples_path, js_examples_path)

    with open(output_json_path, 'w', encoding='utf-8') as f_out:
        output = {
            'status': 'succeeded' if succeeded else 'failed',
            'name': js_module
        }
        json.dump(output, f_out, indent=2)


if __name__ == '__main__':
    main()
