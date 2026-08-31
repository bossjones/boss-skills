---
description: Search Amazon, add item(s) to cart, proceed to checkout, stop
argument-hint: <item to search for>
---

# Amazon Add to Cart

Search Amazon for an item(s), add it/them to cart, and proceed to checkout without submitting the order.

## Variables

| Variable | Value           | Description                                         |
| -------- | --------------- | --------------------------------------------------- |
| SKILL    | `claude-bowser` | Uses your real Chrome (already logged in to Amazon) |
| MODE     | `headed`        | Visible browser                                     |

## Workflow

1. Navigate to https://www.amazon.com
2. Verify the homepage loads (look for the search bar)
3. Search for: {PROMPT}
4. Verify search results appear
5. Click into the first relevant result
6. Verify the product detail page loads with title, price, and "Add to Cart" button
7. Click "Add to Cart"
8. Verify the cart confirmation appears (look for "Added to Cart" or cart count increment)
9. Click "Proceed to checkout" or navigate to the cart
10. Verify the checkout page loads with the item visible
11. STOP — do not submit the order
12. Report: item name, price, and confirmation that it reached checkout
