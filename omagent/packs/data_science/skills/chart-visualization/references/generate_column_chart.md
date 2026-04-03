# generate_column_chart — Column Chart

## Functional Overview
Displays categorical data using vertical columns, useful for comparing quantities across categories or over time.

## Input Fields
### Required
- `data`: array<object>, each containing at least `category` (string) and `value` (number). Provide `group` (string) for grouped or stacked columns.

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
