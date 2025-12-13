#!/usr/bin/env python3
"""
Launch a Gradio demo that showcases surrogate model inference speed.

Frontend is intentionally kept separate from backend logic (see src/demo/backend.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import gradio as gr
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.demo import SurrogateDemoBackend  # pylint: disable=wrong-import-position


backend = SurrogateDemoBackend()
PRODUCT_CHOICES = backend.product_choices
DEFAULT_PRODUCT = PRODUCT_CHOICES[0] if PRODUCT_CHOICES else ""


def _format_predictions(row: dict) -> dict:
    return {
        "product_id": row.get("product_id"),
        "realized_demand": round(row.get("realized_demand", 0), 2),
        "lost_sales": round(row.get("lost_sales", 0), 2),
        "service_level": round(row.get("service_level", 0), 4),
        "lost_sales_rate": round(row.get("lost_sales_rate", 0), 4),
        "order_qty": round(row.get("order_qty", 0), 2),
    }


def run_inference(product_id: str, discount_pct: float, ad_multiplier: float, on_hand_start: float):
    try:
        result = backend.run_scenario(
            product_id=product_id,
            discount_pct=discount_pct or 0.0,
            ad_multiplier=ad_multiplier or 1.0,
            on_hand_override=on_hand_start,
        )
    except Exception as exc:  # pylint: disable=broad-except
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            f"Error running inference: {exc}",
        )

    scenario_df = pd.DataFrame([_format_predictions(result.predictions)])
    baseline_df = pd.DataFrame([_format_predictions(result.baseline)])
    feature_df = pd.DataFrame([result.features])

    info = (
        f"Inference time: {result.inference_ms:.3f} ms | "
        f"Model backend: {result.model_backend} | "
        f"Product: {result.product_id}"
    )
    return scenario_df, baseline_df, feature_df, info


def get_default_on_hand(product_id: str) -> float:
    return backend.default_on_hand(product_id)


with gr.Blocks(title="Sell-Through Co-Pilot — Surrogate Model Demo") as demo:
    gr.Markdown(
        """
        # Surrogate Model Live Demo
        - Adjust discount, ad spend, or starting inventory for a product.
        - Backend runs the trained surrogate model and reports prediction + latency.
        - Uses pre-computed features from the data pipeline (no retraining).
        """
    )

    with gr.Row():
        product = gr.Dropdown(
            choices=PRODUCT_CHOICES,
            value=DEFAULT_PRODUCT,
            label="Product",
            info="Products available in the trained surrogate model",
        )
        discount = gr.Slider(
            minimum=0,
            maximum=0.5,
            step=0.01,
            value=0.1,
            label="Discount percentage",
        )
        ad_mult = gr.Slider(
            minimum=0.5,
            maximum=3.0,
            step=0.1,
            value=1.0,
            label="Ad spend multiplier",
            info="1.0 = current plan, 2.0 = double spend",
        )
        on_hand = gr.Number(
            value=backend.default_on_hand(DEFAULT_PRODUCT) if DEFAULT_PRODUCT else 0,
            label="Starting on-hand units",
            precision=0,
        )

    run_btn = gr.Button("Run surrogate inference", variant="primary")

    gr.Markdown("### Outputs")
    scenario_out = gr.Dataframe(label="Scenario predictions", interactive=False)
    baseline_out = gr.Dataframe(label="Baseline predictions", interactive=False)
    feature_out = gr.Dataframe(label="Features sent to the model", interactive=False)
    info_out = gr.Markdown()

    product.change(fn=get_default_on_hand, inputs=product, outputs=on_hand)
    run_btn.click(
        fn=run_inference,
        inputs=[product, discount, ad_mult, on_hand],
        outputs=[scenario_out, baseline_out, feature_out, info_out],
    )

if __name__ == "__main__":
    demo.launch()

