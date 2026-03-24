# AGENTS.md

## Project Overview

**PeitPE Builder** is a pure Python tool for modifying Windows PE ISOs. It automates the process of downloading, extracting, modifying, and rebuilding bootable Windows PE ISOs with updated applications and customizations.

## Tech Stack

- **Language**: Python 3.10+
- **Package Manager**: uv (fast Python package installer and resolver)
- **Dependencies**: requests, tqdm, beautifulsoup4
- **External Tools**: oscdimg, 7-Zip, DISM (Windows system tools)

## Project Structure

```
peitpe-builder/
├── build.py              # Main entry point (CLI)
├── peitpe/               # Core package
│   ├── config.py         # Configuration management
│   ├── prerequisites.py  # Tool discovery & validation
│   ├── iso_downloader.py # ISO download with resume
│   ├── iso_extractor.py  # ISO extraction via 7-Zip
│   ├── wim_manager.py    # WIM mount/unmount (DISM)
│   ├── app_manager.py    # App injection into WIM
│   ├── wallpaper.py      # Wallpaper replacement
│   ├── iso_builder.py    # ISO building (oscdimg)
│   └── helpers/          # Helper utilities
│       ├── downloader.py # Download with progress
│       ├── github_api.py # GitHub release API
│       └── archiver.py   # 7-Zip wrapper
├── apps/                 # App configuration JSON
│   ├── updates.json      # Apps to update
│   └── additions.json    # New apps to add
├── config.json           # Main configuration
└── assets/               # Wallpaper and resources
```

## Development Commands

```bash
# Install dependencies
uv sync

# Run the builder
uv run build.py [options]

# Run with options
uv run build.py --skip-download --skip-extract
uv run build.py --force-download
uv run build.py --help
```

## Build Pipeline

The builder executes these steps in order:

1. **Download ISO** - Fetch latest Windows PE ISO
2. **Prerequisites** - Verify tools (oscdimg, 7-Zip, DISM)
3. **Extract ISO** - Extract ISO contents using 7-Zip
4. **Update Apps** - Download/update existing applications (injected into ISO directory)
5. **Add Apps** - Inject new applications (injected into ISO directory)
6. **Mount WIM** - Mount boot.wim (only if wallpaper replacement needed)
7. **Replace Wallpaper** - Customize WinPE wallpaper (inside WIM)
8. **Unmount WIM** - Commit changes to WIM
9. **Build ISO** - Create new bootable ISO

**Important**: Apps are injected into the ISO directory (`peit/iso/Programs/`), NOT into the WIM. The WIM is only mounted for wallpaper replacement.

## Configuration

### config.json
Main configuration with paths and settings:
- `SourceISO` - Path to source ISO
- `WorkDir` - Working directory for extracted files
- `MountDir` - WIM mount point
- `OutputISO` - Output ISO path
- `WimFile` - WIM file path within ISO
- `WallpaperSource` - Custom wallpaper path

### apps/*.json
App definitions with:
- `name`, `description`, `enabled`
- `source` - "direct" or "github"
- `download_url` - Direct download URL
- `owner`, `repo`, `asset_pattern` - For GitHub releases
- `type` - "zip", "7z", "exe"
- `extract_sub_dir` - Subdirectory to extract
- `target_path` - Target path in ISO (relative to ISO root, e.g., `\Programs\AppName`)

## Code Conventions

### Module Structure
- Each major function has its own module
- Helper utilities in `helpers/` subpackage
- All modules use type hints
- Dataclasses for configuration objects

### Error Handling
- Raise `RuntimeError` for expected failures
- Include context and remediation steps
- Clean up resources on failure
- Provide manual recovery instructions

### External Tools
- Use `subprocess.run()` with `capture_output=True`
- Pass arguments as list (never shell=True)
- Use `encoding="mbcs"` for Windows output
- Check return codes and provide clear errors

### Progress Display
- Use tqdm for download progress
- Print status messages with prefixes:
  - `[*]` - Information
  - `[OK]` - Success
  - `[WARN]` - Warning
  - `[SKIP]` - Skipped
  - `[FAIL]` - Failure
  - `[+]` - Created/Added

### Path Handling
- Use `pathlib.Path` for all paths
- Resolve relative paths against project root
- Handle Windows backslashes properly
- Support paths with spaces

## Important Notes

### Administrator Required
The script must run as Administrator for:
- DISM mount/unmount operations
- takeown and icacls commands
- Writing to protected system files

### Windows Only
This tool is Windows-specific:
- Uses DISM for WIM operations
- Uses oscdimg for ISO building
- Registry access for tool discovery
- takeown/icacls for permissions

### Large Files
- ISO files can be 1GB+
- Downloads support resume
- SHA-256 verification on completion
- Checksum mismatch triggers re-download

### Error Recovery
If build fails mid-process:
1. Check error message for instructions
2. WIM may still be mounted - unmount manually:
   ```cmd
   dism /Unmount-Image /MountDir:"path" /discard
   ```
3. Partial downloads in `peit/cache/`
4. Extracted files in `peit/iso/`

## Testing

When modifying code:
1. Run `uv run build.py --help` to verify imports
2. Test individual modules with uv
3. Check for type errors in IDE
4. Verify subprocess calls handle Windows paths

## Adding New Features

### Adding a New App
1. Add entry to `apps/updates.json` or `apps/additions.json`
2. Set `enabled: true`
3. Provide download URL or GitHub repo info
4. Specify extraction type and target path

### Adding a New Module
1. Create module in `peitpe/`
2. Follow existing code conventions
3. Import in `build.py` if needed
4. Add step to build pipeline

### Modifying Build Pipeline
1. Edit `build.py` main() function
2. Use invoke_step() for error handling
3. Pass config object to new modules
4. Update CLI arguments if needed
