# generate_flow_diagram — Flow Diagram

## Functional Overview
Visualizes steps in a process or system flow using nodes and connecting lines.

## Input Fields
### Required
- `data`: object, required, contains nodes and edges.
- `data.nodes`: array<object>, at least 1 item with a unique `name`.
- `data.edges`: array<object>, at least 1 item containing `source` and `target` (string), optional `name`.

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
