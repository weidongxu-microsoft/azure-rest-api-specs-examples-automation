import os
import tempfile
from os import path
import subprocess
import logging


class MavenPackage:
    tmp_path: str
    package: str
    version: str

    def __init__(self, tmp_path: str, package: str, version: str):
        self.tmp_path = tmp_path
        self.package = package
        self.version = version

    def test_example(self, java_example: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=self.tmp_path) as tmp_dir:
            maven_path = tmp_dir.name

            self.__prepare_workspace(maven_path)

            example_code_path = path.join(maven_path, 'src', 'main', 'java', 'Main.java')

            with open(example_code_path, 'w', encoding='utf-8') as f:
                f.write(java_example)

            cmd = ['mvn', '--no-transfer-progress', 'package']
            # logging.info('Run mvn package')
            # logging.info('Command line: ' + ' '.join(cmd))
            return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd=maven_path)

    def __prepare_workspace(self, maven_path: str):
        # make dir for maven and src/main/java
        java_path = path.join(maven_path, 'src', 'main', 'java')
        os.makedirs(java_path, exist_ok=True)

        # create pom
        pom_file_path = path.join(maven_path, 'pom.xml')
        pom_str = f'''<project xmlns="http://maven.apache.org/POM/4.0.0" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <modelVersion>4.0.0</modelVersion>

  <groupId>com.azure.resourcemanager</groupId>
  <artifactId>azure-resourcemanager-example</artifactId>
  <version>1.0.0-beta.1</version>
  <packaging>jar</packaging>

  <name>Example</name>
  <description>Template POM for example.</description>

  <properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
  <dependencies>
    <dependency>
      <groupId>com.azure.resourcemanager</groupId>
      <artifactId>{self.package}</artifactId>
      <version>{self.version}</version>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.8.1</version>
        <configuration>
          <release>8</release>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
'''
        with open(pom_file_path, 'w', encoding='utf-8') as f:
            f.write(pom_str)
