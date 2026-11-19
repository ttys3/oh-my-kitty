# Oh my kitty!

the kitty config for tmux users

the shortcuts (key bindings) is heavily inspired by [Oh my tmux!](https://github.com/gpakosz/.tmux#bindings)

mainly used under Linux

## new features

### session support

kitty >= 0.43 finally support session save and allow you to switch between sessions.

we now support save current session to the session file via single keypress <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>s</kbd>.

you 'll need to create a default session file for the first time.

```shell
touch ~/.config/kitty/default.kitty-session
```

TODO: more session management features like:
1. switch between sessions
2. delete session
3. rename session
4. list sessions

## usage

```shell
# backup your config first
# mv ~/.config/kitty  ~/.config/kitty.bak

git clone https://github.com/ttys3/oh-my-kitty.git ~/.config/kitty

touch ~/.config/kitty/default.kitty-session # create a default session file
```

## customization

### override default config

> ⚠️ **Breaking change:** the local override file was renamed from the per-user
> `${USER}.local.conf` (e.g. `alice.local.conf`) to a fixed name **`my.local.conf`**, and it
> is now pulled in with `globinclude` instead of `include`. If you already had a
> `${USER}.local.conf`, rename it after pulling this update — otherwise your overrides
> **silently stop loading** (`globinclude` skips the missing old file without any warning):
>
> ```shell
> mv ~/.config/kitty/${USER}.local.conf ~/.config/kitty/my.local.conf
> ```

You can override any default setting in a git-ignored local config file: **`my.local.conf`**. It is pulled in at the end of `kitty.conf` via `globinclude my.local.conf`, so any settings in it override the defaults — letting you customize kitty without touching the tracked config, which keeps the base config easy to update. Because it uses `globinclude`, kitty silently skips the file when it does not exist, so creating it is optional.

A tracked template `my.local.conf.example` ships with the repo — copy it to get started:

```shell
cp ~/.config/kitty/my.local.conf.example ~/.config/kitty/my.local.conf
```

**Example: Override font family and size**

```conf
# ~/.config/kitty/my.local.conf
font_family Lilex
font_size 13.0
```

You can override any kitty setting in this file. Common customizations include:
- `font_family` - Change the font
- `font_size` - Adjust font size
- `background_opacity` - Set transparency
- `background_image` - Set background image
- And any other kitty configuration option

After creating or modifying `my.local.conf`, reload the config with <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>R</kbd> or restart kitty.

### per-OS config (opt-in)

Not enabled by default. When you share one config between Linux and macOS but some
settings must differ per platform, pull in a per-OS file from your `my.local.conf`:

```conf
# ~/.config/kitty/my.local.conf
include ${KITTY_OS}.local.conf
```

When processing `include`, kitty expands `${KITTY_OS}` to `linux`, `macos` or `bsd`, so this
loads `linux.local.conf` or `macos.local.conf` (relative to the config dir). Both match the
`/*.local.conf` rule in `.gitignore`, so they stay machine-local like `my.local.conf`.

**Example: remote control socket**

`kitty.conf` already sets `allow_remote_control yes`, but without `listen_on` the
`kitty @` commands only work from inside a kitty window. With a socket you can also
control kitty from outside, e.g. `kitty @ --to <socket> ls` to find the window that
runs a given process, then `focus-window --match id:<N>`. The socket syntax differs
per OS, which is exactly what the per-OS file is for:

```conf
# ~/.config/kitty/linux.local.conf
# Abstract UNIX socket: lives in the kernel, not on disk, so nothing is left behind
# and it is easy to find: grep kitty /proc/net/unix
# Note: it has no file permissions — any process in the same network namespace can
# connect to it.
listen_on unix:@kitty
```

```conf
# ~/.config/kitty/macos.local.conf
# macOS has no abstract sockets: `unix:@kitty` starts fine but silently never listens.
# Use a file socket instead. A relative path is resolved against $TMPDIR, i.e.
# /var/folders/…/T/ (per-user, mode 700).
listen_on unix:kitty
```

When `listen_on` is set in the config file, kitty appends `-<kitty_pid>` to the socket name, so the
actual address is `unix:@kitty-<pid>` on Linux and `unix:$TMPDIR/kitty-<pid>` on macOS.
Inside a kitty window it is exported as `$KITTY_LISTEN_ON`:

```shell
# Linux
kitty @ --to unix:@kitty-$(pgrep -xo kitty) ls
# macOS
kitty @ --to unix:$(ls "$TMPDIR"kitty-* | head -1) ls
```

`listen_on` is read only at startup: reloading the config does not open the socket, so
restart kitty after adding it.

## suggested shell alias

```shell
alias icat="kitten icat"
alias s="kitten ssh"
alias d="kitten diff"
```

## Shortcuts

key name see <https://github.com/xkbcommon/libxkbcommon/blob/master/include/xkbcommon/xkbcommon-keysyms.h>

or using `kitty --debug-input` to detect keysyms

### config

keybindings explain:

<kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>R</kbd> means:
press `ctrl` + `a` in the same time, release and then, press R (`shift`+`r`)

| key                                       | description   |
| ----------------------------------------- | ------------- |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>R</kbd> | reload config |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>E</kbd> | edit config |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>D</kbd> | debug config  |

### session

| key                                       | description                         |
| ----------------------------------------- | ----------------------------------- |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>s</kbd> | save current layout to session file |

### tab

| key                                           | description        |
| --------------------------------------------- | ------------------ |
| <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>←</kbd> | goto previous tab        |
| <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>→</kbd> | goto next tab           |
| <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>,</kbd> | move tab backward  |
| <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>.</kbd> | move tab forward   |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>,</kbd>     | change tab title   |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>c</kbd>     | create new tab     |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>x</kbd>     | close window / tab |

### os window

| key                          | description       |
| ---------------------------- | ----------------- |
| <kbd>ctrl</kbd>+<kbd>q</kbd> | quit kitty        |
| <kbd>f11</kbd>               | toggle fullscreen |

### window

| key                                                         | description                  |
| ----------------------------------------------------------- | ---------------------------- |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>-</kbd>                   | horizontal split with cwd    |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>shift</kbd>+<kbd>-</kbd>  | horizontal split             |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>\\</kbd>                  | vertial split with cwd       |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>shift</kbd>+<kbd>\\</kbd> | vertial split                |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>x</kbd>                   | close window                 |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>z</kbd>                   | zoom (maxmize) window        |
| <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>r</kbd>               | resize window                |
| <kbd>ctrl</kbd>+<kbd>←</kbd>                                | goto left window               |
| <kbd>ctrl</kbd>+<kbd>→</kbd>                                | goto right window              |
| <kbd>ctrl</kbd>+<kbd>↑</kbd>                                | goto up window                 |
| <kbd>ctrl</kbd>+<kbd>↓</kbd>                                | goto down window               |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>h</kbd>                   | goto left window               |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>l</kbd>                   | goto right window              |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>k</kbd>                   | goto up window                 |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>j</kbd>                   | goto down window               |
| <kbd>shift</kbd>+<kbd>←</kbd>                               | move current window to left  |
| <kbd>shift</kbd>+<kbd>→</kbd>                               | move current window to right |
| <kbd>shift</kbd>+<kbd>↑</kbd>                               | move current window to up    |
| <kbd>shift</kbd>+<kbd>↓</kbd>                               | move current window to down  |
| <kbd>alt</kbd>+<kbd>n</kbd>                                 | resize window narrower       |
| <kbd>alt</kbd>+<kbd>w</kbd>                                 | resize window wider          |
| <kbd>alt</kbd>+<kbd>u</kbd>                                 | resize window taller         |
| <kbd>alt</kbd>+<kbd>d</kbd>                                 | resize window shorter        |
| <kbd>ctrl</kbd>+<kbd>home</kbd>                             | resize window reset          |

### font

| key                          | description     |
| ---------------------------- | --------------- |
| <kbd>ctrl</kbd>+<kbd>=</kbd> | font size +     |
| <kbd>ctrl</kbd>+<kbd>-</kbd> | font size -     |
| <kbd>ctrl</kbd>+<kbd>0</kbd> | font size reset |

### misc

| key                                                       | description                                                                          |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>t</kbd>                 | kitten themes                                                                        |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>space</kbd>             | copy pasting with hints like [tmux-thumbs](https://github.com/fcsonline/tmux-thumbs) |
| <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>ctrl</kbd>+<kbd>a</kbd> | send real <kbd>ctrl</kbd>+<kbd>a</kbd> (emacs shortcut <kbd>Home</kbd>)              |

## session restore

this config has been enabled by default in this config.

you can use <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>s</kbd> to save the current session to the session file.

which will save the current session to the session file under `~/.config/kitty/session.conf`

> kitty has long had support for [Sessions](https://sw.kovidgoyal.net/kitty/sessions/), aka simple text files where you can define what tabs, windows and programs you wish to run in kitty. Now in addition to that kitty has the ability to [create and switch between sessions](https://sw.kovidgoyal.net/kitty/sessions/#goto-session) with a single keypress and 
> also to manually setup some tabs/windows in kitty and [save it as a session file](https://sw.kovidgoyal.net/kitty/sessions/#complex-sessions), for seamless and intuitive session file creation.


## kitty docs

Keyboard shortcuts <https://sw.kovidgoyal.net/kitty/conf/#keyboard-shortcuts>

The launch command syntax reference <https://sw.kovidgoyal.net/kitty/launch/#syntax-reference>

## troubleshooting

kitty ask me where to save the session file?

you can just create a empty file for the first time:

```shell
touch ~/.config/kitty/default.kitty-session
```

and then you can use <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>s</kbd> to save the current session to the session file, it will not ask you again.

## fonts

### macOS

macOS user fonts is under `~/Library/Fonts`

Iosevka Term is a good font for terminal, you can install it via:

```shell
brew install --cask font-iosevka-term-nerd-font
```

Iosevka is a good font for coding, you can install it via:

```shell
brew install --cask font-iosevka
```

Lilex is a good font for coding, you can install it via:

```shell
brew install --cask font-lilex
```

### Linux

donwload and put the fonts to `~/.local/share/fonts` then run `fc-cache -f -v` to refresh the font cache.