# Subtitle Fonts

This directory contains font files used for subtitle rendering in WomCast.

## Included Fonts

### Noto Sans (Google Fonts)
- **License**: SIL Open Font License 1.1
- **Coverage**: Latin, Greek, Cyrillic, CJK (Chinese, Japanese, Korean), Arabic, Hebrew, Thai, and more
- **Files**:
  - `NotoSans-Regular.ttf` - Regular weight
  - `NotoSans-Bold.ttf` - Bold weight
  - `NotoSansCJK-Regular.ttf` - CJK (Chinese, Japanese, Korean) characters
  - `NotoSansArabic-Regular.ttf` - Arabic script

### Liberation Sans (Red Hat)
- **License**: SIL Open Font License 1.1
- **Coverage**: Latin, Greek, Cyrillic (metrics-compatible with Arial/Helvetica)
- **Files**:
  - `LiberationSans-Regular.ttf` - Regular weight
  - `LiberationSans-Bold.ttf` - Bold weight

## Font Fallback Strategy

The subtitle rendering uses the following font stack:

```css
font-family: 'Noto Sans', 'Liberation Sans', 'Arial', 'Helvetica', sans-serif;
```

1. **Noto Sans**: Primary font with extensive Unicode coverage
2. **Liberation Sans**: Fallback for systems without Noto Sans
3. **Arial/Helvetica**: System fonts on Windows/macOS
4. **sans-serif**: Generic fallback

## CJK Character Support

For Chinese, Japanese, and Korean subtitles, use:

```css
font-family: 'Noto Sans CJK', 'Noto Sans', sans-serif;
```

## License Information

### SIL Open Font License 1.1

Both Noto Sans and Liberation Sans are licensed under the SIL Open Font License 1.1, which permits:
- Free use for personal and commercial purposes
- Modification and redistribution
- Embedding in applications

Full license text: https://openfontlicense.org/

## Font Sources

- **Noto Sans**: https://fonts.google.com/noto/specimen/Noto+Sans
- **Liberation Sans**: https://github.com/liberationfonts/liberation-fonts

## Installation Note

For production deployments, consider self-hosting fonts rather than using CDNs to ensure:
1. Faster load times (no external requests)
2. Offline functionality
3. Privacy (no third-party tracking)
4. Reliability (no CDN downtime)

Current setup: Fonts are bundled with the frontend build and served locally.
