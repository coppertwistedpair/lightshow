# Lightshow

Desktop app for running color cycles and animations on DMX uplights through an
**Enttec DMX USB Pro**. Supported lights (set them to **6-channel mode**):

| Model | Ch1 | Ch2 | Ch3 | Ch4 | Ch5 | Ch6 |
|---|---|---|---|---|---|---|
| Rockville Rockwedge | Red | Green | Blue | White | Amber | Purple |
| Rockville BestPar 50 | Red | Green | Blue | White | Amber | Purple |

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
   address set on the light (6 channels each). **Edit Selected** or a
   double-click changes the model or address later.
3. Press **GO** for the color cycle, or pick an animation or holiday preset.

## Making a release

Every push to `main` builds the exe (downloadable from the Actions run).
To publish it on the Releases page, push a version tag:

```
git tag v1.0.0
git push origin v1.0.0
```
