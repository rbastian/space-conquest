# Turn Display UX Improvements Specification

**Version:** 1.0
**Date:** 2025-10-21
**Status:** APPROVED

---

## 1. Overview

### 1.1 Purpose

This specification defines three targeted UX improvements to the turn display interface for human players. These changes eliminate visual redundancy, improve information density, and enhance table readability.

### 1.2 Changes Summary

| Change | Description | Rationale |
|--------|-------------|-----------|
| **1. Single Turn Banner** | Remove duplicate "Turn N" announcement from within controlled stars table | Eliminates redundancy; banner already appears before combat reports |
| **2a. Column-Aligned Footer** | Add table footer with column-aligned totals for Resources and Ships | Improves scannability; standard table design pattern |
| **2b. Remove Warning Column** | Remove "Warning" column from controlled stars table | Column provides no actionable information; reduces visual clutter |

### 1.3 Design Goals

- **Reduce Clutter**: Eliminate duplicate and low-value information
- **Improve Scannability**: Use standard table patterns (aligned totals)
- **Maintain Clarity**: Preserve all strategic information needed for decision-making
- **Visual Consistency**: Use box-drawing characters matching existing table style

### 1.4 Cross-References

- [Space Conquest Core Spec](/specs/space_conquest_spec.md) — Core game mechanics
- [Combat Report Display Spec](/specs/combat_report_display_spec.md) — Combat report formatting

---

## 2. Change 1: Single Turn Banner

### 2.1 Current Behavior (BEFORE)

**Location:** `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/human_player.py`

The turn banner appears **twice** in the human player display:
1. **First occurrence**: Before combat reports (correct placement)
2. **Second occurrence**: Inside the controlled stars table (redundant)

**Current Display Flow:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    TURN 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚔️ Your fleet (15 ships) emerged from hyperspace...
⚔️ Admiral Sonnet's fleet (12 ships) captured K...

Your Controlled Stars (Turn 5):  ← REDUNDANT TURN ANNOUNCEMENT
┌──────┬─────────────────────┬───────────┬───────┬─────────┐
│ Code │ Star Name           │ Resources │ Ships │ Warning │
├──────┼─────────────────────┼───────────┼───────┼─────────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │         │
│ D    │ Deneb              │     2 RU  │    10 │         │
│ F    │ Fomalhaut          │     3 RU  │     8 │         │
└──────┴─────────────────────┴───────────┴───────┴─────────┘
```

### 2.2 New Behavior (AFTER)

**Goal:** Remove turn number from the controlled stars table header.

**New Display Flow:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    TURN 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚔️ Your fleet (15 ships) emerged from hyperspace...
⚔️ Admiral Sonnet's fleet (12 ships) captured K...

Your Controlled Stars:  ← TURN REMOVED
┌──────┬─────────────────────┬───────────┬───────┬─────────┐
│ Code │ Star Name           │ Resources │ Ships │ Warning │
├──────┼─────────────────────┼───────────┼───────┼─────────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │         │
│ D    │ Deneb              │     2 RU  │    10 │         │
│ F    │ Fomalhaut          │     3 RU  │     8 │         │
└──────┴─────────────────────┴───────────┴───────┴─────────┘
```

### 2.3 Implementation Details

**File to Modify:** `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/display.py`

**Function:** `format_controlled_stars_table()`

**Current Implementation:**
```python
def format_controlled_stars_table(stars_data: list[dict], turn: int) -> str:
    output = [f"Your Controlled Stars (Turn {turn}):"]  # ← REMOVE TURN
    # ... rest of table generation
```

**New Implementation:**
```python
def format_controlled_stars_table(stars_data: list[dict]) -> str:
    output = ["Your Controlled Stars:"]  # ← TURN PARAMETER REMOVED
    # ... rest of table generation
```

**Caller to Update:** `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/human_player.py`

```python
# BEFORE
table = format_controlled_stars_table(stars_data, current_turn)

# AFTER
table = format_controlled_stars_table(stars_data)
```

### 2.4 Rationale

- **Turn is redundant**: Already displayed prominently in banner
- **Visual clutter**: Repeating information reduces scannability
- **Consistency**: Other game sections don't repeat turn in subsection headers

---

## 3. Change 2a: Column-Aligned Footer with Totals

### 3.1 Current Behavior (BEFORE)

**Totals are displayed as plain text below the table:**

```
Your Controlled Stars:
┌──────┬─────────────────────┬───────────┬───────┬─────────┐
│ Code │ Star Name           │ Resources │ Ships │ Warning │
├──────┼─────────────────────┼───────────┼───────┼─────────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │         │
│ D    │ Deneb              │     2 RU  │    10 │         │
│ F    │ Fomalhaut          │     3 RU  │     8 │         │
└──────┴─────────────────────┴───────────┴───────┴─────────┘

Total Resources: 9 RU
Total Ships: 43
```

**Problems:**
- Totals are visually disconnected from their columns
- Hard to mentally map "Total Ships: 43" back to the "Ships" column
- Non-standard table design (most tables show totals in footer row)
- Wastes vertical space

### 3.2 New Behavior (AFTER)

**Totals are displayed in a column-aligned table footer:**

```
Your Controlled Stars:
┌──────┬─────────────────────┬───────────┬───────┐
│ Code │ Star Name           │ Resources │ Ships │
├──────┼─────────────────────┼───────────┼───────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │
│ D    │ Deneb              │     2 RU  │    10 │
│ F    │ Fomalhaut          │     3 RU  │     8 │
├──────┼─────────────────────┼───────────┼───────┤
│      │ TOTAL               │     9 RU  │    43 │
└──────┴─────────────────────┴───────────┴───────┘
```

**Benefits:**
- Visual alignment makes totals instantly readable
- Standard table design pattern (familiar to users)
- Saves 2 lines of vertical space
- Maintains box-drawing visual consistency

### 3.3 Column Width Specifications

**All columns use FIXED widths for alignment:**

| Column       | Width (chars) | Alignment | Format                          |
|--------------|---------------|-----------|----------------------------------|
| **Code**     | 6             | Left      | `"A 🏠 "` or `"D    "`          |
| **Star Name**| 21            | Left      | `"Altair             "`         |
| **Resources**| 11            | Right     | `"     4 RU"` (right-padded)    |
| **Ships**    | 7             | Right     | `"    25"` (right-padded)       |

**Width Calculation:**
```
Total table width = 6 + 21 + 11 + 7 + (4 separators) = 49 characters
Separator characters: │ (vertical bar between columns) and padding spaces
```

**Padding Rules:**
- **Code column**: Left-aligned, pad right with spaces to 6 chars
  - Home star emoji (🏠) counts as 2 chars (visually)
  - Example: `"A 🏠 "` = 'A' + ' ' + '🏠' + ' ' = 6 chars display width
- **Star Name column**: Left-aligned, pad right with spaces to 21 chars
  - Truncate star names longer than 21 chars (rare edge case)
  - Example: `"Altair             "` = 6 + 15 spaces = 21 chars
- **Resources column**: Right-aligned, format as `"%d RU"`, pad left to 11 chars
  - Example: `"     4 RU"` = 5 spaces + "4 RU" = 11 chars
- **Ships column**: Right-aligned, integer only, pad left to 7 chars
  - Example: `"    25"` = 4 spaces + "25" = 7 chars

### 3.4 Table Structure

**Complete table template:**

```
Your Controlled Stars:
┌──────┬─────────────────────┬───────────┬───────┐
│ Code │ Star Name           │ Resources │ Ships │  ← Header row
├──────┼─────────────────────┼───────────┼───────┤  ← Header separator
│ A 🏠 │ Altair             │     4 RU  │    25 │  ← Data rows
│ D    │ Deneb              │     2 RU  │    10 │
│ F    │ Fomalhaut          │     3 RU  │     8 │
├──────┼─────────────────────┼───────────┼───────┤  ← Footer separator (NEW)
│      │ TOTAL               │     9 RU  │    43 │  ← Footer row (NEW)
└──────┴─────────────────────┴───────────┴───────┘
```

**Box-Drawing Characters:**
- `┌` Top-left corner
- `┬` Top junction (between columns)
- `┐` Top-right corner
- `├` Left junction (row separator)
- `┼` Center junction (row separator between columns)
- `┤` Right junction (row separator)
- `│` Vertical bar (column separator)
- `─` Horizontal bar (row separator)
- `└` Bottom-left corner
- `┴` Bottom junction (between columns)
- `┘` Bottom-right corner

### 3.5 Footer Row Specifications

**Format:**
```
│ <6 spaces> │ TOTAL <16 spaces> │ <right-aligned RU> │ <right-aligned ships> │
```

**Implementation Details:**
```python
# Calculate totals
total_ru = sum(star['resources'] for star in stars_data)
total_ships = sum(star['ships'] for star in stars_data)

# Format footer row (same column widths as data rows)
code_cell = " " * 6                              # Empty code column
name_cell = "TOTAL" + " " * 16                   # "TOTAL" left-aligned in 21-char field
ru_cell = f"{total_ru:>8} RU"                    # Right-align RU value in 11-char field
ships_cell = f"{total_ships:>7}"                 # Right-align ships in 7-char field

footer_row = f"│ {code_cell} │ {name_cell} │ {ru_cell} │ {ships_cell} │"
```

**Separator Before Footer:**
```python
# Footer separator uses same structure as header separator
separator = "├──────┼─────────────────────┼───────────┼───────┤"
```

### 3.6 Implementation Checklist

**File to Modify:** `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/display.py`

**Function:** `format_controlled_stars_table()`

**Steps:**
1. **Remove Warning column** (see Change 2b)
2. **Update column width constants** (if not already defined)
3. **Calculate totals** after collecting all star data
4. **Remove plain-text total lines** (old "Total Resources: X" format)
5. **Add footer separator row** (├──────┼─────...┤)
6. **Add footer data row** with column-aligned totals
7. **Verify alignment** by testing with various data sets

---

## 4. Change 2b: Remove Warning Column

### 4.1 Current Behavior (BEFORE)

**The Warning column is always empty:**

```
Your Controlled Stars:
┌──────┬─────────────────────┬───────────┬───────┬─────────┐
│ Code │ Star Name           │ Resources │ Ships │ Warning │
├──────┼─────────────────────┼───────────┼───────┼─────────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │         │
│ D    │ Deneb              │     2 RU  │    10 │         │
│ F    │ Fomalhaut          │     3 RU  │     8 │         │
└──────┴─────────────────────┴───────────┴───────┴─────────┘
```

**Problems:**
- Column header takes 9 characters of width
- Always displays empty cells (no warnings ever shown)
- No functionality in codebase uses this column
- Wastes horizontal space

### 4.2 New Behavior (AFTER)

**Warning column removed entirely:**

```
Your Controlled Stars:
┌──────┬─────────────────────┬───────────┬───────┐
│ Code │ Star Name           │ Resources │ Ships │
├──────┼─────────────────────┼───────────┼───────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │
│ D    │ Deneb              │     2 RU  │    10 │
│ F    │ Fomalhaut          │     3 RU  │     8 │
├──────┼─────────────────────┼───────────┼───────┤
│      │ TOTAL               │     9 RU  │    43 │
└──────┴─────────────────────┴───────────┴───────┘
```

**Benefits:**
- Cleaner table with only actionable information
- Reduces table width by 10 characters (column + separator)
- Easier to scan (fewer columns = faster reading)
- Future-proof: if warnings are needed, combat reports are the proper place

### 4.3 Updated Table Structure (Final)

**Column specification after removal:**

| Column       | Width (chars) | Alignment | Format                          |
|--------------|---------------|-----------|----------------------------------|
| **Code**     | 6             | Left      | `"A 🏠 "` or `"D    "`          |
| **Star Name**| 21            | Left      | `"Altair             "`         |
| **Resources**| 11            | Right     | `"     4 RU"` (right-padded)    |
| **Ships**    | 7             | Right     | `"    25"` (right-padded)       |

**Total table width:** 49 characters (reduced from 59)

### 4.4 Implementation Details

**File to Modify:** `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/display.py`

**Function:** `format_controlled_stars_table()`

**Changes Required:**

1. **Remove Warning header cell:**
   ```python
   # BEFORE
   header = "│ Code │ Star Name           │ Resources │ Ships │ Warning │"

   # AFTER
   header = "│ Code │ Star Name           │ Resources │ Ships │"
   ```

2. **Update table borders:**
   ```python
   # BEFORE
   top_border = "┌──────┬─────────────────────┬───────────┬───────┬─────────┐"
   separator  = "├──────┼─────────────────────┼───────────┼───────┼─────────┤"
   bottom_border = "└──────┴─────────────────────┴───────────┴───────┴─────────┘"

   # AFTER
   top_border = "┌──────┬─────────────────────┬───────────┬───────┐"
   separator  = "├──────┼─────────────────────┼───────────┼───────┤"
   bottom_border = "└──────┴─────────────────────┴───────────┴───────┘"
   ```

3. **Remove Warning cell from data rows:**
   ```python
   # BEFORE
   row = f"│ {code} │ {star_name} │ {resources} │ {ships} │         │"

   # AFTER
   row = f"│ {code} │ {star_name} │ {resources} │ {ships} │"
   ```

4. **Update footer row** (already shown in Change 2a)

### 4.5 Code Search Requirements

**Implementer must verify no code references Warning column:**

```bash
# Search for any Warning-related logic in display code
grep -r "warning" src/interface/display.py
grep -r "Warning" src/interface/display.py

# Search for any Warning data being passed to display functions
grep -r "warning" src/interface/human_player.py
```

**Expected result:** No functional code relies on Warning column (only formatting code to be removed).

---

## 5. Complete Visual Example (Before/After)

### 5.1 BEFORE (Current Implementation)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    TURN 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚔️ Your fleet (15 ships) emerged from hyperspace and defeated the NPC garrison (5 ships) at D (Deneb). You now control D! (You lost 2 ships)
⚔️ Admiral Sonnet Krios's fleet (12 ships) emerged from hyperspace and captured K (Kappa Phoenicis). Admiral Sonnet Krios now controls K! (They lost 1 ship)

Your Controlled Stars (Turn 5):
┌──────┬─────────────────────┬───────────┬───────┬─────────┐
│ Code │ Star Name           │ Resources │ Ships │ Warning │
├──────┼─────────────────────┼───────────┼───────┼─────────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │         │
│ D    │ Deneb              │     2 RU  │    13 │         │
│ F    │ Fomalhaut          │     3 RU  │     8 │         │
│ M    │ Mintaka            │     1 RU  │     5 │         │
└──────┴─────────────────────┴───────────┴───────┴─────────┘

Total Resources: 10 RU
Total Ships: 51

Enter your orders for Turn 6:
```

**Line count:** 17 lines (from banner to input prompt)

### 5.2 AFTER (New Implementation)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    TURN 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚔️ Your fleet (15 ships) emerged from hyperspace and defeated the NPC garrison (5 ships) at D (Deneb). You now control D! (You lost 2 ships)
⚔️ Admiral Sonnet Krios's fleet (12 ships) emerged from hyperspace and captured K (Kappa Phoenicis). Admiral Sonnet Krios now controls K! (They lost 1 ship)

Your Controlled Stars:
┌──────┬─────────────────────┬───────────┬───────┐
│ Code │ Star Name           │ Resources │ Ships │
├──────┼─────────────────────┼───────────┼───────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │
│ D    │ Deneb              │     2 RU  │    13 │
│ F    │ Fomalhaut          │     3 RU  │     8 │
│ M    │ Mintaka            │     1 RU  │     5 │
├──────┼─────────────────────┼───────────┼───────┤
│      │ TOTAL               │    10 RU  │    51 │
└──────┴─────────────────────┴───────────┴───────┘

Enter your orders for Turn 6:
```

**Line count:** 14 lines (from banner to input prompt)

**Improvements:**
- ✅ 3 lines saved (17 → 14)
- ✅ Turn redundancy eliminated
- ✅ Warning column removed (10 chars narrower)
- ✅ Totals column-aligned (easier to scan)
- ✅ Standard table design pattern

---

## 6. Edge Cases & Special Scenarios

### 6.1 Single Star Controlled

**Scenario:** Player controls only their home star

```
Your Controlled Stars:
┌──────┬─────────────────────┬───────────┬───────┐
│ Code │ Star Name           │ Resources │ Ships │
├──────┼─────────────────────┼───────────┼───────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │
├──────┼─────────────────────┼───────────┼───────┤
│      │ TOTAL               │     4 RU  │    25 │
└──────┴─────────────────────┴───────────┴───────┘
```

**Handling:**
- Footer still displayed (shows totals even for single star)
- Footer separator still included
- No special-case logic needed

### 6.2 Many Stars Controlled (10+)

**Scenario:** Player controls 10+ stars (late game)

```
Your Controlled Stars:
┌──────┬─────────────────────┬───────────┬───────┐
│ Code │ Star Name           │ Resources │ Ships │
├──────┼─────────────────────┼───────────┼───────┤
│ A 🏠 │ Altair             │     4 RU  │    25 │
│ B    │ Betelgeuse         │     3 RU  │    18 │
│ C    │ Capella            │     2 RU  │    12 │
│ D    │ Deneb              │     2 RU  │    15 │
│ E    │ Epsilon Eridani    │     1 RU  │     8 │
│ F    │ Fomalhaut          │     3 RU  │    22 │
│ G    │ Gliese 581         │     2 RU  │    10 │
│ H    │ Hadar              │     1 RU  │     6 │
│ I    │ Izar               │     3 RU  │    19 │
│ J    │ Jabbah             │     2 RU  │    11 │
├──────┼─────────────────────┼───────────┼───────┤
│      │ TOTAL               │    23 RU  │   146 │
└──────┴─────────────────────┴───────────┴───────┘
```

**Handling:**
- Table scrolls vertically (no special truncation)
- Footer always at bottom after all data rows
- Large numbers (146 ships) still fit in 7-char Ships column

### 6.3 Very Long Star Names

**Scenario:** Star name exceeds 21 characters (rare but possible)

**Rule:** Truncate star name to 21 characters

**Example:**
```python
# Star name: "Zeta Reticuli Prime" (20 chars) - fits perfectly
# Star name: "Omicron Persei VIII Station" (28 chars) - needs truncation

def format_star_name(name: str, width: int = 21) -> str:
    """Format star name with truncation if needed."""
    if len(name) > width:
        return name[:width-3] + "..."  # "Omicron Persei VI..."
    return name.ljust(width)
```

**Display:**
```
│ O    │ Omicron Persei VI...│     2 RU  │    10 │
```

### 6.4 Large Numbers (999+ Ships)

**Scenario:** Player accumulates 999+ ships on a single star

**Handling:**
- Ships column width (7 chars) accommodates up to 9,999,999 ships
- Right-alignment preserves column structure
- No comma formatting (keeps numbers compact)

**Example:**
```
│ A 🏠 │ Altair             │     4 RU  │  1,523 │  ← If using commas (optional)
│ A 🏠 │ Altair             │     4 RU  │   1523 │  ← Without commas (recommended)
```

**Recommendation:** Do NOT use comma separators (keeps code simpler)

### 6.5 Zero Ships on Controlled Star

**Scenario:** Player controls star but has 0 ships (all in transit or destroyed)

**Handling:**
- Display "0" in Ships column (not blank)
- Tactical implication: star is vulnerable to attack

**Example:**
```
│ D    │ Deneb              │     2 RU  │     0 │
```

### 6.6 Empty Controlled Stars List (Game Over)

**Scenario:** Player has lost all stars (game should end, but defensive coding)

**Handling:**
```
Your Controlled Stars:
┌──────┬─────────────────────┬───────────┬───────┐
│ Code │ Star Name           │ Resources │ Ships │
├──────┼─────────────────────┼───────────┼───────┤
├──────┼─────────────────────┼───────────┼───────┤
│      │ TOTAL               │     0 RU  │     0 │
└──────┴─────────────────────┴───────────┴───────┘
```

**Note:** This scenario should trigger game over logic before display, but table should not crash if called.

---

## 7. Implementation Checklist

### 7.1 Change 1: Single Turn Banner

- [ ] Open `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/display.py`
- [ ] Locate `format_controlled_stars_table()` function
- [ ] Remove `turn` parameter from function signature
- [ ] Change header line from `f"Your Controlled Stars (Turn {turn}):"` to `"Your Controlled Stars:"`
- [ ] Open `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/human_player.py`
- [ ] Locate call to `format_controlled_stars_table()`
- [ ] Remove `turn` argument from function call
- [ ] Test: Verify turn banner appears only once (before combat reports)

### 7.2 Change 2b: Remove Warning Column (Do This First)

- [ ] Open `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/display.py`
- [ ] Locate `format_controlled_stars_table()` function
- [ ] Update header row: remove `│ Warning` column
- [ ] Update top border: change from 5 columns to 4 columns
  - Remove `┬─────────┐` segment
  - Change ending to `┬───────┐`
- [ ] Update header separator: change from 5 columns to 4 columns
  - Remove `┼─────────┤` segment
  - Change ending to `┼───────┤`
- [ ] Update data row formatting: remove warning cell from each row
  - Remove `│         │` at end of row
  - Change row ending to `│ {ships} │`
- [ ] Update bottom border: change from 5 columns to 4 columns
  - Remove `┴─────────┘` segment
  - Change ending to `┴───────┘`
- [ ] Verify no code references "warning" field in star data

### 7.3 Change 2a: Column-Aligned Footer (Do This Second)

- [ ] In `format_controlled_stars_table()`, after generating data rows:
  - [ ] Calculate `total_ru = sum(star['resources'] for star in stars_data)`
  - [ ] Calculate `total_ships = sum(star['ships'] for star in stars_data)`
- [ ] Remove old plain-text total lines:
  - [ ] Delete line: `output.append("")` (blank line before totals)
  - [ ] Delete line: `output.append(f"Total Resources: {total_ru} RU")`
  - [ ] Delete line: `output.append(f"Total Ships: {total_ships}")`
- [ ] Add footer separator row:
  - [ ] `footer_separator = "├──────┼─────────────────────┼───────────┼───────┤"`
  - [ ] `output.append(footer_separator)`
- [ ] Format footer row:
  - [ ] `code_cell = " " * 6`
  - [ ] `name_cell = "TOTAL" + " " * 16`
  - [ ] `ru_cell = f"{total_ru:>8} RU"`
  - [ ] `ships_cell = f"{total_ships:>7}"`
  - [ ] `footer_row = f"│ {code_cell} │ {name_cell} │ {ru_cell} │ {ships_cell} │"`
  - [ ] `output.append(footer_row)`
- [ ] Add bottom border (already exists, just verify placement after footer row)
- [ ] Test alignment with various data sets

### 7.4 Testing Requirements

**Test Case 1: Single Star**
- Input: Player controls only home star (A, Altair, 4 RU, 4 ships)
- Expected: Table displays correctly with footer showing "TOTAL | 4 RU | 4"

**Test Case 2: Multiple Stars**
- Input: Player controls 4 stars with varying resources and ships
- Expected: Footer totals match sum of all rows

**Test Case 3: Large Numbers**
- Input: One star has 999 ships
- Expected: Ships column displays "999" right-aligned in 7-char field

**Test Case 4: Long Star Name**
- Input: Star name with 25 characters
- Expected: Name truncated to 21 chars (18 chars + "...")

**Test Case 5: Zero Ships**
- Input: One controlled star has 0 ships
- Expected: Ships column displays "0" (not blank)

**Test Case 6: Home Star Emoji**
- Input: Home star with 🏠 emoji
- Expected: Code column displays "A 🏠 " correctly within 6-char width

**Test Case 7: Visual Alignment**
- Input: Print table to terminal
- Expected: All columns perfectly aligned, box-drawing characters form clean grid

---

## 8. Testing Criteria for Verification

### 8.1 Visual Inspection Tests

**Test 1: Banner Uniqueness**
- ✓ Turn banner appears exactly once per turn
- ✓ Turn banner appears before combat reports
- ✓ Table header does not include turn number

**Test 2: Table Structure**
- ✓ Table uses box-drawing characters (┌┬┐├┼┤└┴┘│─)
- ✓ All columns have consistent width
- ✓ Header row uses correct column titles
- ✓ Footer separator matches header separator style
- ✓ Footer row has "TOTAL" label in Star Name column

**Test 3: Column Alignment**
- ✓ Code column: left-aligned, 6 chars wide
- ✓ Star Name column: left-aligned, 21 chars wide
- ✓ Resources column: right-aligned, 11 chars wide, format "X RU"
- ✓ Ships column: right-aligned, 7 chars wide, integer only
- ✓ Footer totals align perfectly with data columns above

**Test 4: Data Accuracy**
- ✓ Footer "TOTAL" RU matches sum of all Resources values
- ✓ Footer "TOTAL" Ships matches sum of all Ships values
- ✓ Home star emoji (🏠) displays correctly in Code column
- ✓ Star names display without corruption

### 8.2 Functional Tests

**Test 5: Edge Cases**
- ✓ Single controlled star: footer displays correctly
- ✓ 10+ controlled stars: table scrolls, footer at bottom
- ✓ Star name > 21 chars: truncated with "..."
- ✓ 0 ships on star: displays "0" not blank
- ✓ Large ship count (999+): displays correctly

**Test 6: Integration**
- ✓ Display works correctly after combat reports
- ✓ Display works correctly with no combat reports
- ✓ Display works correctly on Turn 1 (initial state)
- ✓ Display works correctly on Turn 50+ (late game)

### 8.3 Code Quality Tests

**Test 7: No Warnings References**
- ✓ Grep search for "warning" in display.py returns 0 results
- ✓ Grep search for "Warning" in display.py returns 0 results
- ✓ No unused code related to Warning column

**Test 8: No Turn Duplication**
- ✓ Function signature does not include `turn` parameter
- ✓ No turn formatting in table header
- ✓ Caller does not pass turn argument

---

## 9. Files to Modify (Reference)

### 9.1 Primary Implementation Files

| File Path | Changes Required |
|-----------|------------------|
| `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/display.py` | • Remove `turn` parameter from `format_controlled_stars_table()`<br>• Remove Warning column from table structure<br>• Add column-aligned footer with totals<br>• Update all box-drawing border strings |
| `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/human_player.py` | • Update call to `format_controlled_stars_table()` to remove `turn` argument<br>• Verify no other code depends on Warning column |

### 9.2 Files NOT to Modify

**The following files should NOT be changed for this specification:**

- `/Users/robert.bastian/github.com/rbastian/space-conquest/game.py` — Main game loop (no changes needed)
- `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/llm_player.py` — LLM interface (not affected)
- Any files in `/Users/robert.bastian/github.com/rbastian/space-conquest/src/core/` — Core game logic (not affected)

---

## 10. Design Rationale

### 10.1 Why Remove Turn from Table Header?

**Problem:** Turn number appears twice on screen (banner + table header)

**Solution:** Remove from table header, keep in banner

**Rationale:**
- **Visibility**: Banner is more prominent and appears first
- **Redundancy**: Repeating information reduces signal-to-noise ratio
- **Consistency**: Other sections (combat reports, fleets) don't repeat turn
- **User Feedback**: Players noted the duplication felt cluttered

### 10.2 Why Use Column-Aligned Footer?

**Problem:** Plain-text totals below table are visually disconnected

**Solution:** Add footer row with column-aligned totals

**Rationale:**
- **Scannability**: Eye can immediately associate "43" with "Ships" column
- **Standard Pattern**: Most tables (spreadsheets, reports) use footer rows
- **Space Efficiency**: Saves 2 lines of vertical space
- **Professional Appearance**: Matches expected table design conventions

### 10.3 Why Remove Warning Column?

**Problem:** Warning column always empty, wastes 10 chars of width

**Solution:** Remove column entirely

**Rationale:**
- **Zero Value**: Column never displays any information
- **No Future Use**: Combat reports are proper place for warnings/alerts
- **Width Reduction**: Makes table 10 chars narrower (easier to read)
- **Clarity**: Removing unused UI elements reduces cognitive load

### 10.4 Why Fixed-Width Columns?

**Problem:** Dynamic column widths cause alignment issues

**Solution:** Use fixed widths for all columns

**Rationale:**
- **Consistency**: Footer totals must align perfectly with data columns
- **Predictability**: Players can quickly scan fixed-position columns
- **Implementation Simplicity**: No need to calculate max widths per turn
- **Aesthetic**: Clean grid appearance with box-drawing characters

---

## 11. Future Considerations (Out of Scope)

### 11.1 Sortable Columns

**Description:** Allow player to sort table by Code, Star Name, Resources, or Ships

**Benefits:**
- Strategic flexibility (e.g., "show me weakest-defended stars")
- Better late-game management with many stars

**Implementation Considerations:**
- Requires interactive UI (not just display formatting)
- Need to preserve home star prominence (always show first?)
- Command syntax for sorting (e.g., `sort stars by ships`)

### 11.2 Conditional Highlighting

**Description:** Highlight rows with warnings (e.g., 0 ships, under attack)

**Benefits:**
- Immediate visual warning of vulnerable stars
- Replaces removed Warning column with richer information

**Implementation Considerations:**
- ANSI color codes for terminal highlighting
- Define warning conditions (0 ships? enemy fleet incoming?)
- Ensure highlighting doesn't break table alignment

### 11.3 Fleet In-Transit Column

**Description:** Show ships en route to each star

**Benefits:**
- Better situational awareness
- Reduces need to check fleet arrivals separately

**Implementation Considerations:**
- Requires fleet movement tracking
- Column width implications (table becomes wider)
- How to display multiple fleets arriving same turn?

### 11.4 Resource Production Forecast

**Description:** Show next-turn production in Resources column (e.g., "4 RU → 6 RU")

**Benefits:**
- Helps planning for ship builds
- Shows impact of recent conquests

**Implementation Considerations:**
- Production rules must be clearly defined (spec says 1 RU/turn?)
- Column width increases
- May be information overload

---

## 12. Appendix: Complete Code Example

### 12.1 Updated Function Signature

```python
def format_controlled_stars_table(stars_data: list[dict]) -> str:
    """
    Format controlled stars table with column-aligned footer.

    Args:
        stars_data: List of dicts with keys: 'code', 'name', 'resources', 'ships', 'is_home'

    Returns:
        Multi-line string with formatted table

    Example stars_data:
        [
            {'code': 'A', 'name': 'Altair', 'resources': 4, 'ships': 25, 'is_home': True},
            {'code': 'D', 'name': 'Deneb', 'resources': 2, 'ships': 10, 'is_home': False}
        ]
    """
```

### 12.2 Column Width Constants

```python
# Column widths (include padding)
COL_CODE_WIDTH = 6      # "A 🏠 " or "D    "
COL_NAME_WIDTH = 21     # "Altair             "
COL_RU_WIDTH = 11       # "     4 RU"
COL_SHIPS_WIDTH = 7     # "    25"

# Box-drawing characters
CORNER_TL = "┌"
CORNER_TR = "┐"
CORNER_BL = "└"
CORNER_BR = "┘"
JUNCTION_T = "┬"
JUNCTION_B = "┴"
JUNCTION_L = "├"
JUNCTION_R = "┤"
JUNCTION_C = "┼"
VBAR = "│"
HBAR = "─"
```

### 12.3 Table Structure Template

```python
def format_controlled_stars_table(stars_data: list[dict]) -> str:
    output = []

    # Section header
    output.append("Your Controlled Stars:")

    # Top border
    top_border = f"{CORNER_TL}{HBAR * COL_CODE_WIDTH}{JUNCTION_T}{HBAR * COL_NAME_WIDTH}{JUNCTION_T}{HBAR * COL_RU_WIDTH}{JUNCTION_T}{HBAR * COL_SHIPS_WIDTH}{CORNER_TR}"
    output.append(top_border)

    # Header row
    header = f"{VBAR} {'Code':<{COL_CODE_WIDTH-1}} {VBAR} {'Star Name':<{COL_NAME_WIDTH-1}} {VBAR} {'Resources':>{COL_RU_WIDTH-1}} {VBAR} {'Ships':>{COL_SHIPS_WIDTH-1}} {VBAR}"
    output.append(header)

    # Header separator
    header_sep = f"{JUNCTION_L}{HBAR * COL_CODE_WIDTH}{JUNCTION_C}{HBAR * COL_NAME_WIDTH}{JUNCTION_C}{HBAR * COL_RU_WIDTH}{JUNCTION_C}{HBAR * COL_SHIPS_WIDTH}{JUNCTION_R}"
    output.append(header_sep)

    # Data rows
    total_ru = 0
    total_ships = 0

    for star in stars_data:
        code = star['code']
        if star['is_home']:
            code += " 🏠"
        code = code.ljust(COL_CODE_WIDTH - 1)

        name = star['name'][:COL_NAME_WIDTH - 1].ljust(COL_NAME_WIDTH - 1)

        resources = f"{star['resources']} RU".rjust(COL_RU_WIDTH - 1)
        ships = str(star['ships']).rjust(COL_SHIPS_WIDTH - 1)

        row = f"{VBAR} {code} {VBAR} {name} {VBAR} {resources} {VBAR} {ships} {VBAR}"
        output.append(row)

        total_ru += star['resources']
        total_ships += star['ships']

    # Footer separator
    footer_sep = f"{JUNCTION_L}{HBAR * COL_CODE_WIDTH}{JUNCTION_C}{HBAR * COL_NAME_WIDTH}{JUNCTION_C}{HBAR * COL_RU_WIDTH}{JUNCTION_C}{HBAR * COL_SHIPS_WIDTH}{JUNCTION_R}"
    output.append(footer_sep)

    # Footer row
    code_cell = " " * (COL_CODE_WIDTH - 1)
    name_cell = "TOTAL".ljust(COL_NAME_WIDTH - 1)
    ru_cell = f"{total_ru} RU".rjust(COL_RU_WIDTH - 1)
    ships_cell = str(total_ships).rjust(COL_SHIPS_WIDTH - 1)

    footer = f"{VBAR} {code_cell} {VBAR} {name_cell} {VBAR} {ru_cell} {VBAR} {ships_cell} {VBAR}"
    output.append(footer)

    # Bottom border
    bottom_border = f"{CORNER_BL}{HBAR * COL_CODE_WIDTH}{JUNCTION_B}{HBAR * COL_NAME_WIDTH}{JUNCTION_B}{HBAR * COL_RU_WIDTH}{JUNCTION_B}{HBAR * COL_SHIPS_WIDTH}{CORNER_BR}"
    output.append(bottom_border)

    return "\n".join(output)
```

**Note:** This is pseudocode for clarity. Actual implementation should match existing code style.

---

## 13. Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-21 | Initial specification for three UX improvements | game-design-oracle |

---

**END OF SPECIFICATION**
