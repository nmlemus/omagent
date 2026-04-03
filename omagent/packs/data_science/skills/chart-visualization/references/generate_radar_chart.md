# generate_radar_chart — Radar Chart

## Functional Overview
Displays multivariate data in the form of a two-dimensional chart of three or more quantitative variables represented on axes starting from the same point.

## Input Fields
### Required
- `data`: array<object>, each record containing `name` (string) and `value` (number), optional `group` (string).

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
