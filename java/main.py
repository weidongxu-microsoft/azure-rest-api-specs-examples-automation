import os
from os import path
import json
import argparse
import logging
import dataclasses
from typing import List, Dict

namespace = 'com.azure.resourcemanager'

operation_id_key = '* operationId: '
api_version_key = '* api-version: '
example_name_key = '* x-ms-examples: '


@dataclasses.dataclass(eq=True, frozen=True)
class Release:
    tag: str
    package: str
    version: str
    sdk_name: str


@dataclasses.dataclass(eq=True, frozen=True)
class ExampleReference:
    operation_id: str
    api_version: str
    name: str

    def is_valid(self) -> bool:
        return not (self.operation_id is None or self.api_version is None or self.name is None)


@dataclasses.dataclass(eq=True)
class JavaExampleMethodContent:
    example_reference: ExampleReference = None
    content: List[str] = None
    line_start: int = None
    line_end: int = None

    def is_valid(self) -> bool:
        return self.example_reference is not None and self.example_reference.is_valid()


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


def load_example_references(specs_path: str) -> Dict[ExampleReference, str]:
    # load example reference from specs (to be removed)

    logging.info('Loading example info from azure-rest-api-specs')
    example_references = {}
    for root, dirs, files in os.walk(path.join(specs_path, 'specification')):
        for name in files:
            json_path = path.join(root, name)
            if 'resource-manager' in json_path \
                    and path.splitext(json_path)[1] == '.json' \
                    and not path.split(json_path)[0].endswith('examples'):
                with open(json_path, 'r', encoding='utf-8') as f:
                    try:
                        swagger = json.load(f)
                        example_references.update(get_example_references(specs_path, json_path, swagger))
                    except Exception as e:
                        logging.error(f'error {e}')
    logging.info(f'Example info loaded, count: {len(example_references)}')
    return example_references


def get_example_references(specs_path: str, json_path: str, swagger: Dict) -> Dict[ExampleReference, str]:
    example_references = {}
    if 'info' in swagger and 'version' in swagger['info']:
        api_version = swagger['info']['version']
        if 'paths' in swagger:
            for request_path in swagger['paths'].values():
                for operation in request_path.values():
                    if 'operationId' in operation and 'x-ms-examples' in operation:
                        operation_id = operation['operationId'].lower()
                        for example_name, example_ref in operation['x-ms-examples'].items():
                            if '$ref' in example_ref:
                                relative_path = example_ref['$ref']
                                full_path = path.join(path.split(json_path)[0], relative_path)
                                example_ref_value = path.normpath(path.relpath(full_path, specs_path))
                                example_ref_key = ExampleReference(operation_id, api_version, example_name)
                                example_references[example_ref_key] = example_ref_value
    return example_references


def is_aggregated_java_example(lines: List[str]) -> bool:
    # check metadata to see if the sample Java is a candidate for example extraction

    operation_id = None
    api_version = None
    example_name = None
    for line in lines:
        if line.strip().startswith(operation_id_key):
            operation_id = line.strip()[len(operation_id_key):].lower()
        elif line.strip().startswith(api_version_key):
            api_version = line.strip()[len(api_version_key):]
        elif line.strip().startswith(example_name_key):
            example_name = line.strip()[len(example_name_key):]
    return operation_id is not None and api_version is not None and example_name is not None


def get_java_example_method(lines: List[str], start: int) -> JavaExampleMethodContent:
    # extract one example method, start from certain line number

    operation_id = None
    api_version = None
    example_name = None
    java_example_method = JavaExampleMethodContent()
    for index in range(len(lines)):
        if index < start:
            continue

        line = lines[index]
        if line.strip().startswith(operation_id_key):
            operation_id = line.strip()[len(operation_id_key):].lower()
        elif line.strip().startswith(api_version_key):
            api_version = line.strip()[len(api_version_key):]
        elif line.strip().startswith(example_name_key):
            example_name = line.strip()[len(example_name_key):]
        elif line.startswith('    public static void '):
            # begin of method
            java_example_method.example_reference = ExampleReference(operation_id, api_version, example_name)
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
    # format example

    new_lines = []
    skip_head = True
    for line in lines:
        if not skip_head:
            line = line.replace(old_class_name, new_class_name)
            new_lines.append(line)

        if line.startswith('package'):
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


def create_java_examples(release: Release, sdk_examples_path: str, java_examples_path: str,
                         example_references: Dict[ExampleReference, str]):
    for root, dirs, files in os.walk(java_examples_path):
        for name in files:
            filepath = path.join(root, name)
            if path.splitext(filepath)[1] == '.java':
                with open(filepath, encoding='utf-8') as f:
                    lines = f.readlines()

                logging.info(f'Processing java aggreated example: {filepath}')

                if is_aggregated_java_example(lines):
                    aggregated_java_example = break_down_aggregated_java_example(lines)
                    for java_example_method in aggregated_java_example.methods:
                        if java_example_method.example_reference not in example_references:
                            logging.warning(f'Example info not found, skip {java_example_method.example_reference.name}'
                                            f' from file: {filepath}')
                            continue

                        logging.info(f'Processing java example: {java_example_method.example_reference.name}')

                        # re-construct the example class, from example method
                        example_lines = aggregated_java_example.class_opening + java_example_method.content\
                            + aggregated_java_example.class_closing

                        example_filepath = example_references[java_example_method.example_reference]
                        example_dir, example_filename = path.split(example_filepath)

                        # use Main as class name
                        old_class_name = name.split('.')[0]
                        new_class_name = example_filename.split('.')[0]
                        md_filename = new_class_name + '.md'
                        new_class_name = 'Main'
                        example_lines = format_java(example_lines, old_class_name, new_class_name)

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


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %X')

    parser = argparse.ArgumentParser(description='Requires 2 arguments, path of "input.json" and "output.json".')
    parser.add_argument('paths', metavar='path', type=str, nargs=2,
                        help='path of "input.json" or "output.json"')
    args = parser.parse_args()
    input_json_path = args.paths[0]
    output_json_path = args.paths[1]
    with open(input_json_path, 'r', encoding='utf-8') as fin:
        config = json.load(fin)

    specs_path = config['specsPath']
    sdk_path = config['sdkPath']
    sdk_examples_path = config['sdkExamplesPath']

    release = Release(config['release']['tag'],
                      config['release']['package'],
                      config['release']['version'],
                      get_sdk_name_from_package(config['release']['package']))

    java_examples_relative_path = path.join('sdk', release.sdk_name, release.package, 'src', 'samples')
    java_examples_path = path.join(sdk_path, java_examples_relative_path)

    example_references = load_example_references(specs_path)

    create_java_examples(release, sdk_examples_path, java_examples_path, example_references)


if __name__ == '__main__':
    main()
