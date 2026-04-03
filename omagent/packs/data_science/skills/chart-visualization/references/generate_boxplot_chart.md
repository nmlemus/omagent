# generate_boxplot_chart — Boxplot Chart

## Functional Overview
Displays the distribution of data based on a five-number summary, helping to identify outliers and understand data spread.

## Input Fields
### Required
- `data`: array<object>, each containing `category` (string) and `value` (number). Optional `group` (string) for comparing multiple groups.

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
