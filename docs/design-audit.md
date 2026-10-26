# BrandLens design audit

Audit date: 2026-10-25

The audit covers the shared visual system, page templates, metadata and in-app copy. `docs/brandlens-proposal.md` remains the content source of truth; its punctuation and phrasing are intentionally preserved.

| Pattern | Location before rework | Planned replacement |
| --- | --- | --- |
| Translucent blurred header | `app/globals.css:63` | Opaque paper surface with a quiet border. |
| Large shared shadow token, used on multiple components | `app/globals.css:16,39,97,135,282,352` | Remove decorative shadows; use spacing, surface contrast and fine rules. |
| Rotated, shadowed graph card and dotted SVG backdrop | `app/globals.css:97`; `app/graph.tsx` | Align the graph to the page grid and keep only evidence-bearing links and labels. |
| Eyebrow and dot above the home headline | `app/page.tsx:9`; `app/globals.css:81-82` | Put a concrete headline first and move context below it. |
| Italic serif headline emphasis | `app/page.tsx:11,22,24,26,28`; `app/not-found.tsx:4`; `app/globals.css:86` | Use regular, non-italic display typography with no colored emphasis. |
| Generic equal-width process cards | `app/page.tsx:26`; `app/globals.css:147-151` | Use a numbered editorial sequence with varied row widths. |
| Equal-width feature cards | `app/features/page.tsx:9`; `app/globals.css` innovation grid rules | Use a single-column, source-led feature index and alternating evidence excerpts. |
| Decorative arrows and theme glyphs | `app/(marketing)/page.tsx`, `app/ui.tsx`, `app/not-found.tsx` | Remove ornamental arrows; use text labels for theme controls and navigation. |
| Side stripe as the main finding/status treatment | `app/globals.css:261,286,326` and toast styles | Use plain labels, headings and full-width semantic text, with no colored left-edge card motif. |
| Serif italics plus DM Sans pairing | `app/layout.tsx:3,10-11` | Use IBM Plex Sans with Newsreader, both via `next/font`, swap display and Latin subsets. |
| Punctuation dash used as sentence punctuation | `app/contact/contact-form.tsx:37`, `app/opengraph-image.tsx:3`, `app/manifest.ts:5`, `app/api/contact/route.ts:79,118` | Replace punctuation dashes with commas, colons or full stops. Preserve functional minus signs and source proposal text. |
| Skeleton shimmer animation | `app/globals.css:305` | Use static, reduced-motion-safe loading blocks with a restrained color fill. |
| Rotating/dashed graph lines and orbit | `app/globals.css:104,115-116` | Keep graph motion subtle and short, with the existing reduced-motion override. |
| Dense card layout obscures the evidence trail | `app/page.tsx`, `app/features/page.tsx`, `app/globals.css` | Prioritise the approved passage, finding, comparison and 20% versus 30% conflict in a consistent editorial layout. |
| No build-time theme contrast audit | No implementation | Add a Node script that reads both CSS themes, prints WCAG ratios for declared text/background pairs, and fails on a missed threshold. |

## Before and after

Before: the site uses familiar gradient-era startup patterns such as a blurred sticky header, oversized shadows, rotated cards, a decorative dot texture, italicized display emphasis, arrows and repeated equal-width cards. Evidence exists in the content but does not consistently lead the visual hierarchy.

After: the home page opens with a concrete campaign-review claim and account entry points. The campaign graph uses labelled, evidence-bearing links. Process and capability content read as editorial rows. The palette has opaque surfaces, fine rules, semantic severity labels and regular display typography. The Hindi checker and platform previews remain labelled rule-based prototypes.

## Verification

- `npm run lint`, `npm run typecheck`, `npm run build`, and `npm run contrast-check` pass after the final visual changes. The production build runs the contrast checker before Next.js.
- Search across `app`, `site.config.ts`, and text assets in `public`: zero decorative gradient, backdrop blur, shadow, dotted graph pattern, em dash, arrow glyph, Lucide import, or hover opacity matches.
- Emoji-range scan across app and public source text: zero matches. Font import scan: IBM Plex Sans and Newsreader only, both loaded with `next/font`, Latin subset, explicit weights and `display: "swap"`.
- The copy scan for ` - ` returns only CSS sizing expressions and subtraction in scroll/rate-limit calculations. There are no sentence-punctuation uses in app copy, metadata, JSON-LD, or social image text.
- No scroll-reveal, custom cursor or pointer-tracking code remains. Hover, active and visible-focus states are explicit. Interactive transitions are 130 ms; reduced motion disables them and the conflict-line animation.
- Lucide import count: 0. The graph is drawn with inline SVG because its paths carry the campaign evidence relationships. No icon package is needed.

### WCAG contrast results

The build script reads the light and dark tokens from `app/globals.css` and checks each declared text/background and boundary pair. Text uses a 4.5:1 minimum, primary text uses 7:1 and visible boundaries/focus use 3:1.

| Token role | Minimum light ratio | Minimum dark ratio | Threshold | Result |
| --- | ---: | ---: | ---: | --- |
| Primary text | 13.80:1 | 12.51:1 | 7:1 | Pass |
| Secondary text | 4.87:1 | 8.16:1 | 4.5:1 | Pass |
| Accent text | 4.88:1 | 7.44:1 | 4.5:1 | Pass |
| Success, warning and error text | 6.44:1 | 7.85:1 | 4.5:1 | Pass |
| Dark-section text | 14.87:1 | 14.87:1 | 7:1 | Pass |
| Dark-section accent | 5.82:1 | 5.82:1 | 4.5:1 | Pass |
| Button labels, including hover | 6.51:1 | 6.11:1 | 4.5:1 | Pass |
| Visible boundaries | 3.17:1 | 3.81:1 | 3:1 | Pass |
| Focus indicator | 4.88:1 | 7.44:1 | 3:1 | Pass |

## Limitations

The proposal describes the product concept. The website uses account and organisation workflows rather than fictional records. The Hindi checker and platform previews remain simple rule-based prototypes. Contrast checks cover the declared token pairs, not every arbitrary color combination a future component could introduce. Marketing illustrations do not represent live organisation data.
