---
description: Convert tasks.md to Beads issues and reconcile completed work bidirectionally.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Overview

This command:
1. **Validates tasks.md**: Detects duplicates, verifies TDD ordering ⚠️ **NEW**
2. **Converts tasks.md → Beads issues** (if not already done)
3. **Reconciles bidirectionally**: Updates tasks.md based on closed Beads issues
4. **Preserves mappings**: Tracks task ID ↔ Beads ID relationships
5. **Audits migration**: Constitutional compliance, orphan detection, dependency validation ⚠️ **NEW**

## Outline

### 1. Setup & Validation

Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse:
- `FEATURE_DIR`: Absolute path to feature directory
- `AVAILABLE_DOCS`: List of available documents (must include tasks.md)

Verify:
- `tasks.md` exists in FEATURE_DIR
- Beads is available (`bd --version` works)

### 2. Load Mapping File

Check for existing mapping file: `${FEATURE_DIR}/.beads-mapping.json`

**Mapping Format**:
```json
{
  "feature": "015-code-quality-refinement",
  "created_at": "2025-12-09T10:30:00Z",
  "last_sync": "2025-12-09T11:45:00Z",
  "mappings": {
    "T001": {"bead_id": "beads-123", "status": "closed", "title": "..."},
    "T002": {"bead_id": "beads-124", "status": "in_progress", "title": "..."},
    "T003": {"bead_id": "beads-125", "status": "open", "title": "..."}
  }
}
```

If file doesn't exist: Initialize empty mappings.
If file exists: Load existing mappings for reconciliation.

### 3. Parse tasks.md & Validate

Read `${FEATURE_DIR}/tasks.md` and extract all tasks with format:
```
- [x] T001 [P] [US1] Description with file path
- [ ] T002 [US1] Another task in src/file.go
```

**Extract for each task**:
- **Checkbox state**: `[x]` (completed) or `[ ]` (pending)
- **Task ID**: T001, T002, etc.
- **Parallel marker**: [P] (optional)
- **Story label**: [US1], [US2] (optional)
- **Description**: Full text after markers
- **Phase**: Which phase this task belongs to (Setup, Foundational, US1, US2, Polish, etc.)
- **Line number**: For error reporting

**Build task list**:
```javascript
tasks = [
  {
    id: "T001",
    completed_in_tasksmd: true,  // checkbox is [x]
    parallel: true,               // has [P] marker
    story: "US1",                 // from [US1] marker
    description: "Description",
    phase: "Phase 3: User Story 1",
    line: 42
  },
  // ...
]
```

**⚠️ DUPLICATE DETECTION (CRITICAL)**:

During parsing, track seen task IDs:
```javascript
seenTaskIds = {}
duplicates = []

for (task in tasks) {
  if (seenTaskIds[task.id]) {
    duplicates.push({
      taskId: task.id,
      firstOccurrence: seenTaskIds[task.id].line,
      duplicate: task.line,
      description: task.description
    })
  } else {
    seenTaskIds[task.id] = task
  }
}

if (duplicates.length > 0) {
  console.error("❌ CRITICAL: Duplicate task IDs detected:")
  for (dup in duplicates) {
    console.error(`   ${dup.taskId}: Line ${dup.firstOccurrence} and Line ${dup.duplicate}`)
  }
  console.error("\nPlease fix tasks.md before proceeding.")
  exit(1)  // HALT - do not create Beads issues with duplicates
}
```

**TDD ORDERING VALIDATION**:

Verify test tasks appear before implementation tasks for same feature:
```javascript
testTasks = {}    // Track test tasks by story
implTasks = {}    // Track implementation tasks by story
violations = []

for (task in tasks) {
  isTest = task.description.includes("Write test") || task.description.includes("test for")
  story = task.story || task.phase

  if (isTest) {
    testTasks[story] = testTasks[story] || []
    testTasks[story].push(task)
  } else if (story.startsWith("US") || story === "Foundational") {
    implTasks[story] = implTasks[story] || []
    implTasks[story].push(task)

    // Check if implementation appears before tests
    if (!testTasks[story] || testTasks[story].length === 0) {
      violations.push({
        task: task.id,
        story: story,
        line: task.line,
        issue: "Implementation task before test tasks"
      })
    }
  }
}

if (violations.length > 0) {
  console.warn("⚠️  TDD ORDERING WARNINGS:")
  for (v in violations) {
    console.warn(`   ${v.task} (${v.story}): ${v.issue} (line ${v.line})`)
  }
  console.warn("\n   Constitution Principle I requires tests before implementation.")
  console.warn("   Consider reordering tasks.md for TDD compliance.\n")
}
```

### 4. Reconciliation Logic

For each task in tasks.md:

#### A. Task exists in mapping → Reconcile Status

```javascript
if (mapping.mappings[taskId]) {
  // Check current Beads status
  beadStatus = bd show mapping.mappings[taskId].bead_id | parse status

  if (beadStatus === "closed" && !task.completed_in_tasksmd) {
    // Beads closed, tasks.md not → Update tasks.md
    mark_task_complete_in_tasksmd(taskId)
    mapping.mappings[taskId].status = "closed"
  }
  else if (task.completed_in_tasksmd && beadStatus !== "closed") {
    // tasks.md completed, Beads not → Close Beads issue
    bd close mapping.mappings[taskId].bead_id --reason="Completed in tasks.md"
    mapping.mappings[taskId].status = "closed"
  }
  else {
    // Sync status
    mapping.mappings[taskId].status = beadStatus
  }
}
```

#### B. Task NOT in mapping → Create Beads Issue

```javascript
if (!mapping.mappings[taskId] && !task.completed_in_tasksmd) {
  // Create new Beads issue

  // Determine type from phase/story
  type = determine_type(task.phase, task.story)  // task, feature, bug

  // Build title (keep it concise)
  title = `${taskId}: ${truncate(task.description, 80)}`

  // Build description with context
  description = `
**Task ID**: ${taskId}
**Phase**: ${task.phase}
**Story**: ${task.story || "N/A"}
**Parallel**: ${task.parallel ? "Yes" : "No"}

**Description**:
${task.description}

**Source**: tasks.md from feature ${feature_name}
**Created by**: /speckit.taskstobeads
`

  // Create Beads issue
  beadId = bd create "${title}" \
    --type=${type} \
    --description="${description}" \
    --labels="speckit,${task.story}" \
    --priority=2

  // Store mapping
  mapping.mappings[taskId] = {
    bead_id: beadId,
    status: "open",
    title: title,
    created_at: now()
  }
}
```

#### C. Task completed in tasks.md but not in mapping

```javascript
if (!mapping.mappings[taskId] && task.completed_in_tasksmd) {
  // Task was completed before Beads integration
  // Don't create Beads issue - just document in mapping
  mapping.mappings[taskId] = {
    bead_id: null,
    status: "completed_before_beads",
    title: truncate(task.description, 80),
    note: "Completed before Beads integration"
  }
}
```

### 5. Handle Dependencies

After creating all issues, add dependencies between Beads issues:

```javascript
// Parse task dependencies from tasks.md
// Look for dependency markers like:
// - "BLOCKS all user stories"
// - "Depends on T001"
// - Phase ordering (Foundational blocks all US phases)

for (task in tasks) {
  if (task has dependencies) {
    for (dep in task.dependencies) {
      if (mapping.mappings[dep.taskId] && mapping.mappings[task.id]) {
        bd dep add ${mapping.mappings[task.id].bead_id} ${mapping.mappings[dep.taskId].bead_id}
      }
    }
  }
}
```

**Automatic Phase Dependencies**:
- All Foundational phase tasks → block all User Story phases
- User Story phases follow priority order (US1 before US2, etc.) unless explicitly parallel
- Polish phase depends on all User Story phases

### 6. Save Mapping File

Write updated mapping to `${FEATURE_DIR}/.beads-mapping.json`:

```javascript
mapping.last_sync = now()
fs.writeFile(`${FEATURE_DIR}/.beads-mapping.json`, JSON.stringify(mapping, null, 2))
```

### 7. Update tasks.md

If any tasks were marked complete due to Beads reconciliation:
- Update tasks.md file directly
- Change `- [ ]` → `- [x]` for completed tasks
- Preserve all formatting and structure

### 8. Report Summary

Output comprehensive summary:

```
✅ /speckit.taskstobeads Complete

📊 Summary:
- Total tasks in tasks.md: 150
- Tasks already completed: 75
- Beads issues created: 65
- Beads issues reconciled: 10
- Tasks marked complete: 5

📋 Beads Issues Created:
- beads-123 [open]: T001: Setup project structure
- beads-124 [in_progress]: T002: Create authentication middleware
- ...

🔄 Reconciled Changes:
- T010 → Marked complete (Beads issue beads-130 closed)
- T015 → Beads issue beads-135 closed (tasks.md was already complete)
- ...

📁 Files Updated:
- ${FEATURE_DIR}/tasks.md (5 tasks marked complete)
- ${FEATURE_DIR}/.beads-mapping.json (mapping saved)

🎯 Next Steps:
1. Run `bd ready` to see available work
2. Run `bd update <id> --status=in_progress` to claim a task
3. Run `/speckit.taskstobeads` again to sync progress
4. Use `bd sync` at end of session to push changes
```

### 9. Post-Migration Audit

Run automatic validation checks after migration completes:

#### A. Orphan Detection

Check for Beads issues that no longer have tasks:
```javascript
allBeadsIssues = bd list --labels=speckit --format=json | parse
orphans = []

for (beadIssue in allBeadsIssues) {
  // Check if this beads ID exists in any mapping
  taskId = findTaskIdForBeadId(beadIssue.id, mapping)

  if (!taskId) {
    // Check if it's from this feature (check description)
    if (beadIssue.description.includes(`feature ${feature_name}`)) {
      orphans.push({
        beadId: beadIssue.id,
        title: beadIssue.title,
        status: beadIssue.status
      })
    }
  }
}

if (orphans.length > 0) {
  console.warn("\n⚠️  ORPHANED BEADS ISSUES:")
  console.warn("   These Beads issues belong to this feature but have no task mapping:")
  for (orphan in orphans) {
    console.warn(`   - ${orphan.beadId}: ${orphan.title} [${orphan.status}]`)
  }
  console.warn("\n   Recommendation: Close orphans or add corresponding tasks to tasks.md\n")
}
```

#### B. Dependency Validation

Check for circular dependencies and missing blockers:
```javascript
// Run bd dependency validation
dependencyIssues = []

// Check for circular deps (beads should catch this, but verify)
circularDeps = bd doctor | grep "circular" || []

if (circularDeps.length > 0) {
  console.error("\n❌ CIRCULAR DEPENDENCIES DETECTED:")
  for (dep in circularDeps) {
    console.error(`   ${dep}`)
  }
  console.error("\n   Fix these before proceeding with implementation.\n")
}

// Verify foundational tasks block user story tasks
foundationalTaskIds = tasks.filter(t => t.phase.includes("Foundational")).map(t => t.id)
userStoryTaskIds = tasks.filter(t => t.story && t.story.startsWith("US")).map(t => t.id)

missingBlockers = []
for (usTaskId in userStoryTaskIds) {
  usBeadId = mapping.mappings[usTaskId]?.bead_id
  if (!usBeadId) continue

  // Check if blocked by at least one foundational task
  blockedBy = bd show ${usBeadId} | grep "Depends on:" | extract_ids

  hasFoundationalBlocker = false
  for (blockerId in blockedBy) {
    blockerTaskId = findTaskIdForBeadId(blockerId, mapping)
    if (foundationalTaskIds.includes(blockerTaskId)) {
      hasFoundationalBlocker = true
      break
    }
  }

  if (!hasFoundationalBlocker && foundationalTaskIds.length > 0) {
    missingBlockers.push({
      taskId: usTaskId,
      beadId: usBeadId,
      phase: tasks.find(t => t.id === usTaskId).phase
    })
  }
}

if (missingBlockers.length > 0) {
  console.warn("\n⚠️  MISSING FOUNDATIONAL BLOCKERS:")
  console.warn("   These user story tasks should be blocked by foundational tasks:")
  for (blocker in missingBlockers) {
    console.warn(`   - ${blocker.taskId} (${blocker.phase}): ${blocker.beadId}`)
  }
  console.warn("\n   Run manually: bd dep add <us-bead-id> <foundational-bead-id>\n")
}
```

#### C. Constitutional Compliance Report

Generate compliance summary:
```javascript
console.log("\n📋 CONSTITUTIONAL COMPLIANCE AUDIT:\n")

// Principle I: Test-First Development
testTaskCount = tasks.filter(t => t.description.includes("test") || t.description.includes("Test")).length
implTaskCount = tasks.length - testTaskCount - tasks.filter(t => t.completed_in_tasksmd).length

testCoverage = (testTaskCount / (testTaskCount + implTaskCount)) * 100

if (testCoverage >= 40) {
  console.log(`   ✅ Principle I (TDD): ${testCoverage.toFixed(1)}% test coverage (${testTaskCount} test tasks / ${testTaskCount + implTaskCount} active tasks)`)
} else {
  console.warn(`   ⚠️  Principle I (TDD): ${testCoverage.toFixed(1)}% test coverage - Constitution requires tests-first approach`)
}

// Principle V: Small Atomic Commits
avgTaskComplexity = estimateAvgCommitSize(tasks)
if (avgTaskComplexity <= 600) {
  console.log(`   ✅ Principle V (Commits): Tasks scoped for ~${avgTaskComplexity} lines/task (target: 300-600)`)
} else {
  console.warn(`   ⚠️  Principle V (Commits): Tasks may exceed 600 lines/commit - consider splitting larger tasks`)
}

// Dependency Structure
readyCount = bd ready | count
blockedCount = bd blocked | count
totalOpen = bd list --status=open | count

if (readyCount > 0 && blockedCount > 0) {
  console.log(`   ✅ Dependencies: ${readyCount} ready, ${blockedCount} blocked (proper phase structure)`)
} else if (readyCount === 0 && totalOpen > 0) {
  console.warn(`   ⚠️  Dependencies: No tasks ready - check for missing prerequisites or circular deps`)
} else {
  console.log(`   ✅ Dependencies: ${readyCount} ready, ${blockedCount} blocked`)
}

console.log("\n📊 BEADS STATISTICS:\n")
console.log(bd stats | format)

console.log("\n✅ Audit complete. Feature is ready for implementation.\n")
```

## Important Notes

### Reconciliation Workflow

**First Run** (Converting tasks.md → Beads):
```bash
/speckit.taskstobeads
# Creates all uncompleted tasks as Beads issues
# Stores mapping in .beads-mapping.json
```

**During Work** (Tracking progress):
```bash
bd update beads-123 --status=in_progress
# ... do work ...
bd close beads-123
```

**Sync Back** (Reconciling Beads → tasks.md):
```bash
/speckit.taskstobeads
# Checks all mapped Beads issues
# Updates tasks.md with completed tasks
# Creates any new tasks added to tasks.md
```

### Idempotency

- Safe to run multiple times
- Won't create duplicate Beads issues (checks mapping first)
- Won't overwrite manual changes to Beads issues
- Preserves both tasks.md and Beads as source of truth

### Edge Cases

**Task added to tasks.md after initial conversion**:
- Next run will create Beads issue for it

**Task removed from tasks.md**:
- Beads issue remains (manual cleanup required)
- Mapping file preserves history

**Beads issue manually deleted**:
- Next run will detect missing issue
- Won't recreate (checks mapping file)
- Reports warning

**Merge conflicts in tasks.md**:
- Resolve conflicts first
- Then run reconciliation
- Mapping file helps identify which tasks are in Beads

### File Locations

- **Mapping file**: `${FEATURE_DIR}/.beads-mapping.json` (gitignored or committed based on preference)
- **Tasks file**: `${FEATURE_DIR}/tasks.md` (source of truth for task definitions)
- **Beads database**: `.beads/issues.jsonl` (source of truth for execution status)

### Parallel Execution

- Tasks marked with `[P]` are noted in Beads description
- No automatic parallelization in Beads
- User can work on multiple `[P]` tasks simultaneously
- Reconciliation handles multiple in-progress tasks

## Error Handling

- If `bd create` fails → Report error, continue with other tasks
- If mapping file is corrupted → Backup and recreate from Beads data
- If tasks.md format is invalid → Report line number and skip task
- If Beads issue not found → Report warning, mark in mapping as "orphaned"

## Exit Codes

- **0**: Success (all tasks synced)
- **1**: Error (Beads not available, tasks.md not found, etc.)
- **2**: Warning (some tasks couldn't be synced, but majority succeeded)