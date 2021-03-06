#!/usr/bin/env python3.11
# vim:fileencoding=utf-8
# (c) 2021 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import argparse
import collections
import datetime
import itertools
import sys
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.absolute()
OUTPUT_DIR = PROJECT_ROOT / "site"
PROLOGUE = """\
<html>
  <head>
    <meta charset="utf-8"/>
    <title>{title}</title>
    <style>
    body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        grid-template-rows: auto 1fr auto;
        box-sizing: border-box;
        font-family: sans-serif;
    }
    header, footer {
        background-color: #c6c3c5;
        padding: 10px;
        text-align: center;
    }
    </style>
  </head>
  <body>
    <script type="text/javascript"
            src="https://www.gstatic.com/charts/loader.js">
    </script>

    <script type="text/javascript">
      google.charts.load("current", {packages:["timeline"]});
      google.charts.setOnLoadCallback(drawChart);
      function drawChart() {

        var container = document.getElementById('timeline');
        var chart = new google.visualization.Timeline(container);
        var dataTable = new google.visualization.DataTable();
        dataTable.addColumn({ type: 'string', id: 'Row' });
        dataTable.addColumn({ type: 'string', id: 'State' });
        dataTable.addColumn({ type: 'date', id: 'Start' });
        dataTable.addColumn({ type: 'date', id: 'End' });
        dataTable.addRows(["""

EPILOGUE = """\
        ]);

        var options = {
          avoidOverlappingGridLines: false
        };

        chart.draw(dataTable, options);
      }
    </script>
    <header>{title}</header>
    <div id="timeline" style="height: 100%"></div>
    <footer>
        <p>Created by <a href="https://mgorny.pl">Michał Górny</a>, this fork is maintained by <a href="https://github.com/jack1142">Jakub Kuczys (@jack1142)</a></p>
        <p>{footer_link}</p>
    </footer>
  </body>
</html>
"""


def jsdate(dt):
    return f"{dt.year}, {dt.month - 1}, {dt.day}"


def print_row(row_label, bars, f):
    prev = None
    for label, start_date in bars:
        if prev is not None:
            print(
                f"          [ {row_label!r}, {prev[0]!r}, "
                f"new Date({jsdate(prev[1])}), "
                f"new Date({jsdate(start_date)}) ],",
                file=f,
            )
        prev = (label, start_date)


def version_key(version):
    return tuple(int(x) for x in version.split("."))


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument("toml", type=argparse.FileType("rb"), help="Input TOML file")
    args = argp.parse_args()

    data = tomllib.load(args.toml)
    args.toml.close()

    OUTPUT_DIR.mkdir(exist_ok=True)
    for eol in (False, True):
        generate_timeline(args, data, eol)


def generate_timeline(args, data, eol):
    title = "Python release timeline"
    if eol:
        title += " including EOL releases"
        footer_link = '<a href="index.html">Hide EOL releases</a>'
        filename = "eol.html"
    else:
        footer_link = '<a href="eol.html">Show EOL releases</a>'
        filename = "index.html"

    with open(OUTPUT_DIR / filename, "w", encoding="utf-8") as f:
        print(PROLOGUE.replace("{title}", title), file=f)

        max_eol = None
        all_rows = collections.defaultdict(list)
        versions = frozenset(itertools.chain.from_iterable(data.values()))
        for version in sorted(versions, key=version_key):
            vdata = data.get("upstream", {}).get(version)
            if vdata is not None:
                bars = []
                if not eol and "eol" in vdata and vdata["eol"] <= datetime.date.today():
                    continue
                if "dev" in vdata:
                    bars.append(("dev", vdata["dev"]))
                bars.extend(
                    [
                        ("\N{GREEK SMALL LETTER ALPHA}", vdata["alpha1"]),
                        ("\N{GREEK SMALL LETTER BETA}", vdata["beta1"]),
                        ("rc", vdata["rc1"]),
                        ("stable", vdata["final"]),
                    ]
                )
                if "last-bugfix" in vdata:
                    bars.append(("security", vdata["last-bugfix"]))
                if "eol" in vdata and vdata["eol"] != vdata["last-bugfix"]:
                    bars.append(("eol", vdata["eol"]))
                if "eol" in vdata:
                    if max_eol is None:
                        max_eol = bars[-1][1]
                    else:
                        max_eol = max(max_eol, bars[-1][1])
                else:
                    assert max_eol is not None
                    bars.append(("future", max_eol))
                all_rows[version].append((version, bars))

        for version in sorted(versions, key=version_key):
            for label, bars in all_rows[version]:
                print_row(label, bars, f)

        print(
            EPILOGUE.replace("{title}", title).replace("{footer_link}", footer_link),
            file=f,
        )


if __name__ == "__main__":
    sys.exit(main())
