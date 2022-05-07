import unittest
from os import path

from validate import GoVet
from models import GoExample


class TestGoVet(unittest.TestCase):

    def test_example(self):
        code = '''package main
import "fmt"
func main() {
    fmt.Println("hello world")
}
'''

        tmp_path = path.abspath('.')
        go_examples = [GoExample('code', '', code)]
        go_vet = GoVet(tmp_path, 'rsc.io/quote@v1.5.2', '', go_examples)
        result = go_vet.vet()
        self.assertTrue(result.succeeded)
