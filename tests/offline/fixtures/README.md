# Fixtures for the offline suite

Every file is HTTP-shaped — `{"status", "headers", "body"}`, or `raw_body` for
a body that is not valid JSON — and is loaded by
`tests.offline.support.response_from_fixture`.

Two kinds of file live here and **the difference matters**: one kind is
evidence, the other is an assumption. Do not move a file between the two
directories, and do not tidy a captured body — a fixture that has been edited
is no longer evidence, and a fixture that does not match reality is worse than
no fixture at all.

## `bol/` — captured from the live bol.com API

Recorded 2026-08-27/28 against a real account and copied here from the
Dreambits connector platform, where they were captured. Each file keeps the
`_source` and `_note` keys it was captured with; the loader ignores them.

| File | What it is evidence of |
|---|---|
| `token_200.json` | a successful `client_credentials` login: `expires_in` is 599 seconds, and `login.bol.com` returns **none** of the quota headers |
| `token_401.json` | a rejected login — the whole body is `{"error": "invalid_client"}` |
| `orders_page_1.json` | `orders.list()` page 1, and the `x-ratelimit-*` / `x-request-id` headers every API response carries |
| `orders_page_2.json` | page 2 — it is `{}` |
| `orders_page_empty.json` | a page past the end: HTTP 200 with `{}`, the collection key *absent* rather than an empty list |
| `inventory_page_1.json` | a different quota group: limit 20, not orders' 25 |
| `returns_list.json` | another group at limit 20 |
| `economic_operators.json` | the endpoint with its own media type, and a group at limit 100 |
| `process_status_submitted_export.json` | the receipt: HTTP 202, the status object bare at the top level, `PENDING` |
| `process_status_submitted_shipment.json` | the same for a body-parameter write |
| `process_status_getbyids_export_pending.json` | the `getByIds` shape: the same object wrapped in a `processStatuses` list |
| `process_status_getbyids_success.json` | terminal success, with `entityId` and no `links` |
| `process_status_getbyids_failure.json` | terminal failure, with `errorMessage` and no `entityId` |

**Before these are committed, read this.** They are recordings of a live
account. They contain real order ids, order item ids, EANs, third-party
economic-operator company names, and — in `returns_list.json` — a customer's
free-text return comment. This repository is public and publishes to PyPI. See
the note in the P2-3a report: whether these may be committed as they stand, or
must be pseudonymised first, is a decision for the repository owner and not one
the test suite should make quietly.

## `synthetic/` — hand-written

These make **no claim** to be what bol.com returns. Each carries
`"_synthetic": true` and a `_note` saying exactly what it does and does not
assert. They exist because no response was ever captured for the call in
question; each one is there to prove that a method addresses the right URL with
the right body and parses into the right model, and nothing more.

| File | Why it is not evidence |
|---|---|
| `order_single.json` | no `GET /retailer/orders/{id}` was captured. The order-item shape is copied from `bol/orders_page_1.json`; the envelope is invented and omits `shipmentDetails` and `billingDetails`, which a real one carries |
| `offer_single.json` | no `GET /retailer/offers/{id}` was captured. Its keys are the ones `models.py:OffersResponse` declares a coercion for |
| `return_single.json` | no `GET /retailer/returns/{id}` was captured. The `returnItems` shape is copied from `bol/returns_list.json` |
| `delivery_options.json` | no VVB shipping-label response was captured at all. Its keys are the ones `models.py:Labels` declares a coercion for |

Four fixtures worth capturing when someone next has an account in front of
them, listed here so the gap is visible rather than forgotten.
