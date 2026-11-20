"""Clear the active window's scrollback and show what it freed in an overlay.

Bound in kitty.conf:  map kitty_mod+alt+l kitten clear_scrollback.py

A no_ui kitten: handle_result runs inside the kitty process itself, so it can
read the window's Screen directly and measure kitty's own memory before/after.
It calls the same Screen.clear_scrollback() as the built-in
`clear_terminal scrollback active` action (kitty/boss.py), which drops both the
in-window scrollback and the pager history; what is on screen is kept.

The result is shown the same way as the reload-config prompt (ctrl+a>shift+r):
an overlay on top of the window, closed with Enter.
"""
from kittens.tui.handler import result_handler

PROMPT = 'printf "%s\\n" "$@"; echo; read -r -p "Press Enter to exit" _'


def main(args: list[str]) -> None:
    pass


def _anon_mem_kib() -> tuple[int, int] | None:
    """kitty's own anonymous memory (RSS, swap) in KiB; None where /proc is absent (macOS)."""
    rss = swap = 0
    try:
        with open('/proc/self/status') as f:
            for line in f:
                if line.startswith('RssAnon:'):
                    rss = int(line.split()[1])
                elif line.startswith('VmSwap:'):
                    swap = int(line.split()[1])
    except OSError:
        return None
    return rss, swap


def _mib(kib: int) -> str:
    return f'{kib / 1024:,.0f}'


@result_handler(no_ui=True)
def handle_result(args: list[str], answer: None, target_window_id: int, boss) -> None:
    w = boss.window_id_map.get(target_window_id)
    if w is None:
        return
    lines = w.screen.historybuf.count
    before = _anon_mem_kib()
    w.screen.clear_scrollback()
    after = _anon_mem_kib()
    if lines:
        msg = [
            'kitty scrollback cleared.',
            '',
            f'window:  {w.title}',
            f'cleared: {lines:,} lines of scrollback + pager history (on-screen content kept)',
        ]
        if before and after:
            msg.append(f'kitty:   RSS {_mib(before[0])} -> {_mib(after[0])} MiB, '
                       f'swap {_mib(before[1])} -> {_mib(after[1])} MiB')
    else:
        msg = ['kitty scrollback was already empty.', '', f'window:  {w.title}']
    boss.launch(f'--next-to=id:{w.id}', '--type=overlay', '--title=scrollback cleared',
                'sh', '-c', PROMPT, 'sh', *msg)
