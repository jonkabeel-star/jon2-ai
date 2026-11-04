"""Tests for exact training checkpoint state and safe resume metadata."""
import argparse
import random
import sys
import tempfile
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from train_jon2 import save_checkpoint, _training_plan, restore_scheduler_state
from tokenizer import ByteBPETokenizer


class TrainingResumeTests(unittest.TestCase):
    def make_args(self):
        return argparse.Namespace(
            steps=20, batch_size=2, context=8, width=16, heads=2, layers=1,
            dropout=0.0, learning_rate=0.001, weight_decay=0.01,
            warmup_steps=2, validation_fraction=0.1, eval_steps=2,
            eval_every=2, patience=3, min_delta=0.001, grad_clip=1.0,
            minimum_chars=100_000, tokenizer_vocab_size=300,
            tokenizer_min_frequency=1, seed=42, no_amp=True,
            corpus_characters=1234,
        )

    def test_checkpoint_saves_optimizer_scheduler_scaler_and_rng(self):
        torch.manual_seed(11)
        random.seed(11)
        model = torch.nn.Linear(2, 2)
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda _: 1.0)
        loss = model(torch.ones(1, 2)).sum()
        loss.backward()
        optimizer.step()
        scheduler.step()
        scaler = torch.amp.GradScaler("cuda", enabled=False)
        tokenizer = ByteBPETokenizer.train("مرحبا Jon2", vocab_size=300, min_frequency=1)
        args = self.make_args()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.pt"
            save_checkpoint(
                path, model, tokenizer, args, 7, 1.25,
                {"width": 16, "heads": 2, "layers": 1, "context": 8, "dropout": 0.0},
                optimizer, scheduler, scaler, "abc123",
                evaluations_without_improvement=3,
            )
            state = torch.load(path, map_location="cpu", weights_only=False)

        for key in (
            "optimizer_state", "scheduler_state", "scaler_state",
            "python_rng_state", "torch_rng_state", "training_plan",
            "corpus_sha256", "evaluations_without_improvement",
        ):
            self.assertIn(key, state)
        self.assertEqual(state["training_steps"], 7)
        self.assertEqual(state["best_validation_loss"], 1.25)
        self.assertEqual(state["corpus_sha256"], "abc123")
        self.assertEqual(state["evaluations_without_improvement"], 3)
        self.assertEqual(state["training_plan"], _training_plan(args))
        self.assertTrue(state["optimizer_state"]["state"])


    def test_resume_restores_active_optimizer_learning_rate(self):
        parameter_a = torch.nn.Parameter(torch.tensor([1.0]))
        optimizer_a = torch.optim.AdamW([parameter_a], lr=0.01)
        schedule_a = torch.optim.lr_scheduler.LambdaLR(
            optimizer_a, lambda step: min(1.0, (step + 1) / 4)
        )
        optimizer_a.step()
        schedule_a.step()
        optimizer_a.step()
        schedule_a.step()
        expected_lr = optimizer_a.param_groups[0]["lr"]
        saved_scheduler = schedule_a.state_dict()

        parameter_b = torch.nn.Parameter(torch.tensor([1.0]))
        optimizer_b = torch.optim.AdamW([parameter_b], lr=0.01)
        schedule_b = torch.optim.lr_scheduler.LambdaLR(
            optimizer_b, lambda step: min(1.0, (step + 1) / 4)
        )
        self.assertNotEqual(optimizer_b.param_groups[0]["lr"], expected_lr)
        restore_scheduler_state(schedule_b, optimizer_b, saved_scheduler)
        self.assertAlmostEqual(optimizer_b.param_groups[0]["lr"], expected_lr)

    def test_training_plan_captures_schedule_and_data_constraints(self):
        args = self.make_args()
        first = _training_plan(args)
        args.steps += 1
        second = _training_plan(args)
        self.assertNotEqual(first, second)
        self.assertEqual(first["minimum_chars"], 100_000)
        self.assertEqual(first["warmup_steps"], 2)


if __name__ == "__main__":
    unittest.main()
