---
description: Implement the next ready task from Beads issue tracker with SpecKit integration
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Overview

This command bridges SpecKit planning with Beads execution tracking, enabling incremental task-by-task implementation.

**Two modes**:
1. **Without arguments**: Automatically implement the FIRST ready task with constitutional compliance
2. **With argument**: Implement specific task by number, task ID, or Beads ID

## Outline

### 0. Startup Checks (CRITICAL) - AUTOMATED! 🆕

**Run automated startup checks script**:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
STARTUP_SCRIPT="$REPO_ROOT/.specify/scripts/bash/startup-checks.sh"

if [ ! -f "$STARTUP_SCRIPT" ]; then
  echo "❌ ERROR: Startup checks script not found"
  echo "Expected: $STARTUP_SCRIPT"
  exit 1
fi

# Run startup checks (exits with error if any check fails)
STARTUP_RESULT=$("$STARTUP_SCRIPT")
STARTUP_EXIT=$?

if [ $STARTUP_EXIT -ne 0 ]; then
  echo "$STARTUP_RESULT"
  exit $STARTUP_EXIT
fi

# Parse JSON output from startup script
BEADS_VERSION=$(echo "$STARTUP_RESULT" | tail -1 | jq -r '.beads_version')
ISSUE_COUNT=$(echo "$STARTUP_RESULT" | tail -1 | jq -r '.issue_count')
FEATURE_DIR=$(echo "$STARTUP_RESULT" | tail -1 | jq -r '.feature_dir')
MAPPING_FILE=$(echo "$STARTUP_RESULT" | tail -1 | jq -r '.mapping_file')
```

**What startup-checks.sh does** (automatically):
1. ✅ Verifies Beads is installed
2. ✅ Verifies Beads issues exist (.beads/issues.jsonl)
3. ✅ Runs prerequisites check (feature dir, tasks.md)
4. ✅ Verifies Beads mapping file exists
5. ✅ Returns JSON with all context needed

**Proceed to Load Configuration**

### 0a. Load Automation Configuration (🆕 v2.1)

**Load user preferences for auto-close and auto-continue**:

```bash
# Source config loader
CONFIG_LOADER="$REPO_ROOT/.specify/scripts/bash/config-loader.sh"

if [ -f "$CONFIG_LOADER" ]; then
  source "$CONFIG_LOADER"

  # Load all config values
  CONFIG_JSON=$(get_all_config)

  AUTO_CLOSE=$(echo "$CONFIG_JSON" | jq -r '.auto_close')
  AUTO_CONTINUE=$(echo "$CONFIG_JSON" | jq -r '.auto_continue')
  BATCH_MODE=$(echo "$CONFIG_JSON" | jq -r '.batch_mode')
  QUIET_MODE=$(echo "$CONFIG_JSON" | jq -r '.quiet_mode')
  MAX_BATCH_TASKS=$(echo "$CONFIG_JSON" | jq -r '.max_batch_tasks')
  REQUIRE_APPROVAL_ON_FAILURE=$(echo "$CONFIG_JSON" | jq -r '.require_approval_on_failure')
else
  # Config loader not found - use defaults (backward compatible)
  AUTO_CLOSE="false"
  AUTO_CONTINUE="false"
  BATCH_MODE="false"
  QUIET_MODE="false"
  MAX_BATCH_TASKS="5"
  REQUIRE_APPROVAL_ON_FAILURE="true"
fi
```

**Parse command-line flags from $ARGUMENTS**:

```javascript
// Parse $ARGUMENTS for flags
const args = $ARGUMENTS.trim()
let flags = {
  auto: false,
  autoClose: false,
  autoContinue: false,
  batch: false,
  batchSize: MAX_BATCH_TASKS,
  quiet: false,
  requireApproval: false,
  dryRun: false
}

// Parse flags (--auto, --auto-close, --batch=5, etc.)
if (args.includes('--auto')) {
  flags.auto = true
  AUTO_CLOSE = "true"
  AUTO_CONTINUE = "true"
}
if (args.includes('--auto-close')) {
  flags.autoClose = true
  AUTO_CLOSE = "true"
}
if (args.includes('--auto-continue')) {
  flags.autoContinue = true
  AUTO_CONTINUE = "true"
}
if (args.includes('--batch')) {
  flags.batch = true
  BATCH_MODE = "true"
  // Extract batch size if specified: --batch=10
  const batchMatch = args.match(/--batch=(\d+)/)
  if (batchMatch) {
    flags.batchSize = parseInt(batchMatch[1])
    MAX_BATCH_TASKS = flags.batchSize.toString()
  }
}
if (args.includes('--quiet')) {
  flags.quiet = true
  QUIET_MODE = "true"
}
if (args.includes('--require-approval')) {
  flags.requireApproval = true
  REQUIRE_APPROVAL_ON_FAILURE = "true"
  AUTO_CLOSE = "false"  // Override auto-close
  AUTO_CONTINUE = "false"  // Override auto-continue
}
if (args.includes('--dry-run')) {
  flags.dryRun = true
  console.log("🔍 DRY RUN MODE - No changes will be made")
}

// Display configuration (if not quiet mode)
if (QUIET_MODE !== "true") {
  console.log("")
  console.log("⚙️  Configuration:")
  console.log(`   Auto-close: ${AUTO_CLOSE}`)
  console.log(`   Auto-continue: ${AUTO_CONTINUE}`)
  console.log(`   Batch mode: ${BATCH_MODE}`)
  if (BATCH_MODE === "true") {
    console.log(`   Max batch tasks: ${MAX_BATCH_TASKS}`)
  }
  console.log(`   Require approval on failure: ${REQUIRE_APPROVAL_ON_FAILURE}`)
  console.log("")
}
```

**Proceed to Load Mapping**

### 1. Load Beads Mapping (Simplified - Already Verified)

Since startup checks verified mapping file exists, simply load it:

```bash
# Mapping file path already set by startup checks
MAPPING_JSON=$(cat "$MAPPING_FILE")
```

**Note**: If mapping didn't exist, startup-checks.sh would have already exited with error and instructions to run `/speckit.taskstobeads`.

### 2. Get Ready Tasks from Beads

Run `bd ready` and parse output to get all ready issues (no blockers).

**Filter for current feature**:
- Only include issues with `speckit` label
- Cross-reference with mapping file to get task IDs
- Build ready task list:

```javascript
readyTasks = []
beadsOutput = exec("bd ready")
for (line in beadsOutput) {
  if (line contains issue ID) {
    beadId = extract_bead_id(line)

    // Find in mapping
    for (taskId, mapping in mappings) {
      if (mapping.bead_id === beadId) {
        readyTasks.push({
          number: readyTasks.length + 1,
          taskId: taskId,
          beadId: beadId,
          title: mapping.title,
          status: mapping.status
        })
      }
    }
  }
}
```

### 3. Mode Selection

#### Mode A: Auto-Implement First Ready Task (No Arguments)

If `$ARGUMENTS` is empty:

**1. Check if tasks are available**:
```javascript
if (readyTasks.length === 0) {
  // No ready tasks - show status
  display_no_ready_tasks_message()
  exit(0)
}
```

**2. Auto-select first ready task**:
```javascript
selectedTask = readyTasks[0]  // First ready task
```

**3. Display auto-selection**:
```text
✅ Auto-selecting next ready task: [${selectedTask.taskId}] ${selectedTask.beadId}

📋 ${selectedTask.title}

🎯 Implementing with constitutional compliance...
```

**4. Proceed to Pre-Implementation (Section 4)**

#### Mode B: Implement Task (With Arguments)

If `$ARGUMENTS` is provided, parse the task selector:

**Selector types**:
- Number (1, 2, 3): Select from ready tasks list by position
- Task ID (T005, T010): Find task by ID in mapping
- Beads ID (beads-305): Use Beads ID directly

**Parse logic**:
```javascript
selector = $ARGUMENTS.trim()

if (selector matches /^\d+$/) {
  // Number selector
  taskIndex = parseInt(selector) - 1
  if (taskIndex >= 0 && taskIndex < readyTasks.length) {
    selectedTask = readyTasks[taskIndex]
  } else {
    error: "Invalid task number. Run /speckit.implementwithbeads to see available tasks."
  }
}
else if (selector matches /^T\d+$/) {
  // Task ID selector
  if (mapping.mappings[selector]) {
    selectedTask = {
      taskId: selector,
      beadId: mapping.mappings[selector].bead_id,
      title: mapping.mappings[selector].title
    }
  } else {
    error: "Task ${selector} not found in mapping."
  }
}
else if (selector matches /^beads-[a-zA-Z0-9]+$/) {
  // Beads ID selector
  beadId = selector
  for (taskId, mapping in mappings) {
    if (mapping.bead_id === beadId) {
      selectedTask = {
        taskId: taskId,
        beadId: beadId,
        title: mapping.title
      }
      break
    }
  }
  if (!selectedTask) {
    error: "Beads issue ${selector} not found in mapping."
  }
}
else {
  error: "Invalid selector. Use: number (1), task ID (T005), or Beads ID (beads-305)"
}
```

**Verify task is ready**:
- Check if selectedTask is in readyTasks list
- If not in ready list: "⚠️ Task ${taskId} is blocked by dependencies. Run /speckit.implementwithbeads to see ready tasks."
- If ready: Proceed to implementation

### 4. Pre-Implementation - CRITICAL: Claim Task Immediately

**🚨 MANDATORY STEP: Mark task as in_progress BEFORE any implementation**

This MUST be the FIRST action to prevent race conditions with other agents/developers.

**Display task selection**:
```text
✅ Selected: [${taskId}] ${beadId}: ${title}

🚨 CLAIMING TASK (prevents others from starting the same task)...
```

**IMMEDIATELY update Beads status**:
```bash
bd update ${beadId} --status=in_progress
```

**Verify the update succeeded**:
```bash
# Run bd show to confirm status changed
status=$(bd show ${beadId} | grep "Status:" | awk '{print $2}')
if [ "$status" != "in_progress" ]; then
  echo "❌ ERROR: Failed to claim task. Another agent may have claimed it."
  echo "Run 'bd ready' to see available tasks."
  exit 1
fi
```

**Display confirmation**:
```text
✅ Task claimed successfully (status: in_progress)
✅ Other agents will now skip this task

📍 Loading task details...
```

**Load full task context from tasks.md**:
- Read tasks.md
- Find the task line matching taskId
- Extract:
  - Phase (which phase section it's in)
  - Parallel marker ([P])
  - Story label ([US1], [US2], etc.)
  - Full description (including file paths)
  - Any dependency notes

**Display context**:
```text
✅ Status updated to in_progress

📋 Task Context:
   Phase: ${phase}
   Story: ${story || "N/A"}
   Parallel: ${hasParallelMarker ? "Yes" : "No"}
   Description: ${fullDescription}

🎯 Starting implementation...
```

**🔍 SMART DETECTION: Check if already implemented** (🆕 IMPROVEMENT #1):

Run detection script to check if implementation might already exist:
```bash
DETECTION_RESULT=$(.specify/scripts/bash/detect-already-implemented.sh \
  "$fullDescription" "$taskId" "$FEATURE_DIR")
```

**Parse detection result**:
```javascript
if (DETECTION_RESULT.startsWith("ALREADY_IMPLEMENTED:")) {
  parts = DETECTION_RESULT.split(":")
  platform = parts[1]
  pattern = parts[2]

  // Display warning
  console.log("⚠️  IMPLEMENTATION DETECTED!")
  console.log("")
  console.log(`   Pattern: ${pattern}`)
  console.log(`   Platform: ${platform}`)
  console.log(`   File: services/download-api/business/domain/${platform}/downloader.go`)
  console.log("")
  console.log("📝 This appears to be a VERIFICATION TEST, not a new implementation")
  console.log("")
  console.log("Expected behavior:")
  console.log("   ✅ Test should PASS on first run (validates existing implementation)")
  console.log("   ✅ This is backward compatibility validation (User Story 4)")
  console.log("")
  console.log("💡 TIP: Write test to verify the existing behavior works correctly")
  console.log("")
}
```

### 5. Implementation with Constitutional Compliance

**Load implementation context** (similar to /speckit.implement):
- **REQUIRED**: Read plan.md for tech stack and architecture
- **IF EXISTS**: Read spec.md for feature requirements
- **IF EXISTS**: Read data-model.md for entities
- **IF EXISTS**: Read contracts/ for API specs
- **IF EXISTS**: Read research.md for technical decisions
- **REQUIRED**: Read .specify/memory/constitution.md for project principles

**⚖️ CONSTITUTIONAL COMPLIANCE (MANDATORY)**

**Read and parse `.specify/memory/constitution.md`**:
```javascript
constitutionPath = ".specify/memory/constitution.md"
if (file_exists(constitutionPath)) {
  constitutionText = read_file(constitutionPath)

  // Extract principles (markdown sections starting with "## Principle")
  principles = extract_principles(constitutionText)

  // Display constitutional requirements for this task
  console.log("⚖️ Constitutional Principles (from constitution.md):")
  for (principle in principles) {
    console.log(`   ${principle.number}: ${principle.title}`)
    console.log(`      ${principle.summary}`)
  }
} else {
  WARNING: "⚠️ constitution.md not found - using default TDD/SOLID principles"
}
```

**Apply constitution to task implementation**:
- Extract key principles from constitution.md
- Focus on principles most relevant to coding tasks:
  - Test-First Development (usually Principle I)
  - SOLID Design principles (usually Principle II)
  - Small atomic commits (usually Principle V)
- Parse specific rules (line limits, commit sizes, etc.)
- Display these requirements before starting implementation

**Create focused TodoWrite list for this task**:
```javascript
todos = [
  {
    content: `Implement ${taskId}: ${title}`,
    activeForm: `Implementing ${taskId}: ${title}`,
    status: "in_progress"
  }
]

// CONSTITUTIONAL ENFORCEMENT: TDD
if (description contains "test" or description contains "Write test") {
  todos.push({
    content: "✅ PRINCIPLE I: Write tests FIRST (TDD)",
    activeForm: "Writing tests first (TDD)",
    status: "pending"
  })
  todos.push({
    content: "Implement functionality (after tests)",
    activeForm: "Implementing functionality",
    status: "pending"
  })
} else {
  // Implementation task - still need tests first!
  todos.push({
    content: "✅ PRINCIPLE I: Write tests FIRST (TDD)",
    activeForm: "Writing tests before implementation",
    status: "pending"
  })
  todos.push({
    content: "Implement code (SOLID principles)",
    activeForm: "Writing implementation",
    status: "pending"
  })
}

todos.push({
  content: "Run tests and verify (Green phase)",
  activeForm: "Verifying tests pass",
  status: "pending"
})

todos.push({
  content: "✅ PRINCIPLE V: Review commit size (300-600 lines)",
  activeForm: "Reviewing commit size",
  status: "pending"
})

todos.push({
  content: "Verify constitutional compliance",
  activeForm: "Verifying constitutional compliance",
  status: "pending"
})
```

**Execute implementation (CONSTITUTIONALLY COMPLIANT)**:

**Step 1: Test-First (PRINCIPLE I)**
- If task requires tests: Write them FIRST, see them fail
- If task is implementation: Write tests for it FIRST
- Use proper test structure (AAA: Arrange, Act, Assert)
- Follow BDD naming: "Given-When-Then"

**📊 Progress Update**:
```text
🔄 Progress: Writing tests (TDD Red phase)...
```

**Step 2: Implement (PRINCIPLE II: SOLID)**
- Extract file paths from task description
- Create/modify files as needed
- Keep functions < 50 lines
- Inject dependencies
- No God objects

**📊 Progress Update**:
```text
🔄 Progress: Implementing functionality (TDD Green phase)...
```

**Step 3: Verify Tests Pass**
- Run test suite
- Ensure Green phase of TDD
- Fix any failures

**📊 Progress Update**:
```text
🔄 Progress: Running tests...
```

After tests pass:
```text
✅ Tests passed! (Green phase complete)
```

**Step 4: Review Commit Size (PRINCIPLE V)**
- Check line count (target: 300-600)
- If too large: Consider splitting
- Use TodoWrite to track progress

**📊 Progress Update**:
```text
🔄 Progress: Verifying constitutional compliance...
```

**Implementation checklist**:
1. ✅ Read constitution.md
2. ✅ Write tests FIRST (TDD)
3. ✅ Implement following SOLID
4. ✅ Run tests (Green phase)
5. ✅ Review commit size (300-600 lines)
6. ✅ Update TodoWrite as you progress

### 6. Post-Implementation with Constitutional Verification

**⚖️ Constitutional Compliance Check**:

**Re-read constitution and verify compliance**:
```javascript
// Read constitution.md again (may have been updated)
constitution = read_file(".specify/memory/constitution.md")
principles = extract_principles(constitution)

complianceReport = {
  principles: [],
  overallStatus: "PASSED",
  violations: [],
  warnings: []
}

// Check each principle from constitution.md
for (principle in principles) {
  principleCheck = verify_principle(principle, modifiedFiles, taskContext)

  complianceReport.principles.push({
    number: principle.number,
    title: principle.title,
    status: principleCheck.status,  // PASSED, WARNING, FAILED
    details: principleCheck.details
  })

  if (principleCheck.status === "FAILED") {
    complianceReport.overallStatus = "FAILED"
    complianceReport.violations.push(principleCheck.message)
  } else if (principleCheck.status === "WARNING") {
    complianceReport.warnings.push(principleCheck.message)
  }
}

// Common checks (if not explicitly defined in constitution)
// These are fallbacks if constitution doesn't specify limits

// Check for TDD compliance
testsWritten = modifiedFiles.filter(f => f.includes("test")).length > 0
implementationWritten = modifiedFiles.filter(f => !f.includes("test")).length > 0

if (implementationWritten && !testsWritten) {
  complianceReport.warnings.push("⚠️ Implementation without corresponding tests")
}

// Check file sizes
for (file in modifiedFiles) {
  lineCount = count_lines(file)
  if (lineCount > 500) {
    complianceReport.warnings.push(`⚠️ File ${file} exceeds 500 lines`)
  }
}

// Check commit size
totalLinesChanged = sum of all file changes
commitSizeStatus = "PASSED"
if (totalLinesChanged > 600) {
  commitSizeStatus = "WARNING"
  complianceReport.warnings.push(`⚠️ Commit size ${totalLinesChanged} lines exceeds recommended 600`)
}
```

**Verification**:
- Review what was implemented
- Check if task requirements are met
- Verify files were created/modified as expected
- ✅ **Verify constitutional compliance** (above)

**Update TodoWrite**:
- Mark all todos as completed
- Final todo: "Task ${taskId} complete (constitutional compliance: ${complianceStatus})"

**Display completion summary with compliance report**:
```text
✅ Implementation complete!

📝 Files modified:
${list modified files}

⚖️ Constitutional Compliance Report:
   ${for principle in complianceReport.principles}
   ${principle.number}: ${principle.title}
      Status: ${principle.status === "PASSED" ? "✅" : principle.status === "WARNING" ? "⚠️" : "❌"} ${principle.status}
      ${principle.details}
   ${end for}

   Overall Status: ${complianceReport.overallStatus === "PASSED" ? "✅ PASSED" : "❌ NEEDS ATTENTION"}

   ${if complianceReport.violations.length > 0}
   ❌ Violations:
   ${for violation in complianceReport.violations}
      - ${violation}
   ${end for}
   ${end if}

   ${if complianceReport.warnings.length > 0}
   ⚠️  Warnings:
   ${for warning in complianceReport.warnings}
      - ${warning}
   ${end for}
   ${end if}

🎯 Next steps:
1. Review the implementation
2. Run tests if applicable
3. ${complianceReport.overallStatus === "FAILED" ? "Fix compliance violations before closing" : "Close the task if satisfied"}

📊 Metrics:
   - Files modified: ${modifiedFiles.length}
   - Total lines changed: ${totalLinesChanged}
   - Test files: ${testsWritten ? modifiedFiles.filter(f => f.includes("test")).length : 0}
   - Implementation files: ${modifiedFiles.filter(f => !f.includes("test")).length}
```

**Auto-Close Decision (🆕 v2.1)**:

**Evaluate if task should auto-close**:

```javascript
// Determine success criteria
const testsExecuted = /* check if tests were run */
const testsPassed = /* check if tests passed (exit code 0, no failures) */
const compliancePassed = complianceReport.overallStatus === "PASSED" || complianceReport.overallStatus === "WARNING"
const filesModified = modifiedFiles.length > 0

// Evaluate auto-close eligibility
const canAutoClose = testsExecuted && testsPassed && compliancePassed && filesModified

// Auto-close decision
let shouldClose = false
let closeReason = ""

if (AUTO_CLOSE === "true" && canAutoClose) {
  // Auto-close successful implementation
  shouldClose = true
  closeReason = "auto-closed (tests passed, compliance OK)"

  console.log("")
  console.log("✅ Auto-Close Enabled")
  console.log(`   Tests: ${testsPassed ? "✅ PASSED" : "❌ FAILED"}`)
  console.log(`   Compliance: ${compliancePassed ? "✅ PASSED" : "❌ FAILED"}`)
  console.log(`   Files modified: ${filesModified ? "✅ YES" : "❌ NO"}`)
  console.log("")
  console.log(`✅ Auto-closing task (${closeReason})`)

} else if (!canAutoClose && REQUIRE_APPROVAL_ON_FAILURE === "true") {
  // Failed criteria - ask user
  console.log("")
  console.log("❌ Auto-Close Criteria Not Met:")
  if (!testsExecuted) console.log("   - Tests were not executed")
  if (!testsPassed) console.log("   - Tests failed")
  if (!compliancePassed) console.log("   - Compliance check failed")
  if (!filesModified) console.log("   - No files were modified")
  console.log("")

  const answer = promptUser("Close task anyway? (yes/no/fix): ")

  if (answer === "yes") {
    shouldClose = true
    closeReason = "closed despite failures (user approved)"
  } else if (answer === "fix") {
    console.log("🔧 Re-running implementation to fix issues...")
    // Re-run implementation with fixes
    return implementTask(taskId)  // Recursively try again
  } else {
    shouldClose = false
    console.log("⏸️  Task kept as in_progress")
  }

} else if (!canAutoClose && REQUIRE_APPROVAL_ON_FAILURE === "false") {
  // Failed but approval not required - skip close
  shouldClose = false
  console.log("")
  console.log("⚠️  Skipping task closure (criteria not met, require_approval_on_failure=false)")
  console.log("   You can manually close with: bd close ${beadId}")
  console.log("")

} else {
  // Manual mode (AUTO_CLOSE=false) - always ask
  console.log("")
  const answer = promptUser("Is this task complete and ready to close? (yes/no): ")

  if (answer === "yes" || answer === "y") {
    shouldClose = true
    closeReason = "closed (user confirmed)"
  } else {
    shouldClose = false
    console.log("⏸️  Task kept as in_progress")
  }
}
```

**If shouldClose is true**:

**🚨 MANDATORY: Close Beads issue**:
```bash
bd close ${beadId}
```

**Verify closure**:
```bash
# Confirm the issue is closed
status=$(bd show ${beadId} | grep "Status:" | awk '{print $2}')
if [ "$status" = "closed" ]; then
  echo "✅ Beads issue ${beadId} closed successfully"
else
  echo "⚠️ WARNING: Issue may not be closed. Current status: $status"
fi
```

- Mark task complete in tasks.md: Update `- [ ] ${taskId}` to `- [x] ${taskId}`
- Run reconciliation: Execute `/speckit.taskstobeads` to sync
- Output:
  ```text
  ✅ Beads issue ${beadId} closed
  ✅ tasks.md updated (${taskId} marked complete)
  ✅ Reconciliation complete

  📊 Updated Beads Stats:
  ${bd stats}
  ```

**🚨 COMMIT REMINDER** (🆕 IMPROVEMENT #3 - Principle V Enforcement):

```bash
# Run automated compliance check
echo ""
echo "🔍 Running automated constitutional compliance check..."
.specify/scripts/bash/check-constitutional-compliance.sh
COMPLIANCE_EXIT=$?

if [ $COMPLIANCE_EXIT -ne 0 ]; then
  echo ""
  echo "⚠️  Please review warnings above before committing"
  echo ""
fi
```

**Display commit reminder**:
```text
📋 Post-Task Checklist (Principle V):
   [✓] Tests passing
   [✓] Beads issue closed
   [✓] Constitutional compliance verified
   [ ] Changes committed ⚠️  NOT YET

🚨 REMINDER: Small atomic commits (300-600 lines)

Suggested commit command:
   git add ${list modified files}
   git commit -m "${generate_commit_message(taskId, title)}"

Example:
   git add services/download-api/business/domain/instagram/downloader_test.go
   git commit -m "test(instagram): add backward compat test for WithConnector sets both phases (${taskId})"
```

**If shouldClose is false**:
- Keep Beads issue as in_progress
- Skip reconciliation and commit reminder
- Output:
  ```text
  ⏸️  Task kept as in_progress
  Run `bd close ${beadId}` manually when ready
  ```

**Auto-Continue Flow** (🆕 v2.1):

**Determine if should continue to next task**:

```javascript
// Only continue if task was successfully closed
if (!shouldClose) {
  console.log("")
  console.log("🛑 Stopping workflow (task not closed)")
  console.log("")
  return  // Exit without showing next tasks
}

// Task was closed - decide whether to continue
```

**Load next ready tasks**:

```javascript
// Run bd ready again and filter for current feature
const nextReadyTasks = getReadyTasks()  // Using same logic from Section 2

// Calculate progress statistics
const totalTasks = getAllTasksCount()
const closedTasks = getClosedTasksCount()
const progressPercent = ((closedTasks / totalTasks) * 100).toFixed(1)

// Track batch progress if in batch mode
if (BATCH_MODE === "true") {
  const tasksImplementedThisBatch = (tasksImplementedThisBatch || 0) + 1
  const maxBatch = parseInt(MAX_BATCH_TASKS)

  if (tasksImplementedThisBatch >= maxBatch) {
    console.log("")
    console.log(`📊 Batch limit reached (${maxBatch} tasks implemented)`)
    console.log(`   Progress: ${closedTasks}/${totalTasks} (${progressPercent}%)`)
    console.log("")
    console.log("✅ Batch complete!")
    return  // Exit batch mode
  }
}

// Check if any tasks remain
if (nextReadyTasks.length === 0) {
  console.log("")
  console.log("✅ All ready tasks complete!")
  console.log(`📊 Final progress: ${closedTasks}/${totalTasks} (${progressPercent}%)`)
  console.log("")

  const blockedCount = getBlockedTasksCount()
  if (blockedCount > 0) {
    console.log(`⏸️  ${blockedCount} task(s) still blocked by dependencies`)
    console.log("   Run: bd blocked")
  }

  return  // Exit workflow
}

// Tasks remain - decide whether to continue automatically
if (AUTO_CONTINUE === "true" || BATCH_MODE === "true") {
  // Auto-continue without asking
  const nextTask = nextReadyTasks[0]

  console.log("")
  console.log("🔄 Auto-Continue Enabled")
  console.log(`   Next task: [${nextTask.taskId}] ${nextTask.beadId}`)
  console.log(`   Progress: ${closedTasks}/${totalTasks} (${progressPercent}%)`)

  if (BATCH_MODE === "true") {
    console.log(`   Batch: ${tasksImplementedThisBatch}/${MAX_BATCH_TASKS}`)
  }

  console.log("")
  console.log(`🎯 Continuing with ${nextTask.taskId}...`)
  console.log("")

  // Recursively implement next task
  return implementTask(nextTask.taskId)

} else {
  // Manual mode - show interactive prompt
  console.log("")
  console.log("📋 Next Ready Tasks:")
  nextReadyTasks.slice(0, 5).forEach((task, idx) => {
    console.log(`  ${idx + 1}. [${task.taskId}] ${task.beadId}: ${task.title}`)
  })
  console.log("")
  console.log(`📊 Progress: ${closedTasks}/${totalTasks} tasks complete (${progressPercent}%)`)

  if (nextReadyTasks.length > 0) {
    const estimatedTime = estimateTaskTime(nextReadyTasks[0])
    console.log(`⏱️  Estimated time for ${nextReadyTasks[0].taskId}: ~${estimatedTime} minutes`)
  }

  console.log("")
  console.log("🚀 Continue with next ready task?")
  console.log(`  1. Yes - auto-implement ${nextReadyTasks[0].taskId} (${nextReadyTasks[0].title})`)
  console.log(`  2. Select different task (enter number 1-${Math.min(nextReadyTasks.length, 5)})`)
  console.log("  3. Show all ready tasks (bd ready)")
  console.log("  4. Exit")
  console.log("")

  const choice = promptUser("Choice: ")

  if (choice === "1" || choice === "yes" || choice === "y") {
    // Continue with first ready task
    console.log("")
    console.log("🎯 Continuing with next task...")
    console.log("")
    return implementTask(nextReadyTasks[0].taskId)

  } else if (/^\d+$/.test(choice) && parseInt(choice) >= 2 && parseInt(choice) <= Math.min(nextReadyTasks.length, 5) + 1) {
    // User selected specific task number
    const taskIdx = parseInt(choice) - 1
    if (taskIdx >= 0 && taskIdx < nextReadyTasks.length) {
      console.log("")
      console.log(`🎯 Implementing ${nextReadyTasks[taskIdx].taskId}...`)
      console.log("")
      return implementTask(nextReadyTasks[taskIdx].taskId)
    }

  } else if (choice === "3") {
    // Show all ready tasks
    console.log("")
    execSync("bd ready")
    console.log("")
    console.log("💡 Run /speckit.implementwithbeads [taskId] to implement a specific task")

  } else {
    // Exit
    console.log("")
    console.log("✅ Workflow complete!")
    console.log("")
    console.log("💡 Run /speckit.implementwithbeads anytime to continue")
  }
}
```

### 7. Error Handling

**If Beads not available** (checked in Section 0):
```text
❌ ERROR: Beads is not installed

This command requires Beads for task tracking.

📦 Install Beads:
   brew install beadlabs/tap/beads

   Or visit: https://github.com/beadlabs/beads
```

**If no Beads issues exist** (checked in Section 0):
```text
❌ ERROR: No Beads issues found

This command requires Beads issues to be created from tasks.md

📦 Create Beads issues from tasks:
   /speckit.taskstobeads

💡 This will:
   - Read tasks.md from your feature branch
   - Create Beads issues with dependencies
   - Enable incremental task tracking
```

**If tasks.md not found**:
```text
❌ Error: tasks.md not found in feature directory

Run /speckit.tasks to generate the task list first.
```

**If no ready tasks**:
```text
📋 No tasks are ready to work on.

⏸️  All tasks are either:
   - Completed: ${completedCount}
   - Blocked by dependencies: ${blockedCount}
   - In progress: ${inProgressCount}

Check status with:
  bd list --status=open
  bd blocked
```

**If selected task doesn't exist**:
```text
❌ Error: Task not found

Run /speckit.implementwithbeads to see available tasks.
```

**If selected task is blocked**:
```text
⚠️ Task ${taskId} (${beadId}) is blocked by dependencies.

Blocked by:
${list blocking tasks}

Run /speckit.implementwithbeads to see ready tasks instead.
```

## Important Notes

### Incremental Development

This command is designed for **incremental, task-by-task implementation**:
- Implement one task at a time
- Respect dependencies (only shows ready tasks)
- Track progress in Beads
- Sync back to tasks.md automatically

### Difference from /speckit.implement

**`/speckit.implement`**:
- Implements entire feature (all tasks in tasks.md)
- Processes tasks sequentially or in parallel based on plan
- Best for "implement everything" workflow

**`/speckit.implementwithbeads`**:
- Implements ONE task at a time
- Integrates with Beads tracking
- Best for "step-by-step" workflow with team collaboration
- Respects dependencies automatically (via Beads)

### Workflow Example

```bash
# 1. Generate tasks from plan
/speckit.tasks

# 2. Create Beads issues from tasks
/speckit.taskstobeads

# 3. Show what's ready to work on
/speckit.implementwithbeads
# Output: Shows tasks 1-3 are ready

# 4. Implement first task (auto-mode)
/speckit.implementwithbeads
# Implements first ready task, marks complete, shows next tasks

# 5. Implement specific task
/speckit.implementwithbeads T010
# Implements T010 by task ID

# 6. Check what's ready
/speckit.implementwithbeads
# Shows remaining ready tasks

# 7. Continue implementing
/speckit.implementwithbeads  # Auto-implements next ready task
```

### Parallel Workflow

Multiple developers/agents can work simultaneously:

```bash
# Agent A
/speckit.implementwithbeads  # Auto-claims first ready task (T001)

# Agent B (parallel execution)
/speckit.implementwithbeads  # Auto-claims next ready task (T002, if parallel with T001)

# Both complete, reconcile
/speckit.taskstobeads  # Sync progress
```

### Best Practices

1. **Run /speckit.implementwithbeads frequently** to see progress
2. **Confirm task completion** when asked (don't leave tasks in_progress if done)
3. **Let Beads handle dependencies** - don't manually select blocked tasks
4. **Use task IDs** for clarity: `/speckit.implementwithbeads T010` instead of numbers
5. **Reconcile regularly**: The command auto-reconciles after each task, but you can run `/speckit.taskstobeads` manually anytime

## Exit Codes

- **0**: Success (task implemented and closed)
- **1**: Error (prerequisites failed, task not found, Beads not installed, no issues)
- **2**: Warning (task implemented but not closed, or user said "wait")