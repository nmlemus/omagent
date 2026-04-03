# generate_network_graph — Network Graph

## Functional Overview
Visualizes complex relationships and connections between entities (nodes).

## Input Fields
### Required
- `data`: object, required. Contains nodes and edges.
- `data.nodes`: array<object>, unique `name` required.
- `data.edges`: array<object>, contains `source` and `target` (string).

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
