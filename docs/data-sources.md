# Data sources

Weta ships no scientific data. This document lists recognized candidate sources per need, and the provider that would import each. Before any import, the current version, access route and licence terms must be checked at the publisher and recorded in `datasets` and `dataset_versions`. Coverage statements below are orientation only.

## 1. Provider layer

`packages/providers/<domain>/<provider>.py`, each implementing a small protocol (`inspect`, `import_`), producing an `ImportReport` and a `dataset_version`. Providers are the only code allowed to parse external scientific data.

| Domain | Interface | Writes to |
|--------|-----------|-----------|
| Chemical identity and properties | `ChemicalPropertyProvider` | `chemicals`, `chemical_properties`, `chemical_hazard_classifications` |
| Ecotoxicological reference values | `EffectValueProvider` | `chemical_properties` (PNEC, EQS codes) |
| Waste lists and classification criteria | `WasteCodeProvider`, rule packs | `waste_codes`, `hazard_classes`, `regulatory_rules` |
| LCI | `LciProvider` | `lci_*` |
| LCIA methods | `LciaMethodProvider` | `lcia_*`, `impact_categories`, `characterization_factors` |
| Emission factors | `EmissionFactorProvider` | `emission_factors` (keyed by technology, pollutant, source) |
| Transport statistics | `TransportRiskProvider` | `transport_incident_rates` |
| Spatial vector and raster | `SpatialProvider` | `environmental_layers`, `spatial_features`, COG files |
| Meteorology | `MeteoProvider` | `meteorological_series` |
| Routing | `RoutingProvider` | `transport_routes` |
| Dispersion models | `DispersionModel` | results only |
| Regulations | `RulePackProvider` | `regulations`, `regulatory_rules` |

Property selection policy: when several sources give a value for the same chemical property, all are stored. A project-level policy (ordered source preference, experimental before estimated) picks the value used, and the full set defines the uncertainty range.

## 2. Candidate sources

### Chemicals

| Need | Candidates |
|------|------------|
| Identity (CAS, names, structure keys) | PubChem; ECHA substance information; CAS Common Chemistry |
| Physico-chemical and fate properties | ECHA registration dossiers; US EPA CompTox Chemicals Dashboard; PubChem; OECD eChemPortal; supplier safety data sheets (as documents, `USER_PROVIDED` with source) |
| Hazard classification | ECHA Classification and Labelling Inventory (harmonized classifications under CLP Annex VI); GHS classifications from national authorities |
| Ecotoxicity effect values | ECHA dossiers (PNEC); US EPA ECOTOX knowledgebase; national environmental quality standards |

### Waste

| Need | Candidates |
|------|------------|
| Waste codes | European List of Waste; Basel Convention annexes; US RCRA waste codes; national catalogues |
| Sector waste and emission benchmarks | EU BAT reference documents (BREFs); national statistics |
| Facility release data for validation | European Industrial Emissions Portal / E-PRTR; US Toxics Release Inventory |

### LCA

| Need | Candidates |
|------|------------|
| Background LCI | ecoinvent (licensed); EF-compliant datasets; USLCI and Federal LCA Commons; Agribalyse and other national databases; supplier EPDs |
| LCIA methods | Environmental Footprint (EF) method packages from the European Commission JRC; ReCiPe 2016; IPCC assessment report GWP values; USEtox for toxicity; AWARE for water scarcity; TRACI for US contexts |
| Flow mappings | Publisher-provided mapping files; GLAD nomenclature mappings |

### Emission factors

| Need | Candidates |
|------|------------|
| Stationary sources, waste treatment | EMEP/EEA air pollutant emission inventory guidebook; US EPA AP-42; IPCC Guidelines for National Greenhouse Gas Inventories (waste volume) |
| Transport | EMEP/EEA guidebook road transport chapter / COPERT; HBEFA; GLEC framework and ISO 14083 |

### Spatial

| Layer | Global or regional candidates | Notes |
|-------|-------------------------------|-------|
| Roads, settlements, points of interest | OpenStreetMap | Completeness varies; record extract date |
| Rivers, lakes, catchments | HydroSHEDS family (HydroRIVERS, HydroLAKES, HydroBASINS); EU-Hydro; national hydrography | |
| Elevation | Copernicus DEM; SRTM | Resolution limits flow-path analysis |
| Land cover, forests | CORINE Land Cover (Europe); ESA WorldCover; Copernicus Global Land Service | |
| Soil | SoilGrids (ISRIC); European Soil Data Centre; national soil maps | Gridded predictions with their own uncertainty layers |
| Protected areas | World Database on Protected Areas; Natura 2000 (EU) | WDPA has specific terms of use |
| Wetlands | Ramsar sites; national inventories | |
| Population | WorldPop; Global Human Settlement Layer; national census grids | |
| Flood hazard | JRC flood hazard maps; national flood maps | |
| Groundwater | National hydrogeological maps and vulnerability maps; IHME for Europe; WHYMAP at global overview scale | Local data is usually essential |
| Meteorology | ERA5 reanalysis (Copernicus Climate Change Service); national weather services; airport observations | Regulatory dispersion models need specific formats |
| Schools, hospitals | OpenStreetMap; national registers | |

Country notes: for Germany, federal and state geoportals publish many of these layers as open data; for Ghana, national coverage of hydrogeology and receptors is sparser, so global datasets plus project-specific surveys (`OBSERVED`) will carry more weight and the completeness indicators matter more.

### Transport risk

National road accident statistics; published hazardous-goods transport risk studies; national dangerous-goods incident reporting. Rates must be imported with their definition (per vehicle-km, vehicle type, road class) and year.

## 3. Dataset record (minimum metadata)

publisher, title, version or edition, retrieval date, URL or DOI, licence and usage restrictions, citation text, spatial and temporal coverage, resolution or scale, CRS, checksum, import profile, import report (rows accepted, rejected, repaired), known limitations.

## 4. Licence handling

- `datasets.licence` plus machine-readable flags: `redistribution_allowed`, `commercial_use_allowed`, `attribution_required`, `export_of_raw_values_allowed`.
- Report and export builders read these flags: for example raw background LCI exchanges from a licensed database are not written to exports when the licence forbids it; aggregated results are.
- Attribution strings are collected automatically into the report's data-sources section.

## 5. Synthetic demo data

`data/sample/` contains a fictional facility, fictional materials with placeholder identifiers, fictional geometry, and placeholder factors. Every row is `SYNTHETIC_DEMO`. Demo chemicals are named "Demo Solvent A" and so on, with no CAS number, so that they cannot be mistaken for real substances. Demo factor values exist only to exercise the software.
