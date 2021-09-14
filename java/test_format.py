import unittest
from os import path

from format import JavaFormat


class TestJavaFormat(unittest.TestCase):

    def test_example(self):
        maven_path = path.abspath('./javaformat')
        java_format = JavaFormat(maven_path)
        java_format.build()
        code = '''class Main {}
'''
        result = java_format.format(code)
        self.assertEqual(0, result.returncode)
        self.assertEqual('''class Main {
}
''', result.formatted_code)
