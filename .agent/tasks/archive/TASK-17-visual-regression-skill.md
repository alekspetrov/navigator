# TASK-17: Visual Regression Integration Skill

**Status**: 🚧 In Progress
**Priority**: High
**Complexity**: Medium
**Version**: v3.3.0
**Created**: 2025-10-21

---

## 🎯 Objective

Create `visual-regression` skill to automate visual regression testing setup with Chromatic, Percy, or BackstopJS integration.

**User value**: Reduce visual regression setup from 2-3 hours to 5 minutes, ensure pixel-perfect implementation of designs, prevent design system drift.

---

## 📋 Context

Navigator v3.2 introduced `product-design` skill for Figma design handoff. Visual regression closes the loop:

```
Design (Figma) → Code (product-design) → Validation (visual-regression) → CI/CD
```

**Problem**: Setting up visual regression requires:
- Storybook configuration
- Test tool setup (Chromatic/Percy/BackstopJS)
- Story file generation
- CI/CD integration
- Design token validation

**Solution**: Auto-generate all configuration, stories, and CI workflows.

---

## 🏗️ Architecture

### Skill Structure

```
skills/visual-regression/
├── SKILL.md                          # Auto-invocation, instructions
├── functions/
│   ├── story_generator.py            # Generate Storybook stories
│   ├── chromatic_config_generator.py # Chromatic config
│   ├── ci_workflow_generator.py      # GitHub Actions/GitLab CI
│   └── vr_setup_validator.py         # Validate existing setup
├── templates/
│   ├── story-template.tsx.j2         # TypeScript story template
│   ├── chromatic-config.json.j2      # Chromatic configuration
│   ├── github-workflow.yml.j2        # GitHub Actions workflow
│   ├── gitlab-ci.yml.j2              # GitLab CI workflow
│   └── storybook-main.js.j2          # Storybook addon config
└── examples/
    ├── simple-component-vr.md        # Basic component example
    ├── design-system-vr.md           # Full design system setup
    └── existing-storybook-vr.md      # Add to existing Storybook
```

### Integration Points

1. **product-design skill**: After implementation plan, suggest VR setup
2. **CI/CD**: Generate GitHub Actions, GitLab CI, CircleCI configs
3. **Storybook**: Auto-detect existing setup, configure addons
4. **Test tools**: Support Chromatic, Percy, BackstopJS

---

## 🔧 Implementation Plan

### Phase 1: Skill Foundation (Core)

#### 1.1 Create Skill Directory & SKILL.md

**Location**: `skills/visual-regression/SKILL.md`

**Auto-invocation patterns**:
- "Set up visual regression"
- "Add Chromatic tests"
- "Create visual tests for [component]"
- "Configure visual regression testing"
- "Add screenshot testing"

**Skill description** (50 tokens for progressive disclosure):
```
Generate visual regression testing setup (Chromatic, Percy, BackstopJS).
Auto-generates Storybook stories, config files, CI workflows.
Use after implementing components to ensure pixel-perfect designs.
```

**Instructions include**:
- Detect framework (React, Vue, Svelte)
- Detect existing Storybook setup
- Choose test tool (Chromatic default, ask if ambiguous)
- Generate stories for component variants
- Create configuration files
- Generate CI/CD workflow
- Output setup instructions

#### 1.2 Create vr_setup_validator.py

**Purpose**: Detect existing setup, prevent conflicts

**Functions**:
```python
def detect_storybook_config(project_root: str) -> dict:
    """Detect Storybook version and configuration"""
    # Check .storybook/main.js, package.json
    # Return: version, addons, framework

def detect_vr_tool(project_root: str) -> str:
    """Detect existing VR tool (chromatic, percy, backstop)"""
    # Check package.json dependencies
    # Return: tool_name or None

def validate_component_path(component_path: str) -> dict:
    """Validate component exists, extract props"""
    # Parse component file
    # Return: component_name, props, variants

def check_dependencies(project_root: str) -> dict:
    """Check required dependencies installed"""
    # storybook, chromatic, @storybook/addon-chromatic
    # Return: installed, missing
```

**Output**: JSON with detected setup, recommendations

#### 1.3 Create story_generator.py

**Purpose**: Generate Storybook stories with all variants

**Functions**:
```python
def analyze_component(component_path: str, framework: str) -> dict:
    """Extract component props, variants, states"""
    # Parse TypeScript/JSX
    # Return: props, prop_types, default_values

def generate_story(component_info: dict, template_path: str) -> str:
    """Generate story file from template"""
    # Use Jinja2 template
    # Include: default, variants, states, interactions

def create_accessibility_tests(component_info: dict) -> str:
    """Add a11y tests to stories"""
    # @storybook/addon-a11y integration

def create_interaction_tests(component_info: dict) -> str:
    """Add interaction tests (play function)"""
    # @storybook/test integration
```

**Output**: Complete `.stories.tsx` file

#### 1.4 Create chromatic_config_generator.py

**Purpose**: Generate Chromatic configuration

**Functions**:
```python
def generate_chromatic_config(project_info: dict) -> str:
    """Generate chromatic.config.json"""
    # Settings: projectId, buildScriptName, externals, etc.

def generate_storybook_config(existing_config: dict) -> str:
    """Update .storybook/main.js with Chromatic addon"""
    # Add @chromatic-com/storybook addon

def generate_package_scripts(existing_scripts: dict) -> dict:
    """Add chromatic scripts to package.json"""
    # "chromatic": "npx chromatic"
    # "chromatic:ci": "npx chromatic --exit-zero-on-changes"
```

**Output**: Config files as strings

#### 1.5 Create ci_workflow_generator.py

**Purpose**: Generate CI/CD workflows

**Functions**:
```python
def generate_github_workflow(project_info: dict) -> str:
    """Generate .github/workflows/chromatic.yml"""
    # Trigger: push, pull_request
    # Jobs: build storybook, run chromatic

def generate_gitlab_ci(project_info: dict) -> str:
    """Generate .gitlab-ci.yml chromatic job"""

def generate_circleci_config(project_info: dict) -> str:
    """Generate .circleci/config.yml chromatic job"""

def detect_ci_platform(project_root: str) -> str:
    """Detect CI platform from existing files"""
    # Check for .github/, .gitlab-ci.yml, .circleci/
```

**Output**: CI workflow files

### Phase 2: Templates

#### 2.1 story-template.tsx.j2

**Jinja2 template for React/TypeScript stories**:

```typescript
import type { Meta, StoryObj } from '@storybook/react';
import { {{ component_name }} } from './{{ component_file }}';

const meta = {
  title: '{{ story_path }}',
  component: {{ component_name }},
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    {% for prop in props %}
    {{ prop.name }}: { control: '{{ prop.control }}' },
    {% endfor %}
  },
} satisfies Meta<typeof {{ component_name }}>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    {% for prop in default_props %}
    {{ prop.name }}: {{ prop.value }},
    {% endfor %}
  },
};

{% for variant in variants %}
export const {{ variant.name }}: Story = {
  args: {
    {% for prop in variant.props %}
    {{ prop.name }}: {{ prop.value }},
    {% endfor %}
  },
};
{% endfor %}
```

#### 2.2 chromatic-config.json.j2

```json
{
  "projectId": "{{ project_id }}",
  "buildScriptName": "build-storybook",
  "exitZeroOnChanges": true,
  "exitOnceUploaded": true,
  "onlyChanged": true,
  "externals": ["public/**"],
  "skip": "{{ skip_pattern }}",
  "ignoreLastBuildOnBranch": "{{ main_branch }}"
}
```

#### 2.3 github-workflow.yml.j2

```yaml
name: Visual Regression Tests

on:
  push:
    branches: [{{ branches }}]
  pull_request:
    branches: [{{ branches }}]

jobs:
  chromatic:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '{{ node_version }}'
          cache: '{{ package_manager }}'

      - name: Install dependencies
        run: {{ install_command }}

      - name: Run Chromatic
        uses: chromaui/action@latest
        with:
          projectToken: {% raw %}${{ secrets.CHROMATIC_PROJECT_TOKEN }}{% endraw %}
          exitZeroOnChanges: true
```

#### 2.4 storybook-main.js.j2

```javascript
module.exports = {
  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx)'],
  addons: [
    '@storybook/addon-links',
    '@storybook/addon-essentials',
    '@chromatic-com/storybook',
    '@storybook/addon-interactions',
  ],
  framework: {
    name: '@storybook/{{ framework }}',
    options: {},
  },
};
```

### Phase 3: Examples & Documentation

#### 3.1 simple-component-vr.md

Example: Setting up VR for single component

#### 3.2 design-system-vr.md

Example: Full design system with token validation

#### 3.3 existing-storybook-vr.md

Example: Adding VR to existing Storybook setup

### Phase 4: Integration

#### 4.1 Update plugin.json

Register `visual-regression` skill:

```json
{
  "name": "visual-regression",
  "description": "Generate visual regression testing setup (Chromatic/Percy/BackstopJS) with Storybook stories, config files, and CI workflows",
  "auto_invoke_patterns": [
    "set up visual regression",
    "add chromatic tests",
    "create visual tests",
    "configure visual regression",
    "add screenshot testing"
  ]
}
```

#### 4.2 Update product-design Skill

Add step in `product-design/SKILL.md`:

```markdown
## Step 6: Suggest Visual Regression Setup

After generating implementation plan:

"Consider setting up visual regression testing to ensure pixel-perfect implementation:

  'Set up visual regression for [ComponentName]'

This will generate Storybook stories, Chromatic config, and CI integration."
```

#### 4.3 Create SOP

**Location**: `.agent/sops/testing/visual-regression-setup.md`

**Contents**:
- Quick start guide
- Tool comparison (Chromatic vs Percy vs BackstopJS)
- Setup checklist
- Troubleshooting
- Integration with design workflow

---

## 🎯 Success Criteria

### Functional Requirements

- ✅ Auto-detects framework (React, Vue, Svelte)
- ✅ Auto-detects existing Storybook setup
- ✅ Generates stories with all component variants
- ✅ Generates Chromatic/Percy/BackstopJS config
- ✅ Generates CI/CD workflows (GitHub/GitLab/CircleCI)
- ✅ Provides setup instructions
- ✅ Auto-invokes on natural language patterns

### Quality Requirements

- ✅ Generated stories are TypeScript-safe
- ✅ Accessibility tests included (addon-a11y)
- ✅ Interaction tests included (addon-interactions)
- ✅ Non-destructive (backs up existing configs)
- ✅ Validates dependencies before generating

### Documentation Requirements

- ✅ SKILL.md with clear instructions
- ✅ 3 examples (simple, design system, existing setup)
- ✅ SOP for visual regression workflow
- ✅ Integration with product-design documented

---

## 🧪 Testing Strategy

### Manual Testing (nav-test project)

```bash
# Test 1: New component VR setup
"Set up visual regression for ProfileCard component"
→ Verify: story generated, config created, CI workflow added

# Test 2: Existing Storybook
"Add Chromatic to existing Storybook"
→ Verify: addon added, config created, no conflicts

# Test 3: Design system
"Set up visual regression for entire design system"
→ Verify: stories for all components, token validation

# Test 4: CI detection
"Configure visual regression for GitHub Actions"
→ Verify: .github/workflows/chromatic.yml created
```

### Validation Checks

- Generated TypeScript compiles
- Storybook builds successfully
- Chromatic CLI runs (with mock token)
- CI workflow syntax valid

---

## 📊 Token Efficiency

**Before** (manual setup):
- Read Storybook docs: 20k tokens
- Read Chromatic docs: 15k tokens
- Write stories manually: 10k tokens
- Configure CI: 5k tokens
- **Total**: 50k tokens

**After** (visual-regression skill):
- Skill auto-invokes: 0 tokens (natural language)
- Skill instructions load: 3k tokens
- Predefined functions execute: 0 tokens
- **Total**: 3k tokens

**Savings**: 94% (47k tokens saved)

---

## 🚀 Rollout Plan

### Phase 1: Core Skill (v3.3.0-alpha)
- Chromatic support only
- React/TypeScript only
- GitHub Actions only
- Test internally

### Phase 2: Multi-Tool Support (v3.3.0-beta)
- Add Percy support
- Add BackstopJS support
- Test with community

### Phase 3: Multi-Framework (v3.3.0)
- Add Vue support
- Add Svelte support
- Add GitLab CI, CircleCI
- Full release

---

## 📝 Documentation Updates

### Files to Update

1. **README.md**: Add visual-regression to skills list
2. **DEVELOPMENT-README.md**: Add TASK-17 to completed tasks
3. **ROADMAP.md**: Move visual regression from planned to completed
4. **ARCHITECTURE.md**: Document visual-regression skill architecture
5. **RELEASE-NOTES-v3.3.0.md**: Create release notes

### New Files

1. `.agent/sops/testing/visual-regression-setup.md`
2. `skills/visual-regression/SKILL.md`
3. `skills/visual-regression/functions/*.py` (4 files)
4. `skills/visual-regression/templates/*.j2` (5 files)
5. `skills/visual-regression/examples/*.md` (3 files)

---

## 🎓 Lessons for Future Skills

### What Worked Well

- Predefined functions for complex logic
- Templates for consistent output
- Multi-tool support (Chromatic/Percy/BackstopJS)
- Integration with existing skills (product-design)

### What Could Be Better

- Consider MCP server for external tool integration
- Add visual regression dashboard (future v3.4)
- Support more CI platforms out of the box

---

## 📅 Timeline

- **Day 1**: Skill structure, SKILL.md, validator function
- **Day 2**: story_generator.py, templates
- **Day 3**: Config generators (chromatic, CI)
- **Day 4**: Examples, documentation
- **Day 5**: Integration, testing, release

**Estimated effort**: 5 days
**Target release**: v3.3.0 (Q4 2025 → Now 2025-10-21)

---

## 🔗 Related Tasks

- **TASK-16**: Product Design Skill (integration point)
- **TASK-13**: OpenTelemetry (measure VR setup token savings)
- **TASK-10**: Project Skills Generation (pattern to follow)

---

**Created by**: Navigator autonomous task planning
**Last updated**: 2025-10-21
**Version**: v3.3.0
