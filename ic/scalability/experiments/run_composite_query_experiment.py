#!/usr/bin/env python3
"""
Experiment to stress ICQC.

This is using the Xnet test driver to benchmark ICQC performance.
"""
import dataclasses
import json
import os
import sys
import time

import gflags
from termcolor import colored

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common.misc as misc  # noqa
from common.icpy_stress_experiment import IcPyStressExperiment  # noqa
from common.icpy_stress_experiment import get_default_stress_configuration  # noqa

FLAGS = gflags.FLAGS

GB = 1024 * 1024 * 1024
CANISTER_MEMORY = 3.8 * GB
DEFAULT_NUM_PAGES = CANISTER_MEMORY / 4096

NUM_QUERY_THREADS_PER_CANISTER = 2

gflags.DEFINE_integer("call_graph_depth", 2, "Depth of the call graph to generate")
gflags.DEFINE_integer("call_graph_fanout", 2, "Rank of the out degree in each node")
gflags.DEFINE_boolean("dry_run", False, "Just print how many canisters would be needed")
gflags.DEFINE_boolean("duplicate_subtrees", False, "Duplicate subtrees instead of building copies.")
gflags.DEFINE_boolean("debug", False, "Create a list of message exchanges. For debugging purposes.")
gflags.DEFINE_integer("num_pages", DEFAULT_NUM_PAGES, "Number of pages to touch.")

# Configuration for load
CANISTER = "call-tree-test-canister"


class CompositeQueryExperiment(IcPyStressExperiment):
    """Logic for Icqc experiment."""

    def __init__(self):
        """Construct Icqc experiment."""
        super().__init__(False)
        super().init()
        super().init_experiment()

        self.target = self.get_machine_to_instrument()

        self.graph = self.get_topology(FLAGS.call_graph_depth)
        self.root_canister_id = self.install_canister(self.target, CANISTER)
        print("Graph is: ", self.graph)

    def get_topology(self, depth):
        """
        Returns a list of dictionaries.

        The dictionary contains itself recursively (key "subtrees") and
        a canister id indicating which canister should handle this subtree.
        """
        if depth == 0:
            return []

        if FLAGS.duplicate_subtrees:
            # Build a single subtree
            subtree = {
                "canister_id": self.install_canister(self.target, CANISTER),
                "subtrees": self.get_topology(depth - 1),
            }
            return [subtree for _ in range(FLAGS.call_graph_fanout)]
        else:
            # Build call_graph_fanout subtrees
            return [
                {"canister_id": self.install_canister(self.target, CANISTER), "subtrees": self.get_topology(depth - 1)}
                for _ in range(FLAGS.call_graph_fanout)
            ]

    def plot_call_graph(self, response):
        import pydot

        graph = pydot.Dot("call_graph", graph_type="graph")

        parsed = json.loads(response)
        import itertools

        all_cids = set(itertools.chain.from_iterable([(m["sender"], m["receiver"]) for m in parsed]))
        cid_map = {cid: uid for uid, cid in enumerate(all_cids)}
        for message in parsed:
            sender = cid_map[message["sender"]]
            receiver = cid_map[message["receiver"]]
            graph.add_edge(pydot.Edge(sender, receiver, color="blue"))

        graph.write_png("callgraph.png")

    def run_experiment_internal(self, config):
        """Run a single iteration of the Icqc benchmark and return it's metrics."""
        agent = misc.get_agent(self.target)
        arguments_as_json = json.dumps(
            {
                "calltrees": self.graph,
                "debug": False,
                "num_pages": FLAGS.num_pages,
            }
        )
        print(f"Running with {config['rps']} rps - Graph JSON is: {arguments_as_json}")

        # XXX Support multiple concurrent canister call trees w/ multiple root nodes!
        machines = self.get_machines_to_target()
        stress_configuration = dataclasses.replace(
            get_default_stress_configuration(), method="start", payload=arguments_as_json, use_updates=False
        )
        self.run_all(config["rps"], FLAGS.iter_duration, machines, self.root_canister_id, stress_configuration)

        if FLAGS.debug:
            arguments_as_json = json.dumps(
                {
                    "calltrees": self.graph,
                    "debug": True,
                    "num_pages": FLAGS.num_pages,
                }
            )
            print(f"Running debug run (with graph output: {arguments_as_json}")
            t_request_start = time.time()
            response = agent.query_raw(self.root_canister_id, "start", arguments_as_json)
            duration = time.time() - t_request_start
            print(f"Debug run took: {duration}")
            print(f"Response is: {response}")
            parsed = json.loads(response)
            print(f"Total: {len(parsed)} messages (will show only in debug mode)")

            # Plot only the last response
            self.plot_call_graph(response)


if __name__ == "__main__":

    print(
        colored(
            "Note that this benchmark currently needs to run on a system subnet. Use --targets=... to specify IPv6 address of e.g. an NNS node",
            "red",
        )
    )

    exp = CompositeQueryExperiment()
    if FLAGS.dry_run:
        import math

        total = sum([math.pow(FLAGS.call_graph_fanout, d) for d in range(FLAGS.call_graph_depth + 1)])
        print(f"#canister needed for depth={FLAGS.call_graph_depth} and fanout={FLAGS.call_graph_fanout}: {total}")
        sys.exit(0)

    exp.run_experiment({"rps": 2 * NUM_QUERY_THREADS_PER_CANISTER})
    exp.end_experiment()
