# generate_fishbone_diagram — Fishbone Diagram

## Functional Overview
Also known as an Ishikawa diagram, used for cause-and-effect analysis to identify root causes of a problem.

## Input Fields
### Required
- `data`: object, required, must provide a root node `name`. Can extend recursively via `children` (array<object>). Max recommended depth is 3.

### Optional
- `style.backgroundColor`: string, background color.
- `style.palette`: string[], custom color palette.
- `style.texture`: string, default `default`, options: `default`/`rough`.
- `theme`: string, default `default`, options: `default`/`academy`/`dark`.
- `width`: number, default `600`.
- `height`: number, default `400`.
- `title`: string, chart title, default empty.
- `axisXTitle`: string, X-axis title (if applicable).
- `axisYTitle`: string, Y-axis title (if applicable).

## Usage Recommendations
Ensure data types are consistent. For large datasets, consider aggregating or sampling before generation to maintain visual clarity.

## Return Result
- Returns the generated chart image URL and metadata.
