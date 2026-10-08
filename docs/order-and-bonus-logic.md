# Order & Bonus Code Logic

## Order Flow

### 1. Cart Management

Before placing an order the user builds a cart via the Mini App.

| Endpoint | What it does |
|---|---|
| `GET /api/v1/product/my-cart/<chat_id>/` | Returns all cart items with name, price, count, image |
| `POST /api/v1/product/my-cart/<chat_id>/` | Upserts an item — if the product already exists in the cart it updates `count`, never inserts a duplicate row |
| `PATCH /api/v1/product/my-cart/<chat_id>/<product_id>/` | Changes `count`; if `count < 1` the item is deleted |
| `DELETE /api/v1/product/my-cart/<chat_id>/<product_id>/` | Removes the item |

`Cart` has `unique_together = ('user', 'product')` enforced at the DB level (added in migration `product/0003`).

### 2. Placing an Order

**Endpoint:** `POST /api/v1/product/order/<chat_id>/`

**Request body:**
```json
{
  "store": 3,
  "total": 45000,
  "products": [
    {"product": 7, "count": 2},
    {"product": 12, "count": 1}
  ]
}
```

**What happens inside `OrderView.post`** (`apps/product/views.py:37`):

1. Look up `TelegramUser` by `chat_id` — 404 if not found.
2. Deserialize with `OrderSerializer`, which creates one `Order` row and one `OrderProduct` row per item.
3. Deduct `order.total` from `user.summa` and save the user — **no validation that the balance covers the total** (the bot is expected to gate this).
4. Send a notification to the staff Telegram group (`GROUP_ID`) with order id, user phone, store, region, products (Uzbek only).
5. Send a confirmation message to the user in their language (uz/ru) with order summary, store name, phone numbers, and pickup note ("you can pick it up in 5 days").
6. Send a `sendLocation` Telegram message to the user (store GPS coords), replying to the confirmation message.
7. Delete all of the user's `Cart` rows.
8. Return `{"success": true}`.

If the Telegram group message fails (non-200), the view returns 500 and the order has already been saved and the balance already deducted — the bot should handle this edge case.

### 3. Order Confirmation (5-day survey)

**Cron job** (`task.sh`) runs daily at 00:00. It sends an inline-keyboard message to every user whose order was created exactly 5 days ago, asking "Did you receive order #N?".

- `callback_data` format: `yes_<order_id>` / `no_<order_id>` — the bot splits on `_` to extract the order id.
- On "Yes" the bot calls `POST /api/v1/product/order/<chat_id>/<order_id>/confirm/`.
- `OrderConfirmView.post` (`apps/product/views.py:88`) sets `order.is_completed = True`. The query is scoped by both `chat_id` and `order_id` so one user cannot confirm another's order.
- "No" sends nothing to the backend — it is purely informational for the staff.

---

## Bonus Code Logic

### Code Format on the Product (printed code)

Codes printed on physical products embed a checksum so the backend can reject obvious forgeries without a DB lookup.

A printed code looks like: `<prefix><letter><digits4><suffix>`

Where:
- `<prefix>` — arbitrary alphanumeric prefix (identifies the product batch)
- `<letter>` — one uppercase letter, the checksum character
- `<digits4>` — 4-digit numeric suffix (0001–9999)
- `<suffix>` — optional trailing non-digit characters

**Checksum rule:** `int(digits4) % 26 == ord(letter) - ord('A')`

Example: if `digits4 = "0052"` → `52 % 26 = 0` → letter must be `'A'`.

### The Canonical `Bonus.code`

The `Bonus` table stores a **canonical** form of the code — the same prefix, the checksum letter replaced with `A`, and the numeric suffix replaced with `0000`:

```
<prefix>A0000<suffix>
```

This lets a single `Bonus` row cover every printed variant of the same product batch (different `digits4` values all map to the same canonical code). The `summa` on that `Bonus` row is what gets credited.

### Validation Flow (`GET /api/v1/user/bonus/<code>/`)

`CheckCodeView.get` (`apps/user/views.py:34`):

1. **Already redeemed?** `UserSumma.objects.filter(code=<raw_code>)` — the raw typed code is stored, so the exact string the user entered is the uniqueness key.
2. **Extract `digits4` and suffix** — regex `(\d{4})(\D*$)`. Fails → "code doesn't exist".
3. **Extract checksum letter** — regex `([A-Z]$)` applied to the code with `digits4+suffix` stripped. Fails → "code doesn't exist".
4. **Validate checksum** — `int(digits4) % 26 == ord(letter) - ord('A')`. Fails → "code doesn't exist".
5. **Derive canonical code** — replace letter with `A` and `digits4` with `0000`.
6. **DB lookup** — `Bonus.objects.filter(code=canonical)`. Not found → "code doesn't exist".
7. Return `{"success": true}`.

### Redemption Flow (`POST /api/v1/user/bonus/<code>/`)

`CheckCodeView.post` (`apps/user/views.py:64`):

Identical validation steps 1–6, then:

7. Look up `TelegramUser` by `chat_id` from `request.data`.
8. Add `bonus.summa` to `user.summa` and save.
9. Create a `UserSumma` record:
   - `code` = the raw code the user typed (prevents future reuse of the same printed code)
   - `bonus` FK = the `Bonus` row
   - `summa` = `bonus.summa` at redemption time (snapshot — a later admin edit to `Bonus.summa` won't affect history or expiry)
10. Return success message in uz/ru with the credited amount and 1-year validity warning.

### Point Expiry (nightly cron, `task.sh`)

`process_user_points()` runs each night:

1. Find all `UserSumma` rows where `created_at <= now - 365 days` and `is_expired = False`.
2. For each, inside a transaction:
   - Deduct `point.summa` from `user.summa`, clamped at 0 (`max(0, balance - amount)`).
   - Set `point.is_expired = True` — makes the operation idempotent (won't charge twice).
3. Find all `UserSumma` rows where `created_at__date == now - 358 days` and `is_expired = False`.
4. For each, send a Telegram message: "use your balance, it expires in 1 week."

### Relationship Between Models

```
Bonus (canonical code, summa)
  └── UserSumma (raw typed code, snapshot summa, is_expired)
        └── TelegramUser (summa balance)
```

- `Bonus.code` is canonical; `UserSumma.code` is the raw user input.
- The two are not directly joinable by code string — the canonical form must be re-derived from the raw code (as `CheckCodeView` does) to bridge them.
- `UserSumma.bonus` FK exists for admin visibility but `UserSumma.summa` is what drives expiry math.