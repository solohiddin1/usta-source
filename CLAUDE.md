# Leo Bonus — Backend (Django)

Backend API for the **Leo Usta / Leo Bonus** loyalty system (leobonus.uz). Users register
through the Telegram bot (`../bot`), browse products in a Telegram Mini App (`../front`),
redeem bonus codes printed on products to earn balance (`summa`), and place orders picked
up at physical stores. There is no Django-auth user for app clients — the "user" is a
`TelegramUser` identified by Telegram `chat_id`.

**`../leo` integration**: `../leo` is a separate, newer backend (mobile app + JWT auth)
covering the same domain, and is now **the source of truth for the bonus-code catalog and
balance**. `apps/user/views.py: CheckCodeView` (GET/POST `user/bonus/<code>/`) decodes
usta-source's own checksum format locally but delegates the actual lookup/redeem to leo
via `apps/user/leo_client.py`, so a code can't be spent twice across the two systems.
`TelegramUser.summa` is now a **display cache** of leo's `balance`, refreshed from every
redeem response — `product.Bonus`/`product.UserSumma` are no longer written for new
redemptions (they stay populated only with pre-cutover history). See leo's
`apps/integrations/` app and `apps/shared/management/commands/migrate_from_usta.py`
(one-time historical data import) for the other side of this. **Known gap**: `task.sh`'s
nightly 1-year point-expiry job only ever operated on local `UserSumma` rows, so it no
longer covers balance earned through leo — expiry there needs its own implementation in
leo before the "expires in 1 year" message is accurate again. Product catalog, stores,
cart and orders are **not yet** proxied to leo (still fully local here) — same reasoning
would apply if that changes, but the Mini App's (`../front`) existing response-shape
contract needs to be checked first.

## Stack

- Django 5.1.3, Django REST Framework 3.15.2, drf-yasg (Swagger at `/`, Redoc at `/redoc/`)
- PostgreSQL (psycopg2-binary), django-modeltranslation (ru/uz), django-jazzmin admin theme
- Celery + Redis (`config/celery.py`, broker hardcoded). `config/__init__.py` **must** keep
  importing `celery_app` — without it the Django process never creates the app and
  `.delay()` silently goes to the default amqp broker instead of Redis. One task exists:
  `user/tasks.py: broadcast_notification`. Time-based jobs still run via cron `task.sh`
- CORS: allow all; DRF: no auth/permission classes — **all endpoints are open (AllowAny)**

## Directory Structure

```
back/
├── config/           # settings.py (single file), urls.py, celery.py, wsgi/asgi
├── apps/
│   ├── urls.py       # mounts user.urls + product.urls under api/v1/
│   ├── user/         # TelegramUser, regions, stores, info, bonus-code check/redeem
│   └── product/      # categories, products, cart, orders, bonuses, instructions
├── task.sh           # cron jobs: order-received survey, 1-year point expiry
├── Dockerfile, celery-dockerfile, .gitlab-ci.yml
```

`apps/` is appended to `sys.path` (settings.py) so local apps import as `user` / `product`
(NOT `apps.user`).

## Key Models

### app `user` (`apps/user/models.py`)
- **TelegramUser** — `name`, `chat_id` (BigInt, unique — the identity key), `phone`,
  `region` FK, `lang` (2 chars), `summa` (int balance), `created_at`
- **Region** (translated ru/uz), **Store** (+`StorePhone`, lat/long, FK Region)
- **Info** / **InfoPhone** — "contact us" link + phones
- **Notification** / **NotificationImage** (admin: «Уведомления») — broadcast: text + `FileField`
  images, `status` draft→queued→sent plus `sent_count`/`failed_count`. Sent to every
  `TelegramUser` by the admin action "Отправить всем пользователям", which queues
  `broadcast_notification`. Telegram fetches the images by URL (`image_url` =
  `BASE_URL` + media URL), so they must stay publicly served; a media group is capped at
  10 images and the caption rides on the first one.

### app `product` (`apps/product/models.py`)
- **Category** / **SubCategory** (self-FK `parent`) / **Product** (price, description)
- **Bonus** — redeemable code (unique) → adds `summa` to user
- **UserSumma** — record of redeemed codes per user (prevents reuse). Carries `bonus` FK,
  `summa` (the amount granted, snapshotted so a later `Bonus.summa` edit cannot change
  history) and `is_expired`, which makes the nightly 1-year expiry idempotent
- **Order** / **OrderProduct**, **Cart** (`unique_together = ('user', 'product')`)
- **Instruction** — Telegram guide messages stored by the bot (manual `id` PK)
- **ProductImage**

## API Endpoints

All under `i18n_patterns` → effective prefix is `/{lang}/api/v1/` (e.g. `/ru/api/v1/...`).

### user (`apps/user/urls.py`)
| Path | Methods | Notes |
|---|---|---|
| `user/<chat_id>/` | GET, PATCH, POST | POST creates user **+50000 summa signup bonus**, best-effort provisions the matching leo `User` |
| `user/regions/` | GET | region list (name_uz/name_ru) |
| `user/check/<chat_id>/` | GET | de-facto "is registered" check used by the bot |
| `user/users/` | GET | all users (chat_id, lang) |
| `user/bonus/<code>/` | GET, POST | validate / redeem bonus code (checksum format check, then delegates to leo) |
| `user/info/` | GET | contact link + phones |
| `user/stores/<chat_id>/` | GET | stores in the user's region |

### product (`apps/product/urls.py`)
| Path | Methods | Notes |
|---|---|---|
| `product/categories/` | GET | categories + top-level subcategories |
| `product/products/<subcategory_id>/<chat_id>/` | GET | products + `has_in_cart` |
| `product/<pk>/<chat_id>/` | GET | product detail |
| `product/my-cart/<chat_id>/` | GET, POST | cart; POST upserts (never duplicates a product row) |
| `product/my-cart/<chat_id>/<product_id>/` | PATCH, DELETE | set `count` (`count < 1` deletes) / remove item |
| `product/order/<chat_id>/` | POST | create order, deduct summa, notify Telegram group + user |
| `product/order/<chat_id>/<order_id>/confirm/` | POST | mark received; bot calls it on survey "yes" |
| `product/instruction/<pk>/` | GET, POST | bot guide messages |

## Environment Variables (`.env`, loaded via `dotenv_values`)

`SECRET_KEY`, `DEBUG`, `BASE_URL`, `BOT_TOKEN`, `GROUP_ID`,
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`,
`LEO_BASE_URL` (leo's base URL, e.g. `https://leo.leobonus.uz`), `LEO_INTERNAL_TOKEN`
(shared secret — must match `INTERNAL_API_TOKEN` in leo's own `.env`)

Celery broker/backend Redis URL is **hardcoded** in `settings.py` and `config/celery.py`.

## Important Notes

- **Registration has NO SMS OTP step** (removed July 2026): the former
  `user/send-sms/` and `user/verify/` endpoints, the `VerifyPhone` model
  (migration `user/0003_delete_verifyphone.py`), the Eskiz.uz integration
  (`send_verification_code`) and the `SMS_EMAIL`/`SMS_PASSWORD` settings were deleted.
  Registration is now just: bot collects name/phone/region → `POST user/<chat_id>/`.
- Auth model: no tokens/JWT/sessions — identity is only the `chat_id` in the URL.
- Telegram messaging helper: `apps/user/utils.py: send_telegram_message()`.
- leo API client: `apps/user/leo_client.py` — every call to leo goes through here;
  raises `LeoAPIError` (payload shaped like leo's own error responses) on both HTTP
  errors and connection failures/timeouts, so callers only handle one exception type.
- Cron script `task.sh` (daily 00:00, crond in the Dockerfile) pipes one heredoc into
  `manage.py shell`, which **execs it as a single block** — an unguarded exception cancels
  every job after it. Each job is therefore called inside its own `try/except`, and
  `send_question()` runs first.
- Point expiry deducts `UserSumma.summa` once and flips `is_expired`; without that flag
  the nightly run would charge the same point again every night. Balances are clamped at
  0 — the bonus may already have been spent. The "expires in a week" warning fires on the
  single day a point is 358 days old.
- Every `UserSumma` that predates migration `product/0003` was **grandfathered as
  expired**: expiry had never actually run, so leaving them open would have deducted a
  year of backlog from every balance on the first nightly pass. Their `summa`/`bonus`
  were backfilled by re-deriving `Bonus.code` from the stored raw code — the two are not
  joinable directly, since `CheckCodeView.post` saves what the user typed.
- `product/0003` also collapses duplicate `Cart` rows before adding the unique
  constraint; the constraint cannot be applied while duplicates exist.
- The 5-day survey sends `callback_data` `yes_<order_id>` / `no_<order_id>`; the bot
  splits on `_` to report which order was confirmed. Keep both sides in sync.
- Update this CLAUDE.md whenever endpoints, models or integrations change.
