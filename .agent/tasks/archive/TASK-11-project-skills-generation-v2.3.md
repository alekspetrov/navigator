# TASK-11: Project-Specific Skills Generation (v2.3)

**Created**: 2025-10-19
**Status**: Planning
**Priority**: High
**Complexity**: Medium

---

## Context

Following the successful implementation of nav-skill-creator in v2.2, we now use it to generate the 5 project-specific skills outlined in the v2.1-v2.2 roadmap (TASK-08). This validates the self-improving capability and provides high-value automation for common development patterns.

### Current State (v2.2.0)

**Core Navigator skills** (7 total):
- nav-start (session initialization)
- nav-marker (context save points)
- nav-compact (smart context management)
- nav-task (task documentation)
- nav-sop (standard operating procedures)
- nav-skill-creator (skill generation)
- plugin-slash-command (first project-specific skill)

**What's missing**: Generic framework skills for common development patterns

---

## Problem Statement

**Developers repeat common patterns manually**:
- Creating React/Vue components (boilerplate, tests, styles)
- Adding REST/GraphQL API endpoints (routes, validation, tests)
- Database migrations (schema changes, rollbacks)
- Writing backend tests (unit, integration, mocks)
- Writing frontend tests (component, snapshot, e2e)

**Without project-specific skills**:
- Read 3-5 examples manually (~15k tokens)
- Copy-paste and modify patterns
- Inconsistent implementations
- Missing tests
- Token waste

**With project-specific skills**:
- Auto-invoke on trigger phrases
- Consistent output via templates
- Generated with tests
- 80% token reduction (15k → 3k)

---

## Objectives

### Primary Goal
Generate 5 project-specific skills using nav-skill-creator to automate common development patterns.

### Success Criteria
- [ ] 5 skills generated and working
- [ ] Each skill has functions, templates, examples
- [ ] Auto-invocation works correctly
- [ ] Skills produce consistent output
- [ ] Documentation complete
- [ ] Token efficiency validated (80% reduction)

---

## Skills to Generate

### 1. frontend-component

**Purpose**: Create React/Vue/Svelte components with tests and styles

**Trigger phrases**:
- "create component"
- "add component"
- "new component"
- "build a component"

**Components**:
- `functions/component_generator.py` - Generate component code
- `functions/style_generator.py` - Generate styled-components/CSS
- `functions/test_generator.py` - Generate component tests
- `templates/component-template.tsx` - Base component structure
- `templates/test-template.spec.tsx` - Test structure
- `examples/example-button.tsx` - Example functional component
- `examples/example-hook.ts` - Example custom hook

**Token savings**: 15k → 3k (80% reduction)

---

### 2. backend-endpoint

**Purpose**: Create REST/GraphQL API endpoints with validation and tests

**Trigger phrases**:
- "add endpoint"
- "create API"
- "new route"
- "add route"

**Components**:
- `functions/endpoint_generator.py` - Generate route handler
- `functions/route_validator.py` - Validate route structure
- `functions/middleware_generator.py` - Generate middleware
- `templates/endpoint-template.ts` - REST endpoint structure
- `templates/test-template.spec.ts` - API test structure
- `examples/rest-endpoint.ts` - Example REST route
- `examples/graphql-resolver.ts` - Example GraphQL resolver

**Token savings**: 15k → 3k (80% reduction)

---

### 3. database-migration

**Purpose**: Create database migrations with rollback capability

**Trigger phrases**:
- "create migration"
- "add table"
- "modify schema"
- "change database"

**Components**:
- `functions/migration_generator.py` - Generate migration SQL
- `functions/schema_validator.py` - Validate schema changes
- `functions/rollback_generator.py` - Generate rollback SQL
- `templates/migration-template.sql` - Migration structure
- `templates/rollback-template.sql` - Rollback structure
- `examples/add-table-migration.sql` - Example table creation
- `examples/modify-column-migration.sql` - Example column change

**Token savings**: 12k → 3k (75% reduction)

---

### 4. backend-test

**Purpose**: Write backend tests (unit, integration, mocks)

**Trigger phrases**:
- "write test for"
- "add test"
- "test this"
- "create test"

**Components**:
- `functions/test_generator.py` - Generate test code
- `functions/fixture_generator.py` - Generate test fixtures
- `functions/mock_generator.py` - Generate mocks
- `templates/unit-test-template.spec.ts` - Unit test structure
- `templates/integration-test-template.spec.ts` - Integration test structure
- `examples/api-test-example.ts` - Example API test
- `examples/service-test-example.ts` - Example service test

**Token savings**: 18k → 3k (83% reduction)

---

### 5. frontend-test

**Purpose**: Write frontend component tests (unit, snapshot, e2e)

**Trigger phrases**:
- "test this component"
- "write component test"
- "test component"
- "add component test"

**Components**:
- `functions/component_test_generator.py` - Generate component tests
- `functions/snapshot_generator.py` - Generate snapshot tests
- `templates/component-test-template.spec.tsx` - Component test structure
- `templates/e2e-test-template.spec.ts` - E2E test structure
- `examples/button-test-example.tsx` - Example button test
- `examples/form-test-example.tsx` - Example form test

**Token savings**: 16k → 3k (81% reduction)

---

## Implementation Plan

### Phase 1: Generate frontend-component Skill

**Steps**:
1. Invoke nav-skill-creator with task: "Generate frontend-component skill"
2. Provide context:
   - Common React component patterns
   - TypeScript/JSX syntax
   - styled-components or CSS modules
   - Testing patterns (Jest, React Testing Library)
3. Review generated skill structure
4. Test generated skill in nav-test project
5. Refine if needed

**Validation**:
- Skill auto-invokes on "create component"
- Generates component with tests
- Follows React best practices
- Output is consistent

---

### Phase 2: Generate backend-endpoint Skill

**Steps**:
1. Invoke nav-skill-creator with task: "Generate backend-endpoint skill"
2. Provide context:
   - Express/Fastify/NestJS patterns
   - REST API conventions
   - Request validation
   - Error handling
3. Review generated skill structure
4. Test generated skill in nav-test project
5. Refine if needed

**Validation**:
- Skill auto-invokes on "add endpoint"
- Generates route with validation
- Includes error handling
- Includes tests

---

### Phase 3: Generate database-migration Skill

**Steps**:
1. Invoke nav-skill-creator with task: "Generate database-migration skill"
2. Provide context:
   - SQL migration patterns
   - Knex/Prisma/TypeORM conventions
   - Rollback strategies
   - Schema validation
3. Review generated skill structure
4. Test generated skill in nav-test project
5. Refine if needed

**Validation**:
- Skill auto-invokes on "create migration"
- Generates migration + rollback
- Validates schema changes
- Follows migration tool conventions

---

### Phase 4: Generate backend-test Skill

**Steps**:
1. Invoke nav-skill-creator with task: "Generate backend-test skill"
2. Provide context:
   - Jest/Vitest testing patterns
   - Mock strategies (dependency injection)
   - Fixture management
   - Integration test patterns
3. Review generated skill structure
4. Test generated skill in nav-test project
5. Refine if needed

**Validation**:
- Skill auto-invokes on "write test for"
- Generates comprehensive tests
- Includes fixtures and mocks
- Follows testing best practices

---

### Phase 5: Generate frontend-test Skill

**Steps**:
1. Invoke nav-skill-creator with task: "Generate frontend-test skill"
2. Provide context:
   - React Testing Library patterns
   - Snapshot testing
   - E2E testing (Playwright/Cypress)
   - User interaction testing
3. Review generated skill structure
4. Test generated skill in nav-test project
5. Refine if needed

**Validation**:
- Skill auto-invokes on "test this component"
- Generates component tests
- Includes user interaction tests
- Follows testing best practices

---

### Phase 6: Integration & Testing

**Steps**:
1. Test all 5 skills together in realistic workflow
2. Verify auto-invocation doesn't conflict
3. Measure token usage before/after
4. Document edge cases
5. Refine trigger phrases if needed

**Validation**:
- No skill trigger conflicts
- Consistent output quality
- 80%+ token reduction validated
- User workflow feels natural

---

### Phase 7: Documentation & Release

**Steps**:
1. Update plugin.json with new skills
2. Update README.md with 5 new skills
3. Update DEVELOPMENT-README.md with TASK-11 completion
4. Create release notes for v2.3.0
5. Bump version to 2.3.0
6. Commit and push to GitHub
7. Create GitHub release

**Validation**:
- All docs reference correct version
- README shows all 12 skills (7 core + 5 project-specific)
- Release notes comprehensive
- GitHub release published

---

## Token Impact Analysis

### Before v2.3 (Manual Pattern Implementation)

**Frontend component**:
- Read 3 examples (~9k tokens)
- Read docs (~6k tokens)
- Total: ~15k tokens

**Backend endpoint**:
- Read 3 examples (~9k tokens)
- Read API docs (~6k tokens)
- Total: ~15k tokens

**Database migration**:
- Read migration tool docs (~7k tokens)
- Read examples (~5k tokens)
- Total: ~12k tokens

**Backend test**:
- Read testing framework docs (~10k tokens)
- Read examples (~8k tokens)
- Total: ~18k tokens

**Frontend test**:
- Read React Testing Library docs (~8k tokens)
- Read examples (~8k tokens)
- Total: ~16k tokens

**Total per feature**: ~76k tokens
**Over 10 features**: ~760k tokens

---

### After v2.3 (Skills Auto-Invoke)

**Each skill usage**:
- Skill description: 50 tokens (already loaded)
- Skill instructions: ~3k tokens (loaded on invoke)
- Functions: 0 tokens (execute separately)
- Total: ~3k tokens per use

**Total per feature**: ~15k tokens (5 skills × 3k)
**Over 10 features**: ~150k tokens

**Savings**: 760k → 150k = **610k tokens saved (80% reduction)**

---

### Plugin Baseline Token Cost

**v2.2**: 350 tokens (7 skills)
**v2.3**: 600 tokens (12 skills)
**Increase**: +250 tokens

**Trade-off**: +250 token baseline for 610k+ token savings over project lifecycle

**ROI**: 2,440x return on investment

---

## Success Metrics

### Quality Metrics
- [ ] All 5 skills generate working code
- [ ] Generated code follows best practices
- [ ] Tests included and passing
- [ ] Consistent output across invocations

### Token Efficiency
- [ ] 80%+ reduction in token usage per pattern
- [ ] <5k tokens per skill invocation
- [ ] Baseline stays under 1k tokens

### User Experience
- [ ] Auto-invocation feels natural
- [ ] No trigger phrase conflicts
- [ ] Output matches user expectations
- [ ] Minimal manual refinement needed

### Self-Improvement Validation
- [ ] nav-skill-creator successfully generates all 5 skills
- [ ] Minimal manual editing required
- [ ] Pattern proves repeatable
- [ ] Foundation for future skills established

---

## Risks & Mitigation

### Risk 1: Generated Skills Produce Low-Quality Output

**Likelihood**: Medium
**Impact**: High

**Mitigation**:
- Test each skill thoroughly before moving to next
- Refine nav-skill-creator instructions based on learnings
- Include comprehensive examples in skill generation
- Iterate on templates until quality is high

---

### Risk 2: Auto-Invocation Trigger Conflicts

**Likelihood**: Low
**Impact**: Medium

**Mitigation**:
- Choose distinct trigger phrases
- Test all skills together for conflicts
- Document trigger phrase design in nav-skill-creator
- Allow manual skill selection if ambiguous

---

### Risk 3: Skills Too Generic (Don't Match Project Patterns)

**Likelihood**: Medium
**Impact**: Medium

**Mitigation**:
- Skills should analyze actual project patterns
- Include codebase exploration in skill generation
- Provide customization hooks in templates
- Document how to refine generated skills

---

### Risk 4: Token Baseline Creeps Too High

**Likelihood**: Low
**Impact**: Low

**Mitigation**:
- Keep skill descriptions concise (max 100 chars)
- Functions and examples load on-demand only
- Monitor baseline after each skill added
- Target: Keep baseline under 1k tokens

---

## Related Tasks

- **TASK-08**: v2.1-v2.2 roadmap (defined these 5 skills)
- **TASK-10**: nav-skill-creator implementation (tool for generating skills)
- **TASK-07**: Skills migration strategy (foundation)

---

## Notes

### Why These 5 Skills?

**Frontend component**:
- Most common frontend task
- High value (every UI feature needs components)
- Clear patterns (React has well-established conventions)

**Backend endpoint**:
- Most common backend task
- High value (every API feature needs routes)
- Clear patterns (REST/GraphQL conventions)

**Database migration**:
- Tedious and error-prone manually
- High value (schema changes common)
- Critical (rollbacks prevent data loss)

**Backend test**:
- Often skipped due to effort
- High value (prevents regressions)
- Automatable (patterns are consistent)

**Frontend test**:
- Often skipped due to effort
- High value (UI regression prevention)
- Automatable (React Testing Library patterns)

---

### Learning Opportunities

**From Phase 1 (frontend-component)**:
- Quality of nav-skill-creator output
- Whether templates need refinement
- How much manual editing is typical
- Auto-invocation trigger effectiveness

**From Phase 2-5**:
- Refinement strategy for nav-skill-creator
- Common patterns across skill generation
- Edge cases to document
- Best practices for skill design

**From Phase 6 (Integration)**:
- Real-world workflow with multiple skills
- Trigger phrase design patterns
- Token usage in realistic scenarios
- User experience insights

---

### Future Enhancements (v2.4+)

**More framework-specific skills**:
- Next.js-specific (pages, API routes, SSR)
- Django-specific (views, models, serializers)
- Vue-specific (SFCs, composition API)

**Generic infrastructure skills**:
- Docker configuration
- CI/CD pipeline setup
- Deployment automation

**Advanced testing skills**:
- Load testing
- Security testing
- Performance profiling

**Skill marketplace**:
- Share community-generated skills
- Version and distribute skills
- Cross-project skill sync

---

## Timeline

**Phase 1 (frontend-component)**: 1-2 hours
**Phase 2 (backend-endpoint)**: 1-2 hours
**Phase 3 (database-migration)**: 1-2 hours
**Phase 4 (backend-test)**: 1-2 hours
**Phase 5 (frontend-test)**: 1-2 hours
**Phase 6 (Integration)**: 1-2 hours
**Phase 7 (Documentation)**: 1 hour

**Total estimated time**: 8-14 hours (1-2 days)

---

**Task created**: 2025-10-19
**Priority**: High
**Effort**: Medium
**Target completion**: v2.3.0
