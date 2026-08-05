---
name: tinh-gia-lam-tron-hoc-phi
description: "Tinh hoc phi gom VAT 8% va lam tron len hang nghin cho website khoa hoc Anh Lap Trinh. Use when Codex needs to calculate course tuition totals, update index pricing copy such as 'Hoc phi chi hom nay: 1460K (Chua bao gom VAT 8%)', or update payment/QR logic so subtotal + VAT is rounded up to the nearest 1,000 VND."
---

# Tinh Gia Lam Tron Hoc Phi

## Rule

Use this pricing rule for course websites:

1. Treat the displayed course price as the subtotal before VAT.
2. Calculate `vat = round(subtotal * 8%)` to the nearest VND.
3. Calculate `raw_total = subtotal + vat`.
4. Calculate `payment_total = ceil(raw_total / 1000) * 1000`.

Example: `1,480,000 + 118,400 = 1,598,400`, payment total is `1,599,000`.

For coupon prices, apply the same rule to the discounted subtotal. Example: `2,000 + 160 = 2,160`, payment total is `3,000`.

## Website Updates

When updating an Anh Lap Trinh course website:

- On the sales/index page, make the tuition copy explicit that the listed price is before VAT, for example: `Học phí chỉ hôm nay: 1460K (Chưa bao gồm VAT 8%)`.
- On payment pages, show the rounded total as the amount to transfer and QR amount.
- Keep the VAT line as the exact 8% calculation unless the local UI already has a separate rounding line.
- For Django code, prefer helper functions:
  - `_calculate_vat_amount(amount)` returns exact rounded VND VAT.
  - `_payment_total_amount(amount)` returns the rounded-up transfer total.
- For JavaScript/static payment pages, add a `roundUpToThousand(amount)` helper and use it before rendering total amount or building the VietQR URL.

## Script

Use `scripts/calc_rounded_tuition.py` for quick checks:

```bash
python /root/.agents/skills/tinh-gia-lam-tron-hoc-phi/scripts/calc_rounded_tuition.py 1480000 1460K "1.011.000đ"
```
