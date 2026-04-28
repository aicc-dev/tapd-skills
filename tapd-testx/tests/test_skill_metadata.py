import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SkillMetadataTests(unittest.TestCase):
    def read_skill(self, directory: str) -> str:
        return (ROOT / directory / "SKILL.md").read_text(encoding="utf-8")

    def test_skills_use_aicc_tapd_namespace(self) -> None:
        self.assertIn("name: aicc-tapd:base", self.read_skill("tapd-base"))
        self.assertIn("name: aicc-tapd:story", self.read_skill("tapd-story"))
        self.assertIn("name: aicc-tapd:testx", self.read_skill("tapd-testx"))

    def test_story_and_testx_document_chain_order(self) -> None:
        story = self.read_skill("tapd-story")
        testx = self.read_skill("tapd-testx")

        self.assertIn("aicc-tapd:base", story)
        self.assertIn("aicc-tapd:base", testx)
        self.assertIn("aicc-tapd:story", testx)


if __name__ == "__main__":
    unittest.main()
