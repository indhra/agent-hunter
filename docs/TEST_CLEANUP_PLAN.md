# Test Cleanup Plan for test_main.py

## Context
After simplifying main.py from 11 commands to 3 (hunt, audit, rollback), we have 32 failing tests for removed commands.

## Test Classes to REMOVE (for deleted commands)
1. **TestCmdContext** (line 64) - `context` command removed
2. **TestCmdScaffold** (line 117) - `scaffold` command removed
3. **TestCmdUpdate** (line 192) - `update` command removed (folded into audit workflow)
4. **TestCmdInstall** (line 445) - `install` command removed (folded into hunt workflow)
5. **TestCmdRemove** (line 498) - `remove` command removed
6. **TestCmdEnable** (line 545) - `enable` command removed
7. **TestCmdContribute** (line 598) - `contribute` command removed

## Test Classes to KEEP (for core functionality)
1. **TestDispatch** - command routing
2. **TestCmdRollback** - core command
3. **TestCmdAudit** - core command
4. **TestCmdHunt** - core command
5. **TestConfigLoading** - config system
6. **TestDeepMerge** - utility function
7. **TestListInstalledSkills** - helper function (check if still used)
8. **TestPromptConfirmActions** - confirmation UX
9. **TestCmdHuntWithConfirmation** - core workflow
10. **TestEdgeCases** - edge cases
11. **TestConfigErrorHandling** - error handling
12. **TestGetDangerousInstalled** - security helper (check if still used)
13. **TestPromptConfirmActionsEdgeCases** - edge cases
14. **TestCmdHuntActionExecution** - core workflow
15. **TestLoadConfigCorruptDefaults** - config validation
16. **TestHuntFlags** - hunt command flags

## Strategy
Rather than editing the 1875-line file, create a clean version by:
1. Extracting header imports and fixtures
2. Keeping only test classes for core commands (hunt, audit, rollback)
3. Removing all test classes for deleted commands
4. Preserve utility test classes (TestConfigLoading, TestDeepMerge, etc.)

## Expected Outcome
- Reduce test_main.py from ~1875 lines to ~1200 lines
- 100% passing tests for remaining functionality
- Clean foundation for Week 3 test coverage improvements
