# VRMonkey: Automated Privacy Compliance Analysis for Apple Vision Pro Apps

This repository contains the code and data artifacts for our large-scale privacy compliance study of 306 Apple Vision Pro (visionOS) applications. The study examines discrepancies between privacy policies, Apple App Store privacy labels, privacy manifests, and actual network traffic behavior.

## Overview

We developed **VRMonkey**, an automated UI exploration system that interacts with visionOS apps via an ESP32-based Bluetooth mouse emulator while capturing network traffic through a MITM proxy. Combined with NLP-based privacy policy analysis (via PPAudit) and Apple privacy label/manifest extraction, VRMonkey enables systematic detection of privacy compliance violations across multiple data sources.

## Repository Structure

```
open_science/
├── README.md                  # This file
├── requirements.txt           # Python dependencies
│
├── vrmonkey/                  # App exploration system
│   ├── main.py                # Entry point (state explorer)
│   ├── simple_state_explorer.py   # Core exploration engine
│   ├── app_manager.py         # App lifecycle management
│   ├── mouse_controller.py    # Mouse movement & calibration
│   ├── esp32_mouse.py         # ESP32 serial communication
│   ├── omniparser_client.py   # OmniParser UI element detection
│   ├── screenshot_manager.py  # Screenshot capture via GStreamer
│   ├── native_screenshot.py   # GStreamer streaming backend
│   ├── pointer_recognize.py   # Pointer detection (computer vision)
│   ├── password_input_detector.py  # Password field safety guard
│   ├── fast_ui_detector.py    # Fast UI element detection
│   ├── state_graph.py         # State graph tracking
│   ├── eyes.py                # Image quality analysis
│   ├── metrics_manager.py     # Exploration metrics collection
│   ├── config.py              # Configuration parameters
│   ├── core_types.py          # Shared data structures
│   ├── run_batch_apps.py      # Batch exploration runner
│   ├── video_recorder_client.py   # Video recording client
│   └── video_recorder_service.py  # Video recording service
│
├── analysis/                  # Privacy analysis pipeline
│   ├── run_ppaudit_pipeline.py        # 5-step PPAudit NLP pipeline
│   ├── analyze_ppaudit_results.py     # PPAudit result analysis
│   ├── generate_data_flows_v2.py      # Network data flow extraction
│   ├── key_to_datatype_mapper.py      # Key-to-data-type mapping
│   ├── ontology_mapping.py            # Ontology-to-Apple label mapping
│   ├── detect_violations.py           # Label/policy violation detection
│   ├── unified_violation_detection.py # Multi-source violation detection
│   ├── detect_manifest_violations_extended.py  # Manifest violations
│   ├── detect_mismatched_entity_violations.py  # Entity mismatch detection
│   ├── enrich_violations_with_entity_info.py   # Entity enrichment
│   ├── clean_cross_contamination.py   # Cross-contamination cleaning
│   ├── batch_violation_detection.py   # Batch violation processing
│   └── generate_heatmap_306apps.py    # Heatmap visualization
│
├── visualization/             # Paper figure generation
│   ├── create_paper_sankey_final.py           # Sankey diagram
│   ├── visualize_ontology_extension.py        # Ontology tree figure
│   └── create_4col_violation_sankey_v2.py     # 4-column violation Sankey
│
├── ontology/                  # Ontology & taxonomy files
│   ├── data_ontology.gml              # Extended PPAudit data ontology
│   ├── data_synonyms.yml             # 9,104 phrase synonyms
│   └── apple_layer2_integration_final.json  # Apple privacy label mapping
│
└── data/                      # Analysis datasets (306 apps)
    ├── label.csv                      # Apple App Store privacy labels
    ├── manifest.csv                   # Privacy manifests (34 apps)
    ├── manifest_file_mapping_306.csv  # Manifest file mapping
    ├── policy_data_306.csv            # Policy analysis summary
    ├── policy_cus_triplets_234.csv    # Policy CUS triplets (234 apps)
    ├── data_flows_with_appid.csv      # Network data flows
    ├── violations_all_apps.csv        # All detected violations
    ├── violations_all_apps_enriched.csv  # Violations with entity info
    ├── manifest_violations_extended.csv  # Manifest-specific violations
    └── mismatched_entity_violations.csv  # Entity mismatch violations
```

## Components

### 1. VRMonkey Exploration System (`vrmonkey/`)

An automated UI exploration tool for visionOS applications. It uses:
- **ESP32 BLE Mouse**: Hardware-based Bluetooth mouse emulator for reliable input
- **OmniParser**: Vision-language model for UI element detection
- **State Graph**: Tracks visited UI states to maximize exploration coverage
- **GStreamer**: Captures the device screen via AirPlay mirroring

**Usage:**
```bash
# Explore a single app
python vrmonkey/main.py --app "AppName" --timeout 10

# Batch exploration
python vrmonkey/run_batch_apps.py --csv apps.csv
```

### 2. Privacy Analysis Pipeline (`analysis/`)

Multi-stage pipeline that cross-references four data sources:
1. **Privacy Policies** (NLP analysis via PPAudit)
2. **Apple Privacy Labels** (App Store metadata)
3. **Privacy Manifests** (NSPrivacyAccessedAPITypes)
4. **Network Traffic** (MITM proxy captures)

**Pipeline stages:**
```bash
# Step 1: Run PPAudit NLP pipeline on privacy policies
python analysis/run_ppaudit_pipeline.py

# Step 2: Extract data flows from network traffic
python analysis/generate_data_flows_v2.py

# Step 3: Detect violations across all sources
python analysis/unified_violation_detection.py

# Step 4: Detect manifest and entity violations
python analysis/detect_manifest_violations_extended.py
python analysis/detect_mismatched_entity_violations.py

# Step 5: Enrich and clean results
python analysis/enrich_violations_with_entity_info.py
python analysis/clean_cross_contamination.py
```

### 3. Visualization (`visualization/`)

Scripts for generating paper figures:
```bash
# Sankey diagram of violation flows
python visualization/create_paper_sankey_final.py

# Ontology extension tree
python visualization/visualize_ontology_extension.py
```

### 4. Ontology (`ontology/`)

Extended PPAudit data ontology with visionOS-specific data types:
- **13 new nodes** for spatial, biometric, eye/hand tracking data
- **9,104 synonym phrases** for improved NLP matching
- **Apple label mapping** linking ontology terms to App Store categories

### 5. Data (`data/`)

Pre-computed datasets for 306 visionOS applications:
- Privacy labels for all 306 apps
- Privacy manifests for 34 apps that include them
- NLP-extracted policy triplets for 234 apps with accessible policies
- Network data flows extracted from MITM captures
- Detected privacy compliance violations

## Violation Types

The analysis detects seven types of privacy compliance violations:

| Type | Description |
|------|-------------|
| **Omission** | Data collected in traffic but not disclosed in policy or labels |
| **Label Neglect** | Data type in policy but missing from privacy labels |
| **Label Contrary** | Policy says data is not collected, but label claims it is |
| **Manifest Neglect** | API usage detected but not declared in privacy manifest |
| **Manifest Contrary** | Manifest declaration contradicts observed behavior |
| **Mismatched Entity** | Data attributed to wrong entity (1st vs 3rd party) |
| **Policy Incorrect** | Policy claims conflict with observed network behavior |

## Requirements

- Python 3.10+
- See `requirements.txt` for Python package dependencies
- **Hardware** (for VRMonkey exploration):
  - Apple Vision Pro with Developer Mode enabled
  - ESP32 board flashed with BLE Mouse firmware
  - Mac/Linux host with GStreamer for AirPlay mirroring
  - OmniParser model server
- **Software** (for analysis pipeline):
  - PPAudit framework (for NLP policy analysis)
  - mitmproxy (for network traffic capture)

## Installation

```bash
pip install -r requirements.txt
```

## Data Format

### Privacy Labels (`data/label.csv`)
Contains Apple App Store privacy label declarations for each app, including data types, purposes, and collection/sharing indicators.

### Policy CUS Triplets (`data/policy_cus_triplets_234.csv`)
NLP-extracted (Collection, Usage, Sharing) triplets from privacy policies, with data types mapped to the extended ontology.

### Network Data Flows (`data/data_flows_with_appid.csv`)
Observed data flows from network traffic analysis, mapping request keys to data types via the key-to-datatype mapper.

### Violations (`data/violations_all_apps_enriched.csv`)
Complete violation dataset with columns: app_id, violation_type, data_type, source, entity, and supporting evidence.

## License

This project is released for research purposes. Please cite our paper if you use this code or data in your work.
