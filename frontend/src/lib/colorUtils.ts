/**
 * Shiftly Color & Theme Utilities
 * Provides WCAG-compliant contrast-aware color derivation and curated palette definitions.
 */

export interface RgbColor {
  r: number;
  g: number;
  b: number;
}

export interface HslColor {
  h: number;
  s: number;
  l: number;
}

export interface AccentTokens {
  accent: string;
  accentHover: string;
  accentActive: string;
  accentSoft: string;
  accentSoftHover: string;
  accentBorder: string;
  accentText: string;
  accentRing: string;
  accentContrast: string;
}

/**
 * Parses a 3-digit or 6-digit hex string into RGB.
 */
export function hexToRgb(hex: string): RgbColor | null {
  const cleanHex = hex.replace(/^#/, '').trim();
  if (!/^[0-9a-fA-F]{3}$|^[0-9a-fA-F]{6}$/.test(cleanHex)) {
    return null;
  }

  let fullHex = cleanHex;
  if (cleanHex.length === 3) {
    fullHex = cleanHex.split('').map(c => c + c).join('');
  }

  const num = parseInt(fullHex, 16);
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

/**
 * Converts RGB [0..255] to HSL (h: 0..360, s: 0..100, l: 0..100).
 */
export function rgbToHsl(r: number, g: number, b: number): HslColor {
  const rNorm = r / 255;
  const gNorm = g / 255;
  const bNorm = b / 255;

  const max = Math.max(rNorm, gNorm, bNorm);
  const min = Math.min(rNorm, gNorm, bNorm);
  const delta = max - min;

  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (delta !== 0) {
    s = l > 0.5 ? delta / (2 - max - min) : delta / (max + min);
    switch (max) {
      case rNorm:
        h = ((gNorm - bNorm) / delta + (gNorm < bNorm ? 6 : 0)) * 60;
        break;
      case gNorm:
        h = ((bNorm - rNorm) / delta + 2) * 60;
        break;
      case bNorm:
        h = ((rNorm - gNorm) / delta + 4) * 60;
        break;
    }
  }

  return {
    h: Math.round(h),
    s: Math.round(s * 100),
    l: Math.round(l * 100),
  };
}

/**
 * Converts HSL (h: 0..360, s: 0..100, l: 0..100) to RGB [0..255].
 */
export function hslToRgb(h: number, s: number, l: number): RgbColor {
  const hNorm = (h % 360) / 360;
  const sNorm = Math.min(100, Math.max(0, s)) / 100;
  const lNorm = Math.min(100, Math.max(0, l)) / 100;

  if (sNorm === 0) {
    const val = Math.round(lNorm * 255);
    return { r: val, g: val, b: val };
  }

  const hue2rgb = (p: number, q: number, t: number) => {
    let tAdj = t;
    if (tAdj < 0) tAdj += 1;
    if (tAdj > 1) tAdj -= 1;
    if (tAdj < 1 / 6) return p + (q - p) * 6 * tAdj;
    if (tAdj < 1 / 2) return q;
    if (tAdj < 2 / 3) return p + (q - p) * (2 / 3 - tAdj) * 6;
    return p;
  };

  const q = lNorm < 0.5 ? lNorm * (1 + sNorm) : lNorm + sNorm - lNorm * sNorm;
  const p = 2 * lNorm - q;

  const r = Math.round(hue2rgb(p, q, hNorm + 1 / 3) * 255);
  const g = Math.round(hue2rgb(p, q, hNorm) * 255);
  const b = Math.round(hue2rgb(p, q, hNorm - 1 / 3) * 255);

  return { r, g, b };
}

/**
 * Converts RGB to 6-character hex code.
 */
export function rgbToHex(r: number, g: number, b: number): string {
  const toHex = (n: number) => Math.min(255, Math.max(0, Math.round(n))).toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/**
 * Calculates WCAG relative luminance of an sRGB color.
 */
export function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map(val => {
    const s = val / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Calculates the WCAG contrast ratio between two luminance values.
 */
export function getContrastRatio(lum1: number, lum2: number): number {
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Curated Palettes conforming to the Shiftly Design Direction.
 */
export const CURATED_PALETTES = {
  blue: {
    name: 'Blue',
    primary: '#2563EB',
    light: {
      accent: '#2563EB',
      accentHover: '#1D4ED8',
      accentActive: '#1E40AF',
      accentSoft: '#EFF6FF',
      accentSoftHover: '#DBEAFE',
      accentBorder: '#93C5FD',
      accentText: '#1D4ED8',
      accentRing: 'rgba(37, 99, 235, 0.25)',
      accentContrast: '#FFFFFF',
    },
    dark: {
      accent: '#3B82F6',
      accentHover: '#2563EB',
      accentActive: '#1D4ED8',
      accentSoft: 'rgba(59, 130, 246, 0.15)',
      accentSoftHover: 'rgba(59, 130, 246, 0.25)',
      accentBorder: 'rgba(147, 197, 253, 0.35)',
      accentText: '#60A5FA',
      accentRing: 'rgba(59, 130, 246, 0.35)',
      accentContrast: '#FFFFFF',
    },
  },
  cyan: {
    name: 'Cyan',
    primary: '#0891B2',
    light: {
      accent: '#0891B2',
      accentHover: '#0E7490',
      accentActive: '#155E75',
      accentSoft: '#ECFEFF',
      accentSoftHover: '#CFFAFE',
      accentBorder: '#67E8F9',
      accentText: '#0E7490',
      accentRing: 'rgba(8, 145, 178, 0.25)',
      accentContrast: '#FFFFFF',
    },
    dark: {
      accent: '#06B6D4',
      accentHover: '#0891B2',
      accentActive: '#0E7490',
      accentSoft: 'rgba(6, 182, 212, 0.15)',
      accentSoftHover: 'rgba(6, 182, 212, 0.25)',
      accentBorder: 'rgba(103, 232, 249, 0.35)',
      accentText: '#22D3EE',
      accentRing: 'rgba(6, 182, 212, 0.35)',
      accentContrast: '#FFFFFF',
    },
  },
  violet: {
    name: 'Violet',
    primary: '#7C3AED',
    light: {
      accent: '#7C3AED',
      accentHover: '#6D28D9',
      accentActive: '#5B21B6',
      accentSoft: '#F5F3FF',
      accentSoftHover: '#EDE9FE',
      accentBorder: '#C4B5FD',
      accentText: '#6D28D9',
      accentRing: 'rgba(124, 58, 237, 0.25)',
      accentContrast: '#FFFFFF',
    },
    dark: {
      accent: '#8B5CF6',
      accentHover: '#7C3AED',
      accentActive: '#6D28D9',
      accentSoft: 'rgba(139, 92, 246, 0.15)',
      accentSoftHover: 'rgba(139, 92, 246, 0.25)',
      accentBorder: 'rgba(196, 181, 253, 0.35)',
      accentText: '#A78BFA',
      accentRing: 'rgba(139, 92, 246, 0.35)',
      accentContrast: '#FFFFFF',
    },
  },
  purple: {
    name: 'Purple',
    primary: '#9333EA',
    light: {
      accent: '#9333EA',
      accentHover: '#7E22CE',
      accentActive: '#6B21A8',
      accentSoft: '#FAF5FF',
      accentSoftHover: '#F3E8FF',
      accentBorder: '#D8B4FE',
      accentText: '#7E22CE',
      accentRing: 'rgba(147, 51, 234, 0.25)',
      accentContrast: '#FFFFFF',
    },
    dark: {
      accent: '#A855F7',
      accentHover: '#9333EA',
      accentActive: '#7E22CE',
      accentSoft: 'rgba(168, 85, 247, 0.15)',
      accentSoftHover: 'rgba(168, 85, 247, 0.25)',
      accentBorder: 'rgba(216, 180, 254, 0.35)',
      accentText: '#C084FC',
      accentRing: 'rgba(168, 85, 247, 0.35)',
      accentContrast: '#FFFFFF',
    },
  },
  emerald: {
    name: 'Emerald',
    primary: '#059669',
    light: {
      accent: '#059669',
      accentHover: '#047857',
      accentActive: '#065F46',
      accentSoft: '#ECFDF5',
      accentSoftHover: '#D1FAE5',
      accentBorder: '#6EE7B7',
      accentText: '#047857',
      accentRing: 'rgba(5, 150, 105, 0.25)',
      accentContrast: '#FFFFFF',
    },
    dark: {
      accent: '#10B981',
      accentHover: '#059669',
      accentActive: '#047857',
      accentSoft: 'rgba(16, 185, 129, 0.15)',
      accentSoftHover: 'rgba(16, 185, 129, 0.25)',
      accentBorder: 'rgba(110, 231, 183, 0.35)',
      accentText: '#34D399',
      accentRing: 'rgba(16, 185, 129, 0.35)',
      accentContrast: '#FFFFFF',
    },
  },
  teal: {
    name: 'Teal',
    primary: '#0D9488',
    light: {
      accent: '#0D9488',
      accentHover: '#0F766E',
      accentActive: '#115E59',
      accentSoft: '#F0FDFA',
      accentSoftHover: '#CCFBF1',
      accentBorder: '#5EEAD4',
      accentText: '#0F766E',
      accentRing: 'rgba(13, 148, 136, 0.25)',
      accentContrast: '#FFFFFF',
    },
    dark: {
      accent: '#14B8A6',
      accentHover: '#0D9488',
      accentActive: '#0F766E',
      accentSoft: 'rgba(20, 184, 166, 0.15)',
      accentSoftHover: 'rgba(20, 184, 166, 0.25)',
      accentBorder: 'rgba(94, 234, 212, 0.35)',
      accentText: '#2DD4BF',
      accentRing: 'rgba(20, 184, 166, 0.35)',
      accentContrast: '#FFFFFF',
    },
  },
  amber: {
    name: 'Amber',
    primary: '#D97706',
    light: {
      accent: '#D97706',
      accentHover: '#B45309',
      accentActive: '#92400E',
      accentSoft: '#FFFBEB',
      accentSoftHover: '#FEF3C7',
      accentBorder: '#FCD34D',
      accentText: '#B45309',
      accentRing: 'rgba(217, 119, 6, 0.25)',
      accentContrast: '#FFFFFF',
    },
    dark: {
      accent: '#F59E0B',
      accentHover: '#D97706',
      accentActive: '#B45309',
      accentSoft: 'rgba(245, 158, 11, 0.15)',
      accentSoftHover: 'rgba(245, 158, 11, 0.25)',
      accentBorder: 'rgba(252, 211, 77, 0.35)',
      accentText: '#FBBF24',
      accentRing: 'rgba(245, 158, 11, 0.35)',
      accentContrast: '#0F172A',
    },
  },
  rose: {
    name: 'Rose',
    primary: '#E11D48',
    light: {
      accent: '#E11D48',
      accentHover: '#BE123C',
      accentActive: '#9F1239',
      accentSoft: '#FFF1F2',
      accentSoftHover: '#FFE4E6',
      accentBorder: '#FDA4AF',
      accentText: '#BE123C',
      accentRing: 'rgba(225, 29, 72, 0.25)',
      accentContrast: '#FFFFFF',
    },
    dark: {
      accent: '#F43F5E',
      accentHover: '#E11D48',
      accentActive: '#BE123C',
      accentSoft: 'rgba(244, 63, 94, 0.15)',
      accentSoftHover: 'rgba(244, 63, 94, 0.25)',
      accentBorder: 'rgba(253, 164, 175, 0.35)',
      accentText: '#FB7185',
      accentRing: 'rgba(244, 63, 94, 0.35)',
      accentContrast: '#FFFFFF',
    },
  },
};

export type CuratedAccentKey = keyof typeof CURATED_PALETTES;

/**
 * Derives a complete set of accessible, contrast-checked accent tokens
 * from any arbitrary base hex color.
 */
export function deriveAccentPalette(baseHex: string, isDark: boolean): AccentTokens {
  const rgb = hexToRgb(baseHex) || { r: 37, g: 99, b: 235 };
  const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
  const baseLuminance = getLuminance(rgb.r, rgb.g, rgb.b);

  // Determine high-contrast text on top of the primary accent (buttons, primary CTA)
  const contrastOnAccent = baseLuminance > 0.45 ? '#0F172A' : '#FFFFFF';

  if (!isDark) {
    // LIGHT MODE DERIVATION
    // 1. Primary Accent
    const primaryHex = rgbToHex(rgb.r, rgb.g, rgb.b);

    // 2. Hover & Active (darken slightly for tactile click feedback)
    const hoverHsl = { ...hsl, l: Math.max(15, hsl.l - 7) };
    const hoverRgb = hslToRgb(hoverHsl.h, hoverHsl.s, hoverHsl.l);
    const hoverHex = rgbToHex(hoverRgb.r, hoverRgb.g, hoverRgb.b);

    const activeHsl = { ...hsl, l: Math.max(10, hsl.l - 14) };
    const activeRgb = hslToRgb(activeHsl.h, activeHsl.s, activeHsl.l);
    const activeHex = rgbToHex(activeRgb.r, activeRgb.g, activeRgb.b);

    // 3. Soft Background (very pale tint with high lightness)
    const softHsl = { ...hsl, s: Math.min(85, Math.max(30, hsl.s)), l: 96 };
    const softRgb = hslToRgb(softHsl.h, softHsl.s, softHsl.l);
    const softHex = rgbToHex(softRgb.r, softRgb.g, softRgb.b);

    const softHoverHsl = { ...hsl, s: Math.min(85, Math.max(30, hsl.s)), l: 92 };
    const softHoverRgb = hslToRgb(softHoverHsl.h, softHoverHsl.s, softHoverHsl.l);
    const softHoverHex = rgbToHex(softHoverRgb.r, softHoverRgb.g, softHoverRgb.b);

    // 4. Soft Border (clear readable outline around soft pills/badges)
    const borderHsl = { ...hsl, s: Math.min(75, Math.max(35, hsl.s)), l: 80 };
    const borderRgb = hslToRgb(borderHsl.h, borderHsl.s, borderHsl.l);
    const borderHex = rgbToHex(borderRgb.r, borderRgb.g, borderRgb.b);

    // 5. Accent Text: Must meet WCAG AA (4.5:1) against both white (#FFFFFF) and soft background
    let textL = Math.min(42, hsl.l);
    let textRgb = hslToRgb(hsl.h, Math.min(95, Math.max(50, hsl.s)), textL);
    let textLum = getLuminance(textRgb.r, textRgb.g, textRgb.b);
    let contrast = getContrastRatio(1.0, textLum); // against white

    while (contrast < 4.5 && textL > 10) {
      textL -= 2;
      textRgb = hslToRgb(hsl.h, Math.min(95, Math.max(50, hsl.s)), textL);
      textLum = getLuminance(textRgb.r, textRgb.g, textRgb.b);
      contrast = getContrastRatio(1.0, textLum);
    }
    const textHex = rgbToHex(textRgb.r, textRgb.g, textRgb.b);

    // 6. Focus Ring
    const ring = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.25)`;

    return {
      accent: primaryHex,
      accentHover: hoverHex,
      accentActive: activeHex,
      accentSoft: softHex,
      accentSoftHover: softHoverHex,
      accentBorder: borderHex,
      accentText: textHex,
      accentRing: ring,
      accentContrast: contrastOnAccent,
    };
  } else {
    // DARK MODE DERIVATION
    // 1. Primary Accent (ensure it's not too dark on dark surface)
    const darkAccentL = Math.max(48, Math.min(65, hsl.l));
    const darkAccentRgb = hslToRgb(hsl.h, hsl.s, darkAccentL);
    const darkAccentHex = rgbToHex(darkAccentRgb.r, darkAccentRgb.g, darkAccentRgb.b);

    // 2. Hover & Active
    const hoverHsl = { ...hsl, l: Math.max(35, darkAccentL - 6) };
    const hoverRgb = hslToRgb(hoverHsl.h, hoverHsl.s, hoverHsl.l);
    const hoverHex = rgbToHex(hoverRgb.r, hoverRgb.g, hoverRgb.b);

    const activeHsl = { ...hsl, l: Math.max(25, darkAccentL - 12) };
    const activeRgb = hslToRgb(activeHsl.h, activeHsl.s, activeHsl.l);
    const activeHex = rgbToHex(activeRgb.r, activeRgb.g, activeRgb.b);

    // 3. Soft Background (translucent layer over dark surface)
    const soft = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.15)`;
    const softHover = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.25)`;

    // 4. Soft Border
    const border = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.35)`;

    // 5. Accent Text: Must meet WCAG AA (4.5:1) against dark surface #0F172A (luminance ~0.008)
    const darkSurfaceLum = getLuminance(15, 23, 42);
    let textL = Math.max(60, hsl.l);
    let textRgb = hslToRgb(hsl.h, Math.min(100, Math.max(50, hsl.s)), textL);
    let textLum = getLuminance(textRgb.r, textRgb.g, textRgb.b);
    let contrast = getContrastRatio(textLum, darkSurfaceLum);

    while (contrast < 4.5 && textL < 90) {
      textL += 2;
      textRgb = hslToRgb(hsl.h, Math.min(100, Math.max(50, hsl.s)), textL);
      textLum = getLuminance(textRgb.r, textRgb.g, textRgb.b);
      contrast = getContrastRatio(textLum, darkSurfaceLum);
    }
    const textHex = rgbToHex(textRgb.r, textRgb.g, textRgb.b);

    // 6. Focus Ring
    const ring = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.35)`;

    return {
      accent: darkAccentHex,
      accentHover: hoverHex,
      accentActive: activeHex,
      accentSoft: soft,
      accentSoftHover: softHover,
      accentBorder: border,
      accentText: textHex,
      accentRing: ring,
      accentContrast: contrastOnAccent,
    };
  }
}
