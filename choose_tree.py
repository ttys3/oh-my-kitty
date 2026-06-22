#!/usr/bin/env python3
"""
choose-tree — a tmux-style window/tab tree overview kitten for kitty.
Pops up a centered modal box listing all OS windows -> tabs -> windows,
each window showing its title / foreground program / cwd. Type to filter,
Up/Down or Ctrl-n/Ctrl-p to move, Enter to jump, Esc to cancel.
Bound in splits.conf: map ctrl+a>w kitten choose_tree.py

Visual style (tunable constants below):
  - Centered modal box: the kitten runs in an overlay that fills the
    current window, but only draws a rounded box in the centered
    BOX_W_RATIO×BOX_H_RATIO area (kitty is tiling, there is no native
    floating window; the modal look is done by drawing inside the overlay).
  - Theme-following minimal: reverse selection, ● focus marker, dim for
    secondary info/borders; no hardcoded colors, uses the terminal's
    default foreground throughout.
  - Tab title dedupe: kitty's tab title defaults to the active window's
    title, which duplicates the window row. So when the tab title matches
    the active window it shows only `tab N (layout, k win)`; only a custom
    (set_tab_title) title that differs from the window is shown.
  - The current tab's header is highlighted with CURRENT_TAB_COLOR.
  - Tab separator style is chosen by TAB_SEPARATOR: bar/rule/reverse/
    underline/none.
  - Preview pane (SHOW_PREVIEW): the box splits into list (top) + a live
    preview grid (bottom) showing every window in the selected window's tab
    as a bordered cell (content via `kitty @ get-text`), the selected one
    highlighted. Cells lay out left-to-right and wrap to more rows when
    narrow; a single-window tab fills the pane with one cell. The box falls
    back to a pure list when too short (PREVIEW_RATIO / *_MIN_ROWS / CELL_*).

Auto-maximize (AUTO_MAXIMIZE): an overlay's size always equals the active
  window, so triggering from a small split renders a tiny box. On open, if
  the current tab has multiple windows and is not stacked, temporarily
  switch it to the stack layout so the overlay fills the whole tab; the
  original layout is restored in handle_result on close/cancel.

kitty APIs used and their stability (read this if you worry about upgrade
compatibility):
  Stable contracts (rarely change across upgrades):
    - `kitty @ ls` JSON shape (fields are only added) -> read with .get()
    - `kitty @ goto-layout [--match id:N] stack`, `focus-window --match id:N`
  Internal APIs (all have fallbacks/degradation, won't crash the kitten):
    - boss.set_active_window(id, switch_os_window_if_needed=True) / boss.call_remote_control
    - boss.tab_for_id(id).goto_layout(name)  # restore the original layout
    - add_timer(cb, 0, False)  # defer the jump to the next event-loop tick,
      so it isn't clobbered by the focus restore that runs when the overlay closes
    - main.remote_control(['ls'/'goto-layout']) via @kitten_ui
    - styled / wcswidth / EventType  # degrade to no-style/len()/no-filter if missing
If it breaks after an upgrade: run `kitty +kitten choose_tree.py`; the
overlay shows the offending API.
ref: https://sw.kovidgoyal.net/kitty/kittens/custom/
"""
from __future__ import annotations

import json
import os
import re
from math import ceil
from typing import Any

from kitty.boss import Boss
from kittens.tui.handler import Handler, kitten_ui, result_handler
from kittens.tui.loop import Loop

try:
    from kitty.fast_data_types import wcswidth as _wcswidth
except Exception:
    def _wcswidth(s: str) -> int:
        return len(s)

try:
    # Grapheme-cluster splitter (flags/keycaps/ZWJ/VS16 emoji collapse to one
    # cluster). kitty's wcswidth is grapheme-aware, so width must be measured on
    # whole clusters, not codepoints. Fallback: per-codepoint (old buggy width,
    # but never crashes on an older kitty without this symbol).
    from kitty.fast_data_types import split_into_graphemes as _split_graphemes
except Exception:
    def _split_graphemes(s: str) -> list[str]:
        return list(s)

try:
    from kittens.tui.operations import styled as _styled
except Exception:
    def _styled(text: str, **kw: Any) -> str:
        return text

try:
    from kitty.key_encoding import EventType as _EventType
    _RELEASE = _EventType.RELEASE
except Exception:
    _RELEASE = None

HOME = os.path.expanduser('~')

# Modal box size ratio (width / height); tweak freely. 1.0 = full screen.
BOX_W_RATIO = 0.8
BOX_H_RATIO = 0.8

# On open, if the current tab has multiple windows and is not stacked,
# temporarily switch it to stack to enlarge the overlay, then restore on
# close. Set to False to disable.
AUTO_MAXIMIZE = True

# Tab separator style (change this one line and re-test live in kitty):
#   'bar'       leading vertical bar ▌ (cleanest)
#   'rule'      title + dim rule extending to the box edge (strong now that
#               titles are deduped and short)
#   'reverse'   full-width reversed title bar (strongest, like a header bar)
#   'underline' underlined title
#   'none'      bold title only
TAB_SEPARATOR = 'bar'

# Accent color for the current tab's header ('' to disable). A color name
# 'green'/'cyan'/'yellow' or a 0-255 number.
CURRENT_TAB_COLOR = 'green'

# ── Preview pane (tmux choose-tree style) ───────────────────────────────
# Split the modal box into list (top) + preview (bottom). The preview shows a
# live grid of EVERY window in the selected window's TAB: each window is a
# bordered cell laid out left-to-right (wrapping to more rows when too narrow),
# the currently selected window highlighted. A tab with a single window degrades
# to one big cell (== a plain single-window preview). The list stays
# window-level: Up/Down still selects/jumps a window and just drives which cell
# is highlighted; moving to another tab swaps the whole grid.
SHOW_PREVIEW = True
# Preview content comes from `kitty @ get-text --extent screen` on each window
# (verified to return only SGR color codes with --ansi; no cursor moves/OSC).
PREVIEW_ANSI = True       # True: keep colors (SGR); False: plain text (always safe)
# Fraction of the (list + preview) body given to the preview. The grid is dense,
# so it defaults to half. 0.0 disables effectively (list keeps everything).
PREVIEW_RATIO = 0.5
# Degradation floors: only draw a preview when the list keeps >= LIST_MIN_ROWS
# AND the preview gets >= PREVIEW_MIN_ROWS (one row of bordered cells needs 4);
# otherwise the box silently falls back to a pure list (no divider, no crash).
LIST_MIN_ROWS = 3
PREVIEW_MIN_ROWS = 4
# Per-window cell geometry inside the grid. A cell narrower than CELL_MIN_W
# triggers a wrap to more rows; CELL_MIN_H is the min cell height (2 border rows
# + >=2 content rows); CELL_GAP is the blank columns between cells.
CELL_MIN_W = 16
CELL_MIN_H = 4
CELL_GAP = 1
# Divider glyph between the list and the preview grid.
PREVIEW_DIVIDER = '─'


def _shorten_cwd(cwd: str) -> str:
    if not cwd:
        return ''
    if cwd == HOME:
        return '~'
    if cwd.startswith(HOME + os.sep):
        return '~' + cwd[len(HOME):]
    return cwd


def _proc(w: dict[str, Any]) -> str:
    fg = w.get('foreground_processes') or []
    if fg:
        cmdline = (fg[-1] or {}).get('cmdline') or []
        if cmdline:
            exe = os.path.basename(cmdline[0])
            rest = ' '.join(cmdline[1:])
            return (exe + (' ' + rest if rest else '')).strip()
    return w.get('last_reported_cmdline') or ' '.join(w.get('cmdline') or []) or '?'


def _truncate(text: str, width: int) -> str:
    """Truncate to `width` display columns (grapheme-cluster aware), appending
    '…' when cut. Iterates whole graphemes so a flag/keycap/ZWJ/VS16 emoji is
    kept or dropped atomically and the result's display width matches the
    terminal (and _visible_width/_pad). A per-codepoint wcswidth loop is wrong
    here: kitty's wcswidth collapses multi-codepoint graphemes, so summing
    codepoints over-counts flags/ZWJ and under-counts keycaps."""
    if width <= 0:
        return ''
    if _wcswidth(text) <= width:
        return text
    out: list[str] = []
    w = 0
    for g in _split_graphemes(text):
        gw = _wcswidth(g)
        if gw < 0:
            gw = 0
        if w + gw > width - 1:
            out.append('…')
            break
        out.append(g)
        w += gw
    return ''.join(out)


def _truncate_pair(head: str, tail: str, width: int) -> tuple[str, str]:
    """Fit head+tail into width; head has priority, tail gets the remainder."""
    hw = _wcswidth(head)
    if hw >= width:
        return _truncate(head, width), ''
    return head, _truncate(tail, width - hw)


def _pad(text: str, width: int) -> str:
    """Truncate + right-pad to display width (CJK aware)."""
    text = _truncate(text, width)
    return text + ' ' * max(0, width - _wcswidth(text))


# ── Preview pure helpers (no kitty deps beyond _wcswidth/_styled; testable) ──
# `get-text --ansi` (verified live) emits only SGR (\x1b[…m) and occasionally
# OSC (hyperlinks/titles). We strip OSC and keep SGR, truncating SGR-aware.
_OSC_RE = re.compile(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)')
_SGR_RE = re.compile(r'\x1b\[[0-9;:]*m')


def _strip_osc(s: str) -> str:
    """Drop OSC sequences (hyperlinks \x1b]8;…, titles \x1b]0;…); tolerate both
    BEL and ST (\x1b\\) terminators. SGR color codes are left untouched."""
    return _OSC_RE.sub('', s)


def _visible_width(s: str) -> int:
    """Display width of an SGR-annotated string (SGR sequences count 0)."""
    return _wcswidth(_SGR_RE.sub('', s))


def _sgr_truncate(line: str, width: int) -> str:
    """Truncate an SGR-annotated line to `width` display columns.

    SGR sequences (\x1b[…m) pass through verbatim and cost 0 columns; printable
    text is measured/cut by whole grapheme clusters (CJK == 2; a flag/keycap/
    ZWJ/VS16 emoji is kept or dropped atomically, never split). Stops before
    exceeding width with no ellipsis (fills a cell edge-to-edge); a cluster
    straddling the boundary is dropped so the visible width is always <= width
    and matches the terminal. A per-codepoint loop is wrong here: kitty's
    wcswidth is grapheme-aware, so summing codepoints over-counts flags/ZWJ and
    under-counts keycaps, which used to overflow or split a cell (misaligned
    borders). Appends a reset when any SGR was emitted, so color never bleeds
    past the cut or into a border."""
    if width <= 0:
        return ''
    out: list[str] = []
    w = 0
    saw_sgr = False
    pos = 0
    done = False

    def take(seg: str) -> bool:
        """Consume seg grapheme-by-grapheme; return True when width is hit."""
        nonlocal w
        for g in _split_graphemes(seg):
            gw = _wcswidth(g)
            if gw < 0:
                gw = 0
            if w + gw > width:
                return True
            out.append(g)
            w += gw
        return False

    # SGR codes are 0-width and pass through; the text between them is measured.
    for m in _SGR_RE.finditer(line):
        if take(line[pos:m.start()]):
            done = True
            break
        out.append(m.group())
        saw_sgr = True
        pos = m.end()
    if not done:
        take(line[pos:])
    if saw_sgr:
        out.append('\x1b[0m')
    return ''.join(out)


def _grid_dims(n: int, inner: int, ph: int) -> tuple[int, int, int, int, int]:
    """Lay out n window cells in an inner×ph area. Returns
    (cols, rows, cell_w, cell_h, cap). Prefers a single row (cells side by
    side); wraps to more rows when cells would be narrower than CELL_MIN_W;
    caps rows by height (CELL_MIN_H). A hard floor keeps cells renderable
    (>= ~3 cols). cap == cols*rows cells fit; a caller with n>cap marks the
    overflow."""
    n = max(1, n)
    rows_cap = max(1, ph // CELL_MIN_H)
    per_row = max(1, (inner + CELL_GAP) // (CELL_MIN_W + CELL_GAP))
    rows = min(rows_cap, ceil(n / per_row))
    cols = ceil(n / rows)
    max_cols = max(1, (inner + CELL_GAP) // (3 + CELL_GAP))  # keep cell_w >= ~3
    cols = min(cols, max_cols)
    cell_w = (inner - (cols - 1) * CELL_GAP) // cols
    cell_h = ph // rows
    return cols, rows, cell_w, cell_h, cols * rows


def _render_cell(title: str, lines: list[str], w: int, h: int, selected: bool) -> list[str]:
    """Render one window as a bordered cell: h strings, each visible width == w
    (SGR-aware). Row 0 is ┌title…┐, rows 1..h-2 are │content│, the last is
    └────┘. Selected cells get an accent border + title; others a dim border.
    Content keeps the window's own colors, SGR-truncated to the inner width and
    padded with default-bg spaces (so no color bleeds into the borders)."""
    if w < 2 or h < 1:
        return [' ' * max(0, w) for _ in range(max(0, h))]
    fg = CURRENT_TAB_COLOR if (selected and CURRENT_TAB_COLOR) else None
    bstyle: dict[str, Any] = {'fg': fg, 'bold': True} if selected else {'dim': True}
    tstyle: dict[str, Any] = {'fg': fg, 'bold': True} if selected else {}
    iw = w - 2  # inner content width
    rows: list[str] = []
    label = _truncate(title, iw) if iw > 0 else ''
    fill = max(0, iw - _wcswidth(label))
    rows.append(_styled('┌', **bstyle) + _styled(label, **tstyle)
                + _styled('─' * fill + '┐', **bstyle))
    for k in range(max(0, h - 2)):
        raw = lines[k] if k < len(lines) else ''
        if iw > 0:
            t = _sgr_truncate(raw, iw)
            content = t + ' ' * max(0, iw - _visible_width(t))
        else:
            content = ''
        rows.append(_styled('│', **bstyle) + content + _styled('│', **bstyle))
    if h >= 2:
        rows.append(_styled('└' + '─' * iw + '┘', **bstyle))
    return rows[:h]


def _active_tab_info(tree: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the current tab in the `kitty @ ls` tree, return {id, layout, nwin}.
    Prefer the globally focused tab (the kitten is launched from it; more
    accurate with multiple OS windows); fall back to any active tab."""
    def info(tab: dict[str, Any]) -> dict[str, Any]:
        return {'id': tab.get('id'), 'layout': tab.get('layout') or '',
                'nwin': len(tab.get('windows') or ())}
    for key in ('is_focused', 'is_active'):
        for osw in tree:
            for tab in osw.get('tabs') or ():
                if tab.get(key):
                    return info(tab)
    return None


def _tab_display_title(tab: dict[str, Any], wins: tuple) -> str:
    """Dedupe the tab title: return '' (hide it) when it duplicates the active
    window's title; only a custom title that differs from the window is
    returned. Tolerates activity/bell symbol prefixes."""
    tab_title = (tab.get('title') or '').strip()
    if not tab_title:
        return ''
    active_wt = ''
    for w in wins:
        if w.get('is_active') or w.get('is_focused'):
            active_wt = (w.get('title') or '').strip()
            break
    if not active_wt and wins:
        active_wt = (wins[0].get('title') or '').strip()
    # equal / substring either way (handles "✳ xxx" vs "xxx" decoration prefixes)
    if active_wt and (tab_title == active_wt or tab_title in active_wt or active_wt in tab_title):
        return ''
    return tab_title


def _build_items(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    multi_osw = len(tree) > 1
    items: list[dict[str, Any]] = []
    for oi, osw in enumerate(tree):
        for ti, tab in enumerate(osw.get('tabs') or ()):
            wins = tab.get('windows') or ()
            disp_title = _tab_display_title(tab, wins)
            tab_current = bool(tab.get('is_focused'))
            for w in wins:
                wid = w.get('id')
                if wid is None:
                    continue
                title = w.get('title') or ''
                proc = _proc(w)
                cwd = _shorten_cwd(w.get('cwd') or '')
                items.append({
                    'id': wid,
                    'osw_idx': oi,
                    'tab_idx': ti,
                    'multi_osw': multi_osw,
                    'tab_display_title': disp_title,
                    'tab_layout': tab.get('layout') or '',
                    'tab_nwin': len(wins),
                    'tab_is_current': tab_current,
                    'title': title,
                    'proc': proc,
                    'cwd': cwd,
                    'is_focused': bool(w.get('is_focused')),
                    'is_active': bool(w.get('is_active')),
                    'hay': ('%s %s %s %s' % (title, proc, cwd, tab.get('title') or '')).lower(),
                })
    return items


def _get_text(wid: int, ansi: bool) -> list[str]:
    """Capture window `wid`'s current screen via `kitty @ get-text`, returning
    OSC-stripped lines (SGR kept iff ansi). [] on any failure -> blank cell.
    `main` is the module-level KittenUI; its rc_fd is ready once main() runs."""
    cmd = ['get-text', '--match', 'id:%d' % wid, '--extent', 'screen']
    if ansi:
        cmd.append('--ansi')
    try:
        cp = main.remote_control(cmd, capture_output=True)
    except Exception:
        return []
    if getattr(cp, 'returncode', 1) != 0:
        return []
    raw = getattr(cp, 'stdout', b'') or b''
    text = raw.decode('utf-8', 'replace') if isinstance(raw, (bytes, bytearray)) else str(raw)
    lines = _strip_osc(text).split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return lines


class ChooseTree(Handler):

    def __init__(self, items: list[dict[str, Any]]):
        self.items = items
        self.filtered = list(items)
        self.query = ''
        self.top = 0
        self.result: int | None = None
        self.cur = next((i for i, it in enumerate(items) if it['is_focused']), 0)
        # wid -> OSC-stripped preview lines (pre-truncation; re-fit on resize).
        self.preview_cache: dict[int, list[str]] = {}

    def _preview_lines(self, wid: int) -> list[str]:
        """Cached per-window preview lines; one get-text round-trip per wid."""
        raw = self.preview_cache.get(wid)
        if raw is None:
            raw = _get_text(wid, PREVIEW_ANSI)
            self.preview_cache[wid] = raw
        return raw

    def initialize(self) -> None:
        self.cmd.set_cursor_visible(False)
        self.draw()

    def refilter(self) -> None:
        q = self.query.lower().strip()
        keep_id = self.filtered[self.cur]['id'] if self.filtered else None
        if q:
            terms = q.split()
            self.filtered = [it for it in self.items if all(t in it['hay'] for t in terms)]
        else:
            self.filtered = list(self.items)
        self.cur = next((i for i, it in enumerate(self.filtered) if it['id'] == keep_id), 0)
        self.cur = max(0, min(self.cur, len(self.filtered) - 1)) if self.filtered else 0

    def _flat_display(self) -> list[tuple[int | None, bool, str, str, bool]]:
        """Flatten into display rows: (window row index or None, is group header,
        head, tail, is current tab)."""
        out: list[tuple[int | None, bool, str, str, bool]] = []
        multi = bool(self.items and self.items[0]['multi_osw'])
        last_osw: int | None = None
        last_group: tuple[int, int] | None = None
        for i, it in enumerate(self.filtered):
            if multi and it['osw_idx'] != last_osw:
                out.append((None, True, 'OS window %d' % (it['osw_idx'] + 1), '', False))
                last_osw = it['osw_idx']
            g = (it['osw_idx'], it['tab_idx'])
            if g != last_group:
                if it['tab_display_title']:
                    head = 'tab %d: %s  (%s, %d win)' % (
                        it['tab_idx'] + 1, it['tab_display_title'], it['tab_layout'], it['tab_nwin'])
                else:
                    head = 'tab %d  (%s, %d win)' % (it['tab_idx'] + 1, it['tab_layout'], it['tab_nwin'])
                out.append((None, True, head, '', it['tab_is_current']))
                last_group = g
            marker = '●' if it['is_focused'] else ('○' if it['is_active'] else ' ')
            head = ' %s %s' % (marker, it['title'] or '(no title)')
            tail = '  ·  %s  ·  %s' % (it['proc'], it['cwd'])
            out.append((i, False, head, tail, False))
        return out

    def _render_group(self, head: str, is_current: bool, inner: int) -> str:
        """Render one group header row per TAB_SEPARATOR (width always = inner,
        so the box borders stay aligned)."""
        fg = CURRENT_TAB_COLOR if (is_current and CURRENT_TAB_COLOR) else None
        sep = TAB_SEPARATOR
        if sep == 'reverse':
            return _styled(_pad(head, inner), reverse=True, bold=True, fg=fg)
        if sep == 'underline':
            text = _truncate(head, inner)
            pad_sp = ' ' * max(0, inner - _wcswidth(text))
            return _styled(text, bold=True, underline='straight', fg=fg) + pad_sp
        if sep == 'rule':
            ruler = '═' if head.startswith('OS window') else '─'
            label = _truncate(head + '  ', inner)
            fillw = max(0, inner - _wcswidth(label))
            return _styled(label, bold=True, fg=fg) + (_styled(ruler * fillw, dim=True) if fillw else '')
        if sep == 'none':
            return _styled(_pad(head, inner), bold=True, fg=fg)
        # 'bar' (default): leading vertical bar ▌
        return _styled(_pad('▌ ' + head, inner), bold=True, fg=fg)

    def _render_rows(self, inner: int, list_h: int) -> list[str]:
        """Build the rows inside the modal box (padded + styled, all display
        width = inner)."""
        rows: list[str] = []
        rows.append(_styled(_pad('Search: ' + self.query + '▏', inner), bold=True))
        info = '%d/%d · ↑↓ ^n^p move · Enter jump · Esc cancel' % (len(self.filtered), len(self.items))
        if SHOW_PREVIEW:
            info += ' · ^r refresh'
        rows.append(_styled(_pad(info, inner), dim=True))
        flat = self._flat_display()
        sel = next((k for k, row in enumerate(flat) if row[0] == self.cur), 0)
        if sel < self.top:
            self.top = sel
        elif sel >= self.top + list_h:
            self.top = sel - list_h + 1
        self.top = max(0, min(self.top, max(0, len(flat) - list_h)))
        for idx, is_group, head, tail, is_current in flat[self.top:self.top + list_h]:
            if is_group:
                rows.append(self._render_group(head, is_current, inner))
            elif idx == self.cur:
                rows.append(_styled(_pad(head + tail, inner), reverse=True))
            else:
                h2, t2 = _truncate_pair(head, tail, inner)
                fillw = max(0, inner - _wcswidth(h2) - _wcswidth(t2))
                rows.append(h2 + (_styled(t2 + ' ' * fillw, dim=True) if (t2 or fillw) else ''))
        while len(rows) < 2 + list_h:
            rows.append(' ' * inner)
        return rows[:2 + list_h]

    def _split_body(self, avail: int) -> tuple[int, int]:
        """Divide the body height into (list_h, preview_h). preview_h == 0 means
        no preview/divider (pure list). Only splits when the list keeps
        LIST_MIN_ROWS and the preview gets PREVIEW_MIN_ROWS after one divider
        row; otherwise degrades to a pure list."""
        if not SHOW_PREVIEW or avail < LIST_MIN_ROWS + 1 + PREVIEW_MIN_ROWS:
            return max(1, avail), 0
        usable = avail - 1  # one row for the divider
        preview = max(PREVIEW_MIN_ROWS, round(usable * PREVIEW_RATIO))
        list_h = usable - preview
        if list_h < LIST_MIN_ROWS:
            list_h = LIST_MIN_ROWS
            preview = usable - list_h
        if preview < PREVIEW_MIN_ROWS:
            return max(1, avail), 0
        return list_h, preview

    def _render_divider(self, inner: int) -> str:
        """A dim titled rule between the list and the preview, naming the tab
        being previewed. Width is exactly inner (borders stay aligned)."""
        it = self.filtered[self.cur] if self.filtered else None
        if it:
            label = ' tab %d: %d window%s%s ' % (
                it['tab_idx'] + 1, it['tab_nwin'], '' if it['tab_nwin'] == 1 else 's',
                (' (%s)' % it['tab_layout']) if it['tab_layout'] else '')
        else:
            label = ' preview '
        lead = PREVIEW_DIVIDER * 2
        label = _truncate(label, max(0, inner - _wcswidth(lead)))
        fill = max(0, inner - _wcswidth(lead) - _wcswidth(label))
        return _styled(lead + label + PREVIEW_DIVIDER * fill, dim=True)

    def _render_preview(self, inner: int, preview_h: int) -> list[str]:
        """Render the selected window's tab as a grid of bordered window cells,
        the current selection highlighted. Returns exactly preview_h rows, each
        of display width inner."""
        blank = [' ' * inner for _ in range(preview_h)]
        if not self.filtered:
            return blank
        cur = self.filtered[self.cur]
        sel_id = cur['id']
        # every window of the selected window's tab, in ls order (from items, not
        # filtered: preview the whole tab even while the list is filtered)
        wins = [it for it in self.items
                if it['osw_idx'] == cur['osw_idx'] and it['tab_idx'] == cur['tab_idx']]
        if not wins:
            return blank
        n = len(wins)
        cols, rows, cell_w, cell_h, cap = _grid_dims(n, inner, preview_h)
        shown = wins[:cap]
        overflow = n - len(shown)
        body_h = max(0, cell_h - 2)
        cells: list[list[str]] = []
        for idx, it in enumerate(shown):
            title = 'win%d %s' % (idx + 1, it['proc'] or it['title'] or '?')
            if overflow and idx == len(shown) - 1:
                title = '+%d more · %s' % (overflow, title)
            content = self._preview_lines(it['id'])
            if body_h and len(content) > body_h:
                content = content[-body_h:]  # tail: prompt / latest output
            cells.append(_render_cell(title, content, cell_w, cell_h, it['id'] == sel_id))
        gap = ' ' * CELL_GAP
        out: list[str] = []
        for r in range(rows):
            row_cells = cells[r * cols:(r + 1) * cols]
            if not row_cells:
                break
            for k in range(cell_h):
                pieces = [c[k] if k < len(c) else ' ' * cell_w for c in row_cells]
                line = gap.join(pieces)
                line += ' ' * max(0, inner - _visible_width(line))
                out.append(line)
        out = out[:preview_h]
        while len(out) < preview_h:
            out.append(' ' * inner)
        return out

    def draw(self) -> None:
        self.cmd.clear_screen()
        rows, cols = self.screen_size.rows, self.screen_size.cols
        bw = min(cols, max(24, int(cols * BOX_W_RATIO)))
        bh = min(rows, max(6, int(rows * BOX_H_RATIO)))
        mx = max(0, (cols - bw) // 2)
        my = max(0, (rows - bh) // 2)
        left = ' ' * mx
        inner = bw - 2
        avail = max(1, bh - 4)  # minus border (2) minus search/info (2)
        list_h, preview_h = self._split_body(avail)
        body = self._render_rows(inner, list_h)
        if preview_h > 0:
            body.append(self._render_divider(inner))
            body.extend(self._render_preview(inner, preview_h))
        bar = _styled('│', dim=True)
        out: list[str] = ['' for _ in range(my)]
        title = '─ choose-tree '
        tfill = max(0, inner - _wcswidth(title))
        out.append(left + _styled('╭' + title + '─' * tfill + '╮', dim=True))
        for r in body:
            out.append(left + bar + r + bar)
        out.append(left + _styled('╰' + '─' * inner + '╯', dim=True))
        for ln in out:
            self.print(ln)

    def _move(self, delta: int) -> None:
        if not self.filtered:
            return
        self.cur = max(0, min(self.cur + delta, len(self.filtered) - 1))
        self.draw()

    def on_text(self, text: str, in_bracketed_paste: bool = False) -> None:
        self.query += text
        self.refilter()
        self.draw()

    def on_key(self, key_event: Any) -> None:
        if _RELEASE is not None and getattr(key_event, 'type', None) is _RELEASE:
            return
        if key_event.matches('esc') or key_event.matches('ctrl+c') or key_event.matches('ctrl+g'):
            self.quit_loop(1)
        elif key_event.matches('enter'):
            if self.filtered:
                self.result = int(self.filtered[self.cur]['id'])
            self.quit_loop(0)
        elif key_event.matches('down') or key_event.matches('ctrl+n'):
            self._move(1)
        elif key_event.matches('up') or key_event.matches('ctrl+p'):
            self._move(-1)
        elif key_event.matches('page_down'):
            self._move(max(1, int(self.screen_size.rows * BOX_H_RATIO) - 5))
        elif key_event.matches('page_up'):
            self._move(-max(1, int(self.screen_size.rows * BOX_H_RATIO) - 5))
        elif key_event.matches('home'):
            self.cur = 0
            self.draw()
        elif key_event.matches('end'):
            self.cur = max(0, len(self.filtered) - 1)
            self.draw()
        elif key_event.matches('backspace'):
            if self.query:
                self.query = self.query[:-1]
                self.refilter()
                self.draw()
        elif key_event.matches('ctrl+r'):
            # invalidate the previewed tab's window caches, then redraw (re-fetch)
            if self.filtered:
                cur = self.filtered[self.cur]
                for it in self.items:
                    if it['osw_idx'] == cur['osw_idx'] and it['tab_idx'] == cur['tab_idx']:
                        self.preview_cache.pop(it['id'], None)
            self.draw()

    def on_interrupt(self) -> None:
        self.quit_loop(1)

    def on_eot(self) -> None:
        self.quit_loop(1)

    def on_resize(self, screen_size: Any) -> None:
        super().on_resize(screen_size)
        self.draw()


@kitten_ui(allow_remote_control=True)
def main(args: list[str]) -> Any:
    try:
        cp = main.remote_control(['ls'], capture_output=True)
    except Exception as e:
        raise SystemExit(
            'choose-tree: failed to query the window list via remote control: %s\n'
            '@kitten_ui/remote_control may have changed after a kitty upgrade; '
            'see the notes at the top of this file.' % e
        )
    if getattr(cp, 'returncode', 1) != 0:
        err = (getattr(cp, 'stderr', b'') or b'')
        msg = err.decode('utf-8', 'replace') if isinstance(err, (bytes, bytearray)) else str(err)
        raise SystemExit('choose-tree: `kitty @ ls` failed: ' + (msg or 'unknown error'))
    tree = json.loads(cp.stdout)
    items = _build_items(tree)
    if not items:
        return None

    # Enlarge: temporarily switch the current tab to stack so the active window
    # (and this overlay on top of it) fills the whole tab. Only when the tab has
    # multiple windows and is not already stacked. The restore info is carried
    # back to handle_result via the return value.
    restore: dict[str, Any] | None = None
    if AUTO_MAXIMIZE:
        ati = _active_tab_info(tree)
        if ati and ati.get('id') is not None and ati['layout'] != 'stack' and ati['nwin'] > 1:
            try:
                main.remote_control(['goto-layout', '--match', 'id:%d' % ati['id'], 'stack'])
                restore = {'tab': ati['id'], 'layout': ati['layout']}
            except Exception:
                restore = None  # enlarge failed: keep running as-is, selection still works

    handler = ChooseTree(items)
    Loop().loop(handler)
    if handler.result is None:
        return {'wid': None, 'restore': restore} if restore else None
    return {'wid': handler.result, 'restore': restore}


@result_handler()
def handle_result(args: list[str], answer: Any, target_window_id: int, boss: Boss) -> None:
    # Accept both the old return (bare int) and the new one (dict)
    if isinstance(answer, dict):
        wid = answer.get('wid')
        restore = answer.get('restore')
    else:
        wid = answer
        restore = None

    # 1) Restore the original layout synchronously. This is not a focus op, so
    #    it won't be overridden by the focus restore that follows; it restores
    #    the ORIGINAL tab (the user may have jumped to a different tab).
    if restore and restore.get('layout'):
        try:
            tab = boss.tab_for_id(int(restore['tab']))
            if tab is not None:
                tab.goto_layout(restore['layout'])
        except Exception:
            pass

    if not wid:
        return
    wid = int(wid)

    def _jump(timer_id: int | None = None) -> None:
        # By now the overlay has closed and focus is restored to the original
        # window, so jumping here is the "last step" and won't be overridden.
        try:
            if boss.set_active_window(wid, switch_os_window_if_needed=True) is not None:
                return
        except Exception:
            pass
        try:
            active = boss.window_id_map.get(target_window_id)
            boss.call_remote_control(active, ('focus-window', '--match=id:%d' % wid))
        except Exception:
            pass

    # Defer to the next event-loop tick: run after the overlay closes and focus
    # is restored, so the jump isn't overridden.
    try:
        from kitty.fast_data_types import add_timer
        add_timer(_jump, 0, False)
    except Exception:
        _jump()
