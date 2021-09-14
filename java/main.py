import sys
import concurrent
from concurrent.futures import ThreadPoolExecutor
import os
from os import path
import json
import argparse
import logging
import dataclasses
from typing import List, Dict

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
            original_file = line.strip()[len(original_file_key):].lower()
        elif line.startswith('    public static void '):
            # begin of method
            java_example_method.example_reference = original_file
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


def format_java(java_format: JavaFormat, lines: List[str], old_class_name: str, new_class_name: str) -> List[str]:
    # format example as Java code

    new_lines = []
    skip_head = True
    for line in lines:
        if not skip_head:
            # use new class name
            line = line.replace(old_class_name, new_class_name)
            new_lines.append(line)

        # remove package
        if line.startswith('package'):
            skip_head = False

    java_code = ''.join(new_lines)

    result = java_format.format(java_code)
    if result.returncode == 0:
        return result.formatted_code.splitlines(keepends=True)
    else:
        logging.error('Java code format failed')
        return new_lines


def format_markdown(doc_reference: str, lines: List[str]) -> str:
    # format markdown

    md_lines = [doc_reference + '\n',
                '\n',
                '```java\n']
    md_lines += lines
    md_lines.append('```\n')
    return ''.join(md_lines)


def process_java_example(release: Release, sdk_examples_path: str,
                         java_format: JavaFormat, maven_package: MavenPackage,
                         filepath: str):
    filename = path.basename(filepath)
    logging.info(f'Processing Java aggregated sample: {filename}')

    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

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
                example_lines = format_java(java_format, example_lines, old_class_name, new_class_name)

                # compile example
                java_example = ''.join(example_lines)
                result = maven_package.test_example(java_example)
                if result.returncode:
                    # maven package fail, skip this example
                    logging.error(f'Maven test failed, skip the example: {example_filename}')
                    logging.info('Maven log:\n' + result.stdout)
                else:
                    md_filename = example_filename.split('.')[0] + '.md'

                    # add doc reference to markdown, as guidance for user to configure project and authenticate
                    doc_link = f'https://github.com/Azure/azure-sdk-for-java/blob/{release.tag}/sdk/' \
                               f'{release.sdk_name}/{release.package}/README.md'
                    doc_reference = f'Read the [SDK documentation]({doc_link}) on how to add the SDK ' \
                                    f'to your project and authenticate.'
                    md_str = format_markdown(doc_reference, example_lines)

                    # use the examples-java folder for Java example
                    md_dir = example_dir + '-java'
                    md_dir_path = path.join(sdk_examples_path, md_dir)
                    os.makedirs(md_dir_path, exist_ok=True)

                    md_file_path = path.join(md_dir_path, md_filename)
                    with open(md_file_path, 'w', encoding='utf-8') as f:
                        f.write(md_str)
                    logging.info(f'Markdown written to file: {md_file_path}')


def create_java_examples(release: Release, sdk_examples_path: str, java_examples_path: str):
    logging.info('Preparing tools and thread pool')

    maven_package = MavenPackage(tmp_path, release.package, release.version)

    java_format = JavaFormat(tmp_path, path.join(script_path, 'javaformat'))
    java_format.build()

    logging.info(f'Processing SDK examples: {release.sdk_name}')
    with ThreadPoolExecutor(max_workers=10) as executor:
        java_paths = []
        for root, dirs, files in os.walk(java_examples_path):
            for name in files:
                filepath = path.join(root, name)
                if path.splitext(filepath)[1] == '.java':
                    java_paths.append(filepath)

        futures = []
        for filepath in java_paths:
            futures.append(executor.submit(lambda filepath1=filepath: process_java_example(
                    release, sdk_examples_path,
                    java_format, maven_package,
                    filepath1)))

        concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)
        for future in futures:
            future.result()


def main():
    global script_path
    global tmp_path

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %X')

    script_path = path.abspath(os.path.dirname(sys.argv[0]))

    parser = argparse.ArgumentParser(description='Requires 2 arguments, path of "input.json" and "output.json".')
    parser.add_argument('paths', metavar='path', type=str, nargs=2,
                        help='path of "input.json" or "output.json"')
    args = parser.parse_args()
    input_json_path = args.paths[0]
    output_json_path = args.paths[1]
    with open(input_json_path, 'r', encoding='utf-8') as fin:
        config = json.load(fin)

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

    create_java_examples(release, sdk_examples_path, java_examples_path)


if __name__ == '__main__':
    main()
