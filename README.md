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
- Simple Inventory 0.6.x

## Releases

The CI validates the Python, JSON and frontend sources on pull requests and on
pushes to `main`. It also builds a HACS-ready `simple_inventory_dashboard.zip`.

On `main`, the version in
`custom_components/simple_inventory_dashboard/manifest.json` is published as a
Git tag and GitHub Release (for example, version `0.2.0` creates tag `v0.2.0`).
Increment the manifest version and the matching `?v=` value in `__init__.py`
before merging a new release. An existing version is never overwritten.
