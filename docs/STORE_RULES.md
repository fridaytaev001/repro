# FIELD demo store rules — v1

The original FIELD store is a synthetic target built for Repro. It contains a disclosed seeded defect. No real payments, customer records, or shipments are used.

- Product: Everyday Weekender, $100.00 per unit; supported quantities 1–3.
- Currency: USD. Shipping: free within the US. Tax: always $0.00 in this fixture.
- SAVE10: 10% off merchandise at every supported quantity.
- Coupon entry is available on the details step; the review and order-complete steps show totals without a coupon input or Apply button.
- Changing a US shipping address or moving between checkout steps must preserve a valid SAVE10 discount.
- VIP20: member-only. The guest demo cart is ineligible; rejection is correct behavior.
- Any other code is invalid. Invalid-code attempts must preserve an existing valid coupon.
- Session storage: browser-local cart in `localStorage`, key `field-demo-cart-v1`. There is no shared server-side cart state.
- Reset: one item, no coupon, details step, synthetic address Alex Field / 100 Market Street / San Francisco / 94111 / US. A new browser context has the same starting state.

These public rules describe expected behavior without giving the investigator the hidden triggering sequence. Tests and the operator-only demo guide are evaluation material and must stay outside investigator observations.
