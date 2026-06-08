# Tasks: SH17 Dataset Migration

**Input**: Design documents from `/specs/001-sh17-migration/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- No setup tasks required. We are modifying an existing file.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- No foundational infrastructure changes required.

---

## Phase 3: User Story 1 - Automatic PPE Violation Detection (Priority: P1) 🎯 MVP

**Goal**: System automatically flags workers missing required PPE using the SH17 dataset model, determining violations by bounding box overlap rather than negative classes.

**Independent Test**: Feed an image without a helmet, verify a Helmet Violation is triggered.

### Implementation for User Story 1

- [x] T001 [US1] Remove yolov8n.pt fallback bug in `f:\SmartFactory\backend\detector.py` so the system fails gracefully if `best.pt` is missing.
- [x] T002 [US1] Update `CLASS_MAP` with 17 SH17 classes in `f:\SmartFactory\backend\detector.py`.
- [x] T003 [US1] Remove double-drawn bounding box bug (`annotated_frame = result.plot()`) in `f:\SmartFactory\backend\detector.py`.
- [x] T004 [US1] Remove old hardcoded filter logic for `cls_id == 0` (color/aspect-ratio) in `f:\SmartFactory\backend\detector.py`.
- [x] T005 [US1] Implement IoA spatial overlap logic for helmet and vest violations in `f:\SmartFactory\backend\detector.py`.

**Checkpoint**: At this point, the backend is fully migrated and should correctly identify PPE violations via spatial overlap.

---

## Phase 4: User Story 2 - Small PPE Detection Support (Priority: P2)

**Goal**: Identify smaller safety equipment like Gloves and Glasses.

**Independent Test**: Stand in front of camera with gloves and verify the `Gloves` bounding box appears.

### Implementation for User Story 2

- *No independent code tasks needed. The SH17 `CLASS_MAP` update (T002) implicitly resolves this.*

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T006 Run quickstart.md validation locally using `python app.py` and a camera feed.

---

## Dependencies & Execution Order

- **Setup / Foundational**: N/A
- **User Story 1 (P1)**: Contains the core rewrites for `detector.py`. These must be executed sequentially (T001 -> T005).
- **User Story 2 (P2)**: Included in US1 changes.
- **Polish**: Depends on all code tasks being completed.
