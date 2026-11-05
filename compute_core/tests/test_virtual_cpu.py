import unittest

from compute_core.virtual_cpu import CPUError, VirtualCPU


class VirtualCPUTests(unittest.TestCase):
    def test_arithmetic_and_output(self):
        cpu = VirtualCPU()
        program = [
            ("SET", "R0", 19),
            ("SET", "R1", 23),
            ("ADD", "R2", "R0", "R1"),
            ("OUT", "R2"),
            ("HALT",),
        ]
        self.assertEqual(cpu.run(program), [42])
        self.assertEqual(cpu.registers["R2"], 42)

    def test_store_and_load(self):
        cpu = VirtualCPU()
        program = [
            ("SET", "R0", 123456),
            ("STORE", 12, "R0"),
            ("LOAD", "R1", 12),
            ("OUT", "R1"),
        ]
        self.assertEqual(cpu.run(program), [123456])

    def test_invalid_memory_address_is_rejected(self):
        cpu = VirtualCPU()
        with self.assertRaises(CPUError):
            cpu.run([("LOAD", "R0", 999999)])

    def test_instruction_limit(self):
        cpu = VirtualCPU(max_steps=5)
        with self.assertRaises(CPUError):
            cpu.run([("JMP", 0)])


if __name__ == "__main__":
    unittest.main()
