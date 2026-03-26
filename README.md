# PeitPE

A script to modify WinPE(s) for my needs.

Currently supports modifying latest Hiren's BootCD PE as the base.

> [!WARNING]
> This project is vibe-coded, expect hidden bugs and slow maintenance.

## Installation

This project uses [uv](https://github.com/astral-sh/uv), to get started:

```
git clone https://github.com/teppyboy/PeitPE
cd PeitPE
sudo uv run python ./build.py
```

Note that [gsudo](...) or [sudo in Windows](...) is needed, as this uses DISM and it requires Administrator permissions to use.

## License

[MIT](./LICENSE)
