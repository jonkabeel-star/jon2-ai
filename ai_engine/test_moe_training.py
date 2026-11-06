import tempfile, unittest
from pathlib import Path
try:
    import torch
except ImportError:
    torch = None
if torch is not None:
    from moe_20b import Jon2MoEForCausalLM, MoE20BConfig
    from moe_training import causal_lm_objective, load_training_checkpoint, save_training_checkpoint, train_microbatch, validate_20b_training_hardware, validate_corpus_scale

@unittest.skipIf(torch is None, "PyTorch is unavailable")
class MoETrainingTests(unittest.TestCase):
    def setUp(self):
        config = MoE20BConfig(vocab_size=48, hidden_size=24, num_layers=1, num_attention_heads=3, num_key_value_heads=1, num_experts=3, experts_per_token=2, expert_intermediate_size=16, max_position_embeddings=16)
        self.model = Jon2MoEForCausalLM(config)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=1e-3)
        self.config = {"test": True, "vocab_size": 48}
        self.corpus_hash, self.tokenizer_hash = "a" * 64, "b" * 64
    def test_corpus_scale_gate(self):
        with self.assertRaises(ValueError):
            validate_corpus_scale(100, 1000, 10)
        self.assertEqual(validate_corpus_scale(10000, 1000, 10), 10)
    def test_objective_includes_router_auxiliary_loss(self):
        loss, metrics = causal_lm_objective(self.model, torch.randint(0, 48, (2, 8)))
        self.assertTrue(torch.isfinite(loss))
        self.assertGreaterEqual(metrics["router_aux_loss"], 0)
    def test_optimizer_step_changes_weights(self):
        tokens = torch.randint(0, 48, (2, 8))
        before = self.model.embed_tokens.weight.detach().clone()
        metrics = train_microbatch(self.model, self.optimizer, tokens)
        self.assertTrue(torch.isfinite(torch.tensor(metrics["total_loss"])))
        self.assertFalse(torch.equal(before, self.model.embed_tokens.weight))
    def test_checkpoint_round_trip_and_hash_gate(self):
        train_microbatch(self.model, self.optimizer, torch.randint(0, 48, (2, 8)))
        expected = {k: v.detach().clone() for k, v in self.model.state_dict().items()}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.pt"
            digest = save_training_checkpoint(path, model=self.model, optimizer=self.optimizer, step=7, config=self.config, corpus_sha256=self.corpus_hash, tokenizer_sha256=self.tokenizer_hash, tokens_seen=1234)
            self.assertEqual(len(digest), 64)
            with torch.no_grad():
                for parameter in self.model.parameters():
                    parameter.zero_()
            meta = load_training_checkpoint(path, model=self.model, optimizer=self.optimizer, expected_config=self.config, corpus_sha256=self.corpus_hash, tokenizer_sha256=self.tokenizer_hash)
            self.assertEqual(meta, {"step": 7, "tokens_seen": 1234})
            for key, value in self.model.state_dict().items():
                self.assertTrue(torch.equal(value, expected[key]))
            with self.assertRaises(ValueError):
                load_training_checkpoint(path, model=self.model, optimizer=self.optimizer, expected_config=self.config, corpus_sha256="c" * 64, tokenizer_sha256=self.tokenizer_hash)
    def test_missing_cuda_rejected_by_hardware_gate(self):
        if not torch.cuda.is_available():
            with self.assertRaises(RuntimeError):
                validate_20b_training_hardware()

if __name__ == "__main__":
    unittest.main()
