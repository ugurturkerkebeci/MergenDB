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

    def test_repl_use_commands(self):
        import os, tempfile, shutil
        from mergendb.cli.repl import MergenCLI
        from mergendb.client import Table, Schema, ColumnDef, DataType

        temp_dir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            t_path = os.path.join(temp_dir, "101m.mgdb")
            sch = Schema([ColumnDef("id", DataType.INT64), ColumnDef("name", DataType.STRING)])
            tbl = Table.create(t_path, sch)
            tbl.insert([{"id": 1234, "name": "Test"}])

            cli = MergenCLI()
            cli.execute_command("USE 101m;")
            self.assertEqual(cli.active_table, "101m.mgdb")

            cli.active_table = None
            cli.execute_command("USE 101m.mgdb;")
            self.assertEqual(cli.active_table, "101m.mgdb")

            cli.active_table = None
            cli.execute_command("USE TABLE 101m;")
            self.assertEqual(cli.active_table, "101m.mgdb")

            cli.execute_command("USE DATABASE test_db;")
            self.assertEqual(cli.active_database, "test_db")
            self.assertIsNone(cli.active_table)
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_lexer_numeric_identifier(self):
        from mergendb.query.lexer import Lexer, TokenType
        tokens = Lexer("FROM 101m.mgdb | WHERE id=1234").tokenize()
        self.assertEqual(tokens[0].type, TokenType.FROM)
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].value, "101m.mgdb")
        self.assertEqual(tokens[4].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[4].value, "id")
        self.assertEqual(tokens[6].type, TokenType.INT_LITERAL)
        self.assertEqual(tokens[6].value, 1234)

if __name__ == "__main__":
    unittest.main()
