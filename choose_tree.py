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
    if width <= 0:
        return ''
    if _wcswidth(text) <= width:
        return text
    out: list[str] = []
    w = 0
    for ch in text:
        cw = _wcswidth(ch)
        if cw < 0:
            cw = 0
        if w + cw > width - 1:
            out.append('…')
            break
        out.append(ch)
        w += cw
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


class ChooseTree(Handler):

    def __init__(self, items: list[dict[str, Any]]):
        self.items = items
        self.filtered = list(items)
        self.query = ''
        self.top = 0
        self.result: int | None = None
        self.cur = next((i for i, it in enumerate(items) if it['is_focused']), 0)

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

    def draw(self) -> None:
        self.cmd.clear_screen()
        rows, cols = self.screen_size.rows, self.screen_size.cols
        bw = min(cols, max(24, int(cols * BOX_W_RATIO)))
        bh = min(rows, max(6, int(rows * BOX_H_RATIO)))
        mx = max(0, (cols - bw) // 2)
        my = max(0, (rows - bh) // 2)
        left = ' ' * mx
        inner = bw - 2
        list_h = max(1, bh - 4)  # minus border (2) minus search/info (2)
        body = self._render_rows(inner, list_h)
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
