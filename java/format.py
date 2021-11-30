from os import path
import subprocess
import dataclasses
import tempfile
import logging


@dataclasses.dataclass(eq=True)
class CompletedJavaCode:
    returncode: int
    formatted_code: str = ''


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

    def format(self, java_example: str) -> CompletedJavaCode:
        with tempfile.TemporaryDirectory(dir=self.tmp_path) as tmp_dir_name:
            tmp_filepath = path.join(tmp_dir_name, 'tmp.java')

            with open(tmp_filepath, 'w', encoding='utf-8') as f:
                f.write(java_example)

            cmd = ['java',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED',
                   '--add-exports', 'jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED',
                   '-jar', 'target/javaformat-1.0.0-beta.1-jar-with-dependencies.jar', tmp_dir_name]
            # logging.info('Format java code')
            # logging.info('Command line: ' + ' '.join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd=self.maven_path)

            if result.returncode:
                return CompletedJavaCode(result.returncode)
            else:
                with open(tmp_filepath, encoding='utf-8') as f:
                    formatted_code = f.read()
                return CompletedJavaCode(result.returncode, formatted_code)
