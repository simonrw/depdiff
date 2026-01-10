# depdiff

A viewer for package updates in a `requirements.txt` style Python definitions.

## Running

### Terminal mode

TBD

### TUI mode

```
$ git -C ~/work/localstack/localstack show 6269d348d072 | uv run python main.py --tui
```

#### TUI Keyboard shortcuts

* Press ctrl+q twice to quit
* Press j/k to move to different files
* Press u/d to scroll the diff up/down half a page
* Press space and b to scroll the diff up/down a whole page

## Development

- Make sure that every change is checked by running `uv run ty check`. This command must complete successfully
- Types should be used throughout
- Using `typing.Any` is FORBIDDEN

## Testing

- Run tests with `uv run pytest`
- If debugging a test, run a single test with `uv run pytest <test name> -n 0`
