# generate_word_cloud_chart — Word Cloud Chart

## Functional Overview
Visualizes word frequency, with word size proportional to its value.

## Input Fields
### Required
- `data`: array<object>, each record containing `text` (string) and `value` (number).

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
