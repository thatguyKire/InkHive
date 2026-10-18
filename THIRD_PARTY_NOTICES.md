# Third-Party Notices

COLLABoard includes the following third-party material in this repository. Their licences require the notices below to be kept.

## Chart.js 4.4.1

* File: `modules/dashboard/static/dashboard/vendor/chart.umd.min.js` (unchanged except for the removed source-map comment; the licence header is kept)
* Source: https://www.chartjs.org · https://github.com/chartjs/Chart.js
* Licence: MIT

```
The MIT License (MIT)

(c) 2023 Chart.js Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

## Python packages

The server uses the packages in `requirements.txt` (Django, Channels, Daphne, WhiteNoise, Pillow and others) under their own permissive licences (BSD, MIT, HPND and similar). They are installed at build time and are not copied into this repository.

## Removed

* `core/img/graphy.png`, the "Graphy" texture by We Are Pixel8 from transparenttextures.com. No licence was stated, so the graph-paper background is now drawn with CSS.
* `help_app/img/gmail (1).png` (the Gmail logo, a Google trademark), replaced by our own envelope icon.

## Our own artwork

The SVG icons `core/icons/trash.svg` and `help_app/img/email.svg` were drawn for this project. The origin of the PNG icons in `core/icons/` and the COLLABoard logo still has to be confirmed by the team (see [docs/LEGAL.md](docs/LEGAL.md) item L-5).
