import unittest
import sys
import io
from mergendb.cli.completions import generate_completions

class TestCliAndCompletions(unittest.TestCase):
    def test_bash_completions(self):
        code = generate_completions("bash")
        self.assertIn("_mergen_completions", code)
        self.assertIn("complete -F", code)

    def test_zsh_completions(self):
        code = generate_completions("zsh")
        self.assertIn("#compdef mergen", code)
        self.assertIn("_mergen", code)

    def test_powershell_completions(self):
        code = generate_completions("powershell")
        self.assertIn("Register-ArgumentCompleter", code)
        self.assertIn("mergen", code)

    def test_fish_completions(self):
        code = generate_completions("fish")
        self.assertIn("complete -c mergen", code)

    def test_invalid_shell(self):
        with self.assertRaises(ValueError):
            generate_completions("unknown_shell")

if __name__ == "__main__":
    unittest.main()
