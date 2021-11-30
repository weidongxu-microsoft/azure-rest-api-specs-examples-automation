import sys
import os
from os import path
import json
import argparse
import logging
import dataclasses
from typing import List

from modules import JavaExample, JavaFormatResult
from package import MavenPackage
from format import JavaFormat


script_path: str = '.'
tmp_path: str

namespace = 'com.azure.resourcemanager'

original_file_key = '* x-ms-original-file: '


@dataclasses.dataclass(eq=True, frozen=True)
class Release:
    tag: str
    package: str
    version: str
    sdk_name: str


@dataclasses.dataclass(eq=True)
class JavaExampleMethodContent:
    example_relative_path: str = None
    content: List[str] = None
    line_start: int = None
    line_end: int = None

    def is_valid(self) -> bool:
        return self.example_relative_path is not None


@dataclasses.dataclass(eq=True)
class AggregatedJavaExample:
    methods: List[JavaExampleMethodContent]
    class_opening: List[str] = None
    class_closing: List[str] = None


def get_sdk_name_from_package(package: str) -> str:
    if package == 'azure-resourcemanager':
        return 'resourcemanager'
    else:
        return package[len('azure-resourcemanager-'):]


def is_aggregated_java_example(lines: List[str]) -> bool:
    # check metadata to see if the sample Java is a candidate for example extraction

    for line in lines:
        if line.strip().startswith(original_file_key):
            return True
    return False


def get_java_example_method(lines: List[str], start: int) -> JavaExampleMethodContent:
    # extract one example method, start from certain line number

    original_file = None
    java_example_method = JavaExampleMethodContent()
    for index in range(len(lines)):
        if index < start:
            continue

        line = lines[index]
        if line.strip().startswith(original_file_key):
            original_file = line.strip()[len(original_file_key):]
        elif line.startswith('    public static void '):
            # begin of method
            java_example_method.example_relative_path = original_file
            java_example_method.line_start = index
        elif line.startswith('    }'):
            # end of method
            java_example_method.line_end = index + 1
            break

    if java_example_method.is_valid():
        # backtrace to include javadoc and comments before the method declaration
        for index in range(java_example_method.line_start - 1, start - 1, -1):
            line = lines[index]
            if line.strip().startswith('*') or line.strip().startswith('/*') or line.strip().startswith('*/') \
                    or line.strip().startswith('//'):
                java_example_method.line_start = index
            else:
                break
        java_example_method.content = lines[java_example_method.line_start:java_example_method.line_end]

    return java_example_method


def break_down_aggregated_java_example(lines: List[str]) -> AggregatedJavaExample:
    # break down sample Java to multiple examples

    aggregated_java_example = AggregatedJavaExample([])
    java_example_method = get_java_example_method(lines, 0)
    line_start = java_example_method.line_start
    line_end = java_example_method.line_end
    while java_example_method.is_valid():
        aggregated_java_example.methods.append(java_example_method)
        line_end = java_example_method.line_end
        java_example_method = get_java_example_method(lines, java_example_method.line_end)
    aggregated_java_example.class_opening = lines[0:line_start]
    aggregated_java_example.class_closing = lines[line_end:]
    return aggregated_java_example


def format_java(lines: List[str], old_class_name: str, new_class_name: str) -> List[str]:
    # format example as Java code

    new_lines = []
    skip_head = True
    for line in lines:
        if not skip_head:
            # use new class name
            line = line.replace('class ' + old_class_name + ' {', 'class ' + new_class_name + ' {', 1)
            new_lines.append(line)

        # remove package
        if line.startswith('package '):
            skip_head = False

    return new_lines


def format_markdown(doc_reference: str, lines: List[str]) -> str:
    # format markdown

    md_lines = [doc_reference + '\n',
                '\n',
                '```java\n']
    md_lines += lines
    md_lines.append('```\n')
    return ''.join(md_lines)


def process_java_example(filepath: str) -> List[JavaExample]:
    # process aggregated Java sample to examples

    filename = path.basename(filepath)
    logging.info(f'Processing Java aggregated sample: {filename}')

    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    java_examples = []
    if is_aggregated_java_example(lines):
        aggregated_java_example = break_down_aggregated_java_example(lines)
        for java_example_method in aggregated_java_example.methods:
            if java_example_method.is_valid():
                logging.info(f'Processing java example: {java_example_method.example_relative_path}')

                # re-construct the example class, from example method
                example_lines = aggregated_java_example.class_opening + java_example_method.content \
                    + aggregated_java_example.class_closing

                example_filepath = java_example_method.example_relative_path
                example_dir, example_filename = path.split(example_filepath)

                # use Main as class name
                old_class_name = filename.split('.')[0]
                new_class_name = 'Main'
                example_lines = format_java(example_lines, old_class_name, new_class_name)

                filename = example_filename.split('.')[0]
                # use the examples-java folder for Go example
                md_dir = (example_dir + '-java') if example_dir.endswith('/examples') \
                    else example_dir.replace('/examples/', '/examples-java/')

                java_example = JavaExample(filename, md_dir, ''.join(example_lines))
                java_examples.append(java_example)

    return java_examples


def validate_java_examples(release: Release, java_examples: List[JavaExample]) -> JavaFormatResult:
    # batch validate Java examples

    java_format = JavaFormat(tmp_path, path.join(script_path, 'javaformat'))
    java_format.build()
    java_format_result = java_format.format(java_examples)

    if java_format_result.succeeded:
        maven_package = MavenPackage(tmp_path, release.package, release.version)
        succeeded = maven_package.compile(java_examples)
        if not succeeded:
            return JavaFormatResult(False, java_format_result.examples)

    return java_format_result


def generate_markdowns(release: Release, sdk_examples_path: str, java_examples: List[JavaExample]):
    # generate markdowns from Go examples

    for java_example in java_examples:
        md_dir = java_example.target_dir
        md_filename = java_example.target_filename + '.md'

        # add doc reference to markdown, as guidance for user to configure project and authenticate
        doc_link = f'https://github.com/Azure/azure-sdk-for-java/blob/{release.tag}/sdk/' \
                   f'{release.sdk_name}/{release.package}/README.md'
        doc_reference = f'Read the [SDK documentation]({doc_link}) on how to add the SDK ' \
                        f'to your project and authenticate.'
        md_str = format_markdown(doc_reference, java_example.content.splitlines(keepends=True))

        # use the examples-java folder for Java example
        md_dir_path = path.join(sdk_examples_path, md_dir)
        os.makedirs(md_dir_path, exist_ok=True)

        md_file_path = path.join(md_dir_path, md_filename)
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(md_str)
        logging.info(f'Markdown written to file: {md_file_path}')


def create_java_examples(release: Release, sdk_examples_path: str, java_examples_path: str) -> bool:
    logging.info('Preparing tools and thread pool')

    logging.info(f'Processing SDK examples: {release.sdk_name}')
    java_examples = []
    java_paths = []
    for root, dirs, files in os.walk(java_examples_path):
        for name in files:
            filepath = path.join(root, name)
            if path.splitext(filepath)[1] == '.java':
                java_paths.append(filepath)

    for filepath in java_paths:
        java_examples += process_java_example(filepath)

    if java_examples:
        logging.info('Validating SDK examples')
        java_build_result = validate_java_examples(release, java_examples)

        if java_build_result.succeeded:
            generate_markdowns(release, sdk_examples_path, java_build_result.examples)
        else:
            logging.error('Validation failed')

        return java_build_result.succeeded
    else:
        logging.info('SDK examples not found')
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

    # specs_path = config['specsPath']
    sdk_path = config['sdkPath']
    sdk_examples_path = config['sdkExamplesPath']
    tmp_path = config['tempPath']

    release = Release(config['release']['tag'],
                      config['release']['package'],
                      config['release']['version'],
                      get_sdk_name_from_package(config['release']['package']))

    java_examples_relative_path = path.join('sdk', release.sdk_name, release.package, 'src', 'samples')
    java_examples_path = path.join(sdk_path, java_examples_relative_path)

    succeeded = create_java_examples(release, sdk_examples_path, java_examples_path)

    with open(output_json_path, 'w', encoding='utf-8') as f_out:
        group = 'com.azure.resourcemanager'
        output = {
            'status': 'succeeded' if succeeded else 'failed',
            'name': f'{group}:{release.package}:{release.version}'
        }
        json.dump(output, f_out, indent=2)


if __name__ == '__main__':
    main()
