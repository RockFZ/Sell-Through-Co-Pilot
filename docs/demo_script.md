# Gradio Demo Voice-Over Script

## Introduction (0:00 - 0:30)
"Welcome to the Sell-Through Co-Pilot demo. Today I'll show you our interactive Gradio interface that demonstrates millisecond-speed scenario analysis using our surrogate model for inventory optimization."

---

## Scene 1: Interface Overview (0:30 - 1:00)
*[Show the Gradio interface]*
"This is our Gradio demo interface. On the left, we have input controls: product selection, discount percentage, ad spend multiplier, and starting inventory. On the right, we'll see model predictions and the inference time."

---

## Scene 2: Baseline Prediction (1:00 - 1:30)
*[Click "Run surrogate inference" with default settings]*
"Let me run a baseline prediction for SKU-001 with default settings: 10% discount, normal ad spend.
*[Click]*
"Results appear instantly - under a millisecond. We see service level of [read value], realized demand of [read value] units, and order quantity of [read value]."

---

## Scene 3: Promotional Impact (1:30 - 2:30)
*[Increase discount to 20%]*
"Now let's increase the discount to 20% to see the promotional impact.
*[Click]*
"With a 20% discount, realized demand increases to [read value] and service level changes to [read value]. The inference still completes in under a millisecond."

---

## Scene 4: Advertising Impact (2:30 - 3:30)
*[Reset discount, increase ad multiplier to 2.0]*
"Let's test advertising spend. I'll double the ad spend multiplier to 2.0.
*[Click]*
"With doubled ad spend, we see [read value] realized demand. We can instantly compare this to the baseline."

---

## Scene 5: Inventory Optimization (3:30 - 4:30)
*[Adjust starting inventory]*
"Now let's test different inventory levels. I'll reduce starting inventory.
*[Click]*
"With lower inventory, service level drops to [read value] and lost sales increase to [read value]. This helps identify optimal inventory levels."

---

## Scene 6: Speed Demonstration (4:30 - 5:00)
*[Run multiple scenarios quickly]*
"Let me run several scenarios rapidly.
*[Click multiple times]*
"Each inference completes in under a millisecond. Compare this to full simulations taking 12 seconds - that's a 12,000x speedup, enabling real-time optimization."

---

## Scene 7: Model Transparency (5:00 - 5:30)
*[Show the features table]*
"The interface shows transparency - here are the exact features sent to the model: discounts, ad spend, inventory levels. This builds trust in the predictions."

---

## Conclusion (5:30 - 6:00)
"In summary: millisecond speed enables real-time analysis, the model is accurate and learned from full simulations, and the interface makes advanced optimization accessible. This demonstrates our Milestone 2 integration of Orbit forecasting, Robyn marketing mix modeling, and our XGBoost surrogate model. Thank you!"

---

## Key Talking Points:
- **Speed**: "Under a millisecond" / "12,000x faster"
- **Real-time**: "Instant results" / "Interactive optimization"
- **Practical**: "Production-ready" / "Actionable insights"
- **Transparent**: "See what features drive predictions"

