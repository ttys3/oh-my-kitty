# Oh my kitty!

the kitty config for tmux users

the shortcuts (key bindings) is heavily inspired by [Oh my tmux!](https://github.com/gpakosz/.tmux#bindings)

mainly used under Linux

## usage

```shell
# backup your config first
# mv ~/.config/kitty  ~/.config/kitty.bak

git clone https://github.com/ttys3/oh-my-kitty.git ~/.config/kitty
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

> if you have used <kbd>ctrl</kbd>+<kbd>a</kbd>><kbd>s</kbd> generate the session, you do not need this.

you can create your session file under `~/.config/kitty`, let's say the filename is `session.conf`

change `startup_session none` to `startup_session session.conf`

create `session.conf` like this:

```ini
new_tab home
layout splits
cd ~
launch zsh
focus

new_tab work
cd ~/work
launch zsh

new_tab nvim
cd ~/.config/nvim
launch zsh

new_tab go
cd ~/repo/go
launch zsh

new_tab rust
cd ~/repo/rust
launch zsh
```

## kitty docs

Keyboard shortcuts <https://sw.kovidgoyal.net/kitty/conf/#keyboard-shortcuts>

The launch command syntax reference <https://sw.kovidgoyal.net/kitty/launch/#syntax-reference>

## troubleshooting

the behavior of `listen_on` differs from the behavior of `--listen-on` cli flag.

the cli one is exactly the same.

the config file one will append a random postfix to the socket name, this is strange logic.

start kitty:
```
kitty -o allow_remote_control=yes --listen-on unix:/run/user/1000/kitty.sock
```

on other terminal:

```
 kitty @ --to unix:/run/user/1000/kitty.sock launch --type=tab --cwd "/tmp" --tab-title "My Tab" --keep-focus bash
```
