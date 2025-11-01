# Choice System Guide: How `event` and `goto_script` Work

## Overview
The choice system allows you to create branching dialogues where players can make decisions. Each choice can:
- Trigger custom events (via `event`)
- Jump to different dialogue scripts (via `goto_script`)
- Jump to specific lines in scripts (via `goto_line`)

## How It Works

### 1. **Creating a Choice Line**

A choice line is a `DialogueLine` that contains a `choices` parameter with a list of `DialogueChoice` objects:

```python
DialogueLine(
    speaker="Shione",
    text="Which path will you take?",
    choices=[
        DialogueChoice("Go left", event="go_left", goto_script="left_path"),
        DialogueChoice("Go right", event="go_right", goto_script="right_path"),
        DialogueChoice("Stay here", event="stay_here")  # No goto_script = continue in current script
    ],
    portrait_key="shione_neutral"
)
```

### 2. **The `event` Parameter**

**Purpose**: Triggers custom game logic when a choice is selected.

**How it works**:
1. When player selects a choice with an `event` string
2. The event string is returned from `select_choice()`
3. It's passed to `handle_dialogue_event(event_string)` in `game.py`
4. You add custom logic in `handle_dialogue_event()` to handle different events

**Example**:
```python
# In your dialogue script:
DialogueChoice("Open the door", event="unlock_door")

# In game.py, handle_dialogue_event():
def handle_dialogue_event(self, event: str):
    if event == "unlock_door":
        self.game_flags.add("door_unlocked")
        # Maybe play a sound, change a sprite, etc.
    elif event == "select_book1":
        self.game_flags.add("read_book1")
        # Track which book player chose
```

**Common use cases**:
- Unlock doors/items
- Set flags (e.g., `game_flags.add("flag_name")`)
- Play sounds/visual effects
- Change game state
- Start another dialogue script
- Anything else you want to happen when that choice is selected!

### 3. **The `goto_script` Parameter**

**Purpose**: Jumps to a different dialogue script after the choice is selected.

**How it works**:
1. If `goto_script` is specified, the dialogue system loads that script ID
2. If `goto_line` is also specified, it jumps to that line number (None = start from beginning)
3. The dialogue continues from that new script/line
4. If `goto_script` is not specified, it continues to the next line in the current script

**Example**:
```python
# Choice jumps to "book1" script
DialogueChoice("Read Book 1", goto_script="book1")

# Choice jumps to "book2" script, starting at line 5
DialogueChoice("Read Book 2", goto_script="book2", goto_line=5)

# Choice doesn't jump, just continues in current script
DialogueChoice("Skip", goto_script=None)  # or just omit goto_script
```

**Script IDs**: These must match the keys in `self.scripts` dictionary:
```python
self.scripts = {
    "book1": [DialogueLine(...), DialogueLine(...)],
    "book2": [DialogueLine(...), DialogueLine(...)],
    "left_path": [DialogueLine(...)],
    # etc.
}
```

### 4. **Using Both Together**

You can use `event` and `goto_script` together:

```python
DialogueChoice(
    "Enter the red room",
    event="enter_red_room",      # Triggers custom logic
    goto_script="red_room_intro" # Jumps to different script
)
```

When this choice is selected:
1. The `event` triggers `handle_dialogue_event("enter_red_room")`
2. The dialogue jumps to the `"red_room_intro"` script
3. Both happen in sequence

### 5. **Complete Example**

```python
# In simple_2d_game.py, inside DialogSystem.scripts:
"main_dialog": [
    DialogueLine(
        "Shione",
        "Which book would you like to read?",
        choices=[
            DialogueChoice(
                "Book about hope",
                event="select_hopeful_book",
                goto_script="book1"
            ),
            DialogueChoice(
                "Book about sadness",
                event="select_sad_book",
                goto_script="book2"
            ),
            DialogueChoice(
                "I don't want to read",
                event="reject_reading"
                # No goto_script = stays in current script
            )
        ],
        portrait_key="shione_neutral"
    ),
    # This line only shows if player chose "I don't want to read"
    DialogueLine("Shione", "That's okay, maybe later.", portrait_key="shione_neutral")
],

# In game.py, handle_dialogue_event():
def handle_dialogue_event(self, event: str):
    if event == "select_hopeful_book":
        self.game_flags.add("read_hopeful_book")
        print("Player chose the hopeful book!")
        
    elif event == "select_sad_book":
        self.game_flags.add("read_sad_book")
        print("Player chose the sad book!")
        
    elif event == "reject_reading":
        print("Player didn't want to read")
        # Maybe change Shione's dialogue next time
```

### 6. **Key Points**

- **`event`**: Optional string that triggers custom logic in `handle_dialogue_event()`
- **`goto_script`**: Optional script ID to jump to (must exist in `scripts` dictionary)
- **`goto_line`**: Optional line number within `goto_script` (None = start from beginning)
- You can use `event` alone, `goto_script` alone, or both together
- If neither is specified, dialogue just continues to the next line in current script
- Always wrap choices inside a `DialogueLine` with the `choices` parameter

### 7. **Fixing Your Code**

Your current code has a syntax issue. Here's the correct format:

```python
# ❌ WRONG - DialogueChoice can't be in script list directly
"room1_hall": [
    DialogueChoice(...)  # This won't work!
],

# ✅ CORRECT - Use DialogueLine with choices parameter
"room1_hall": [
    DialogueLine(
        "Shione",
        "Which book is the most favorite for you?",
        choices=[
            DialogueChoice("Book 1", event="select_book1", goto_script="book1"),
            DialogueChoice("Book 2", event="select_book2", goto_script="book2"),
            DialogueChoice("Book 3", event="select_book3", goto_script="book3"),
        ],
        portrait_key="shione_neutral"
    )
],
```

The key is: **`DialogueChoice` objects go inside the `choices` list of a `DialogueLine`**, not directly in the script list.

