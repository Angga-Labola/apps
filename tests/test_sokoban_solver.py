import unittest
from unittest.mock import patch

import sokoban_router
import sokoban_solver


class SokobanSolverTests(unittest.TestCase):
    def test_solver_finds_a_solution(self):
        self.assertEqual(
            sokoban_solver.solve_sokoban_level("#####\n#@$.#\n#####"),
            "solvable",
        )

    def test_solver_returns_walk_and_push_sequence(self):
        self.assertEqual(
            sokoban_solver.find_sokoban_solution(
                "#######\n#@ $ .#\n#######"
            ),
            ("solvable", "rRR"),
        )

    def test_solver_proves_corner_deadlock_unsolvable(self):
        self.assertEqual(
            sokoban_solver.solve_sokoban_level("#####\n#$  #\n# .@#\n#####"),
            "unsolvable",
        )

    def test_solver_reports_unrecognized_maps_as_unknown(self):
        self.assertEqual(
            sokoban_solver.solve_sokoban_level({"name": "No map"}),
            "unknown",
        )

    def test_solver_uses_existing_letslogic_solution_counts(self):
        self.assertEqual(
            sokoban_solver.solve_sokoban_level({"blue_moves": 12}),
            "solvable",
        )

    @patch(
        "sokoban_router.get_saved_sokoban_collection",
        return_value={"levels": [{"id": 1}]},
    )
    @patch(
        "sokoban_router.find_sokoban_solution",
        return_value=("solvable", "rRR"),
    )
    def test_route_returns_selected_level_solution(self, _find_solution, _get_collection):
        self.assertEqual(
            sokoban_router.solve_saved_sokoban_level("44", 0, show_solution=True),
            {"status": "solvable", "solution": "rRR"},
        )

    @patch(
        "sokoban_router.get_saved_sokoban_collection",
        return_value={"levels": [{"id": 1}]},
    )
    @patch("sokoban_router.solve_sokoban_level", return_value="unsolvable")
    def test_route_checks_selected_level(self, solve, _get_collection):
        self.assertEqual(
            sokoban_router.solve_saved_sokoban_level("44", 0),
            {"status": "unsolvable", "solution": None},
        )
        solve.assert_called_once_with({"id": 1})


if __name__ == "__main__":
    unittest.main()
