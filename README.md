# Lightshow

Desktop app for running color cycles and animations on DMX uplights through an
**Enttec DMX USB Pro**. Supported lights (set the light to the matching DMX mode):

| Model | Channels | Layout |
|---|---|---|
| Rockville Rockwedge (6-ch) | 6 | Red, Green, Blue, White, Amber, Purple |
| Rockville BestPar 50 (6-ch) | 6 | Red, Green, Blue, White, Amber, Purple |
| Rockville BestPar 50 (10-ch) | 10 | Dimmer, Red, Green, Blue, White, Amber, Purple, Strobe, Function, Speed |

In 10-channel mode the app holds the dimmer at full and leaves strobe and the
built-in functions off; colors are controlled the same way as 6-channel mode.

Pick the model when adding a light. Models are defined in `FIXTURE_TYPES` in
`core/fixture_manager.py`.

## Download and run (easiest)

1. Go to the **Releases** page of this repo and download `Lightshow.exe`.
   (Or open the **Actions** tab, pick the latest successful run, and download
   the `Lightshow-windows` artifact.)
2. Put it in its own folder and double-click it. Your light list is saved to
   `config.json` next to the exe.

## Run from source

Requires Python 3.10+ from [python.org](https://www.python.org/downloads/).

Double-click `run.bat`. The first run creates a `.venv` folder and installs the
dependencies; later runs start straight away.

Or manually:

```
py -3 -m pip install -r requirements.txt
py -3 main.py
```

## Using it

1. Plug in the Enttec, click **Refresh**, pick its COM port, click **Connect**.
   (Not sure which port? Device Manager → Ports (COM & LPT) → "USB Serial Port".)
2. Add each light under **Fixtures**: pick its model and enter the DMX start
   address set on the light. **Edit Selected** or a
   double-click changes the model or address later.
   **Add Multiple** adds a batch of one model (e.g. "Wash 1" … "Wash 8") at
   evenly spaced addresses; nothing is added if any address would overlap.
3. Press **GO** for the color cycle, or pick an animation or holiday preset.

## Making a release

Every push to `main` builds the exe (downloadable from the Actions run).
To publish it on the Releases page, push a version tag:

```
git tag v1.0.0
git push origin v1.0.0
```
