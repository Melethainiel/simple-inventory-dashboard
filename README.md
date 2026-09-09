# Simple Inventory Dashboard

A dedicated Home Assistant sidebar panel for
[Simple Inventory](https://github.com/blaineventurine/simple_inventory).

The dashboard uses Simple Inventory's native WebSocket API and Home Assistant
services. Data stays in Simple Inventory; this integration only provides the UI.

## Features

- Overview across all configured inventories
- Responsive item grid with search, category and location filters
- Add and edit items
- Increment, decrement and delete actions
- Low-stock and expiry indicators
- Recent inventory history
- JSON export
- French and English UI
- Assist-friendly services for searching, listing a bin, storing and taking items

## Voice assistant integration

On Home Assistant 2026.8 or newer, the integration contributes six native tools
directly to the **Assist** LLM API. No YAML scripts or manual entity exposure are
required. Select **Assist** as the control mode in the conversation agent; it can
then discover and call these tools automatically:

- `simple_inventory_dashboard.list_inventories`: lists every configured inventory
  with its ID and totals
- `simple_inventory_dashboard.search_items`: partial, case- and accent-insensitive
  search across all inventories (or one optional inventory)
- `simple_inventory_dashboard.list_location`: exact location/bin lookup
- `simple_inventory_dashboard.store_item`: creates an item, or increments an
  existing item with the same name
- `simple_inventory_dashboard.take_item`: finds and decrements an item; if a
  partial name matches several items, it returns the matches without changing stock
- `simple_inventory_dashboard.edit_item`: edits the name, total quantity, unit,
  location, category, description, barcode, price, expiry and shopping-list settings

The same operations remain available as response-enabled services for dashboards
and automations. They discover inventories dynamically, so inventory IDs do not
need to be hard-coded:

```yaml
- action: simple_inventory_dashboard.search_items
  data:
    query: tournevis
  response_variable: inventory_result
```

The conversation agent can handle requests such as “où sont les tournevis ?”,
“qu'y a-t-il dans le bac A1 ?” or “j'ai pris deux piles”. `inventory` accepts
either the configured inventory name (for example `Armoire bureau`) or its ID.

## Install

1. Install and configure **Simple Inventory**.
2. In HACS, add this repository as a custom repository of type **Integration**.
3. Install **Simple Inventory Dashboard** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**.
5. Add **Simple Inventory Dashboard**.

The **Inventaire** entry then appears in the Home Assistant sidebar.

## Manual install

Copy `custom_components/simple_inventory_dashboard` into Home Assistant's
`config/custom_components` directory, restart, then add the integration from
**Settings → Devices & services**.

## Compatibility

- Home Assistant 2024.7 or newer
- Simple Inventory 0.6.x or newer

## Releases

The CI validates the Python, JSON and frontend sources on pull requests and on
pushes to `main`. It also builds a HACS-ready `simple_inventory_dashboard.zip`.

On `main`, the version in
`custom_components/simple_inventory_dashboard/manifest.json` is published as a
Git tag and GitHub Release (for example, version `0.2.0` creates tag `v0.2.0`).
Increment the manifest version and the matching `?v=` value in `__init__.py`
before merging a new release. An existing version is never overwritten.
