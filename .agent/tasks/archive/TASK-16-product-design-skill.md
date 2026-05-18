# TASK-16: Product Design Skill with Figma MCP Integration

**Created**: 2025-10-21
**Status**: In Progress
**Priority**: High
**Complexity**: High
**Estimated Time**: 8-12 hours

---

## Context

**Problem**: Design handoff from Figma to code is manual, time-consuming (6-10 hours), and error-prone. Design system drift happens when tokens/components diverge between design and implementation.

**Goal**: Create a Navigator skill that automates design review, token extraction, component mapping, and implementation planning using Figma MCP integration. Reduce design handoff time from 6-10 hours to 15-20 minutes (95% reduction).

**Why This Matters**:
- Eliminates manual design token extraction (currently 1+ hour)
- Detects design system drift automatically
- Prevents duplicate components via similarity matching
- Generates implementation plans with acceptance criteria
- Maintains Navigator's token-efficient, autonomous workflow

---

## Design Decisions

### Architecture: Hybrid Skill

**Progressive Enhancement Strategy**:
- **Phase 1**: Manual design review (works without Figma MCP)
- **Phase 2**: Automated extraction via Figma MCP
- **Phase 3**: Advanced features (drift detection, visual regression)

**Why Hybrid**:
- Immediate value without MCP dependency
- Graceful degradation when Figma Desktop not running
- Supports teams without Figma Enterprise (Code Connect)

### Documentation Structure

```
.agent/
└── design-system/           # New directory (separate from system/)
    ├── design-tokens.json   # DTCG format (W3C standard)
    ├── ui-kit-inventory.md  # Component catalog
    ├── component-mapping.json # Figma node ID → code path
    └── reviews/             # Temporal design reviews
        └── YYYY-MM-DD-[feature].md
```

**Why separate from `system/`**:
- Design reviews are temporal (archived after implementation)
- System docs are living architecture
- Different loading patterns (reviews on-demand, inventory always)

### Token Optimization

**Never load**:
- All design review reports (50+ over time = 250k+ tokens)
- Full Figma MCP responses (can be 350k+ tokens)
- Entire UI kit component code

**Always load when skill active**:
- `ui-kit-inventory.md` (~3k tokens)
- `design-tokens.json` (~2k tokens)
- Specific design review for active task (~5k tokens)

**Total**: ~10k tokens vs 150k+ loading everything (93% reduction)

---

## Implementation Plan

### Phase 1: Core Skill Structure (Manual Workflow)

**Goal**: Working skill without Figma MCP dependency

#### Step 1.1: Create Skill Directory Structure

```bash
.claude-plugin/skills/product-design/
├── SKILL.md                    # Main skill prompt (2-3k tokens)
├── functions/
│   ├── design_analyzer.py      # Extract patterns from Figma data
│   ├── token_extractor.py      # Variables → DTCG design tokens
│   ├── component_mapper.py     # Figma component → code mapping
│   ├── design_system_auditor.py # Compare design vs implementation
│   └── implementation_planner.py # Generate task docs
├── templates/
│   ├── design-review-report.md # Analysis output template
│   ├── design-tokens-diff.md   # Token changes summary
│   └── ui-kit-impact.md        # Component library impact
└── examples/
    └── dashboard-redesign-review.md # Reference example
```

**Acceptance Criteria**:
- [ ] Directory structure created
- [ ] All function files exist with docstrings
- [ ] All template files exist with placeholder content
- [ ] Example design review demonstrates output format

#### Step 1.2: Implement design_analyzer.py

**Purpose**: Extract design patterns from Figma MCP data or manual analysis

**Core Algorithm**:
```python
def analyze_design(figma_metadata, variables, ui_kit_inventory):
    """
    Analyzes Figma design data and compares against existing UI kit.

    Args:
        figma_metadata: Figma MCP get_metadata response or manual description
        variables: Figma MCP get_variable_defs response or manual token list
        ui_kit_inventory: Current UI kit inventory JSON

    Returns:
        {
            "new_tokens": [...],
            "new_components": [...],
            "similar_components": [...],
            "breaking_changes": [...]
        }
    """
```

**Features**:
- Extract unique component types from metadata
- Compare against ui_kit_inventory
- Identify patterns (repeated structures = potential components)
- Calculate similarity scores (Levenshtein distance on structure)
- Flag breaking changes (modified existing component mappings)

**Acceptance Criteria**:
- [ ] Parses Figma MCP metadata format (XML-like sparse structure)
- [ ] Identifies new components not in ui_kit_inventory
- [ ] Calculates similarity scores for potential reuse (>70% = suggest extending existing)
- [ ] Returns structured JSON output
- [ ] Works with manual input when MCP unavailable

#### Step 1.3: Implement token_extractor.py

**Purpose**: Convert Figma variables to DTCG design tokens

**DTCG Format** (W3C Design Tokens Community Group spec):
```json
{
  "color": {
    "primary": {
      "500": {
        "$value": "#3B82F6",
        "$type": "color",
        "$description": "Primary brand color - buttons, links"
      }
    }
  },
  "spacing": {
    "md": {
      "$value": "16px",
      "$type": "dimension"
    }
  }
}
```

**Features**:
- Parse Figma `get_variable_defs` response
- Semantic naming alignment (Figma "Primary 500" → "color.primary.500")
- Type detection (color, dimension, typography, shadow)
- Conflict resolution (flag manual review when tokens diverge)
- Generate diff summary (added/modified/removed)

**Acceptance Criteria**:
- [ ] Outputs valid DTCG format JSON
- [ ] Handles all token types (color, spacing, typography, radius, shadow)
- [ ] Generates diff vs existing design-tokens.json
- [ ] Preserves manual customizations in existing tokens
- [ ] Works with manual token list when MCP unavailable

#### Step 1.4: Implement component_mapper.py

**Purpose**: Map Figma components to codebase components

**Mapping Format**:
```json
{
  "figma_node_12345": {
    "figma_name": "Button/Primary/Large",
    "code_path": "src/components/ui/Button.tsx",
    "code_component": "Button",
    "props_mapping": {
      "variant": "primary",
      "size": "lg"
    },
    "confidence": 0.98
  }
}
```

**Features**:
- Parse Figma `get_code_connect_map` response
- Search codebase for component files (glob patterns)
- Fuzzy matching component names (Button, ButtonComponent, Btn)
- Extract variant mappings from component props
- Identify unmapped components (need creation)

**Acceptance Criteria**:
- [ ] Generates component-mapping.json
- [ ] Searches project using glob patterns (*.tsx, *.vue, *.jsx)
- [ ] Fuzzy matches component names (90%+ confidence threshold)
- [ ] Lists unmapped Figma components separately
- [ ] Updates existing mappings without overwriting manual edits

#### Step 1.5: Implement design_system_auditor.py

**Purpose**: Compare design vs implementation, find drift

**Audit Checks**:
1. Token drift (Figma vs design-tokens.json)
2. Component reuse opportunities (similar structures)
3. Unused tokens (exist in code, not in Figma)
4. Missing tokens (exist in Figma, not in code)
5. Tailwind config alignment

**Output Format**:
```markdown
## Token Alignment

✅ **In Sync**: 87 tokens match exactly
⚠️  **Drift Detected**: 5 tokens modified in Figma, not in code
  - color.primary.600: #2563EB (Figma) vs #1D4ED8 (code)
❌ **Missing in Code**: 12 new tokens from design
🗑️  **Unused in Design**: 3 tokens exist in code, not used in Figma

## Component Reuse Analysis

**StatBadge**: 78% similarity to existing `Badge` component
- Recommendation: Extend Badge with `variant="stat"` prop
- Avoids: Creating duplicate component
```

**Acceptance Criteria**:
- [ ] Compares Figma tokens vs design-tokens.json
- [ ] Identifies drift with specific values
- [ ] Calculates component similarity scores
- [ ] Parses Tailwind config for token usage
- [ ] Generates markdown audit report

#### Step 1.6: Implement implementation_planner.py

**Purpose**: Generate implementation task docs with phased breakdown

**Template-Driven Generation**:
- Uses `templates/design-review-report.md` for structure
- Injects analysis results from previous functions
- Generates phased implementation plan
- Creates acceptance criteria checklist
- Estimates complexity per component

**Task Doc Structure**:
```markdown
# TASK-XX: [Feature] Implementation

## Design Review
Reference: .agent/design-system/reviews/YYYY-MM-DD-[feature].md

## Implementation Phases

### Phase 1: Design Tokens (estimated 2 hours)
**Priority**: High (foundation)

#### Subtasks
1. Add new color tokens to design-tokens.json
2. Run Style Dictionary build
3. Update Tailwind @theme

**Acceptance Criteria**:
- [ ] All new tokens available in Tailwind utilities
- [ ] No breaking changes to existing token references

### Phase 2: [Component Name] (estimated 3 hours)
...
```

**Acceptance Criteria**:
- [ ] Generates valid Navigator task document
- [ ] Phases ordered by dependency (tokens → atoms → molecules → organisms)
- [ ] Complexity estimates included
- [ ] Acceptance criteria for each phase
- [ ] Migration strategy for breaking changes

#### Step 1.7: Create SKILL.md Main Prompt

**Structure** (following Navigator skill pattern):

```markdown
---
auto_invoke:
  triggers:
    - "Review this design"
    - "Analyze Figma mockup"
    - "Design handoff for {feature}"
    - "Check design system impact"
    - "Plan implementation for design"
  description: "Automates design review, token extraction, and implementation planning"
---

# Product Design Skill

[Skill instructions...]
```

**Key Sections**:
1. **What This Skill Does** (problem statement)
2. **When to Auto-Invoke** (trigger scenarios)
3. **Workflow Protocol** (5-step process)
4. **Figma MCP Integration** (when available, how to use)
5. **Manual Workflow** (fallback without MCP)
6. **Design System Documentation** (loading strategy)
7. **Predefined Functions** (what each does)
8. **Templates** (output formats)
9. **Token Optimization** (Navigator principles)
10. **Troubleshooting** (common issues)

**Acceptance Criteria**:
- [ ] SKILL.md is 2-3k tokens (measured)
- [ ] Auto-invoke triggers comprehensive
- [ ] Clear workflow steps (1-5)
- [ ] Examples for manual and MCP workflows
- [ ] Troubleshooting section covers MCP token limits

#### Step 1.8: Create Template Files

**templates/design-review-report.md**:
- Header with date, Figma link, reviewer
- New design tokens section (added/modified/removed)
- New components section (atoms/molecules/organisms)
- Design system impact analysis
- Implementation recommendations (phased approach)

**templates/design-tokens-diff.md**:
- Side-by-side comparison table
- Visual indicators (✅ match, ⚠️ drift, ❌ missing, 🗑️ unused)
- Migration notes for breaking changes

**templates/ui-kit-impact.md**:
- Component reuse opportunities
- Similarity scores with recommendations
- New components required
- Breaking changes to existing components

**Acceptance Criteria**:
- [ ] All templates use consistent markdown formatting
- [ ] Placeholder variables clearly marked ({{PLACEHOLDER}})
- [ ] Templates match example output in documentation
- [ ] Visual indicators (emoji) used appropriately

#### Step 1.9: Create Example Design Review

**examples/dashboard-redesign-review.md**:
- Complete example matching template structure
- Real-world scenario (dashboard with metrics)
- Shows token extraction results
- Shows component analysis
- Shows implementation plan

**Purpose**: Reference for users and validation of template quality

**Acceptance Criteria**:
- [ ] Example demonstrates all template sections
- [ ] Realistic design scenario (not trivial)
- [ ] Shows both simple and complex components
- [ ] Includes breaking change example

---

### Phase 2: Figma MCP Integration

**Goal**: Automate extraction using Figma Desktop MCP server

#### Step 2.1: MCP Server Detection

**Function**: `detect_mcp_server()`

**Logic**:
```python
def detect_mcp_server():
    """
    Detects which Figma MCP server is available.

    Returns:
        {
            "type": "local" | "remote" | "none",
            "url": "http://127.0.0.1:3845/mcp" | "https://mcp.figma.com/mcp" | None,
            "tools_available": ["get_design_context", "get_variable_defs", ...]
        }
    """
```

**Detection Strategy**:
1. Check for local server (http://127.0.0.1:3845/mcp)
2. If unavailable, check for remote server config
3. If none, return manual workflow mode

**Acceptance Criteria**:
- [ ] Detects local Figma Desktop MCP server
- [ ] Falls back to remote server if configured
- [ ] Returns "none" when no MCP available
- [ ] Lists available tools per server type

#### Step 2.2: Large Selection Handling

**Problem**: Figma MCP returns >350k tokens for large screens, exceeds Claude Code 25k default limit

**Solution**: Metadata-first approach

**Workflow**:
```markdown
1. Use `get_metadata` first (sparse XML, low tokens)
2. Parse metadata to identify component node IDs
3. Fetch components individually via `get_design_context`
4. Aggregate results
```

**Environment Variable Recommendation**:
```bash
# In skill documentation
export MAX_MCP_OUTPUT_TOKENS=100000
```

**Acceptance Criteria**:
- [ ] Uses `get_metadata` before `get_design_context`
- [ ] Breaks large selections into smaller chunks
- [ ] Documents MAX_MCP_OUTPUT_TOKENS requirement
- [ ] Handles timeout errors gracefully

#### Step 2.3: Automated Token Extraction

**Integration**: `token_extractor.py` + `get_variable_defs`

**Workflow**:
1. Call Figma MCP `get_variable_defs`
2. Parse response JSON
3. Convert to DTCG format
4. Compare with existing design-tokens.json
5. Generate diff summary

**Acceptance Criteria**:
- [ ] Automatically extracts all Figma variables
- [ ] Handles all variable types (color, number, string, boolean)
- [ ] Preserves variable descriptions from Figma
- [ ] Generates complete diff report

#### Step 2.4: Automated Component Mapping

**Integration**: `component_mapper.py` + `get_code_connect_map`

**Workflow**:
1. Call Figma MCP `get_code_connect_map`
2. Parse response with node IDs → code paths
3. Verify code paths exist in project
4. Update component-mapping.json

**Note**: Requires Figma Enterprise for Code Connect

**Acceptance Criteria**:
- [ ] Extracts Code Connect mappings when available
- [ ] Falls back to fuzzy matching when Code Connect unavailable
- [ ] Validates code paths exist before mapping
- [ ] Warns when Code Connect not configured

---

### Phase 3: Advanced Features

**Goal**: Enterprise-grade design system workflow

#### Step 3.1: Visual Regression Test Generation

**Integration**: Generate Chromatic test configuration

**Output**: `.storybook/test-runner.ts` config for visual regression

**Acceptance Criteria**:
- [ ] Generates Chromatic configuration
- [ ] Creates stories for new components
- [ ] Documents visual testing workflow

#### Step 3.2: Design System Drift Alerts

**Workflow**: Run auditor on every design review, flag high-priority drift

**Alert Thresholds**:
- 🚨 Critical: >10 tokens drifted, breaking changes
- ⚠️  Warning: >5 tokens drifted, no breaking changes
- ℹ️  Info: New tokens/components added

**Acceptance Criteria**:
- [ ] Automatic drift detection on every review
- [ ] Priority levels assigned
- [ ] Actionable recommendations provided

#### Step 3.3: Breaking Change Migration Planner

**Feature**: Generate migration guides for breaking component changes

**Output**: Migration markdown with:
- Before/after code examples
- Automated codemod scripts (if possible)
- Manual steps required
- Rollout strategy

**Acceptance Criteria**:
- [ ] Detects breaking changes automatically
- [ ] Generates migration documentation
- [ ] Provides rollback strategy

---

### Phase 4: Project-Specific Generation via nav-skill-creator

**Goal**: Zero-config skill generation per project

#### Step 4.1: Codebase Analysis Integration

**nav-skill-creator workflow**:
```
1. User: "Create a skill for product design with Figma integration"
2. nav-skill-creator invoked
3. Analyzes codebase:
   - React vs Vue detection
   - Tailwind config location
   - Component directory structure
   - Testing framework (Jest, Vitest)
   - Storybook presence
4. Generates product-design skill:
   - Tailored to framework
   - Pre-configured paths
   - Template examples match project conventions
5. Creates .agent/design-system/ structure
6. Runs initial UI kit inventory scan
7. Extracts current design tokens from Tailwind config
```

**Acceptance Criteria**:
- [ ] nav-skill-creator can generate product-design skill
- [ ] Auto-detects framework (React/Vue/Svelte)
- [ ] Pre-configures all file paths
- [ ] Scans existing components for initial inventory

#### Step 4.2: Initial UI Kit Inventory Scan

**Function**: `scan_existing_components()`

**Logic**:
```python
def scan_existing_components(project_root):
    """
    Scans codebase for existing UI components.

    Returns:
        {
            "atoms": [...],
            "molecules": [...],
            "organisms": [...]
        }
    """
```

**Detection Strategy**:
- Glob search: `src/components/**/*.{tsx,vue,jsx}`
- Parse component exports
- Categorize by directory structure (if atomic design used)
- Extract props/variants via AST parsing

**Acceptance Criteria**:
- [ ] Finds all component files in project
- [ ] Extracts component names and paths
- [ ] Attempts atomic design categorization
- [ ] Generates initial ui-kit-inventory.md

---

## Testing Strategy

### Unit Tests

**Functions to Test**:
- `design_analyzer.py`: Component extraction, similarity matching
- `token_extractor.py`: DTCG format conversion, diff generation
- `component_mapper.py`: Fuzzy matching, path validation
- `design_system_auditor.py`: Drift detection, comparison logic
- `implementation_planner.py`: Task doc generation

**Framework**: pytest

**Coverage Target**: 80%+ for all functions

### Integration Tests

**Scenarios**:
1. Full manual workflow (no MCP)
2. Full automated workflow (with MCP mocked)
3. Hybrid workflow (partial MCP data)
4. Error handling (MCP timeout, invalid Figma data)

**Test Data**:
- Mock Figma MCP responses (JSON fixtures)
- Sample design-tokens.json
- Sample ui-kit-inventory.md

### Manual Testing

**Test Project**: Navigator plugin itself

**Test Scenarios**:
1. Review hypothetical dashboard redesign (manual)
2. Extract tokens from mock Figma data
3. Generate implementation plan
4. Verify task doc follows Navigator format

---

## Rollout Plan

### Step 1: Internal Testing (Navigator Project)
- Test skill on Navigator plugin codebase
- Refine based on real usage
- Document learnings

### Step 2: Documentation Update
- Add product-design skill to README.md
- Update plugin.json with new skill
- Create usage guide in .agent/sops/development/

### Step 3: Version Bump
- Increment to v3.2.0 (minor version, new feature)
- Update marketplace.json
- Run version audit script

### Step 4: Release
- Commit all changes
- Create git tag v3.2.0
- Push to GitHub
- Create GitHub release with changelog

---

## Success Metrics

### Efficiency Gains

**Before Product Design Skill**:
- Manual design review: 2-4 hours
- Component discovery: 1-2 hours
- Token extraction: 1 hour
- Implementation planning: 2-3 hours
- **Total**: 6-10 hours

**After**:
- Automated design review: 5 minutes
- Component discovery: Instant
- Token extraction: Instant
- Implementation planning: 10 minutes
- **Total**: 15-20 minutes (developer review)

**Time Savings**: ~95% reduction

### Quality Metrics

- **Design system drift**: Detected automatically on every review
- **Component reuse rate**: Tracked in ui-kit-inventory
- **Token consistency**: 100% via automated sync
- **Implementation accuracy**: Acceptance criteria in every task

---

## Documentation Requirements

### README.md Update

Add section:
```markdown
### product-design

Automates design review, token extraction, and implementation planning.

**Auto-invokes when user says**:
- "Review this design"
- "Analyze Figma mockup"
- "Design handoff for [feature]"
- "Check design system impact"

**Features**:
- Figma MCP integration (auto-detects local/remote server)
- Design token extraction (DTCG format)
- Component mapping (Figma → code)
- Design system drift detection
- Implementation plan generation
- Tailwind CSS integration

**Setup** (optional - enhances automation):
```bash
# Install Figma Desktop MCP
claude mcp add --transport http figma-desktop http://127.0.0.1:3845/mcp
```

**Usage**:
```
"Review the dashboard redesign from Figma"
# Skill analyzes design, extracts tokens, maps components,
# generates implementation plan as Navigator task doc
```
```

### SOP Creation

**File**: `.agent/sops/development/product-design-workflow.md`

**Contents**:
- Step-by-step workflow
- Figma MCP setup instructions
- Troubleshooting common issues
- Token optimization best practices

---

## Risks and Mitigations

### Risk: Figma MCP Token Limit Exceeded

**Likelihood**: High (large designs can be 350k+ tokens)

**Mitigation**:
- Metadata-first approach (use `get_metadata` before `get_design_context`)
- Component-by-component extraction (avoid full screen selections)
- Document `MAX_MCP_OUTPUT_TOKENS=100000` requirement
- Clear error messaging with resolution steps

### Risk: Figma MCP Not Available

**Likelihood**: Medium (requires Figma Desktop running)

**Mitigation**:
- Graceful fallback to manual workflow
- Clear messaging about manual vs automated modes
- Manual workflow still provides value (template-driven analysis)

### Risk: Component Similarity Matching False Positives

**Likelihood**: Medium (algorithm may suggest wrong component)

**Mitigation**:
- Confidence threshold (>70% for recommendations)
- Always flag for manual review
- Show similarity score and reasoning
- Developer has final decision

### Risk: DTCG Format Changes

**Likelihood**: Low (W3C spec approaching v1.0.0)

**Mitigation**:
- Monitor W3C Design Tokens spec updates
- Version DTCG format in design-tokens.json
- Provide migration script if spec changes

---

## Dependencies

### Required
- Python 3.8+ (for predefined functions)
- Navigator v3.1+ (skill architecture)

### Optional (Enhanced Features)
- Figma Desktop app (for local MCP server)
- Figma Enterprise plan (for Code Connect)
- Style Dictionary (for token transformation)
- Tailwind CSS 4.0+ (for @theme support)

---

## Next Steps

1. ✅ Create TASK-16 implementation plan document (this file)
2. ⏳ Create skill directory structure
3. ⏳ Implement Phase 1 functions (manual workflow)
4. ⏳ Create SKILL.md main prompt
5. ⏳ Create template files
6. ⏳ Create example design review
7. ⏳ Register skill in plugin.json
8. ⏳ Test manual workflow
9. ⏳ Implement Phase 2 (Figma MCP integration)
10. ⏳ Update documentation (README, SOPs)
11. ⏳ Version bump and release

---

**Last Updated**: 2025-10-21
**Navigator Version**: 3.1.0
**Target Version**: 3.2.0
