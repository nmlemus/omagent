# generate_district_map — District Map

## Functional Overview
Visualizes data on a regional map (China). Suitable for displaying geographic distributions by province, city, or district.

## Input Fields
### Required
- `title`: string, required (≤16 chars), describes the map theme.
- `data`: object, required. Contains region config.
- `data.name`: string, required, location name in China.

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
