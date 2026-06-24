---
name: Cinematic Storytelling
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1b1b1b'
  surface-container: '#1f1f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353535'
  on-surface: '#e2e2e2'
  on-surface-variant: '#d6c4ad'
  inverse-surface: '#e2e2e2'
  inverse-on-surface: '#303030'
  outline: '#9e8e7a'
  outline-variant: '#514534'
  surface-tint: '#ffba3e'
  primary: '#ffbd49'
  on-primary: '#432c00'
  primary-container: '#e5a00d'
  on-primary-container: '#593b00'
  inverse-primary: '#7f5700'
  secondary: '#c4c7cb'
  on-secondary: '#2d3134'
  secondary-container: '#464a4d'
  on-secondary-container: '#b5b9bc'
  tertiary: '#96ceff'
  on-tertiary: '#003351'
  tertiary-container: '#49b5ff'
  on-tertiary-container: '#004569'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdeae'
  primary-fixed-dim: '#ffba3e'
  on-primary-fixed: '#281900'
  on-primary-fixed-variant: '#604100'
  secondary-fixed: '#e0e3e7'
  secondary-fixed-dim: '#c4c7cb'
  on-secondary-fixed: '#181c1f'
  on-secondary-fixed-variant: '#43474a'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#91ccff'
  on-tertiary-fixed: '#001e31'
  on-tertiary-fixed-variant: '#004b73'
  background: '#131313'
  on-background: '#e2e2e2'
  surface-variant: '#353535'
typography:
  display-xl:
    fontFamily: Hanken Grotesk
    fontSize: 72px
    fontWeight: '800'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '800'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  safe-area-top: 64px
  safe-area-bottom: 48px
  gutter: 20px
  stack-xs: 4px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 24px
  stack-xl: 40px
---

## Brand & Style
The design system is engineered for high-impact, celebratory data visualization. It targets a tech-savvy audience that values media consumption and personal analytics. The emotional response is one of nostalgia and excitement—mimicking the "opening night" of a theatrical premiere.

The aesthetic blends **Glassmorphism** with **High-Contrast Bold** elements. It utilizes immersive 9:16 vertical layouts common in social "stories," focusing on high-energy transitions, vibrant background blurs, and crisp, legible data points. The interface is designed to disappear, allowing the user's media history and personal stats to take center stage.

## Colors
The palette is rooted in a "Theater Dark" philosophy. The primary background is absolute black (#000000) to maximize contrast on OLED mobile displays and create an infinite canvas effect. 

**Plex Orange** serves as the primary action and highlight color, used for CTA buttons and critical data highlights. Supporting gradients provide a shifting emotional "vibe" for different data categories (e.g., Music vs. Film). These gradients should be applied to background ambient lights or glassmorphic card borders to differentiate chapters in the user's narrative.

## Typography
The typography strategy prioritizes scale and hierarchy to create a cinematic feel. **Hanken Grotesk** is used for all display and headline levels; its contemporary, sharp geometric forms feel modern and premium. **Display XL** is reserved for hero statistics (e.g., total minutes watched).

**Inter** provides a functional counterpoint for body copy and metadata. It ensures legibility when displaying dense information like movie titles or technical stats. All labels utilize an uppercase, tracked-out style to evoke the feel of film credits and professional media metadata.

## Layout & Spacing
This design system utilizes a fixed 9:16 aspect ratio "Story" layout. Content is centered within a 4-column fluid grid with 20px gutters. 

Significant safe areas are maintained at the top (for the progress indicator) and bottom (for navigation and share actions). Vertical rhythm is established using a strict 8px baseline grid. Large "Display" elements should be positioned in the vertical center of the screen to ensure focus, while supplemental lists are anchored to the bottom third.

## Elevation & Depth
Depth is created through **Glassmorphism** rather than traditional drop shadows. Surfaces use a "Surface-Glass" technique:
- **Backdrop Blur:** 20px to 40px blur on container backgrounds.
- **Translucency:** 10-15% white or gray fills to catch the background color light.
- **Inner Borders:** 1px solid white stroke at 10% opacity on the top and left edges to simulate a "light catch" on the edge of the glass.

Higher elevation layers (like "Share" modals) use a darker overlay (Scrim) and more intense blur to pull the user's focus away from the background story.

## Shapes
The shape language is friendly but structured. Main story containers and interactive cards utilize a `rounded-xl` (1.5rem / 24px) corner radius to match the hardware curvature of modern high-end smartphones. 

Buttons and chips use a `rounded-full` (Pill) shape to distinguish them from structural content containers. Image assets (movie posters, artist photos) should maintain a `rounded-lg` (1rem / 16px) radius to feel cohesive within the larger glass containers.

## Components
### Progress Indicators
Segmented bars at the top of the screen. Active segments are white (#FFFFFF); inactive segments are white at 20% opacity. They should have a 4px height and 4px gap between segments.

### Hero Stat Cards
Glassmorphic containers featuring **Display XL** typography. These should animate in with a slight scale-up effect. Text should be white or the Primary Orange depending on the stat's importance.

### Ranking Lists
Used for "Top 5" styles. Each row features a large numeric index (Label MD), a 40px rounded image/avatar, and vertical stack for title and subtitle. Rows are separated by a 1px divider at 5% opacity.

### Action Buttons
Primary buttons use the Plex Orange (#E5A00D) with black text for maximum punch. Secondary buttons use a glass background with a white outline.

### Background Gradients
Dynamic mesh gradients that shift slowly (60s loop) to prevent static "burn-in" and maintain the celebratory energy of the experience.