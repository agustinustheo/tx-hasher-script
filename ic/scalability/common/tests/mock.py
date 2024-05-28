"""A mock experiment."""
import sys
import unittest
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, Mock

import gflags

p = Path(__file__).parents[2]
sys.path.append(f"{p}/")

import common.misc as misc  # noqa
from common.base_experiment import BaseExperiment  # noqa
from common.workload_experiment import WorkloadExperiment  # noqa
from common import report  # noqa
from common.workload import Workload  # noqa
from common import ssh  # noqa

FLAGS = gflags.FLAGS
FLAGS.__delattr__("artifacts_path")
gflags.DEFINE_string("artifacts_path", "scalability/artifacts/release", "Path to the artifacts directory")


class ExperimentMock(WorkloadExperiment):
    """Logic for experiment 1."""

    def __init__(self):
        """Construct experiment 1."""
        super().__init__()
        self.install_canister("some canister")

    def run_experiment_internal(self, config):
        """Mock similar to experiment 1."""
        return self.run_workload_generator(
            self.machines,
            self.target_nodes,
            200,
            duration=60,
        )


class Test_Experiment(TestCase):
    """Implements a generic experiment with dependencies mocked away."""

    def test_verify__mock(self):
        """Test passes when the experiment runs to end."""
        sys.argv = [
            "mock.py",
            "--testnet",
            "abc",
            "--wg_testnet",
            "def",
            "--workload_generator_machines",
            "3.3.3.3,4.4.4.4",
        ]

        misc.parse_command_line_args()

        ssh.run_all_ssh_in_parallel = Mock()
        ssh.scp_in_parallel = Mock()

        # Mock functions that won't work without a proper IC deployment
        ExperimentMock._WorkloadExperiment__get_targets = Mock(return_value=["1.1.1.1", "2.2.2.2"])
        ExperimentMock._WorkloadExperiment__get_subnet_for_target = MagicMock()
        ExperimentMock.get_subnet_to_instrument = MagicMock()
        BaseExperiment._get_subnet_info = Mock(return_value="{}")
        ExperimentMock._BaseExperiment__get_topology = Mock(return_value="{}")
        ExperimentMock._BaseExperiment__store_hardware_info = MagicMock()
        ExperimentMock.get_iter_logs_from_targets = MagicMock()
        ExperimentMock.install_canister = MagicMock()
        ExperimentMock._BaseExperiment__init_metrics = MagicMock()
        ExperimentMock._WorkloadExperiment__kill_workload_generator = MagicMock()
        BaseExperiment._turn_off_replica = MagicMock()
        ExperimentMock._WorkloadExperiment__check_workload_generator_installed = Mock(return_value=True)
        ExperimentMock.get_ic_version = MagicMock(return_value="deadbeef")
        ExperimentMock._WorkloadExperiment__wait_for_quiet = MagicMock(return_value=None)
        Workload.fetch_results = Mock(return_value=[0, 0])
        report.evaluate_summaries = MagicMock()

        exp = ExperimentMock()
        exp.canister_ids = {"foorbar": ["abc"]}
        exp.run_experiment({})
        exp._BaseExperiment__init_metrics = MagicMock()
        exp._WorkloadExperiment__kill_workload_generator = MagicMock()

        exp.subnet_id = "abc"
        exp.write_summary_file("test", {"iter_duration": 300}, [], "some x value")
        exp.end_experiment()

        exp.install_canister.assert_called_once()
        Workload.fetch_results.assert_called_once()
        report.evaluate_summaries.assert_called_once()


if __name__ == "__main__":
    unittest.main()
