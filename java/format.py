from os import path
import shutil
import platform
import subprocess
import tempfile
import logging
from typing import List

from modules import JavaExample, JavaFormatResult


OS_WINDOWS = platform.system().lower() == 'windows'


class JavaFormat:
    tmp_path: str
    maven_path: str

    def __init__(self, tmp_path: str, maven_path: str):
        self.tmp_path = tmp_path
        self.maven_path = maven_path

    def build(self):
        files = ['pom.xml', 'eclipse-format-azure-sdk-for-java.xml']
        for file in files:
            shutil.copyfile(path.join(self.maven_path, file), path.join(self.tmp_path, file))

    def format(self, examples: List[JavaExample]) -> JavaFormatResult:
        with tempfile.TemporaryDirectory(dir=self.tmp_path) as tmp_dir_name:
            filename_no = 1
            for example in examples:
                filename = 'Code' + str(filename_no) + '.java'
                filename_no += 1

                filepath = path.join(tmp_dir_name, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(example.content)

            logging.info('Format java code')
            cmd = ['mvn' + ('.cmd' if OS_WINDOWS else ''), 'spotless:apply', '-P', 'spotless']
            logging.info('Command line: ' + ' '.join(cmd))
            result = subprocess.run(cmd, cwd=self.tmp_path)

            if result.returncode:
                return JavaFormatResult(False, [])

            # read formatted examples from java files
            formatted_examples = []
            filename_no = 1
            for example in examples:
                filename = 'Code' + str(filename_no) + '.java'
                filename_no += 1

                filepath = path.join(tmp_dir_name, filename)

                with open(filepath, encoding='utf-8') as f:
                    content = f.read()
                    formatted_examples.append(JavaExample(example.target_filename, example.target_dir, content))

            return JavaFormatResult(True, formatted_examples)
