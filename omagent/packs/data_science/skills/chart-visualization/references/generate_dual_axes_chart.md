# generate_dual_axes_chart — Dual Axes Chart

## Functional Overview
Displays two different metrics with different scales on the same chart using two Y-axes.

## Input Fields
### Required
- `categories`: string[], X-axis labels in order.
- `series`: array<object>, each item contains `type` ('column' or 'line') and `data` (number array matching categories length). Optional `axisYTitle` (string).

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
