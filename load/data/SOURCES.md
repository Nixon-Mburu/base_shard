# Location provenance

`locations.json` is a compact, reproducible selection of up to four populated places per county, prioritizing county capitals, from the [GeoNames Kenya dump](https://download.geonames.org/export/dump/KE.zip), downloaded 2026-09-10. It covers all 47 Kenyan counties. Each place retains its GeoNames ID and source coordinates. Names and coordinates are real public geographic data; they are town reference points, not customer doorsteps.

GeoNames data is licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/); credit: [GeoNames](https://www.geonames.org/). See the [dump format and license](https://download.geonames.org/export/dump/readme.txt). Source ZIP SHA-256: `63dc0a6ae78125f0a64863a27e00d27becbe0a3c35d3a48de4bc3aeb5f4d5f6f`.

Merchant/contact names are fictional combinations of common Kenyan given/family names. Names are not linked to real people; businesses, street/building descriptions and non-dialable `000…` phone placeholders are synthetic. County weights are an explicit test distribution, not a population or economic survey. `hotspot` makes 60% of generated merchants Nairobi-based; it does not imply geo-routing or sharding in the current backend.
