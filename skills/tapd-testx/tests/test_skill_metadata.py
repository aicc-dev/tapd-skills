import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = ROOT / "skills"
SKILL_NAMES = ("tapd-base", "tapd-story", "tapd-testx")


class SkillMetadataTests(unittest.TestCase):
    def read_skill(self, directory: str) -> str:
        return (SKILLS_ROOT / directory / "SKILL.md").read_text(encoding="utf-8")

    def test_skills_live_under_standard_skills_directory(self) -> None:
        self.assertEqual(
            ["tapd-base", "tapd-story", "tapd-testx"],
            sorted(path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()),
        )

    def test_skill_names_match_installable_directories(self) -> None:
        for skill_name in SKILL_NAMES:
            with self.subTest(skill_name=skill_name):
                self.assertIn(f"name: {skill_name}", self.read_skill(skill_name))

    def test_story_and_testx_document_chain_order(self) -> None:
        story = self.read_skill("tapd-story")
        testx = self.read_skill("tapd-testx")

        self.assertIn("tapd-base", story)
        self.assertIn("tapd-base", testx)
        self.assertIn("tapd-story", testx)


if __name__ == "__main__":
    unittest.main()
