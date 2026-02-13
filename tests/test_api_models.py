# -*- coding: utf-8 -*-

from api.models import (
    ChoiceItem,
    CompositeArchitecture,
    ResearchRequest,
)


class TestResearchRequestNormalization:
    def test_defaults_produce_structured_config(self):
        request = ResearchRequest()

        config = request.to_research_config()

        assert config["main_algorithm"]["key"] == "adaptive"
        assert config["main_algorithm"]["name"]
        assert len(config["performance_objectives"]) >= 1
        assert config["composite_architecture"]["feedback"]["key"] == "pid"

    def test_string_inputs_are_normalized_to_known_options(self):
        request = ResearchRequest(
            main_algorithm="MPC",
            performance_objectives=["fast transient", "overshoot reduction"],
            composite_architecture="SMC + ZPETC + ESO",
            custom_topic="  precision motion control  ",
        )

        config = request.to_research_config()

        assert config["main_algorithm"]["key"] == "mpc"
        assert config["composite_architecture"]["feedback"]["key"] == "smc"
        assert config["composite_architecture"]["feedforward"]["key"] == "zpetc"
        assert config["composite_architecture"]["observer"]["key"] == "eso"
        assert config["custom_topic"] == "precision motion control"

    def test_duplicate_performance_objectives_are_deduplicated(self):
        request = ResearchRequest(
            performance_objectives=[
                ChoiceItem(key="fast_transient", name="Fast Transient Response"),
                ChoiceItem(key="fast_transient", name="Fast Transient Response"),
                "overshoot reduction",
            ]
        )

        config = request.to_research_config()
        keys = [item["key"] for item in config["performance_objectives"]]

        assert keys.count("fast_transient") == 1
        assert "overshoot_reduction" in keys

    def test_composite_architecture_object_is_supported(self):
        request = ResearchRequest(
            composite_architecture=CompositeArchitecture(
                feedback=ChoiceItem(key="lqr", name="LQR"),
                feedforward=ChoiceItem(key="preview_control", name="Preview Control"),
                observer=ChoiceItem(key="kalman", name="Kalman Filter"),
            )
        )

        config = request.to_research_config()

        assert config["composite_architecture"]["feedback"]["key"] == "lqr"
        assert config["composite_architecture"]["feedforward"]["key"] == "preview_control"
        assert config["composite_architecture"]["observer"]["key"] == "kalman"
