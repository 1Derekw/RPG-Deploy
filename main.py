from drafter import *
from dataclasses import dataclass, fields
import random
import time
import math
import json


# ==========================================
# COMPACT LAYOUT FOR NON-MAP SCREENS
# ==========================================

_original_drafter_page = Page

_COMPACT_SCREEN_CSS = """
body {
    line-height: 1.25;
}
h1, h2, h3, h4 {
    margin-top: 0.45em;
    margin-bottom: 0.35em;
}
p {
    margin-top: 0.25em;
    margin-bottom: 0.25em;
}
button {
    margin: 3px 3px 3px 0;
    padding: 5px 9px;
}
"""

# Hovering over any item name shows its weight. The weights come from
# ITEM_WEIGHTS (see below), which is filled into this script at runtime.
_WEIGHT_TOOLTIP_JS = r"""
(function () {
    var WEIGHTS = __WEIGHTS__;
    var NOTES = __DESCRIPTIONS__;
    var NAMES = __NAMES__;
    var pattern = new RegExp(
        "^\\s*(?:\u2713\\s*|Use\\s+)?" +
        "(the crown|crafting tablet|iron sword|wood|iron|leather|rations?|medicine|club|stake|scaffolding|bow|arrows?|sinew)" +
        "(?=\\s*(?::|\\(|selected))",
        "i"
    );

    // Returns {title, note, italic} for text that names an item.
    function tipFor(text) {
        var match = pattern.exec(text);

        if (!match) {
            return null;
        }

        var key = match[1].toLowerCase();

        if (key === "ration") {
            key = "rations";
        }

        if (key === "the crown") {
            key = "crown";
        }

        if (!(key in WEIGHTS)) {
            return null;
        }

        var name = NAMES[key]
            || key.charAt(0).toUpperCase() + key.slice(1);
        var tip = {
            title: name + " - weight: " + WEIGHTS[key],
            note: "",
            italic: false
        };

        if (key in NOTES) {
            tip.note = NOTES[key].text;
            tip.italic = NOTES[key].italic;
        }

        return tip;
    }

    function markElement(element, tip) {
        element.setAttribute("data-tip", tip.title);

        if (tip.note) {
            element.setAttribute("data-tip-note", tip.note);
        }

        if (tip.italic) {
            element.setAttribute("data-tip-italic", "1");
        }
    }

    // Mark every item name with its tooltip text.
    function addTooltips() {
        var walker = document.createTreeWalker(
            document.body, NodeFilter.SHOW_TEXT, null
        );
        var nodes = [];

        while (walker.nextNode()) {
            nodes.push(walker.currentNode);
        }

        nodes.forEach(function (node) {
            var parent = node.parentNode;

            if (!parent || parent.nodeName === "SCRIPT"
                || parent.nodeName === "STYLE") {
                return;
            }

            var tip = tipFor(node.nodeValue);

            if (!tip) {
                return;
            }

            if (parent.children.length === 0) {
                // The text is the only thing in its element.
                markElement(parent, tip);
            } else if (parent.getAttribute("data-tip-wrapper") !== "1") {
                // The text shares its element with a button: wrap it.
                var span = document.createElement("span");
                markElement(span, tip);
                span.setAttribute("data-tip-wrapper", "1");
                parent.replaceChild(span, node);
                span.appendChild(node);
            }
        });
    }

    // One instant tooltip box that follows the cursor.
    function getTipBox() {
        var box = document.getElementById("weight_tip_box");

        if (!box) {
            box = document.createElement("div");
            box.id = "weight_tip_box";
            box.style.cssText =
                "position: fixed; display: none; z-index: 99999; " +
                "pointer-events: none; padding: 3px 8px; " +
                "background: #000; color: #fff; " +
                "border: 1px solid #aaa; border-radius: 4px; " +
                "font-size: 13px; white-space: nowrap;";
            document.body.appendChild(box);
        }

        return box;
    }

    function fillTipBox(box, target) {
        box.textContent = "";

        var title = document.createElement("div");
        title.textContent = target.getAttribute("data-tip");
        box.appendChild(title);

        var note = target.getAttribute("data-tip-note");

        if (note) {
            var noteLine = document.createElement("div");
            noteLine.textContent = note;

            if (target.getAttribute("data-tip-italic") === "1") {
                noteLine.style.fontStyle = "italic";
            }

            box.appendChild(noteLine);
        }
    }

    function moveTipBox(event) {
        var box = getTipBox();
        box.style.left = (event.clientX + 14) + "px";
        box.style.top = (event.clientY + 16) + "px";
    }

    // Listeners are attached to the document only once, even if
    // this script runs again after a page change.
    if (!window.__weightTipsInstalled) {
        window.__weightTipsInstalled = true;

        document.addEventListener("mouseover", function (event) {
            var target = event.target.closest
                ? event.target.closest("[data-tip]")
                : null;
            var box = getTipBox();

            if (target) {
                fillTipBox(box, target);
                box.style.display = "block";
                moveTipBox(event);
            } else {
                box.style.display = "none";
            }
        });

        document.addEventListener("mousemove", function (event) {
            var box = getTipBox();

            if (box.style.display === "block") {
                moveTipBox(event);
            }
        });

        document.addEventListener("mouseout", function (event) {
            if (!event.relatedTarget) {
                getTipBox().style.display = "none";
            }
        });
    }

    addTooltips();
    setTimeout(addTooltips, 100);
    setTimeout(addTooltips, 500);
})();
"""


def Page(state, content, *args, **kwargs):
    # Leave the map screen's layout untouched; compact every other screen.
    if getattr(state, "screen", None) not in ("map", "storage", "craft", "loot"):
        existing_css = kwargs.get("css", "")
        kwargs["css"] = _COMPACT_SCREEN_CSS + "\n" + existing_css

    # Add the item-weight hover text to every screen.
    tooltip_js = _WEIGHT_TOOLTIP_JS.replace(
        "__WEIGHTS__", json.dumps(ITEM_WEIGHTS)
    ).replace(
        "__DESCRIPTIONS__", json.dumps(ITEM_DESCRIPTIONS)
    ).replace(
        "__NAMES__", json.dumps(ITEM_NAMES)
    )
    kwargs["js"] = kwargs.get("js", "") + "\n" + tooltip_js

    return _original_drafter_page(state, content, *args, **kwargs)



# ==========================================
# SETTINGS
# ==========================================

MAP_SIZE = 60
START_X = 30
START_Y = 30

# Moved from (47, 20): approximately 5 steps toward the
# second stronghold, followed by 10 steps away from camp.
TOWER_LOCATION = (54, 22)

TRAP_COOLDOWN = 30
SCAVENGE_COOLDOWN = 60

RESOURCE_TYPES = ["wood", "iron", "leather"]

ITEM_WEIGHTS = {
    "wood": 1,
    "iron": 4,
    "leather": 2,
    "rations": 1,
    "medicine": 4,
    "club": 3,
    "stake": 0.5,
    "iron sword": 8,
    "bow": 8,
    "arrows": 0.1,
    "sinew": 1,
    "scaffolding": 1,
    "crafting tablet": 10,
    "crown": 40
}

# Display names for items whose name is not just the key.
ITEM_NAMES = {
    "crown": "The Crown",
    "iron sword": "Iron Sword",
    "crafting tablet": "Crafting Tablet",
    "arrows": "Arrows"
}


def item_label(item):
    return ITEM_NAMES.get(item, item.title())


# Extra sentence shown in an item's hover text (after its weight).
ITEM_DESCRIPTIONS = {
    "scaffolding": {
        "text": "Will be useful for climbing.",
        "italic": False
    },
    "bow": {
        "text": "Flying Enemies Beware!",
        "italic": False
    },
    "crafting tablet": {
        "text": "Great for crafting on the go!",
        "italic": False
    },
    "crown": {
        "text": "heavy the head that wears the crown",
        "italic": True
    }
}

ALL_ITEMS = [
    "wood", "iron", "leather", "rations",
    "medicine", "club", "stake", "iron sword", "bow", "arrows",
    "sinew", "scaffolding", "crafting tablet"
]


# ==========================================
# GAME STATE
# ==========================================

@dataclass
class State:
    player_health: int
    player_max_health: int
    player_x: int
    player_y: int

    enemy_health: int
    enemy_max_health: int
    enemy_damage: int
    enemy_name: str

    message: str
    game_over: bool
    victory: bool
    in_encounter: bool
    screen: str

    terrain: list
    explored: list
    permanent_explored: list
    expedition_explored: list

    houses: list
    strongholds: list
    searched_locations: list
    secured_locations: list
    completed_strongholds: list
    roads: list

    inventory: dict
    storage: dict
    capacity: int

    weapon_name: str
    weapon_weight: int

    movement_steps: int
    trap_count: int
    last_trap_time: float
    last_scavenge_time: float

    event_log: list

    selected_attacks: list
    selected_healing: list
    turn_number: int

    discovered_materials: list

    current_location: tuple
    location_stage: int

    pending_loot: dict
    loot_return_action: str
    stronghold_progress: dict
    claimed_outposts: list
    combat_kind: str

    leather_armor: bool
    iron_armor: bool

    house_progress: dict
    completed_houses: list
    iron_mines: list
    mine_progress: dict
    completed_mines: list
    iron_crafting_unlocked: bool

    skeleton_safe_steps: int = 0
    protein_shake: bool = False
    tower_location: tuple = TOWER_LOCATION
    tower_level: int = 0
    tower_active: bool = False

    # Items dropped while looting. These remain available
    # until the player leaves the loot screen.
    dropped_items: dict = None

    # Run statistics shown on the winning screen.
    game_start_time: float = 0.0
    game_end_time: float = 0.0
    total_collected: dict = None
    total_healing: int = 0

    # Health of each Spawned Skeleton in front of The Necromancer.
    # The first one in the list is the one the player is attacking.
    skeleton_queue: list = None

    # The Shield is a permanent upgrade: it gives a second evasion roll.
    shield: bool = False

    # True while the player is using the Crafting Tablet from a loot page.
    tablet_mode: bool = False


# ==========================================
# EVENT LOG
# ==========================================

def split_message_lines(message):
    # Break a multi-line message into separate lines, collapsing
    # consecutive repeats of the same line.
    lines = []

    for line in (message or "").splitlines():
        if line.strip() and (not lines or lines[-1] != line):
            lines.append(line)

    return lines


def add_log(state, message):
    # Each line of a message is stored as its own log entry so that
    # the log can reliably tell what has already been recorded.
    for line in split_message_lines(message):
        if not state.event_log or state.event_log[-1] != line:
            state.event_log.append(line)

        if len(state.event_log) > 5:
            state.event_log.pop(0)


def event_log_content(state):
    # Automatically put new messages in the event log. This catches
    # messages from routes that only set state.message.
    message_lines = split_message_lines(state.message)

    if message_lines:
        # Many routes already call add_log themselves. Only log the
        # message here if its lines are not already the newest entries.
        recent = message_lines[-5:]

        if state.event_log[-len(recent):] != recent:
            add_log(state, state.message)

    # The message has now been handled; clear it so that an old message
    # can never be logged a second time on a later page.
    state.message = ""

    content = [Header("EVENT LOG")]

    # Text components render inline in Drafter, so each message must be
    # wrapped in a Div to force a separate block/line in the browser.
    # Keep the five most recent messages, newest first.
    for message in reversed(state.event_log[-5:]):
        content.append(Div(Text(message)))

    return content


# ==========================================
# INVENTORY
# ==========================================

def item_weight(item):
    return ITEM_WEIGHTS.get(item, 0)


def inventory_weight(state):
    total = 0

    for item, amount in state.inventory.items():
        total += item_weight(item) * amount

    return total


def displayed_inventory_weight(state):
    # Capacity is checked using the exact weight; only the display rounds up.
    return str(math.ceil(inventory_weight(state) - 1e-9))


def add_item(state, item, amount):
    added = 0

    for _ in range(amount):
        if inventory_weight(state) + item_weight(item) <= state.capacity + 1e-9:
            state.inventory[item] = state.inventory.get(item, 0) + 1
            added += 1
        else:
            break

    return added


def remove_item(state, item, amount):
    if state.inventory.get(item, 0) < amount:
        return False

    state.inventory[item] -= amount

    if state.inventory[item] <= 0:
        del state.inventory[item]

    return True


def storage_has(state, item, amount):
    return state.storage.get(item, 0) >= amount


def spend_storage(state, item, amount):
    if not storage_has(state, item, amount):
        return False

    state.storage[item] -= amount

    if state.storage[item] <= 0:
        del state.storage[item]

    return True


def transfer_to_inventory(state, item):
    if state.storage.get(item, 0) <= 0:
        state.message = "There is none of that item in storage."
        return

    if add_item(state, item, 1) == 0:
        state.message = "You do not have enough carrying capacity."
        return

    state.storage[item] -= 1

    if state.storage[item] <= 0:
        del state.storage[item]

    state.message = ""


def transfer_to_storage(state, item):
    if state.inventory.get(item, 0) <= 0:
        state.message = "You are not carrying any of that item."
        return

    remove_item(state, item, 1)
    state.storage[item] = state.storage.get(item, 0) + 1
    state.message = ""


def transfer_amount_to_inventory(state, item, amount):
    stored = state.storage.get(item, 0)
    requested = min(amount, stored)
    if requested <= 0:
        state.message = "There is none of that item in storage."
        return
    added = add_item(state, item, requested)
    if added <= 0:
        state.message = "You do not have enough carrying capacity."
        return
    state.storage[item] -= added
    if state.storage[item] <= 0:
        del state.storage[item]
    state.message = "Took " + str(added) + " " + item + " from storage."


MATERIAL_ITEMS = ["wood", "iron", "leather", "rations", "sinew", "arrows"]

# Items that can be rolled as loot (no weapons or tools).
LOOT_ROLLABLE_ITEMS = [
    "wood", "iron", "leather", "rations", "medicine"
]

# Items that get an "All" button in the storage column.
TAKE_ALL_ITEMS = [
    "wood", "iron", "leather", "rations", "medicine", "scaffolding",
    "sinew", "arrows"
]


def transfer_all_materials_to_storage(state):
    moved = 0

    for item in MATERIAL_ITEMS:
        amount = state.inventory.get(item, 0)

        if amount > 0:
            remove_item(state, item, amount)
            state.storage[item] = state.storage.get(item, 0) + amount
            moved += amount

    if moved == 0:
        state.message = "You are not carrying any materials."
    else:
        state.message = "Moved all materials to storage."


def transfer_all_to_inventory(state, item):
    stored = state.storage.get(item, 0)

    if stored <= 0:
        state.message = "There is none of that item in storage."
        return

    added = add_item(state, item, stored)

    if added == 0:
        state.message = "You do not have enough carrying capacity."
        return

    state.storage[item] -= added

    if state.storage[item] <= 0:
        del state.storage[item]

    if added < stored:
        state.message = (
            "Took " + str(added) + " " + item
            + " (carrying capacity reached)."
        )
    else:
        state.message = ""


# ==========================================
# LOOT DROPPING AND PICKING UP
# ==========================================

def drop_loot_item(state, item):
    if state.inventory.get(item, 0) <= 0:
        state.message = "You are not carrying any " + item + "."
        return

    remove_item(state, item, 1)

    if state.dropped_items is None:
        state.dropped_items = {}

    state.dropped_items[item] = state.dropped_items.get(item, 0) + 1

    state.message = ""


def pick_up_dropped_item(state, item):
    if state.dropped_items is None:
        state.dropped_items = {}

    if state.dropped_items.get(item, 0) <= 0:
        state.message = "There is no dropped " + item + " here."
        return

    if add_item(state, item, 1) == 0:
        state.message = "You do not have enough carrying capacity."
        return

    state.dropped_items[item] -= 1

    if state.dropped_items[item] <= 0:
        del state.dropped_items[item]

    state.message = ""


# ==========================================
# HEALTH AND EVASION
# ==========================================

def record_collected(state, item, amount):
    # Keeps the running totals shown on the winning screen.
    if state.total_collected is None:
        state.total_collected = {}

    state.total_collected[item] = state.total_collected.get(item, 0) + amount


def heal_player(state, amount):
    # Heals up to the maximum and records how much health was
    # actually restored for the winning screen.
    healed = max(0, min(amount, state.player_max_health - state.player_health))
    state.player_health += healed
    state.total_healing += healed
    return healed


def health_bar(current_health, max_health):
    if max_health <= 0:
        return "[----------]"

    filled = current_health * 10 // max_health
    filled = min(filled, 10)
    return "[" + "#" * filled + "-" * (10 - filled) + "]"


def evades_attack():
    return random.randint(1, 10) == 1


def player_evades_attack(state):
    if evades_attack():
        return True

    if state.shield:
        if evades_attack():
            return True

    return False


# ==========================================
# LOOT TABLE
# ==========================================

def roll_loot(number_of_rolls=5, reroll_empty=False):
    loot = {
        "rations": 0,
        "wood": 0,
        "leather": 0,
        "medicine": 0,
        "iron": 0
    }

    successful_rolls = 0

    while successful_rolls < number_of_rolls:
        roll = random.randint(1, 100)
        found_item = False

        if roll <= 40:
            pass
        elif roll <= 70:
            loot["rations"] += random.randint(1, 2)
            found_item = True
        elif roll <= 85:
            loot["wood"] += random.randint(1, 2)
            found_item = True
        elif roll <= 95:
            loot["leather"] += random.randint(1, 2)
            found_item = True
        elif roll <= 97.5:
            loot["medicine"] += 1
            found_item = True
        else:
            loot["iron"] += 1
            found_item = True

        if found_item or not reroll_empty:
            successful_rolls += 1

    return loot


def roll_tower_loot(number_of_rolls=5):
    # The tower's own loot table (every roll counts):
    #   40% nothing
    #   30% 1 to 6 wood
    #   20% 3 to 7 rations
    #   10% 1 to 2 medicine
    loot = {
        "rations": 0,
        "wood": 0,
        "leather": 0,
        "medicine": 0,
        "iron": 0
    }

    for _ in range(number_of_rolls):
        roll = random.randint(1, 100)

        if roll <= 40:
            pass
        elif roll <= 70:
            loot["wood"] += random.randint(1, 6)
        elif roll <= 90:
            loot["rations"] += random.randint(3, 7)
        else:
            loot["medicine"] += random.randint(1, 2)

    return loot


# ==========================================
# LOOT SELECTION
# ==========================================

def take_loot_item(state, item):
    if state.pending_loot.get(item, 0) <= 0:
        state.message = "There is no more " + item + " available."
        return

    if add_item(state, item, 1) == 0:
        state.message = (
            "You do not have enough carrying capacity. "
            "Drop something from your inventory to make room."
        )
        return

    state.pending_loot[item] -= 1

    if state.pending_loot[item] <= 0:
        del state.pending_loot[item]

    # Keep a running total of everything picked up from loot.
    record_collected(state, item, 1)

    if item in RESOURCE_TYPES:
        if item not in state.discovered_materials:
            state.discovered_materials.append(item)

    state.message = ""


def crafting_tablet_available(state):
    # The tablet only works from loot pages shown after a fight
    # (not from the outpost's ration pile).
    return (
        state.inventory.get("crafting tablet", 0) > 0
        and state.loot_return_action not in ("", "outpost")
    )


def loot_page(state):
    state.screen = "loot"

    if state.dropped_items is None:
        state.dropped_items = {}

    inventory_content = [Header("YOUR INVENTORY")]
    loot_content = [Header("AVAILABLE LOOT")]
    dropped_content = [Header("DROPPED ITEMS")]

    # The Crown only exists on the loot page shown after The King.
    king_loot = state.loot_return_action == "tower_king"

    if king_loot:
        carried_items = ALL_ITEMS + ["crown"]
        available_items = ["crown"]
    else:
        carried_items = ALL_ITEMS
        available_items = LOOT_ROLLABLE_ITEMS

    for item in carried_items:
        inventory_content.append(
            Div(
                Text(
                    item_label(item) + ": "
                    + str(state.inventory.get(item, 0))
                ),
                Button("-", drop_routes[item])
            )
        )

    inventory_content.append(
        Text(
            "Weight: " + displayed_inventory_weight(state)
            + " / " + str(state.capacity)
        )
    )

    # Weapons and tools can never be rolled as loot, so they are
    # not listed in the available loot column.
    for item in available_items:
        loot_content.append(
            Div(
                Text(
                    item_label(item) + ": "
                    + str(state.pending_loot.get(item, 0))
                ),
                Button("+", loot_routes[item])
            )
        )

    for item in carried_items:
        dropped_content.append(
            Div(
                Text(
                    item_label(item) + ": "
                    + str(state.dropped_items.get(item, 0))
                ),
                Button("+", dropped_routes[item])
            )
        )

    # After The King, Continue only works while carrying The Crown.
    continue_disabled = king_loot and state.inventory.get("crown", 0) < 1

    craft_buttons = []

    if crafting_tablet_available(state):
        craft_buttons.append(Button("Craft", "open_crafting_tablet"))

    content = event_log_content(state) + [
        Header("LOOT"),
        Text(
            "Use - to drop one carried item. Use + to collect loot "
            "or pick up a dropped item."
        ),
        Div(
            Div(*inventory_content, id="loot_inventory"),
            Div(*loot_content, id="loot_available"),
            Div(*dropped_content, id="loot_dropped"),
            id="loot_columns"
        ),
        Div(
            Button("Continue", "finish_loot", disabled=continue_disabled),
            *craft_buttons
        )
    ]

    return Page(
        state,
        content,
        css="""
        #loot_columns {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            align-items: start;
        }

        #loot_inventory, #loot_available, #loot_dropped {
            border: 1px solid #777;
            padding: 12px;
            border-radius: 6px;
            min-width: 0;
        }

        @media (max-width: 800px) {
            #loot_columns {
                grid-template-columns: 1fr;
            }
        }
        """
    )


@route
def loot_wood(state):
    take_loot_item(state, "wood")
    return loot_page(state)


@route
def loot_iron(state):
    take_loot_item(state, "iron")
    return loot_page(state)


@route
def loot_leather(state):
    take_loot_item(state, "leather")
    return loot_page(state)


@route
def loot_rations(state):
    take_loot_item(state, "rations")
    return loot_page(state)


@route
def loot_medicine(state):
    take_loot_item(state, "medicine")
    return loot_page(state)


@route
def loot_club(state):
    take_loot_item(state, "club")
    return loot_page(state)


@route
def loot_sword(state):
    take_loot_item(state, "iron sword")
    return loot_page(state)


@route
def loot_stake(state):
    take_loot_item(state, "stake")
    return loot_page(state)


@route
def drop_wood(state):
    drop_loot_item(state, "wood")
    return loot_page(state)


@route
def drop_iron(state):
    drop_loot_item(state, "iron")
    return loot_page(state)


@route
def drop_leather(state):
    drop_loot_item(state, "leather")
    return loot_page(state)


@route
def drop_rations(state):
    drop_loot_item(state, "rations")
    return loot_page(state)


@route
def drop_medicine(state):
    drop_loot_item(state, "medicine")
    return loot_page(state)


@route
def drop_club(state):
    drop_loot_item(state, "club")
    return loot_page(state)


@route
def drop_sword(state):
    drop_loot_item(state, "iron sword")
    return loot_page(state)


@route
def drop_stake(state):
    drop_loot_item(state, "stake")
    return loot_page(state)


@route
def dropped_wood(state):
    pick_up_dropped_item(state, "wood")
    return loot_page(state)


@route
def dropped_iron(state):
    pick_up_dropped_item(state, "iron")
    return loot_page(state)


@route
def dropped_leather(state):
    pick_up_dropped_item(state, "leather")
    return loot_page(state)


@route
def dropped_rations(state):
    pick_up_dropped_item(state, "rations")
    return loot_page(state)


@route
def dropped_medicine(state):
    pick_up_dropped_item(state, "medicine")
    return loot_page(state)


@route
def dropped_club(state):
    pick_up_dropped_item(state, "club")
    return loot_page(state)


@route
def dropped_sword(state):
    pick_up_dropped_item(state, "iron sword")
    return loot_page(state)


@route
def dropped_stake(state):
    pick_up_dropped_item(state, "stake")
    return loot_page(state)


@route
def loot_bow(state):
    take_loot_item(state, "bow")
    return loot_page(state)


@route
def loot_arrows(state):
    take_loot_item(state, "arrows")
    return loot_page(state)


@route
def loot_sinew(state):
    take_loot_item(state, "sinew")
    return loot_page(state)


@route
def drop_bow(state):
    drop_loot_item(state, "bow")
    return loot_page(state)


@route
def drop_arrows(state):
    drop_loot_item(state, "arrows")
    return loot_page(state)


@route
def drop_sinew(state):
    drop_loot_item(state, "sinew")
    return loot_page(state)


@route
def dropped_bow(state):
    pick_up_dropped_item(state, "bow")
    return loot_page(state)


@route
def dropped_arrows(state):
    pick_up_dropped_item(state, "arrows")
    return loot_page(state)


@route
def dropped_sinew(state):
    pick_up_dropped_item(state, "sinew")
    return loot_page(state)


@route
def drop_tablet(state):
    drop_loot_item(state, "crafting tablet")
    return loot_page(state)


@route
def dropped_tablet(state):
    pick_up_dropped_item(state, "crafting tablet")
    return loot_page(state)


@route
def loot_crown(state):
    take_loot_item(state, "crown")
    return loot_page(state)


@route
def drop_crown(state):
    drop_loot_item(state, "crown")
    return loot_page(state)


@route
def dropped_crown(state):
    pick_up_dropped_item(state, "crown")
    return loot_page(state)


@route
def drop_scaffolding(state):
    drop_loot_item(state, "scaffolding")
    return loot_page(state)


@route
def dropped_scaffolding(state):
    pick_up_dropped_item(state, "scaffolding")
    return loot_page(state)


loot_routes = {
    "wood": "loot_wood",
    "iron": "loot_iron",
    "leather": "loot_leather",
    "rations": "loot_rations",
    "medicine": "loot_medicine",
    "club": "loot_club",
    "iron sword": "loot_sword",
    "stake": "loot_stake",
    "crown": "loot_crown",
    "bow": "loot_bow",
    "arrows": "loot_arrows",
    "sinew": "loot_sinew"
}

drop_routes = {
    "wood": "drop_wood",
    "iron": "drop_iron",
    "leather": "drop_leather",
    "rations": "drop_rations",
    "medicine": "drop_medicine",
    "club": "drop_club",
    "iron sword": "drop_sword",
    "stake": "drop_stake",
    "bow": "drop_bow",
    "arrows": "drop_arrows",
    "sinew": "drop_sinew",
    "scaffolding": "drop_scaffolding",
    "crown": "drop_crown",
    "crafting tablet": "drop_tablet"
}

dropped_routes = {
    "wood": "dropped_wood",
    "iron": "dropped_iron",
    "leather": "dropped_leather",
    "rations": "dropped_rations",
    "medicine": "dropped_medicine",
    "club": "dropped_club",
    "iron sword": "dropped_sword",
    "stake": "dropped_stake",
    "bow": "dropped_bow",
    "arrows": "dropped_arrows",
    "sinew": "dropped_sinew",
    "scaffolding": "dropped_scaffolding",
    "crown": "dropped_crown",
    "crafting tablet": "dropped_tablet"
}

store_routes = {
    "wood": "store_wood",
    "iron": "store_iron",
    "leather": "store_leather",
    "rations": "store_rations",
    "medicine": "store_medicine",
    "club": "store_club",
    "iron sword": "store_sword",
    "stake": "store_stake",
    "bow": "store_bow",
    "arrows": "store_arrows",
    "sinew": "store_sinew",
    "scaffolding": "store_scaffolding",
    "crafting tablet": "store_tablet"
}

take_routes = {
    "wood": "take_wood",
    "iron": "take_iron",
    "leather": "take_leather",
    "rations": "take_rations",
    "medicine": "take_medicine",
    "club": "take_club",
    "iron sword": "take_sword",
    "stake": "take_stake",
    "bow": "take_bow",
    "arrows": "take_arrows",
    "sinew": "take_sinew",
    "scaffolding": "take_scaffolding",
    "crafting tablet": "take_tablet"
}


# ==========================================
# FINISH LOOT
# ==========================================

@route
def finish_loot(state):
    action = state.loot_return_action
    state.tablet_mode = False

    # The King's loot page can only be left while carrying The Crown.
    if action == "tower_king":
        if state.inventory.get("crown", 0) < 1:
            state.message = "You must carry The Crown to continue."
            return loot_page(state)

        state.pending_loot = {}
        state.dropped_items = {}
        state.loot_return_action = ""
        return win_page(state)

    state.pending_loot = {}
    state.dropped_items = {}
    state.loot_return_action = ""

    state.game_over = False
    state.victory = False
    state.in_encounter = False

    if action == "skeleton":
        state.message = "You leave the battlefield."
        add_log(state, state.message)
        return map_page(state)

    if action == "tower_level":
        if state.tower_level == 4:
            state.message = "You defeated the Necromancer. The King awaits."
        else:
            state.message = (
                "You cleared tower level "
                + str(state.tower_level) + ". "
                + NEXT_TOWER_ENEMY.get(state.tower_level, "The next enemy")
                + " awaits."
            )
        add_log(state, state.message)
        return tower_page(state)

    if action == "stronghold_first":
        state.stronghold_progress[str(state.current_location)] = "first_guard_done"
        state.location_stage = 0
        state.message = "The first guardian is defeated."
        add_log(state, state.message)
        return location_page(state)

    if action == "stronghold_second":
        state.stronghold_progress[str(state.current_location)] = "second_guard_done"
        state.location_stage = 0
        state.message = "The Stronghold Guardian is defeated."
        add_log(state, state.message)
        return location_page(state)

    if action == "stronghold_end":
        location = state.current_location

        if location not in state.completed_strongholds:
            state.completed_strongholds.append(location)

        if location not in state.searched_locations:
            state.searched_locations.append(location)

        build_road(state, location)

        state.location_stage = 0
        state.message = (
            "You defeated all three guardians! "
            "The stronghold is now a secured outpost."
        )

        add_log(state, state.message)
        return map_page(state)

    if action == "house_first":
        state.house_progress[str(state.current_location)] = "first_guard_done"
        state.location_stage = 0
        state.message = "The house guardian is defeated."
        add_log(state, state.message)
        return location_page(state)

    if action == "house_end":
        location = state.current_location

        if location not in state.completed_houses:
            state.completed_houses.append(location)

        if location not in state.searched_locations:
            state.searched_locations.append(location)

        state.location_stage = 0
        state.message = "You finished exploring the house. The location is now secured."
        add_log(state, state.message)
        return map_page(state)

    if action == "mine_first":
        state.mine_progress[str(state.current_location)] = "first_guard_done"
        state.location_stage = 0
        state.message = "The Iron Miner has been defeated."
        add_log(state, state.message)
        return location_page(state)

    if action == "mine_end":
        location = state.current_location

        if location not in state.completed_mines:
            state.completed_mines.append(location)

        state.iron_crafting_unlocked = True
        state.location_stage = 0
        state.message = "You cleared the iron mine!"
        add_log(state, state.message)
        return map_page(state)

    if action == "outpost":
        location = state.current_location

        if location not in state.claimed_outposts:
            state.claimed_outposts.append(location)

        state.message = "You collected supplies from the outpost."
        add_log(state, state.message)
        return map_page(state)

    return map_page(state)


# ==========================================
# COMBAT SETUP
# ==========================================

# Tower fights reuse the behaviour of these existing fights.
GUARDIAN_KINDS = ("stronghold_final", "tower_guardian", "flying_guardian")
MINER_KINDS = ("mine_buff", "tower_miner")
TOWER_LEVEL_KINDS = (
    "tower_skeleton", "tower_guardian", "tower_miner", "tower_necromancer"
)

# Shown after clearing a tower level (index = level just cleared).
NEXT_TOWER_ENEMY = {
    1: "The Buff Stronghold Guardian",
    2: "The Buff Iron Miner",
    3: "The Necromancer"
}

SPAWNED_SKELETON_HEALTH = 60
SPAWNED_SKELETON_DAMAGE = 15
NECROMANCER_SPAWN_INTERVAL = 4


def start_combat(state, enemy_name="Skeleton",
                 enemy_health=60, enemy_damage=5,
                 combat_kind="skeleton"):

    state.enemy_name = enemy_name
    state.enemy_health = enemy_health
    state.enemy_max_health = enemy_health
    state.enemy_damage = enemy_damage

    state.in_encounter = True
    state.game_over = False
    state.victory = False

    state.selected_attacks = []
    state.selected_healing = []
    state.turn_number = 0

    state.combat_kind = combat_kind
    state.screen = "battle"
    state.skeleton_queue = []

    state.message = enemy_name + " appears! Prepare for battle!"

    if combat_kind in GUARDIAN_KINDS:
        state.message += (
            "\nThe " + enemy_name + " deals " + str(enemy_damage)
            + " damage every turn, plus 3 more for each action you "
            "take—attacking or healing. Plan carefully."
        )

    elif combat_kind in MINER_KINDS:
        state.message += (
            "\nThe Buff Iron Miner has 200 health. Its 35-damage "
            "attack is unblockable and it attacks every other turn."
        )

    elif combat_kind == "tower_king":
        state.message += (
            "\nBeware the King's Armor! He takes 5 less damage "
            "from all sources."
        )

    elif combat_kind == "tower_necromancer":
        state.skeleton_queue = [
            SPAWNED_SKELETON_HEALTH, SPAWNED_SKELETON_HEALTH
        ]
        state.message += (
            "\nTwo Spawned Skeletons stand in front of The Necromancer."
        )

    elif combat_kind == "skeleton":
        state.skeleton_safe_steps = 5

    # The event log shows the newest line first, so the extra lines are
    # logged BEFORE the "appears" line. That way they read directly
    # underneath it on screen.
    intro_lines = split_message_lines(state.message)
    state.message = "\n".join(intro_lines[1:] + intro_lines[:1])

    add_log(state, state.message)


def attack_available(state, attack_name):
    if attack_name == "Punch":
        return True

    if attack_name == "Club":
        return state.inventory.get("club", 0) > 0

    if attack_name == "Iron Sword":
        return (
            state.inventory.get("iron sword", 0) > 0
            and state.turn_number % 2 == 0
        )

    if attack_name == "Bow":
        return state.inventory.get("bow", 0) > 0 and state.inventory.get("arrows", 0) > 0

    return False


def healing_available(state, item):
    return state.inventory.get(item, 0) > 0


# ==========================================
# LOCATION END LOOT
# ==========================================

def reach_location_end(state, location_type):
    state.pending_loot = roll_loot(8, True)
    state.dropped_items = {}

    if location_type == "stronghold":
        state.loot_return_action = "stronghold_end"
        state.message = (
            "You defeated the final stronghold guardian! "
            "Choose which supplies to carry."
        )

    elif location_type == "house":
        state.loot_return_action = "house_end"
        state.message = (
            "You have reached the end of the house! "
            "Choose which supplies to carry."
        )

    elif location_type == "mine":
        state.loot_return_action = "mine_end"
        state.message = "You cleared the iron mine! Choose which supplies to carry."

    state.in_encounter = False
    state.game_over = False
    state.victory = False

    add_log(state, state.message)
    return loot_page(state)


# ==========================================
# DEATH
# ==========================================

def player_dies(state):
    state.game_over = True
    state.victory = False
    state.in_encounter = False

    state.player_health = state.player_max_health
    state.inventory = {}

    state.player_x = START_X
    state.player_y = START_Y

    state.explored = list(state.permanent_explored)
    state.expedition_explored = []

    state.searched_locations = list(state.secured_locations)

    state.selected_attacks = []
    state.selected_healing = []

    state.pending_loot = {}
    state.dropped_items = {}
    state.loot_return_action = ""

    state.tower_active = False
    state.tower_level = 0

    state.screen = "camp"

    state.message = (
        "Your journey comes to an abrupt end. "
        "You awaken at the campsite, stripped of your carried items."
    )

    add_log(state, "You were defeated and returned to camp.")


# ==========================================
# DEALING DAMAGE TO ENEMIES
# ==========================================

def damage_necromancer_side(state, damage):
    # The player can only hit the first Spawned Skeleton. Damage beyond
    # what it has left carries over to the next skeleton, and after the
    # last skeleton, to The Necromancer himself.
    messages = []
    remaining = damage

    while remaining > 0:
        if state.skeleton_queue:
            front_health = state.skeleton_queue[0]

            if remaining >= front_health:
                state.skeleton_queue.pop(0)
                remaining -= front_health

                if remaining > 0:
                    if state.skeleton_queue:
                        messages.append(
                            str(remaining) + " overkill damage is applied "
                            "to the next skeleton."
                        )
                    else:
                        messages.append(
                            str(remaining) + " overkill damage is applied "
                            "to The Necromancer."
                        )
            else:
                state.skeleton_queue[0] = front_health - remaining
                remaining = 0
        else:
            state.enemy_health -= remaining
            remaining = 0

    return messages


def deal_damage_to_enemy(state, raw_damage):
    # Returns (damage dealt, extra messages).
    if state.combat_kind == "tower_king":
        # The King takes 5 less damage from every attack.
        dealt = max(1, raw_damage - 5)
        state.enemy_health -= dealt
        return dealt, []

    if state.combat_kind == "tower_necromancer":
        return raw_damage, damage_necromancer_side(state, raw_damage)

    state.enemy_health -= raw_damage
    return raw_damage, []


# ==========================================
# ENEMY TURN
# ==========================================

def necromancer_turn(state):
    # Every Spawned Skeleton in front of The Necromancer attacks.
    # The Necromancer himself does no damage.
    lines = []
    hits = 0
    evaded = 0

    for _ in state.skeleton_queue:
        if player_evades_attack(state):
            evaded += 1
        else:
            hits += 1

    if hits > 0:
        damage = hits * SPAWNED_SKELETON_DAMAGE
        state.player_health -= damage

        if hits == 1:
            lines.append(
                "1 Spawned Skeleton attacks for " + str(damage) + " damage!"
            )
        else:
            lines.append(
                str(hits) + " Spawned Skeletons attack for "
                + str(damage) + " damage!"
            )

    if evaded > 0:
        if evaded == 1:
            lines.append("You evaded 1 attack!")
        else:
            lines.append("You evaded " + str(evaded) + " attacks!")

    # Every 4th turn, two more Spawned Skeletons appear.
    if (state.turn_number + 1) % NECROMANCER_SPAWN_INTERVAL == 0:
        state.skeleton_queue.append(SPAWNED_SKELETON_HEALTH)
        state.skeleton_queue.append(SPAWNED_SKELETON_HEALTH)
        lines.append("The Necromancer summons two more Spawned Skeletons!")

    return "\n".join(lines)


def enemy_turn(state):
    if state.game_over:
        return

    if state.combat_kind == "tower_necromancer":
        message = necromancer_turn(state)

    elif state.combat_kind in MINER_KINDS:
        # The first attack occurs after the first player turn.
        # It then attacks every other turn.
        if state.turn_number % 2 == 0:
            state.player_health -= 35
            message = (
                "The Buff Iron Miner lands its unblockable "
                "35-damage attack!"
            )
        else:
            message = "The Buff Iron Miner is preparing its next attack."

    else:
        if player_evades_attack(state):
            message = "You evaded the attack!"

            if state.shield:
                message += " Your shield helped protect you."
        else:
            state.player_health -= state.enemy_damage

            if state.player_health < 0:
                state.player_health = 0

            message = (
                state.enemy_name + " attacks for "
                + str(state.enemy_damage) + " damage!"
            )

    if state.player_health < 0:
        state.player_health = 0

    state.message += "\n" + message
    add_log(state, message)

    if state.player_health <= 0:
        player_dies(state)


# ==========================================
# COMBAT: SELECT ATTACKS
# ==========================================

def toggle_attack(state, attack_name):
    if not attack_available(state, attack_name):
        state.message = attack_name + " is not available."
        return battle_page(state)

    if attack_name in state.selected_attacks:
        state.selected_attacks.remove(attack_name)
    else:
        state.selected_attacks.append(attack_name)

    return battle_page(state)


@route
def select_punch(state):
    return toggle_attack(state, "Punch")


@route
def select_club(state):
    return toggle_attack(state, "Club")


@route
def select_sword(state):
    return toggle_attack(state, "Iron Sword")


@route
def select_bow(state):
    return toggle_attack(state, "Bow")


@route
def use_stake(state):
    if not state.in_encounter or state.enemy_health <= 0:
        state.message = "There is no enemy to attack."
        return battle_page(state)

    if not remove_item(state, "stake", 1):
        state.message = "You do not have a Stake."
        return battle_page(state)

    # Stakes always deal 5 raw damage; Protein Shake does not affect them.
    raw_damage = 5
    damage, extra_messages = deal_damage_to_enemy(state, raw_damage)
    state.enemy_health = max(0, state.enemy_health)

    state.message = "Stake dealt " + str(damage) + " damage. It did not use your turn."

    for extra in extra_messages:
        state.message += "\n" + extra

    add_log(state, state.message)

    if state.enemy_health <= 0:
        result = complete_combat_victory(state, [state.message])
        if result is not None:
            return result
        return loot_page(state)

    return battle_page(state)


# ==========================================
# COMBAT: SELECT HEALING
# ==========================================

def toggle_healing(state, item):
    if not healing_available(state, item):
        state.message = "You do not have any " + item + "."
        return battle_page(state)

    if item in state.selected_healing:
        state.selected_healing.remove(item)
    else:
        state.selected_healing.append(item)

    return battle_page(state)


@route
def select_ration(state):
    return toggle_healing(state, "rations")


@route
def select_medicine(state):
    return toggle_healing(state, "medicine")


# ==========================================
# COMBAT: END TURN
# ==========================================

def complete_combat_victory(state, turn_messages):
    if state.enemy_health <= 0:
        state.game_over = True
        state.victory = True
        state.in_encounter = False

        turn_messages.append("You defeated the " + state.enemy_name + "!")
        combat_kind = state.combat_kind

        if combat_kind == "skeleton":
            state.pending_loot = roll_loot(3)
            state.loot_return_action = "skeleton"

        elif combat_kind in TOWER_LEVEL_KINDS:
            # Tower levels give 5 rolls, with wood and iron rerolled.
            # (Spawned Skeletons never drop anything.)
            state.pending_loot = roll_tower_loot(5)
            state.loot_return_action = "tower_level"

        elif combat_kind == "tower_king":
            # The only reward for defeating The King is The Crown.
            state.pending_loot = {"crown": 1}
            state.loot_return_action = "tower_king"

        elif combat_kind == "stronghold_first":
            state.pending_loot = roll_loot(6)
            state.loot_return_action = "stronghold_first"

        elif combat_kind == "stronghold_second":
            state.pending_loot = roll_loot(6)
            state.loot_return_action = "stronghold_second"

        elif combat_kind in GUARDIAN_KINDS:
            for message in turn_messages:
                add_log(state, message)

            state.selected_attacks = []
            state.selected_healing = []
            return reach_location_end(state, "stronghold")

        elif combat_kind == "house_first":
            state.pending_loot = roll_loot(6)
            state.loot_return_action = "house_first"

        elif combat_kind == "mine_first":
            state.pending_loot = roll_loot(6)
            state.loot_return_action = "mine_first"

        elif combat_kind == "house_buff":
            for message in turn_messages:
                add_log(state, message)

            state.selected_attacks = []
            state.selected_healing = []
            return reach_location_end(state, "house")

        elif combat_kind in MINER_KINDS:
            for message in turn_messages:
                add_log(state, message)

            state.selected_attacks = []
            state.selected_healing = []
            return reach_location_end(state, "mine")

        else:
            state.pending_loot = roll_loot(3)
            state.loot_return_action = "skeleton"

        state.dropped_items = {}
        state.message = "\n".join(turn_messages)

        for message in turn_messages:
            add_log(state, message)

        state.selected_attacks = []
        state.selected_healing = []
        state.screen = "loot"
        return



@route
def resolve_turn(state):
    if state.game_over:
        return

    turn_messages = []
    actions_taken = 0

    if "rations" in state.selected_healing:
        if remove_item(state, "rations", 1):
            heal_player(state, 10)
            actions_taken += 1
            turn_messages.append("Ration restored 10 health.")

    if "medicine" in state.selected_healing:
        if remove_item(state, "medicine", 1):
            heal_player(state, 50)
            actions_taken += 1
            turn_messages.append("Medicine restored 50 health.")

    state.player_health = min(state.player_health, state.player_max_health)

    attacks = list(state.selected_attacks)

    for attack_name in attacks:
        if state.enemy_health <= 0:
            break

        # Protein Shake boosts weapons, not Punch.
        bonus = 5 if state.protein_shake else 0

        if attack_name == "Punch":
            damage, extra_messages = deal_damage_to_enemy(state, 15)
            state.player_health -= 5
            actions_taken += 1
            turn_messages.append(
                "Punch dealt " + str(damage)
                + " damage. You took 5 self-damage."
            )
            turn_messages.extend(extra_messages)

        elif attack_name == "Club":
            if attack_available(state, "Club"):
                damage, extra_messages = deal_damage_to_enemy(state, 10 + bonus)
                actions_taken += 1
                turn_messages.append("Club dealt " + str(damage) + " damage.")
                turn_messages.extend(extra_messages)

        elif attack_name == "Iron Sword":
            if attack_available(state, "Iron Sword"):
                damage, extra_messages = deal_damage_to_enemy(state, 25 + bonus)
                actions_taken += 1
                turn_messages.append(
                    "Iron Sword dealt " + str(damage) + " damage."
                )
                turn_messages.extend(extra_messages)

        elif attack_name == "Bow":
            # Bow shots bypass blocking. A single arrow is spent only
            # when the bow actually fires.
            if attack_available(state, "Bow") and remove_item(state, "arrows", 1):
                raw_bow_damage = 10 + bonus
                if state.enemy_name == "Flying Guardian":
                    raw_bow_damage += 10
                damage, extra_messages = deal_damage_to_enemy(state, raw_bow_damage)
                actions_taken += 1
                turn_messages.append("Bow dealt " + str(damage) + " damage. 1 arrow used.")
                turn_messages.extend(extra_messages)

        if state.player_health <= 0:
            state.player_health = 0
            break

    if state.enemy_health < 0:
        state.enemy_health = 0

    if (
        state.combat_kind in GUARDIAN_KINDS
        and state.enemy_health > 0
        and state.player_health > 0
    ):
        # The configured base damage is 6 for the first stronghold/tower
        # and 12 for the second stronghold, plus 3 per player action.
        damage = state.enemy_damage + actions_taken * 3

        if player_evades_attack(state):
            evade_message = "You evaded the Buff Stronghold Guardian's attack!"

            if state.shield:
                evade_message += " Your shield helped protect you."

            turn_messages.append(evade_message)
        else:
            state.player_health -= damage

            turn_messages.append(
                "The Buff Stronghold Guardian dealt "
                + str(damage)
                + " damage (" + str(state.enemy_damage)
                + " base + 3 for each of your "
                + str(actions_taken)
                + " action(s))!"
            )

        if state.player_health < 0:
            state.player_health = 0

    if state.player_health <= 0:
        state.message = "\n".join(turn_messages)

        for message in turn_messages:
            add_log(state, message)

        player_dies(state)
        return

    if state.enemy_health <= 0:
        return complete_combat_victory(state, turn_messages)

    if not turn_messages:
        turn_messages.append("You chose not to use any items or attacks.")

    state.message = "\n".join(turn_messages)

    for message in turn_messages:
        add_log(state, message)

    if state.combat_kind not in GUARDIAN_KINDS:
        enemy_turn(state)

    state.turn_number += 1
    state.selected_attacks = []
    state.selected_healing = []


@route
def end_turn(state):
    resolve_turn(state)

    if state.screen == "win":
        return win_page(state)

    if state.screen == "loot":
        return loot_page(state)

    if state.screen == "camp":
        return camp_page(state)

    return battle_page(state)


# ==========================================
# COMBAT PAGE
# ==========================================

@route
def battle_page(state):
    if state.screen == "loot":
        return loot_page(state)

    if not state.in_encounter and not state.game_over:
        return camp_page(state)

    state.screen = "battle"

    content = event_log_content(state) + [
        Header("THE DUNGEON"),

        Header("Player"),
        Text(
            "Health: " + str(state.player_health)
            + " / " + str(state.player_max_health)
        ),
        Text(health_bar(state.player_health, state.player_max_health)),

        Header(state.enemy_name),
        Text(
            "Health: " + str(state.enemy_health)
            + " / " + str(state.enemy_max_health)
        ),
        Text(health_bar(state.enemy_health, state.enemy_max_health)),
    ]

    if state.combat_kind == "tower_necromancer":
        content.append(Header("Spawned Skeletons"))

        if state.skeleton_queue:
            content.append(
                Text(
                    "Spawned Skeletons in front of The Necromancer: "
                    + str(len(state.skeleton_queue))
                )
            )
            content.append(
                Text(
                    "Front Spawned Skeleton health: "
                    + str(state.skeleton_queue[0]) + " / "
                    + str(SPAWNED_SKELETON_HEALTH)
                )
            )
            content.append(
                Text(
                    health_bar(
                        state.skeleton_queue[0], SPAWNED_SKELETON_HEALTH
                    )
                )
            )
        else:
            content.append(Text("No Spawned Skeletons are left."))

    content += [
        Header("Healing Items"),
        Text("Rations: " + str(state.inventory.get("rations", 0))),
        Text("Medicine: " + str(state.inventory.get("medicine", 0)))
    ]

    if state.inventory.get("bow", 0) > 0:
        content.append(Text("Arrows: " + str(state.inventory.get("arrows", 0))))

    ration_label = (
        "✓ Ration selected"
        if "rations" in state.selected_healing
        else "Ration (+10 HP)"
    )

    medicine_label = (
        "✓ Medicine selected"
        if "medicine" in state.selected_healing
        else "Medicine (+50 HP)"
    )

    content.append(
        Button(
            ration_label,
            "select_ration",
            disabled=not healing_available(state, "rations")
        )
    )

    content.append(
        Button(
            medicine_label,
            "select_medicine",
            disabled=not healing_available(state, "medicine")
        )
    )

    content.append(Header("Attacks"))

    punch_label = (
        "✓ Punch selected"
        if "Punch" in state.selected_attacks
        else "Punch (15 damage, 5 self-damage)"
    )

    content.append(Div(Button(punch_label, "select_punch")))

    if attack_available(state, "Club"):
        club_label = (
            "✓ Club selected"
            if "Club" in state.selected_attacks
            else "Club (10 damage)"
        )
        content.append(Div(Button(club_label, "select_club")))

    if state.inventory.get("iron sword", 0) > 0:
        if attack_available(state, "Iron Sword"):
            sword_label = (
                "✓ Iron Sword selected"
                if "Iron Sword" in state.selected_attacks
                else "Iron Sword (25 damage)"
            )
            content.append(Div(Button(sword_label, "select_sword")))
        else:
            content.append(Div(Text("Iron Sword is resting this turn.")))

    if state.inventory.get("stake", 0) > 0:
        content.append(
            Div(
                Button(
                    "Use Stake (5 damage, does not use turn) - "
                    + str(state.inventory.get("stake", 0)) + " available",
                    "use_stake"
                )
            )
        )

    if state.inventory.get("bow", 0) > 0 and state.inventory.get("arrows", 0) > 0:
        bow_label = (
            "✓ Bow selected"
            if "Bow" in state.selected_attacks
            else "Bow (10 damage, uses 1 arrow)"
        )
        content.append(Div(Button(bow_label, "select_bow")))

    if state.protein_shake:
        content.append(Text("Protein Shake active: +5 damage to all weapons."))

    content.extend([
        Header("End of Turn"),
        Button("End of Turn", "end_turn")
    ])

    return Page(state, content)


# ==========================================
# TERRAIN AND LOCATIONS
# ==========================================

def create_terrain():
    rng = random.Random(42)
    terrain = []

    symbols = [".", ",", ",", ",", "."]

    for y in range(MAP_SIZE):
        row = ""

        for x in range(MAP_SIZE):
            row += rng.choice(symbols)

        terrain.append(list(row))

    patches = [
        (5, 7, "~"),
        (19, 5, "/"),
        (38, 12, "/"),
        (9, 29, "^"),
        (29, 35, ";"),
        (46, 45, "~"),
        (4, 48, "/")
    ]

    for start_x, start_y, symbol in patches:
        for y in range(start_y, min(start_y + 6, MAP_SIZE)):
            for x in range(start_x, min(start_x + 6, MAP_SIZE)):
                terrain[y][x] = symbol

    return ["".join(row) for row in terrain]


def create_locations():
    houses = [
        (24, 22),
        (36, 23),
        (22, 37),
        (38, 36),
        (25, 30),
        (35, 30),
        # Additional houses. Each is more than 3 map steps from every
        # existing house, stronghold, mine, and the tower.
        (8, 30),
        (30, 8),
        (50, 10),
        (10, 50),
        (50, 50),
        (5, 5),
        (55, 30),
        (30, 55),
        (45, 5),
        (5, 45)
    ]

    strongholds = [
        (18, 18),
        (40, 38)
    ]

    iron_mines = [(13, 13)]

    return houses, strongholds, iron_mines


def find_closest_stronghold(state):
    if not state.strongholds:
        return None

    return state.strongholds[0]


def tower_unlocked(state):
    return (
        len(state.strongholds) >= 2
        and state.strongholds[0] in state.completed_strongholds
        and state.strongholds[1] in state.completed_strongholds
    )


# ==========================================
# MAP REVEAL
# ==========================================

def reveal_area(state):
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            if abs(dx) == 3 and abs(dy) == 3:
                continue

            x = state.player_x + dx
            y = state.player_y + dy

            if 0 <= x < MAP_SIZE and 0 <= y < MAP_SIZE:
                if (x, y) not in state.explored:
                    state.explored.append((x, y))


def map_symbol(state, x, y):
    location = (x, y)

    if location == (state.player_x, state.player_y):
        return "@"

    if location == (START_X, START_Y):
        return "C"

    first_stronghold = find_closest_stronghold(state)
    first_stronghold_done = (
        first_stronghold in state.completed_strongholds
    )

    # The first stronghold is always visible until conquered. Once
    # completed, it becomes the outpost marker, including after death.
    if location == first_stronghold:
        return "O" if first_stronghold_done else "S"

    # Later structures appear only after their prerequisite is met.
    # Their visibility is based on permanent progression, not whether
    # they happened to be inside the current expedition's explored area.
    if location in state.strongholds:
        if not first_stronghold_done:
            return " "
        if location in state.completed_strongholds:
            return "O"
        return "S"

    if location in state.iron_mines:
        if not first_stronghold_done:
            return " "
        if location in state.completed_mines:
            return "i"
        return "I"

    # The tower remains hidden until both strongholds are completed.
    if location == state.tower_location:
        return "T" if tower_unlocked(state) else " "

    if location in state.roads:
        return "#"

    # Completed houses remain marked; undiscovered houses are hidden
    # until the player explores their surrounding map area.
    if location in state.completed_houses or location in state.searched_locations:
        return "h"

    if location in state.houses:
        return "H" if location in state.explored else " "

    if location not in state.explored:
        return " "

    return state.terrain[y][x]



# ==========================================
# MAP PAGE
# ==========================================

@route
def map_page(state):
    state.screen = "map"
    reveal_area(state)

    board = []

    for y in range(MAP_SIZE):
        row = ""

        for x in range(MAP_SIZE):
            row += map_symbol(state, x, y)

        board.append(row)

    content = event_log_content(state) + [
        Header("DUNGEON EXPLORATION"),
        Text("Use the arrow keys to move."),
        Text(
            "@ = You | C = Camp | S = Stronghold | "
            "O = Outpost"
        ),
        Text("H = House | I = Iron Mine"),
        Text("T = The Tower | # = Road"),
        Text("Rations: " + str(state.inventory.get("rations", 0))),
        Text(
            "Capacity: " + displayed_inventory_weight(state)
            + " / " + str(state.capacity)
        ),
        PreformattedText(
            "\n".join(board),
            id="dungeon_map_active"
        ),
        Button("UP", "move_up", id="move_up_button", hidden=True),
        Button("DOWN", "move_down", id="move_down_button", hidden=True),
        Button("LEFT", "move_left", id="move_left_button", hidden=True),
        Button("RIGHT", "move_right", id="move_right_button", hidden=True)
    ]

    return Page(
        state,
        content,
        css="""
        #dungeon_map_active {
            font-family: monospace;
            font-size: 8px;
            line-height: 8px;
            letter-spacing: 0px;
            white-space: pre;
        }
        """,
        js="""
        document.onkeydown = function(event) {
            if (!document.getElementById("dungeon_map_active")) {
                return;
            }

            const buttons = {
                "ArrowUp": "move_up_button",
                "ArrowDown": "move_down_button",
                "ArrowLeft": "move_left_button",
                "ArrowRight": "move_right_button"
            };

            const buttonId = buttons[event.key];

            if (buttonId) {
                event.preventDefault();
                const button = document.getElementById(buttonId);

                if (button) {
                    button.click();
                }
            }
        };
        """
    )


# ==========================================
# MOVEMENT
# ==========================================

def terrain_description(state):
    symbol = state.terrain[state.player_y][state.player_x]

    descriptions = {
        ".": "You walk across open dirt.",
        ",": "Grass moves gently around your feet.",
        ";": "Thick brush surrounds you.",
        "/": "Trees surround you in a quiet forest.",
        "^": "Rocky ground stretches beneath your feet.",
        "~": "Water stretches out before you."
    }

    return descriptions.get(symbol, "You continue exploring.")


def move_player_in_direction(state, direction):
    old_x = state.player_x
    old_y = state.player_y

    if direction == "up" and state.player_y > 0:
        state.player_y -= 1
    elif direction == "down" and state.player_y < MAP_SIZE - 1:
        state.player_y += 1
    elif direction == "left" and state.player_x > 0:
        state.player_x -= 1
    elif direction == "right" and state.player_x < MAP_SIZE - 1:
        state.player_x += 1

    moved = old_x != state.player_x or old_y != state.player_y

    if not moved:
        return map_page(state)

    state.movement_steps += 1

    safe_this_step = state.skeleton_safe_steps > 0

    if safe_this_step:
        state.skeleton_safe_steps -= 1

    if state.movement_steps % 3 == 0:
        if state.inventory.get("rations", 0) > 0:
            remove_item(state, "rations", 1)
            add_log(state, "You consumed one ration.")

            if state.inventory.get("rations", 0) == 3:
                add_log(state, "Rations limited.")
        else:
            add_log(state, "Starvation sets in.")
            player_dies(state)
            return camp_page(state)

    reveal_area(state)

    if (state.player_x, state.player_y) == (START_X, START_Y):
        return return_to_camp(state)

    description = terrain_description(state)

    if state.movement_steps % 2 == 0:
        state.message = description
        add_log(state, description)
    else:
        state.message = ""

    location = (state.player_x, state.player_y)

    # The Tower exists even while it is hidden on the map.
    tower_accessible = location == state.tower_location

    # A house that has been completed can never be entered again.
    enterable_house = (
        location in state.houses
        and location not in state.completed_houses
    )

    if (
        enterable_house
        or location in state.strongholds
        or location in state.iron_mines
        or tower_accessible
    ):
        state.current_location = location
        return location_page(state)

    if location not in state.roads and not safe_this_step:
        if random.randint(1, 100) <= 8:
            start_combat(state)
            return battle_page(state)

    return map_page(state)


@route
def move_up(state):
    return move_player_in_direction(state, "up")


@route
def move_down(state):
    return move_player_in_direction(state, "down")


@route
def move_left(state):
    return move_player_in_direction(state, "left")


@route
def move_right(state):
    return move_player_in_direction(state, "right")


# ==========================================
# LOCATION PAGE
# ==========================================

@route
def location_page(state):
    location = state.current_location

    if location == state.tower_location:
        content = event_log_content(state) + [
            Header("THE TOWER"),
            Div(
                Text(
                    "The Tower has five levels. An enemy waits on "
                    "each one."
                )
            ),
            Div(Text("Climbing each level costs 1 scaffolding.")),
            Div(
                Text(
                    "Scaffolding in inventory: "
                    + str(state.inventory.get("scaffolding", 0))
                )
            ),
            Button(
                "Climb to Level 1 (1 Scaffolding)",
                "enter_tower",
                disabled=state.inventory.get("scaffolding", 0) < 1
            ),
            Button("Leave", "leave_location")
        ]

        return Page(state, content)

    if location in state.strongholds:
        if location in state.completed_strongholds:
            content = event_log_content(state) + [
                Header("OUTPOST"),
                Text("You have reached a secured outpost.")
            ]

            if location in state.claimed_outposts:
                content.append(Text("You have already collected supplies here."))
            else:
                content.append(Text("There are rations available at this outpost."))
                content.append(Button("Collect Outpost Rations", "collect_outpost"))

            content.append(Button("Leave", "leave_location"))
            return Page(state, content)

        key = str(location)
        progress = state.stronghold_progress.get(key, "")

        content = event_log_content(state) + [
            Header("STRONGHOLD"),
            Text("You have reached a stronghold.")
        ]

        if progress == "first_guard_done":
            content.append(Text("The first guardian has been defeated."))
            content.append(Button("Explore Further", "explore_further"))
        elif progress == "second_guard_done":
            content.append(Text("The Stronghold Guardian has been defeated."))
            content.append(Button("Explore Further", "explore_further"))
        else:
            content.append(Text("A guardian stands in your way."))
            content.append(Button("Explore", "explore_location"))

        content.append(Button("Leave", "leave_location"))
        return Page(state, content)

    if location in state.iron_mines:
        if location in state.completed_mines:
            return Page(
                state,
                event_log_content(state) + [
                    Header("IRON MINE"),
                    Text("This iron mine has already been cleared."),
                    Button("Leave", "leave_location")
                ]
            )

        key = str(location)
        progress = state.mine_progress.get(key, "")

        content = event_log_content(state) + [
            Header("IRON MINE"),
            Text("You have discovered an iron mine.")
        ]

        if progress == "first_guard_done":
            content.append(Text("The Iron Miner has been defeated."))
            content.append(Button("Explore Further", "explore_mine_further"))
        else:
            content.append(Text("An Iron Miner is guarding the mine."))
            content.append(Button("Explore", "explore_location"))

        content.append(Button("Leave", "leave_location"))
        return Page(state, content)

    if location in state.houses:
        if location in state.completed_houses:
            return Page(
                state,
                event_log_content(state) + [
                    Header("HOUSE"),
                    Text("You have already cleared this house."),
                    Button("Leave", "leave_location")
                ]
            )

        key = str(location)
        progress = state.house_progress.get(key, "")

        content = event_log_content(state) + [
            Header("HOUSE"),
            Text("You have reached a house.")
        ]

        if progress == "first_guard_done":
            content.append(Text("The first house guardian is defeated."))
            content.append(Button("Explore Further", "explore_house_further"))
        else:
            content.append(Text("A guardian stands inside the house."))
            content.append(Button("Explore", "explore_location"))

        content.append(Button("Leave", "leave_location"))
        return Page(state, content)

    return map_page(state)


@route
def leave_location(state):
    state.message = "You leave the location behind."
    add_log(state, state.message)
    return map_page(state)


# ==========================================
# THE TOWER
# ==========================================

def start_tower_level(state):
    level = state.tower_level

    # start_combat logs its own "appears" lines, so the level line is
    # logged first and nothing is logged twice.
    add_log(state, "Tower level " + str(level) + " of 5.")

    if level == 1:
        start_combat(state, "Tower Skeleton", 60, 5, "tower_skeleton")
    elif level == 2:
        start_combat(state, "Flying Guardian", 200, 6, "tower_guardian")
    elif level == 3:
        start_combat(state, "Buff Iron Miner", 200, 35, "tower_miner")
    elif level == 4:
        start_combat(state, "The Necromancer", 300, 0, "tower_necromancer")
    else:
        start_combat(state, "The King", 250, 55, "tower_king")

    return battle_page(state)


@route
def enter_tower(state):
    if state.inventory.get("scaffolding", 0) < 1:
        state.message = (
            "You need 1 scaffolding in your inventory to climb "
            "to level 1."
        )
        return location_page(state)

    remove_item(state, "scaffolding", 1)

    state.tower_level = 1
    state.tower_active = True

    message = "You use 1 scaffolding to climb to level 1 of The Tower."

    state.message = message
    add_log(state, message)

    return start_tower_level(state)


@route
def tower_next_level(state):
    if not state.tower_active:
        state.message = "You are not currently inside The Tower."
        return map_page(state)

    if state.tower_level >= 5:
        state.message = "You have already reached the final level."
        return tower_page(state)

    if state.inventory.get("scaffolding", 0) < 1:
        state.message = (
            "You need 1 scaffolding in your inventory to climb higher."
        )
        return tower_page(state)

    remove_item(state, "scaffolding", 1)
    state.tower_level += 1

    state.message = (
        "You use 1 scaffolding to climb to level "
        + str(state.tower_level) + "."
    )
    add_log(state, state.message)

    return start_tower_level(state)


@route
def tower_retreat(state):
    state.tower_active = False
    state.tower_level = 0

    state.message = "You retreat from The Tower. Its levels have been reset."
    add_log(state, state.message)

    return map_page(state)


@route
def tower_page(state):
    state.screen = "tower"

    scaffolding = state.inventory.get("scaffolding", 0)

    content = event_log_content(state) + [
        Header("THE TOWER"),
        Div(Text("You are on level " + str(state.tower_level) + " of 5.")),
        Div(Text("Scaffolding in inventory: " + str(scaffolding))),
        Button(
            "Continue to Level " + str(state.tower_level + 1)
            + " (1 Scaffolding)",
            "tower_next_level",
            disabled=scaffolding < 1
        ),
        Button("Retreat", "tower_retreat")
    ]

    return Page(state, content)


# ==========================================
# PLAY AGAIN
# ==========================================

@route
def play_again(state):
    # Everything resets: inventory, storage, upgrades, map progress,
    # completed locations, statistics and the timer.
    fresh_state = make_initial_state()

    for field in fields(State):
        setattr(state, field.name, getattr(fresh_state, field.name))

    return index(state)


# ==========================================
# WINNING SCREEN
# ==========================================

def format_duration(total_seconds):
    total = int(total_seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60

    if hours > 0:
        return str(hours) + "h " + str(minutes) + "m " + str(seconds) + "s"

    return str(minutes) + "m " + str(seconds) + "s"


@route
def win_page(state):
    state.screen = "win"
    state.in_encounter = False
    state.message = ""

    state.tower_active = False
    state.tower_level = 0

    # The clock stops the first time the winning screen is shown.
    if state.game_end_time == 0:
        state.game_end_time = time.time()

    elapsed = 0

    if state.game_start_time > 0:
        elapsed = state.game_end_time - state.game_start_time

    if state.total_collected is None:
        state.total_collected = {}

    content = [
        # Text is inline in Drafter, so the "new line" between these two
        # sentences is made by putting each one in its own Div.
        Div(Header("Congrats!")),
        Div(Text("You have won!")),

        Header("Materials Gathered"),
    ]

    for item in LOOT_ROLLABLE_ITEMS:
        content.append(
            Div(
                Text(
                    item.title() + ": "
                    + str(state.total_collected.get(item, 0))
                )
            )
        )

    content.extend([
        Header("Healing"),
        Div(Text("Total health restored: " + str(state.total_healing))),

        Header("Time"),
        Div(Text("Time to complete: " + format_duration(elapsed))),

        Button("Play Again", "play_again")
    ])

    return Page(state, content)


# ==========================================
# EXPLORE A LOCATION
# ==========================================

@route
def explore_location(state):
    location = state.current_location

    if location in state.strongholds:
        key = str(location)
        progress = state.stronghold_progress.get(key, "")

        if progress != "":
            state.message = "You have already defeated the first guardian."
            return location_page(state)

        if len(state.strongholds) > 1 and location == state.strongholds[1]:
            start_combat(state, "Guardian", 160, 15, "stronghold_first")
        else:
            start_combat(state, "Guardian", 60, 10, "stronghold_first")
        state.location_stage = 1
        return battle_page(state)

    if location in state.iron_mines:
        key = str(location)

        if state.mine_progress.get(key, "") == "first_guard_done":
            state.message = "You have already defeated the Iron Miner."
            return location_page(state)

        start_combat(state, "Iron Miner", 120, 15, "mine_first")
        state.location_stage = 1
        return battle_page(state)

    if location in state.houses:
        key = str(location)

        if state.house_progress.get(key, "") == "first_guard_done":
            state.message = "You have already defeated the first guardian."
            return location_page(state)

        start_combat(state, "House Guardian", 60, 10, "house_first")
        state.location_stage = 1
        return battle_page(state)

    return map_page(state)


# ==========================================
# EXPLORE FURTHER: STRONGHOLD
# ==========================================

@route
def explore_further(state):
    key = str(state.current_location)
    progress = state.stronghold_progress.get(key, "")

    second_stronghold = (
        len(state.strongholds) > 1
        and state.current_location == state.strongholds[1]
    )

    if progress == "first_guard_done":
        if second_stronghold:
            start_combat(state, "Stronghold Guardian", 220, 20, "stronghold_second")
        else:
            start_combat(state, "Stronghold Guardian", 120, 15, "stronghold_second")
        return battle_page(state)

    if progress == "second_guard_done":
        if second_stronghold:
            start_combat(state, "Flying Guardian", 300, 12, "flying_guardian")
        else:
            start_combat(state, "Flying Guardian", 200, 6, "flying_guardian")
        return battle_page(state)

    state.message = "You must defeat the guardian first."
    return location_page(state)


# ==========================================
# EXPLORE FURTHER: HOUSE
# ==========================================

@route
def explore_house_further(state):
    chance = random.randint(1, 2)

    if chance == 1:
        state.message = "You found the end of the house!"
        add_log(state, state.message)
        return reach_location_end(state, "house")

    start_combat(
        state,
        "Stronger House Guardian",
        120,
        15,
        "house_buff"
    )

    return battle_page(state)


# ==========================================
# EXPLORE FURTHER: IRON MINE
# ==========================================

@route
def explore_mine_further(state):
    chance = random.randint(1, 2)

    if chance == 1:
        state.message = "You found the end of the iron mine!"
        add_log(state, state.message)
        return reach_location_end(state, "mine")

    start_combat(
        state,
        "Buff Iron Miner",
        200,
        35,
        "mine_buff"
    )

    return battle_page(state)


# ==========================================
# OUTPOST
# ==========================================

@route
def collect_outpost(state):
    location = state.current_location

    if location in state.claimed_outposts:
        state.message = "You have already collected these supplies."
        return location_page(state)

    amount = random.randint(3, 8)

    state.pending_loot = {"rations": amount}
    state.dropped_items = {}
    state.loot_return_action = "outpost"
    state.screen = "loot"

    state.message = (
        "The outpost has rations available. "
        "Choose how many you want to carry."
    )

    add_log(state, state.message)
    return loot_page(state)


# ==========================================
# RETURN TO MAP AFTER COMBAT
# ==========================================

@route
def return_to_map(state):
    state.in_encounter = False
    state.game_over = False
    state.victory = False

    state.message = "You continue exploring the dungeon."
    add_log(state, state.message)

    return map_page(state)


# ==========================================
# STRONGHOLD ROAD
# ==========================================

def build_road(state, location):
    x, y = location

    for road_x in range(min(x, START_X), max(x, START_X) + 1):
        point = (road_x, y)

        if point not in state.roads:
            state.roads.append(point)

    for road_y in range(min(y, START_Y), max(y, START_Y) + 1):
        point = (START_X, road_y)

        if point not in state.roads:
            state.roads.append(point)


# ==========================================
# CAMP PAGE
# ==========================================

@route
def camp_page(state):
    state.screen = "camp"
    state.tablet_mode = False

    content = event_log_content(state) + [
        Header("THE CAMPSITE"),
        Text("You are safe here."),
        Button(
            "Rest (Medicine) - Full Heal",
            "rest_at_camp",
            disabled=(
                state.player_health >= state.player_max_health
                or (
                    state.inventory.get("medicine", 0)
                    + state.storage.get("medicine", 0)
                ) <= 0
            )
        ),

        Header("Player"),
        Text("Health: " + str(state.player_health)),
        Text("Maximum health: " + str(state.player_max_health)),
        Text("Carrying capacity: " + str(state.capacity)),
        Text(
            "Current weight: " + displayed_inventory_weight(state)
            + " / " + str(state.capacity)
        ),

        Button("Explore", "explore"),
        Button("Storage", "storage_page"),
        Button("Craft", "craft_page"),

        Header("Camp Activities"),
        Button("Collect Traps", "use_traps"),
        Button("Scavenge for Wood", "scavenge")
    ]

    return Page(state, content)


# ==========================================
# REST AT CAMP
# ==========================================

@route
def rest_at_camp(state):
    if state.player_health >= state.player_max_health:
        state.message = "You are already at full health."
        return camp_page(state)

    # Use medicine you are carrying first, then campsite storage.
    if state.inventory.get("medicine", 0) > 0:
        remove_item(state, "medicine", 1)
    elif storage_has(state, "medicine", 1):
        spend_storage(state, "medicine", 1)
    else:
        state.message = "You need 1 medicine to rest."
        return camp_page(state)

    heal_player(state, state.player_max_health - state.player_health)
    state.message = (
        "You use 1 medicine and rest. Your health is fully restored to "
        + str(state.player_max_health) + "."
    )

    add_log(state, state.message)
    return camp_page(state)


# ==========================================
# STORAGE PAGE
# ==========================================

@route
def storage_page(state):
    state.screen = "storage"

    inventory_content = [Header("YOUR INVENTORY")]
    storage_content = [Header("CAMPSITE STORAGE")]

    for item in ALL_ITEMS:
        inventory_content.append(
            Div(
                Text(
                    item.title() + ": "
                    + str(state.inventory.get(item, 0))
                ),
                Button("-", store_routes[item])
            )
        )

    inventory_content.append(
        Text(
            "Weight: " + displayed_inventory_weight(state)
            + " / " + str(state.capacity)
        )
    )
    inventory_content.append(
        Button("All Materials", "store_all_materials")
    )

    for item in ALL_ITEMS:
        row = [
            Text(
                item.title() + ": "
                + str(state.storage.get(item, 0))
            ),
            Button("+", take_routes[item])
        ]

        if item in TAKE_ALL_ITEMS:
            row.append(Button("All", take_all_routes[item]))
        if item in ("rations", "arrows"):
            row.append(Button("10", take_ten_routes[item]))

        storage_content.append(Div(*row))

    content = event_log_content(state) + [
        Header("CAMPSITE STORAGE"),
        Text("Use - to store one carried item. Use + to take one stored item."),
        Div(
            Div(*inventory_content, id="carried_column"),
            Div(*storage_content, id="storage_column"),
            id="storage_columns"
        ),
        Button("Back to Camp", "camp_page")
    ]

    return Page(
        state,
        content,
        css="""
        #storage_columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            align-items: start;
        }

        #carried_column, #storage_column {
            border: 1px solid #777;
            padding: 12px;
            border-radius: 6px;
            min-width: 0;
        }

        @media (max-width: 600px) {
            #storage_columns {
                grid-template-columns: 1fr;
            }
        }
        """
    )


# ==========================================
# STORAGE TRANSFER ROUTES
# ==========================================

def return_from_storage_transfer(state):
    return storage_page(state)


@route
def store_wood(state):
    transfer_to_storage(state, "wood")
    return return_from_storage_transfer(state)


@route
def store_iron(state):
    transfer_to_storage(state, "iron")
    return return_from_storage_transfer(state)


@route
def store_leather(state):
    transfer_to_storage(state, "leather")
    return return_from_storage_transfer(state)


@route
def store_rations(state):
    transfer_to_storage(state, "rations")
    return return_from_storage_transfer(state)


@route
def store_medicine(state):
    transfer_to_storage(state, "medicine")
    return return_from_storage_transfer(state)


@route
def store_club(state):
    transfer_to_storage(state, "club")
    return return_from_storage_transfer(state)


@route
def store_sword(state):
    transfer_to_storage(state, "iron sword")
    return return_from_storage_transfer(state)


@route
def store_stake(state):
    transfer_to_storage(state, "stake")
    return return_from_storage_transfer(state)


@route
def store_scaffolding(state):
    transfer_to_storage(state, "scaffolding")
    return return_from_storage_transfer(state)


@route
def take_scaffolding(state):
    transfer_to_inventory(state, "scaffolding")
    return return_from_storage_transfer(state)


@route
def take_all_scaffolding(state):
    transfer_all_to_inventory(state, "scaffolding")
    return return_from_storage_transfer(state)


@route
def store_tablet(state):
    transfer_to_storage(state, "crafting tablet")
    return return_from_storage_transfer(state)


@route
def take_tablet(state):
    transfer_to_inventory(state, "crafting tablet")
    return return_from_storage_transfer(state)


@route
def store_bow(state):
    transfer_to_storage(state, "bow")
    return return_from_storage_transfer(state)


@route
def store_arrows(state):
    transfer_to_storage(state, "arrows")
    return return_from_storage_transfer(state)


@route
def store_sinew(state):
    transfer_to_storage(state, "sinew")
    return return_from_storage_transfer(state)


@route
def take_bow(state):
    transfer_to_inventory(state, "bow")
    return return_from_storage_transfer(state)


@route
def take_arrows(state):
    transfer_to_inventory(state, "arrows")
    return return_from_storage_transfer(state)


@route
def take_sinew(state):
    transfer_to_inventory(state, "sinew")
    return return_from_storage_transfer(state)


@route
def take_ten_rations(state):
    transfer_amount_to_inventory(state, "rations", 10)
    return return_from_storage_transfer(state)


@route
def take_ten_arrows(state):
    transfer_amount_to_inventory(state, "arrows", 10)
    return return_from_storage_transfer(state)


@route
def store_all_materials(state):
    transfer_all_materials_to_storage(state)
    return return_from_storage_transfer(state)


@route
def take_wood(state):
    transfer_to_inventory(state, "wood")
    return return_from_storage_transfer(state)


@route
def take_iron(state):
    transfer_to_inventory(state, "iron")
    return return_from_storage_transfer(state)


@route
def take_leather(state):
    transfer_to_inventory(state, "leather")
    return return_from_storage_transfer(state)


@route
def take_rations(state):
    transfer_to_inventory(state, "rations")
    return return_from_storage_transfer(state)


@route
def take_medicine(state):
    transfer_to_inventory(state, "medicine")
    return return_from_storage_transfer(state)


@route
def take_club(state):
    transfer_to_inventory(state, "club")
    return return_from_storage_transfer(state)


@route
def take_sword(state):
    transfer_to_inventory(state, "iron sword")
    return return_from_storage_transfer(state)


@route
def take_stake(state):
    transfer_to_inventory(state, "stake")
    return return_from_storage_transfer(state)



# ==========================================
# STORAGE: TAKE ALL ROUTES
# ==========================================

@route
def take_all_wood(state):
    transfer_all_to_inventory(state, "wood")
    return return_from_storage_transfer(state)


@route
def take_all_iron(state):
    transfer_all_to_inventory(state, "iron")
    return return_from_storage_transfer(state)


@route
def take_all_leather(state):
    transfer_all_to_inventory(state, "leather")
    return return_from_storage_transfer(state)


@route
def take_all_rations(state):
    transfer_all_to_inventory(state, "rations")
    return return_from_storage_transfer(state)


@route
def take_all_medicine(state):
    transfer_all_to_inventory(state, "medicine")
    return return_from_storage_transfer(state)


@route
def take_all_club(state):
    transfer_all_to_inventory(state, "club")
    return return_from_storage_transfer(state)


@route
def take_all_sword(state):
    transfer_all_to_inventory(state, "iron sword")
    return return_from_storage_transfer(state)


@route
def take_all_stake(state):
    transfer_all_to_inventory(state, "stake")
    return return_from_storage_transfer(state)


@route
def take_all_sinew(state):
    transfer_all_to_inventory(state, "sinew")
    return return_from_storage_transfer(state)


@route
def take_all_arrows(state):
    transfer_all_to_inventory(state, "arrows")
    return return_from_storage_transfer(state)


take_all_routes = {
    "wood": "take_all_wood",
    "iron": "take_all_iron",
    "leather": "take_all_leather",
    "rations": "take_all_rations",
    "medicine": "take_all_medicine",
    "club": "take_all_club",
    "iron sword": "take_all_sword",
    "stake": "take_all_stake",
    "scaffolding": "take_all_scaffolding",
    "sinew": "take_all_sinew",
    "arrows": "take_all_arrows"
}

take_ten_routes = {
    "rations": "take_ten_rations",
    "arrows": "take_ten_arrows"
}


# ==========================================
# EXPLORE
# ==========================================

@route
def explore(state):
    state.player_x = START_X
    state.player_y = START_Y

    state.game_over = False
    state.victory = False
    state.in_encounter = False

    state.movement_steps = 0
    state.expedition_explored = []

    state.claimed_outposts = []

    # completed_houses is NOT reset: finished houses stay finished.
    state.house_progress = {}

    state.tower_active = False
    state.tower_level = 0

    state.screen = "map"

    add_log(state, "You leave camp and begin exploring.")
    return map_page(state)


# ==========================================
# RETURN TO CAMP
# ==========================================

@route
def return_to_camp(state):
    if (state.player_x, state.player_y) != (START_X, START_Y):
        state.message = "You must walk back to the campsite."
        return map_page(state)

    state.permanent_explored = list(state.explored)
    state.expedition_explored = []

    state.secured_locations = list(state.searched_locations)

    state.in_encounter = False
    state.game_over = False
    state.victory = False

    state.screen = "camp"

    state.message = "You return safely to the campsite with your inventory."
    add_log(state, state.message)

    return camp_page(state)


# ==========================================
# TRAPS
# ==========================================

@route
def use_traps(state):
    current_time = time.time()

    if state.last_trap_time > 0:
        elapsed = current_time - state.last_trap_time

        if elapsed < TRAP_COOLDOWN:
            remaining = int(TRAP_COOLDOWN - elapsed) + 1
            state.message = (
                "You must wait " + str(remaining)
                + " seconds before collecting traps again."
            )
            return camp_page(state)

    total_rations = 0

    for _ in range(state.trap_count):
        for _ in range(3):
            result = random.randint(1, 100)

            if result <= 30:
                pass
            elif result <= 70:
                total_rations += 1
            elif result <= 90:
                total_rations += 2
            else:
                total_rations += 3

    state.storage["rations"] = state.storage.get("rations", 0) + total_rations
    record_collected(state, "rations", total_rations)
    state.last_trap_time = current_time

    state.message = (
        "You collected " + str(total_rations)
        + " rations from " + str(state.trap_count)
        + " trap(s)! They were placed in storage."
    )

    add_log(state, state.message)
    return camp_page(state)


# ==========================================
# SCAVENGE
# ==========================================

def scavenge_wood_range(state):
    # The amount of wood grows as strongholds are completed.
    # (The player is not told about this.)
    if (
        len(state.strongholds) > 1
        and state.strongholds[1] in state.completed_strongholds
    ):
        return 4, 8

    if state.strongholds[0] in state.completed_strongholds:
        return 2, 5

    return 2, 3


@route
def scavenge(state):
    current_time = time.time()

    if state.last_scavenge_time > 0:
        elapsed = current_time - state.last_scavenge_time

        if elapsed < SCAVENGE_COOLDOWN:
            remaining = int(SCAVENGE_COOLDOWN - elapsed) + 1
            state.message = (
                "You must wait " + str(remaining)
                + " seconds before scavenging again."
            )
            return camp_page(state)

    minimum_wood, maximum_wood = scavenge_wood_range(state)
    amount = random.randint(minimum_wood, maximum_wood)

    state.storage["wood"] = state.storage.get("wood", 0) + amount
    record_collected(state, "wood", amount)
    state.last_scavenge_time = current_time

    state.message = (
        "You scavenged " + str(amount)
        + " pieces of wood and placed them in storage."
    )

    add_log(state, state.message)
    return camp_page(state)


# ==========================================
# CRAFTING PAGE
# ==========================================
#
# Normal crafting pays from campsite storage and puts the result in
# storage. The Crafting Tablet (state.tablet_mode) pays the same
# standard recipe costs from the player's INVENTORY ONLY and puts
# the result in the inventory. It never touches storage, the loot
# that is waiting to be picked up, or the dropped items.
#

TABLET_COST_MULTIPLIER = 1.0

RECIPES = {
    "medicine": {"rations": 5},
    "club": {"wood": 3},
    "stake": {"wood": 1},
    "iron sword": {"iron": 2, "wood": 1},
    "crafting tablet": {"iron": 1, "wood": 10},
    "iron": {"rations": 10},
    "leather": {"rations": 5},
    "sinew": {"leather": 2},
    "arrows": {"iron": 1, "wood": 5, "sinew": 2},
    "bow": {"wood": 10, "sinew": 3},
    "scaffolding": {"wood": 2, "sinew": 1},
    "protein shake": {"medicine": 8},
    "shield": {"iron": 1, "wood": 5, "leather": 2},
    "leather armor": {"leather": 10},
    "iron armor": {"iron": 10},
    "backpack": {"leather": 5},
    "convoy": {"wood": 10, "iron": 5}
}


def scaled_cost(state, cost):
    if not state.tablet_mode:
        return dict(cost)

    scaled = {}

    for item, amount in cost.items():
        scaled[item] = math.ceil(amount * TABLET_COST_MULTIPLIER)

    return scaled


def cost_text(state, cost):
    parts = []

    for item, amount in scaled_cost(state, cost).items():
        parts.append(str(amount) + " " + item.title())

    return ", ".join(parts)


def cost_suffix(state, cost):
    # Show the same standard recipe prices at home and on the tablet.
    return " (" + cost_text(state, cost) + ")"


def start_craft(state, cost, output_item=None):
    # Checks that the player can pay, then pays. Returns False (and sets
    # a message) if the craft cannot happen.
    cost = scaled_cost(state, cost)

    for item, amount in cost.items():
        if state.tablet_mode:
            have = state.inventory.get(item, 0)
            where = "carried"
        else:
            have = state.storage.get(item, 0)
            where = "stored"

        if have < amount:
            state.message = (
                "You need " + str(amount) + " " + where + " " + item + "."
            )
            return False

    if state.tablet_mode and output_item is not None:
        # The result goes into the inventory, so it must fit once the
        # ingredients have been used up. (Upgrades that make no item,
        # such as armor or the shield, never need room.)
        new_weight = inventory_weight(state)

        for item, amount in cost.items():
            new_weight -= item_weight(item) * amount

        new_weight += item_weight(output_item)

        if new_weight > state.capacity:
            state.message = "You do not have enough carrying capacity."
            return False

    for item, amount in cost.items():
        if state.tablet_mode:
            remove_item(state, item, amount)
        else:
            spend_storage(state, item, amount)

    return True


def give_crafted_item(state, item):
    # Crafted materials: inventory with the tablet, storage otherwise.
    if state.tablet_mode:
        add_item(state, item, 1)
    else:
        state.storage[item] = state.storage.get(item, 0) + 1


def deliver_crafted_weapon(state, item):
    if add_item(state, item, 1):
        state.message = "You crafted a " + item.title() + " and placed it in your inventory."
    else:
        state.storage[item] = state.storage.get(item, 0) + 1
        state.message = (
            "You crafted a " + item.title()
            + ", but your inventory is full. It was placed in storage."
        )
    add_log(state, state.message)


@route
def open_crafting_tablet(state):
    if not crafting_tablet_available(state):
        return loot_page(state)

    state.tablet_mode = True
    return craft_page(state)


@route
def close_tablet(state):
    state.tablet_mode = False
    return loot_page(state)


@route
def craft_page(state):
    state.screen = "craft"

    side_content = []

    if state.tablet_mode:
        side_content.append(Header("YOUR INVENTORY"))

        for item in ALL_ITEMS:
            side_content.append(
                Text(item.title() + ": " + str(state.inventory.get(item, 0)))
            )

        side_content.append(
            Div(
                Text(
                    "Weight: " + displayed_inventory_weight(state)
                    + " / " + str(state.capacity)
                )
            )
        )
    else:
        side_content.append(Header("CAMPSITE STORAGE"))

        for item in ALL_ITEMS:
            side_content.append(
                Text(item.title() + ": " + str(state.storage.get(item, 0)))
            )

    next_trap_cost = {"wood": state.trap_count * 2}

    crafting_options = Div(
        Div(
            Header("Equipment"),
            Button("Medicine" + cost_suffix(state, RECIPES["medicine"]), "craft_medicine"),
            Button("Club" + cost_suffix(state, RECIPES["club"]), "craft_club"),
            Button("Stake" + cost_suffix(state, RECIPES["stake"]) + " (Breaks on use)", "craft_stake"),
            Button("Iron Sword" + cost_suffix(state, RECIPES["iron sword"]), "craft_sword"),
            Button("Crafting Tablet" + cost_suffix(state, RECIPES["crafting tablet"]), "craft_tablet"),
            Button("Bow" + cost_suffix(state, RECIPES["bow"]), "craft_bow"),
            id="craft_equipment"
        ),
        Div(
            Header("Materials"),
            Button("Iron" + cost_suffix(state, RECIPES["iron"]), "craft_iron"),
            Button("Leather" + cost_suffix(state, RECIPES["leather"]), "craft_leather"),
            Button("Sinew" + cost_suffix(state, RECIPES["sinew"]), "craft_sinew"),
            Button("Arrows (10)" + cost_suffix(state, RECIPES["arrows"]), "craft_arrows"),
            Button("Scaffolding" + cost_suffix(state, RECIPES["scaffolding"]), "craft_scaffolding"),
            id="craft_materials"
        ),
        Div(
            Header("Permanent Upgrades"),
            Button("Protein Shake" + cost_suffix(state, RECIPES["protein shake"]), "craft_protein_shake"),
            Text("Permanently adds 5 damage to weapon attacks."),
            Div(Button("Shield" + cost_suffix(state, RECIPES["shield"]), "craft_shield")),
            Button("Upgrade Trap Capacity", "upgrade_traps"),
            *(
                [
                    Text("Current traps: " + str(state.trap_count)),
                    Text("Next trap upgrade: " + cost_text(state, next_trap_cost).lower())
                ] if state.trap_count < 5 else []
            ),
            Button("Leather Armor (+50 Max HP)" + cost_suffix(state, RECIPES["leather armor"]), "craft_leather_armor"),
            Button("Iron Armor (+100 Max HP)" + cost_suffix(state, RECIPES["iron armor"]), "craft_iron_armor"),
            Div(Text("Current capacity: " + str(state.capacity))),
            Div(
                Button("Leather Backpack (+20)" + cost_suffix(state, RECIPES["backpack"]), "craft_backpack"),
                Button("Convoy (+40)" + cost_suffix(state, RECIPES["convoy"]), "upgrade_convoy")
            ),
            id="craft_permanent"
        ),
        id="craft_options"
    )

    if state.tablet_mode:
        intro = [Div(Text("Crafting costs are paid from your inventory."))]
        back_button = Button("Back", "close_tablet")
    else:
        intro = [Text("Crafting costs are paid from campsite storage.")]
        back_button = Button("Back to Camp", "camp_page")

    content = event_log_content(state) + intro + [
        Div(
            Div(crafting_options, id="crafting_left"),
            Div(*side_content, id="crafting_storage"),
            id="craft_layout"
        ),
        Div(back_button, id="craft_back")
    ]

    return Page(
        state,
        content,
        css="""
        #craft_back {
            text-align: right;
            margin-top: 10px;
        }
        #craft_layout {
            display: grid;
            grid-template-columns: minmax(0, 2fr) minmax(190px, 1fr);
            gap: 12px;
            align-items: start;
        }
        #craft_options {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            align-items: start;
        }
        #craft_permanent {
            grid-column: 1 / -1;
        }
        #craft_options > div, #crafting_storage {
            border: 1px solid #777;
            border-radius: 6px;
            padding: 7px;
            min-width: 0;
        }
        #crafting_storage {
            position: sticky;
            top: 8px;
        }
        #craft_options h2, #craft_options h3,
        #crafting_storage h2, #crafting_storage h3 {
            margin-top: 4px;
            margin-bottom: 5px;
        }
        #craft_options button {
            margin: 3px 2px;
            padding: 5px 8px;
        }
        #craft_options p, #crafting_storage p {
            margin: 4px 0;
        }
        @media (max-width: 750px) {
            #craft_layout {
                grid-template-columns: 1fr;
            }
            #crafting_storage {
                position: static;
            }
        }
        @media (max-width: 500px) {
            #craft_options {
                grid-template-columns: 1fr;
            }
        }
        """
    )


# ==========================================
# CRAFTING: PROTEIN SHAKE
# ==========================================

@route
def craft_protein_shake(state):
    if state.protein_shake:
        state.message = "Already crafted this item."
        return craft_page(state)

    first_stronghold = find_closest_stronghold(state)

    if first_stronghold not in state.completed_strongholds:
        state.message = "Missing requirement: complete the first stronghold."
        return craft_page(state)

    if not start_craft(state, RECIPES["protein shake"]):
        return craft_page(state)

    state.protein_shake = True

    state.message = (
        "You obtained the Protein Shake! All weapon attacks now "
        "deal 5 extra damage, including weapons you obtain later."
    )

    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: MEDICINE
# ==========================================

@route
def craft_medicine(state):
    if not start_craft(state, RECIPES["medicine"], "medicine"):
        return craft_page(state)

    give_crafted_item(state, "medicine")

    state.message = "You obtained 1 medicine!"
    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: CLUB
# ==========================================

@route
def craft_club(state):
    if not start_craft(state, RECIPES["club"], "club"):
        return craft_page(state)

    deliver_crafted_weapon(state, "club")
    return craft_page(state)


# ==========================================
# CRAFTING: STAKE
# ==========================================

@route
def craft_stake(state):
    if not start_craft(state, RECIPES["stake"], "stake"):
        return craft_page(state)

    deliver_crafted_weapon(state, "stake")
    return craft_page(state)


# ==========================================
# CRAFTING: IRON SWORD
# ==========================================

@route
def craft_sword(state):
    if not start_craft(state, RECIPES["iron sword"], "iron sword"):
        return craft_page(state)

    deliver_crafted_weapon(state, "iron sword")
    return craft_page(state)


# ==========================================
# CRAFTING: CRAFTING TABLET
# ==========================================

@route
def craft_tablet(state):
    if not start_craft(state, RECIPES["crafting tablet"], "crafting tablet"):
        return craft_page(state)

    deliver_crafted_weapon(state, "crafting tablet")
    return craft_page(state)


# ==========================================
# CRAFTING: SHIELD (permanent upgrade)
# ==========================================

@route
def craft_shield(state):
    if state.shield:
        state.message = "Already crafted this item."
        return craft_page(state)

    if not start_craft(state, RECIPES["shield"]):
        return craft_page(state)

    state.shield = True

    state.message = (
        "You obtained the Shield! You now get a second chance "
        "to evade attacks."
    )

    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: IRON
# ==========================================

@route
def craft_iron(state):
    if not state.iron_crafting_unlocked:
        state.message = "Missing requirement: complete the Iron Mine."
        return craft_page(state)

    if not start_craft(state, RECIPES["iron"], "iron"):
        return craft_page(state)

    give_crafted_item(state, "iron")

    state.message = (
        "You obtained 1 iron from "
        + str(scaled_cost(state, RECIPES["iron"])["rations"])
        + " rations!"
    )
    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: LEATHER MATERIAL
# ==========================================

@route
def craft_leather(state):
    first_stronghold = find_closest_stronghold(state)

    if first_stronghold not in state.completed_strongholds:
        state.message = "Missing requirement: complete the first stronghold."
        return craft_page(state)

    if not start_craft(state, RECIPES["leather"], "leather"):
        return craft_page(state)

    give_crafted_item(state, "leather")

    state.message = (
        "You crafted 1 leather from "
        + str(scaled_cost(state, RECIPES["leather"])["rations"])
        + " rations!"
    )
    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: SINEW, ARROWS AND BOW
# ==========================================

@route
def craft_sinew(state):
    if not start_craft(state, RECIPES["sinew"], "sinew"):
        return craft_page(state)
    give_crafted_item(state, "sinew")
    state.message = "You crafted 1 sinew."
    add_log(state, state.message)
    return craft_page(state)


@route
def craft_arrows(state):
    # Ten arrows are crafted per recipe. Check their carrying weight
    # before paying for ingredients.
    cost = scaled_cost(state, RECIPES["arrows"])
    projected_weight = inventory_weight(state)
    if state.tablet_mode:
        for item, amount in cost.items():
            projected_weight -= item_weight(item) * amount
    if projected_weight + item_weight("arrows") * 10 > state.capacity + 1e-9:
        state.message = "You do not have enough carrying capacity for 10 arrows."
        return craft_page(state)
    if not start_craft(state, RECIPES["arrows"]):
        return craft_page(state)
    add_item(state, "arrows", 10)
    state.message = "You crafted 10 arrows and placed them in your inventory."
    add_log(state, state.message)
    return craft_page(state)


@route
def craft_bow(state):
    if not start_craft(state, RECIPES["bow"], "bow"):
        return craft_page(state)
    deliver_crafted_weapon(state, "bow")
    return craft_page(state)


# ==========================================
# CRAFTING: SCAFFOLDING
# ==========================================

@route
def craft_scaffolding(state):
    if not start_craft(state, RECIPES["scaffolding"], "scaffolding"):
        return craft_page(state)

    give_crafted_item(state, "scaffolding")

    state.message = (
        "You crafted 1 scaffolding from "
        + cost_text(state, RECIPES["scaffolding"]) + "!"
    )
    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: LEATHER ARMOR
# ==========================================

@route
def craft_leather_armor(state):
    if state.leather_armor:
        state.message = "Already crafted this item."
        return craft_page(state)

    if not start_craft(state, RECIPES["leather armor"]):
        return craft_page(state)

    state.leather_armor = True
    state.player_max_health += 50
    state.player_health += 50

    state.message = (
        "You obtained leather armor! Your health is now "
        + str(state.player_health) + " / "
        + str(state.player_max_health) + "."
    )

    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: IRON ARMOR
# ==========================================

@route
def craft_iron_armor(state):
    if state.iron_armor:
        state.message = "Already crafted this item."
        return craft_page(state)

    if not state.leather_armor:
        state.message = "Missing requirement: Leather Armor."
        return craft_page(state)

    if not start_craft(state, RECIPES["iron armor"]):
        return craft_page(state)

    state.iron_armor = True
    state.player_max_health += 100
    state.player_health += 100

    state.message = (
        "You obtained iron armor! Your health is now "
        + str(state.player_health) + " / "
        + str(state.player_max_health) + "."
    )

    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: BACKPACK
# ==========================================

@route
def craft_backpack(state):
    if state.capacity >= 60:
        state.message = "Already crafted this item."
        return craft_page(state)

    if not start_craft(state, RECIPES["backpack"]):
        return craft_page(state)

    state.capacity = 60

    state.message = "You obtained a leather backpack. Capacity is now 60."
    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: CONVOY
# ==========================================

@route
def upgrade_convoy(state):
    if state.capacity >= 100:
        state.message = "Already crafted this item."
        return craft_page(state)

    if state.capacity < 60:
        state.message = "Missing requirement: Leather Backpack."
        return craft_page(state)

    if not start_craft(state, RECIPES["convoy"]):
        return craft_page(state)

    state.capacity = 100

    state.message = "Your convoy is ready! Capacity is now 100."
    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# CRAFTING: TRAPS
# ==========================================

@route
def upgrade_traps(state):
    if state.trap_count >= 5:
        state.message = "You already have the maximum of 5 traps."
        return craft_page(state)

    if not start_craft(state, {"wood": state.trap_count * 2}):
        return craft_page(state)

    state.trap_count += 1

    state.message = (
        "You upgraded your trap capacity to "
        + str(state.trap_count)
        + " traps! The next upgrade will cost "
        + str(state.trap_count * 2)
        + " wood."
    )

    add_log(state, state.message)
    return craft_page(state)


# ==========================================
# TITLE PAGE
# ==========================================
#
# Drafter opens the route named "index" first, so this is the page the
# player sees when the game loads. (The combat page is battle_page.)
#

DESCRIPTION_TEXT = (
    "Hello there, and welcome to my RPG game!\n\n"
    "I don't want to give too much away, but here are the basics:\n\n"
    "- All items have tooltips that can be accessed by hovering over them with your mouse.\n"
    "- Every 3 steps, you will consume 1 ration, and if you run out of rations, you will starve to death.\n"
    "- When you die, you lose all items in your inventory and respawn at the campsite.\n"
    "- The turn order is as follows\n\n"
    "    - The player heals (if selected)\n\n"
    "    - The player deals damage and takes self damage (if selected)\n\n"
    "    - The enemy attacks\n\n"
    "- If you don't know if you can do something, try it first. (Hint: can you hold multiple weapons?)\n\n"
    "Alright, have fun!!!!!!"
)


@route
def index(state):
    state.screen = "title"

    content = [
        Header("Welcome to the Dungeon"),
        Button("Start", "start_game"),
        Button("Description", "description_page")
    ]

    return Page(state, content)


@route
def start_game(state):
    # The run timer starts the first time Start is clicked.
    if state.game_start_time == 0:
        state.game_start_time = time.time()

    return camp_page(state)


@route
def description_page(state):
    state.screen = "description"

    content = [
        Header("Description"),
        PreformattedText(DESCRIPTION_TEXT),
        Button("Back", "index")
    ]

    return Page(state, content)


# ==========================================
# TESTING SWITCHES
# ==========================================
#
# Set TEST_MODE to True to:
# - Reveal the entire map.
# - Turn off random skeleton encounters.
#
# Set it back to False before submitting the game.
#

TEST_MODE = False


# ==========================================
# START GAME
# ==========================================

def make_initial_state():
    houses, strongholds, iron_mines = create_locations()

    initial_explored = [
        (x, y)
        for y in range(27, 34)
        for x in range(27, 34)
        if not (
            (x == 27 and y == 27)
            or (x == 33 and y == 27)
            or (x == 27 and y == 33)
            or (x == 33 and y == 33)
        )
    ]

    if TEST_MODE:
        initial_explored = [
            (x, y)
            for y in range(MAP_SIZE)
            for x in range(MAP_SIZE)
        ]

    return State(
        player_health=100,
        player_max_health=100,
        player_x=START_X,
        player_y=START_Y,

        enemy_health=80,
        enemy_max_health=80,
        enemy_damage=5,
        enemy_name="Skeleton",

        message="Welcome to the campsite.",
        game_over=False,
        victory=False,
        in_encounter=False,
        screen="camp",

        terrain=create_terrain(),
        explored=list(initial_explored),
        permanent_explored=list(initial_explored),
        expedition_explored=[],

        houses=houses,
        strongholds=strongholds,
        searched_locations=[],
        secured_locations=[],
        completed_strongholds=[],
        roads=[],

        inventory={
            "wood": 0,
            "iron": 0,
            "leather": 0,
            "rations": 15,
            "medicine": 1,
            "club": 0,
            "stake": 0,
            "iron sword": 0,
            "bow": 0,
            "arrows": 0,
            "sinew": 0,
            "scaffolding": 0,
            "crafting tablet": 0
        },

        storage={
            "wood": 0,
            "iron": 0,
            "leather": 0,
            "rations": 0,
            "medicine": 0,
            "club": 0,
            "stake": 0,
            "iron sword": 0,
            "bow": 0,
            "arrows": 0,
            "sinew": 0,
            "scaffolding": 0,
            "crafting tablet": 0
        },

        capacity=40,

        weapon_name="Fists",
        weapon_weight=0,

        movement_steps=0,
        trap_count=1,
        last_trap_time=0,
        last_scavenge_time=0,

        event_log=["You awaken at a familiar campsite."],

        selected_attacks=[],
        selected_healing=[],
        turn_number=0,

        discovered_materials=[],

        current_location=(0, 0),
        location_stage=0,

        pending_loot={},
        loot_return_action="",
        stronghold_progress={},
        claimed_outposts=[],
        combat_kind="skeleton",

        leather_armor=False,
        iron_armor=False,

        house_progress={},
        completed_houses=[],
        iron_mines=iron_mines,
        mine_progress={},
        completed_mines=[],
        iron_crafting_unlocked=False,

        skeleton_safe_steps=0,
        protein_shake=False,
        tower_location=TOWER_LOCATION,
        tower_level=0,
        tower_active=False,

        dropped_items={},

        game_start_time=0.0,
        game_end_time=0.0,
        total_collected={
            "rations": 0,
            "wood": 0,
            "leather": 0,
            "medicine": 0,
            "iron": 0
        },
        total_healing=0
    )


start_server(
    make_initial_state(),
    theme="terminal",
    site_title="THE DUNGEON"
)

