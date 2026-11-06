import unittest

import torch

from moe_20b import (
    Jon2MoEForCausalLM,
    MoE20BConfig,
    default_20b_config,
    estimate_active_parameters,
    estimate_moe_parameters,
)


class Jon2MoEArchitectureTests(unittest.TestCase):
    def test_default_configuration_is_20b_class_without_instantiating_weights(self):
        config = default_20b_config()
        total = estimate_moe_parameters(config)
        active = estimate_active_parameters(config)
        self.assertGreater(total, 20_000_000_000)
        self.assertLess(total, 21_000_000_000)
        self.assertGreater(active, 3_500_000_000)
        self.assertLess(active, 3_900_000_000)
        self.assertLess(active, total)

    def test_invalid_grouped_query_dimensions_rejected(self):
        config = MoE20BConfig(
            vocab_size=64, hidden_size=32, num_layers=1,
            num_attention_heads=4, num_key_value_heads=3,
            num_experts=2, experts_per_token=1,
            expert_intermediate_size=16, max_position_embeddings=16,
        )
        with self.assertRaises(ValueError):
            config.validate()

    def test_small_model_forward_shape_and_gradients(self):
        config = MoE20BConfig(
            vocab_size=64, hidden_size=32, num_layers=2,
            num_attention_heads=4, num_key_value_heads=2,
            num_experts=4, experts_per_token=2,
            expert_intermediate_size=24, max_position_embeddings=32,
        )
        model = Jon2MoEForCausalLM(config)
        tokens = torch.randint(0, config.vocab_size, (2, 7))
        logits = model(tokens)
        self.assertEqual(tuple(logits.shape), (2, 7, config.vocab_size))
        self.assertTrue(torch.isfinite(model.router_aux_loss))
        loss = logits.float().mean() + 0.01 * model.router_aux_loss
        loss.backward()
        self.assertIsNotNone(model.layers[0].moe.router.weight.grad)
        self.assertTrue(any(
            expert.gate_proj.weight.grad is not None
            for expert in model.layers[0].moe.experts
        ))

    def test_context_limit_is_enforced(self):
        config = MoE20BConfig(
            vocab_size=32, hidden_size=16, num_layers=1,
            num_attention_heads=2, num_key_value_heads=1,
            num_experts=2, experts_per_token=1,
            expert_intermediate_size=8, max_position_embeddings=4,
        )
        model = Jon2MoEForCausalLM(config)
        with self.assertRaises(ValueError):
            model(torch.ones((1, 5), dtype=torch.long))

    def test_tied_embeddings_parameter_count_matches_module(self):
        config = MoE20BConfig(
            vocab_size=32, hidden_size=16, num_layers=1,
            num_attention_heads=2, num_key_value_heads=1,
            num_experts=2, experts_per_token=1,
            expert_intermediate_size=8, max_position_embeddings=4,
        )
        model = Jon2MoEForCausalLM(config)
        self.assertIsNone(model.lm_head)
        self.assertEqual(
            estimate_moe_parameters(config),
            sum(parameter.numel() for parameter in model.parameters()),
        )


if __name__ == "__main__":
    unittest.main()
