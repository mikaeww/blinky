import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from blinky.session import project  # noqa: E402


class ProjectNameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def repo(self, folder, origin=None):
        git = self.root / folder / ".git"
        git.mkdir(parents=True)
        config = "[core]\n\tbare = false\n"
        if origin:
            config += f'[remote "origin"]\n\turl = {origin}\n'
        (git / "config").write_text(config)
        return self.root / folder

    def test_origin_name_wins_over_folder_name(self):
        for i, url in enumerate(("git@github.com:example/demo-project.git", "https://github.com/example/demo-project",
                    "https://github.com/example/demo-project.git/")):
            with self.subTest(url=url):
                root = self.repo(f"v2-{i}", url)
                (root / "src" / "deep").mkdir(parents=True)
                self.assertEqual(project.name_for(str(root / "src" / "deep")), "demo-project")

    def test_repo_without_origin_uses_repo_folder(self):
        root = self.repo("rewa")
        (root / "crates").mkdir()
        self.assertEqual(project.name_for(str(root / "crates")), "rewa")

    def test_worktree_follows_gitdir_file(self):
        main = self.repo("main", "git@github.com:me/leech.git")
        worktree_git = main / ".git" / "worktrees" / "feature"
        worktree_git.mkdir(parents=True)
        (worktree_git / "commondir").write_text("../..\n")
        tree = self.root / "feature-tree"
        tree.mkdir()
        (tree / ".git").write_text(f"gitdir: {worktree_git}\n")
        self.assertEqual(project.name_for(str(tree)), "leech")

    def test_plain_folder_and_missing_folder(self):
        plain = self.root / "notes"
        plain.mkdir()
        self.assertEqual(project.name_for(str(plain)), "notes")
        self.assertEqual(project.name_for(str(self.root / "gone" / "away")), "away")


if __name__ == "__main__":
    unittest.main()
