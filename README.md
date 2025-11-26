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