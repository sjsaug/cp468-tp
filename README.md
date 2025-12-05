# cp468-tp

Mate-in-N chess searcher with a Tkinter GUI, a regression test suite, and optional plotting utilities.

## Clone & checkout `august`
```bash
git clone https://github.com/sjsaug/cp468-tp.git
cd cp468-tp
git checkout august
```

## Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
(Use `.venv\Scripts\activate` on Windows.)

## Run the solver/test suite
```bash
python testing.py
```
This runs all bundled FEN puzzles and prints success stats.

## Run the GUI
```bash
python gui.py
```
A Tkinter window opens; load any FEN and click the mate-in-N buttons to animate the solution.
