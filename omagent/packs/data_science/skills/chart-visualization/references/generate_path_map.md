# generate_path_map — Path Map

## Functional Overview
Visualizes routes or paths on a geographic map (China).

## Input Fields
### Required
- `title`: string, required (≤16 chars).
- `data`: array<object>, at least 1 route object.
- `data[].data`: string[], required, array of ordered POI names in China.

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
