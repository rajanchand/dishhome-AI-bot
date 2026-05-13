"""
DishHome AI Voice Bot - Knowledge Base Service
Static knowledge about DishHome services, plans, and troubleshooting.
"""

import json
import os
from typing import Optional
from loguru import logger


class KnowledgeBase:
    """
    DishHome knowledge base for FAQ, plans, and troubleshooting.
    Data is loaded from JSON files and used to augment LLM context.
    """

    def __init__(self):
        self._faq: dict = {}
        self._troubleshooting: dict = {}
        self._loaded = False

    def load(self) -> None:
        """Load knowledge base from JSON files."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        knowledge_dir = os.path.join(base_dir, "knowledge")

        faq_path = os.path.join(knowledge_dir, "dishhome_faq.json")
        troubleshoot_path = os.path.join(knowledge_dir, "troubleshooting.json")

        try:
            if os.path.exists(faq_path):
                with open(faq_path, "r", encoding="utf-8") as f:
                    self._faq = json.load(f)
                logger.info(f"Loaded FAQ: {len(self._faq.get('faqs', []))} entries")

            if os.path.exists(troubleshoot_path):
                with open(troubleshoot_path, "r", encoding="utf-8") as f:
                    self._troubleshooting = json.load(f)
                logger.info("Loaded troubleshooting guide")

            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")

    def search_faq(self, query: str, language: str = "en") -> list[dict]:
        """Search FAQ entries matching the query."""
        if not self._loaded:
            self.load()

        results = []
        query_lower = query.lower()
        for faq in self._faq.get("faqs", []):
            keywords = faq.get("keywords", [])
            if any(kw.lower() in query_lower for kw in keywords):
                answer_key = f"answer_{language}" if f"answer_{language}" in faq else "answer_en"
                results.append({
                    "question": faq.get(f"question_{language}", faq.get("question_en", "")),
                    "answer": faq.get(answer_key, ""),
                    "category": faq.get("category", ""),
                })
        return results[:5]

    def get_troubleshooting_steps(self, issue: str, language: str = "en") -> list[str]:
        """Get troubleshooting steps for a specific issue."""
        if not self._loaded:
            self.load()

        issue_lower = issue.lower()
        for guide in self._troubleshooting.get("guides", []):
            keywords = guide.get("keywords", [])
            if any(kw.lower() in issue_lower for kw in keywords):
                steps_key = f"steps_{language}" if f"steps_{language}" in guide else "steps_en"
                return guide.get(steps_key, [])
        return []


knowledge_base = KnowledgeBase()
