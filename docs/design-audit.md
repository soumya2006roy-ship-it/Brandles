# BrandLens design audit

Audit date: 2026-10-25

The audit covers the shared visual system, page templates, demo, metadata and in-app copy. `docs/brandlens-proposal.md` remains the content source of truth; its punctuation and phrasing are intentionally preserved.

| Pattern | Location before rework | Planned replacement |
| --- | --- | --- |
| Translucent blurred header | `app/globals.css:63` | Opaque paper surface with a quiet border. |
| Large shared shadow token, used on multiple components | `app/globals.css:16,39,97,135,282,352` | Remove decorative shadows; use spacing, surface contrast and fine rules. |
| Rotated, shadowed graph card and dotted SVG backdrop | `app/globals.css:97`; `app/graph.tsx` | Align the graph to the page grid and keep only evidence-bearing links and labels. |
| Eyebrow and dot above the home headline | `app/page.tsx:9`; `app/globals.css:81-82` | Put a concrete headline first and move context below it. |
| Italic serif headline emphasis | `app/page.tsx:11,22,24,26,28`; `app/not-found.tsx:4`; `app/globals.css:86` | Use regular, non-italic display typography with no colored emphasis. |
| Generic equal-width process cards | `app/page.tsx:26`; `app/globals.css:147-151` | Use a numbered editorial sequence with varied row widths. |
| Equal-width feature cards | `app/features/page.tsx:9`; `app/globals.css` innovation grid rules | Use a single-column, source-led feature index and alternating evidence excerpts. |
| Decorative arrows and theme glyphs | `app/page.tsx`, `app/ui.tsx`, `app/demo/demo-experience.tsx`, `app/not-found.tsx` | Remove ornamental arrows; use text labels for theme controls and navigation. |
| Side stripe as the main finding/status treatment | `app/globals.css:261,286,326` and toast styles | Use plain labels, headings and full-width semantic text, with no colored left-edge card motif. |
| Serif italics plus DM Sans pairing | `app/layout.tsx:3,10-11` | Use IBM Plex Sans with Newsreader, both via `next/font`, swap display and Latin subsets. |
| Punctuation dash used as sentence punctuation | `app/contact/contact-form.tsx:37`, `app/demo/demo-experience.tsx:71`, `app/opengraph-image.tsx:3`, `app/manifest.ts:5`, `app/api/contact/route.ts:79,118` | Replace punctuation dashes with commas, colons or full stops. Preserve functional minus signs and source proposal text. |
| Skeleton shimmer animation | `app/globals.css:305` | Use static, reduced-motion-safe loading blocks with a restrained color fill. |
| Rotating/dashed graph lines and orbit | `app/globals.css:104,115-116` | Keep graph motion subtle and short, with the existing reduced-motion override. |
| Dense card layout obscures the evidence trail | `app/page.tsx`, `app/features/page.tsx`, `app/globals.css` | Prioritise the approved passage, finding, comparison and 20% versus 30% conflict in a consistent editorial layout. |
| No build-time theme contrast audit | No implementation | Add a Node script that reads both CSS themes, prints WCAG ratios for declared text/background pairs, and fails on a missed threshold. |

## Before and after

Before: the site uses familiar gradient-era startup patterns such as a blurred sticky header, oversized shadows, rotated cards, a decorative dot texture, italicized display emphasis, arrows and repeated equal-width cards. Evidence exists in the content but does not consistently lead the visual hierarchy.

After: (to be completed after the redesign and contrast verification.)

## Verification

- (to be completed after the redesign.)

## Limitations

The proposal describes a product concept. The site demo remains a seeded local simulation. The Hindi checker and platform previews remain simple rule-based prototypes. No production product capability is implied by the visuals.
