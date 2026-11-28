<!-- header:begin (generated from project metadata) -->
<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/seb5594/hass-cigarette_vending_finder-integration/main/custom_components/cigarette_vending_finder/brand/dark_logo@2x.png">
    <img src="https://raw.githubusercontent.com/seb5594/hass-cigarette_vending_finder-integration/main/custom_components/cigarette_vending_finder/brand/logo@2x.png" alt="Cigarette Vending Finder" width="360" height="101">
  </picture>
  <br>
  Cigarette Vending Finder
</h1>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=seb5594&amp;repository=hass-cigarette_vending_finder-integration&amp;category=integration"><img src="https://img.shields.io/static/v1?label=HACS%20%C2%B7%20Marketplace&amp;message=Add%20integration&amp;color=41BDF5&amp;logo=homeassistantcommunitystore&amp;logoColor=white&amp;style=for-the-badge" alt="HACS · Marketplace" height="28"></a>
  <a href="https://github.com/seb5594/hass-cigarette_vending_finder-integration/actions/workflows/compat.yml"><img src="https://img.shields.io/static/v1?label=home%20assistant&amp;message=%E2%89%A5%202024.6.4&amp;color=1877A5&amp;style=for-the-badge" alt="home assistant" height="28"></a><br>
  <a href="https://github.com/seb5594/hass-cigarette_vending_finder-integration/releases/tag/2026.11.28"><img src="https://img.shields.io/static/v1?label=integration%20version&amp;message=2026.11.28&amp;color=1877A5&amp;style=for-the-badge" alt="integration version" height="28"></a>
  <a href="https://github.com/seb5594/hass-cigarette_vending_finder-integration/releases"><img src="https://img.shields.io/github/downloads/seb5594/hass-cigarette_vending_finder-integration/2026.11.28/total?label=downloads&amp;color=1877A5&amp;style=for-the-badge" alt="downloads" height="28"></a><br>
  <a href="https://github.com/seb5594/hass-cigarette_vending_finder-integration/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/seb5594/hass-cigarette_vending_finder-integration/ci.yml?branch=main&amp;label=checks&amp;style=flat" alt="checks" height="20"></a>
  <img src="https://img.shields.io/static/v1?label=tests&amp;message=4%20passed&amp;color=2F855A&amp;style=flat" alt="tests" height="20">
  <a href="https://github.com/seb5594/hass-cigarette_vending_finder-integration/issues"><img src="https://img.shields.io/github/issues/seb5594/hass-cigarette_vending_finder-integration?label=issues&amp;style=flat" alt="issues" height="20"></a><br>
  <a href="https://paypal.me/seb5594"><img src="https://img.shields.io/static/v1?label=Support&amp;message=PayPal&amp;color=0070BA&amp;logo=paypal&amp;logoColor=white&amp;style=for-the-badge" alt="PayPal" height="24"></a>
  <a href="https://buymeacoffee.com/seb5594"><img src="https://raw.githubusercontent.com/seb5594/Home-Assistant-Apps/473dc258f963096745aac327df54950eb9b59066/.github/assets/support-beer.svg" alt="Buy me a beer" height="24"></a><br>
  <a href="https://github.com/seb5594/hass-cigarette_vending_finder-integration#license"><img src="https://img.shields.io/github/license/seb5594/hass-cigarette_vending_finder-integration?label=license&amp;style=flat" alt="license" height="20"></a>
</p>
<!-- header:end -->

**🇬🇧 English** · [🇩🇪 Deutsch](README.de.md)

Find the nearest **mapped** cigarette vending machines from a Home Assistant location or a person's current coordinates. OpenStreetMap/Overpass supplies international coverage without an API key. The integration cannot promise that every real machine is mapped, still operating, or accessible at the time of your visit.

## Install

Add this repository as a custom **Integration** in Home Assistant's Marketplace (or HACS on older versions), download it, restart Home Assistant, then add **Cigarette Vending Finder** under **Settings → Devices & services**. The compatibility badge shows the minimum version declared for installation through HACS.

Choose an optional default person, a maximum radius (1–100 km, default 25), and the number of results on the map (1–30, default 10). Without a person, scheduled searches start at your Home Assistant home location. A configured person needs a device tracker with latitude and longitude. Location searches occur on setup, approximately every six hours, and when you run the action.

## Find a machine now

Run `cigarette_vending_finder.find_nearest` from **Developer tools → Actions**. Supply `person: person.sebastian` to search from that person's current coordinates, or supply both `latitude` and `longitude`. Both are optional if you configured a default person or want to search around home.

```yaml
# Example: run this action in an automation and inspect the structured result.
action: cigarette_vending_finder.find_nearest
data:
  person: person.sebastian
  maximum_radius_km: 25
  limit: 5
response_variable: cigarette_machines
```

Home Assistant versions before 2023.7 support the search action without `response_variable`. Read the result from the distance sensor attributes or the map markers. Older setup screens may require entering the optional `person.*` entity ID as text.

The response contains `origin`, `count`, `nearest`, and `machines`. Each location includes distance **as the crow flies**, OSM and navigation links, and any available OSM details (`location`, `description`, `level`, street address, operator, brand, access, opening hours, payment methods, and survey date). `image_url` is supplied only when the OSM item provides an image or Wikimedia Commons file. A `mapillary` tag, when available, appears in `details` as a photo identifier; no Mapillary image is fetched. The nearest-distance sensor and up to the configured number of `geo_location` entities update after the action; markers appear on the Home Assistant map. Missing details are not fabricated.

The action returns an empty `machines` list and `nearest: null` if no mapped machine exists inside the requested radius. It reports a validation error when a person has no usable coordinates. If an Overpass lookup fails, the action reports a lookup error. Previous sensor data may then be stale.

## Data, images, and privacy

The query selects `amenity=vending_machine` with `vending=cigarettes` (also supporting semicolon-separated vending categories). It searches progressively larger circles, deduplicates OSM nodes, ways and relations, and keeps location-based responses for six hours to reduce public API traffic. The default public Overpass endpoint has a fair-use policy and may reject or delay queries; a large number of users must use their own infrastructure. The integration sends the requested coordinates to Overpass, and Home Assistant may request image URLs from external hosts when displaying machine pictures. Other sources cannot be merged without reuse rights.

Machine data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL. Photos retain their respective licenses; follow the image link for their attribution. Contribute corrections and missing locations directly to OpenStreetMap. Geofabrik country extracts may be used for a separately operated regional dataset, subject to the same ODbL.

## Development

The caller workflows in `.github/workflows/` use [`hass-workflows`](https://github.com/seb5594/hass-workflows) for validation, real Home Assistant compatibility tests and release ZIPs. `ORCHESTRATION_PAT` is optional for the public shared engine; it is required only for features that need cross-repository permissions. For local checks after cloning that repository under `.engine/`: `python .engine/.scripts/managed.py check integration`, `python .engine/.scripts/integration_checks.py` and `python -m unittest discover -s .github/tests`.

<!-- support:begin (generated, shared text) -->
## Say thanks

All my projects are built in my spare time, just for the fun of it. Still, they take a lot of time and care, and many of the smart home gadgets I buy end up here because I want to make them cloud-free and smart-home ready. Every bit of support means a lot to me.

If my work helped you or turned out to be useful, show your appreciation with a hot drink for my next sleepless night.

[![PayPal](https://img.shields.io/static/v1?label=Support&message=PayPal&color=0070BA&logo=paypal&logoColor=white&style=for-the-badge)](https://paypal.me/seb5594) [![Buy me a beer](https://raw.githubusercontent.com/seb5594/Home-Assistant-Apps/473dc258f963096745aac327df54950eb9b59066/.github/assets/support-beer.svg)](https://buymeacoffee.com/seb5594)
<!-- support:end -->

<!-- license:begin (generated from the license file) -->
## License

[![license](https://img.shields.io/static/v1?label=license&message=Apache-2.0&color=5B6770&style=flat)](LICENSE)

Published under the [Apache License 2.0](LICENSE).
<!-- license:end -->
