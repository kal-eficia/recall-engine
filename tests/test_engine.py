import unittest
from datetime import date
from pathlib import Path

from recall_engine import Attempt, Question, build_starter, interleave, load_bank, load_log, replay, six_week_review

EX = Path(__file__).resolve().parent.parent / "examples"
D = date.fromisoformat


class Boxes(unittest.TestCase):
    def test_right_answers_climb_and_wrong_resets(self):
        log = [Attempt("A", "q1", D("2026-01-01"), True), Attempt("A", "q1", D("2026-01-02"), True),
               Attempt("A", "q1", D("2026-01-05"), False)]
        s = replay(log, "A")["q1"]
        self.assertEqual((s.box, s.seen, s.wrong), (0, 3, 1))
        s2 = replay(log, "A", until=D("2026-01-02"))["q1"]
        self.assertEqual(s2.box, 2)


class Starter(unittest.TestCase):
    def setUp(self):
        self.bank, self.log = load_bank(EX / "bank.csv"), load_log(EX / "attempts.csv")

    def test_size_and_no_duplicates(self):
        picks = build_starter(self.bank, self.log, "Bilal", D("2026-11-25"), size=8, seed=1)
        ids = [p.question.id for p in picks]
        self.assertEqual(len(ids), 8)
        self.assertEqual(len(set(ids)), 8)

    def test_overdue_wrong_items_come_first_in_priority(self):
        picks = build_starter(self.bank, self.log, "Bilal", D("2026-11-25"), size=4, seed=1)
        self.assertTrue(any(p.reason == "got it wrong last time" for p in picks))

    def test_only_taught_topics_for_fresh_questions(self):
        picks = build_starter(self.bank, self.log, "Zara", D("2026-11-25"), size=10, covered_topics=["The CPU"], seed=2)
        fresh = [p for p in picks if p.reason == "not asked yet"]
        self.assertTrue(all(p.question.topic == "The CPU" for p in fresh))

    def test_interleave_avoids_neighbours(self):
        from recall_engine import Pick, ItemState
        qs = [Question(f"a{i}", "A", "q") for i in range(3)] + [Question(f"b{i}", "B", "q") for i in range(2)]
        out = interleave([Pick(q, "", ItemState()) for q in qs])
        topics = [p.question.topic for p in out]
        self.assertTrue(all(x != y for x, y in zip(topics, topics[1:])), topics)


class Review(unittest.TestCase):
    def test_review_has_baseline_for_first_topic(self):
        bank, log = load_bank(EX / "bank.csv"), load_log(EX / "attempts.csv")
        trends = {t.topic: t for t in six_week_review(bank, log, "Amir", D("2026-11-25"))}
        self.assertIsNotNone(trends["The CPU"].baseline)
        self.assertIsNotNone(trends["The CPU"].recent)


if __name__ == "__main__":
    unittest.main()
