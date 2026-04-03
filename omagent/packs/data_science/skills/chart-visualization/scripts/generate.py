#!/usr/bin/env python3

import sys
import json
import os
import urllib.request
import urllib.error
import uuid
import re

CHART_TYPE_MAP = {
    "generate_area_chart": "area",
    "generate_bar_chart": "bar",
    "generate_boxplot_chart": "boxplot",
    "generate_column_chart": "column",
    "generate_district_map": "district-map",
    "generate_dual_axes_chart": "dual-axes",
    "generate_fishbone_diagram": "fishbone-diagram",
    "generate_flow_diagram": "flow-diagram",
    "generate_funnel_chart": "funnel",
    "generate_histogram_chart": "histogram",
    "generate_line_chart": "line",
    "generate_liquid_chart": "liquid",
    "generate_mind_map": "mind-map",
    "generate_network_graph": "network-graph",
    "generate_organization_chart": "organization-chart",
    "generate_path_map": "path-map",
    "generate_pie_chart": "pie",
    "generate_pin_map": "pin-map",
    "generate_radar_chart": "radar",
    "generate_sankey_chart": "sankey",
    "generate_scatter_chart": "scatter",
    "generate_treemap_chart": "treemap",
    "generate_venn_chart": "venn",
    "generate_violin_chart": "violin",
    "generate_word_cloud_chart": "word-cloud",
}

def get_vis_request_server():
    return os.environ.get("VIS_REQUEST_SERVER", "https://antv-studio.alipay.com/api/gpt-vis")

def get_service_identifier():
    return os.environ.get("SERVICE_ID")

def http_post(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_message = e.read().decode('utf-8')
        raise Exception(f"HTTP {e.code}: {error_message}")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")

def generate_chart_url(chart_type, options):
    url = get_vis_request_server()
    payload = {
        "type": chart_type,
        "source": "chart-visualization-creator",
        **options
    }

    data = http_post(url, payload)

    if not data.get("success"):
        raise Exception(data.get("errorMessage", "Unknown error"))

    return data.get("resultObj")

def generate_map(tool, input_data):
    url = get_vis_request_server()
    payload = {
        "serviceId": get_service_identifier(),
        "tool": tool,
        "input": input_data,
        "source": "chart-visualization-creator"
    }

    data = http_post(url, payload)

    if not data.get("success"):
        raise Exception(data.get("errorMessage", "Unknown error"))

    return data.get("resultObj")

def download_image(url, output_dir, prefix):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            image_data = response.read()

        filename = f"{prefix}_{uuid.uuid4().hex[:6]}.png"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "wb") as f:
            f.write(image_data)

        return filepath
    except Exception as e:
        return f"Failed to download ({e}). Web URL: {url}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate.py <spec_json_or_file> [output_dir]", file=sys.stderr)
        sys.exit(1)

    spec_arg = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."

    # Ensure output dir exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    try:
        if os.path.exists(spec_arg):
            with open(spec_arg, 'r', encoding='utf-8') as f:
                spec = json.load(f)
        else:
            spec = json.loads(spec_arg)
    except Exception as e:
        print(f"Error parsing spec: {str(e)}", file=sys.stderr)
        sys.exit(1)

    specs = spec if isinstance(spec, list) else [spec]

    for item in specs:
        tool = item.get("tool")
        args = item.get("args", {})

        if not tool:
            print(f"Error: 'tool' field missing in spec: {json.dumps(item)}", file=sys.stderr)
            continue

        chart_type = CHART_TYPE_MAP.get(tool)
        if not chart_type:
            print(f"Error: Unknown tool '{tool}'", file=sys.stderr)
            continue

        is_map_chart_tool = tool in ["generate_district_map", "generate_path_map", "generate_pin_map"]

        try:
            if is_map_chart_tool:
                result = generate_map(tool, args)
                if result and result.get("content"):
                    for content_item in result["content"]:
                        if content_item.get("type") == "text":
                            text_output = content_item.get("text")
                            # Try to extract the static image URL for map
                            match = re.search(r"Static map preview and download URL: (https://\S+)", text_output)
                            if match:
                                img_url = match.group(1)
                                local_path = download_image(img_url, output_dir, chart_type)
                                print(f"Saved locally to: {local_path}")
                                print(f"Full details:
{text_output}")
                            else:
                                print(text_output)
                else:
                    print(json.dumps(result))
            else:
                url = generate_chart_url(chart_type, args)
                local_path = download_image(url, output_dir, chart_type)
                print(f"Saved locally to: {local_path}")
        except Exception as e:
            print(f"Error generating chart for {tool}: {str(e)}", file=sys.stderr)

if __name__ == "__main__":
    main()
