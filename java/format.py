from os import path
import subprocess
import tempfile
import logging
from typing import List

from modules import JavaExample, JavaFormatResult


class JavaFormat:
    tmp_path: str
    maven_path: str

    def __init__(self, tmp_path: str, maven_path: str):
        self.tmp_path = tmp_path
        self.maven_path = maven_path

    def build(self):
        cmd = ['mvn', '--quiet', 'package']
        logging.info('Build javaformat')
        logging.info('Command line: ' + ' '.join(cmd))
        subprocess.check_call(cmd, cwd=self.maven_path)

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
            cmd = ['java',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED',
                   '-jar', 'target/javaformat-1.0.0-beta.1-jar-with-dependencies.jar', tmp_dir_name]
            logging.info('Command line: ' + ' '.join(cmd))
            result = subprocess.run(cmd, cwd=self.maven_path)

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
