# Milestone 1 datasets: synthetic Figma personas

Two CSV files, plus a validator script. Everything here is **synthetic** or **research notes**. Nothing describes real people or real Figma users.

| File | Rows | What it is |
|---|---|---|
| `persona_profiles.csv` | 16 | Demonstration personas for Figma usability testing |
| `research_sources.csv` | 16 | Sources actually consulted on 2026-10-12, with findings and limits |
| `validate_datasets.py` | - | Structural checks (run `python validate_datasets.py`) |

## persona_profiles.csv

Each row is one fictional persona. The 16 rows cover beginner learner, design student, intermediate and experienced designers, two frontend developers, product manager, freelancer, team collaborator, UX researcher, an accessibility-constraint designer, a non-designer, a tool switcher, a design lead, an interaction designer and a content designer.

**Core fields:** `persona_id`, `persona_label`, `role`, `experience_level`, `relevant_skills`, `product_familiarity`, `goals`, `motivations`, `preferences`, `working_style`, `behavioral_traits`, `confidence_level`, `learning_preferences`, `usability_needs`, `assumptions_and_limitations`, `creation_timestamp`, `update_timestamp`, `persona_status`, `evidence_type`.

**Fields added beyond your list, and why:**
- `archetype`: ties each row to the user type you asked for.
- `figma_features_in_scope`: the Figma features the persona touches, kept separate so documentation-backed facts are not mixed with assumptions.
- `work_context`: team and setting, used instead of demographics.
- `attribute_provenance`: says which fields are user-configurable, AI-assumed or documentation-supported.
- `source_ids`: links to `research_sources.csv`.
- `generation_method`, `is_synthetic`, `schema_version`: for traceability and for later storage work.

**Value rules:** `experience_level` is beginner / intermediate / advanced / expert. `confidence_level` is low / medium / high. `persona_status` is draft / active / archived (all rows are `draft`). Multi-value cells use `;` as separator. Timestamps are ISO 8601 UTC.

**Demographics:** deliberately left out (no age, gender, ethnicity, nationality). Role, skill and context fields carry what usability testing needs. This follows the stereotype risk reported in S12. Labels are descriptive nicknames, not human names.

## research_sources.csv

Only pages I opened or searched during this session are listed. Each row says what the source supports and what it does not. A blank `publication_date_if_available` means I did not see a date. `evidence_type` separates published evidence from official documentation. Persona rows use `ai_generated_example`.

## Known limitations

- **Persona content is AI-written.** Apart from feature names (backed by Figma Help pages S13-S16), goals, traits and behaviors are my design assumptions, not research findings. No real Figma users were interviewed or surveyed.
- **No validation against real users.** The personas should not be described as representative of Figma users until checked against real data.
- **Your original files were not available** in my environment, so nothing was reused, merged or checked against them. Traceability to those files is not established.
- **Source depth is uneven.** Several sources were read from search excerpts or abstracts only, as noted per row. For S08 I read only the video summary page, not the full NN/g article.
- **Coverage gaps.** No dedicated source was consulted on user interviews or surveys. Behavioral segmentation is covered only by a passing mention in S01. Kaggle and Hugging Face were not searched. Persona storage and lifecycle design have no sources; they will be design decisions.
- **Figma facts can go stale.** Seat rules and features were read on 2026-10-12.

## Not included yet

The generation engine, storage and lifecycle code, architecture diagram, tests, research summary and milestone report are not part of this delivery.
