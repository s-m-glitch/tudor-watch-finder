---
name: add-watch
description: |
  Add a new watch SKU to Tic (Tudor Inventory Checker). Use this skill when the user wants to:
  - Add a new watch model to track
  - Add another dial variant
  - Update existing watch details (price, reference, etc.)
  - Remove a watch from the available options

  Triggers: "add watch", "new SKU", "different watch", "add a dial", "another variant", "remove watch"
---

# Add Watch to Tic

Tic supports multiple watches. Users can switch between them using tabs in the UI.

## Watch Configuration

All watches are defined in `config.py` in the `WATCHES` dictionary:

```python
WATCHES = {
    "M79930-0007": {
        "model": "Ranger",
        "reference": "M79930-0007",
        "case_size": "36mm",
        "case_material": "steel",
        "dial": "Beige domed dial",
        "price": 3775,
        "full_name": "Tudor Ranger 36mm steel case with Beige domed dial",
        "image": "https://www.tudorwatch.com/-/media/model/ranger/m79930-0007.png"
    },
    # Add more watches here...
}

DEFAULT_WATCH = "M79930-0007"  # Reference of the default watch
```

## Adding a New Watch

1. Get watch details from https://www.tudorwatch.com/en/watches

2. Add entry to `WATCHES` dict in `config.py`:
```python
"<REFERENCE>": {
    "model": "<Model>",           # e.g., "Ranger", "Black Bay", "Pelagos"
    "reference": "<REFERENCE>",   # e.g., "M79930-0001"
    "case_size": "<Size>",        # e.g., "36mm", "39mm", "41mm"
    "case_material": "<Material>",# e.g., "steel", "gold", "titanium"
    "dial": "<Dial>",             # e.g., "Black domed dial"
    "price": <Price>,             # USD, no commas
    "full_name": "Tudor <Model> <Size> <Material> case with <Dial>",
    "image": "https://www.tudorwatch.com/-/media/model/<model>/<reference>.png"
}
```

3. Optionally update `DEFAULT_WATCH` to make the new watch the default

## Removing a Watch

Delete the entry from `WATCHES` dict. Ensure `DEFAULT_WATCH` still references a valid watch.

## How It Works

- Frontend fetches `/api/watches` to get all available watches
- Tabs are generated for each watch (labeled by dial color)
- Selected watch reference is passed to `/api/call` when making phone calls
- The AI phone agent uses the selected watch's details in its script
