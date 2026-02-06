import json
import plotly.graph_objects as go
import argparse


def load_sankey_data(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)


def create_figure(data, title='', width=1400, height=700):
    fig = go.Figure(go.Sankey(
        arrangement='snap',
        node=dict(
            pad=12,
            thickness=18,
            line=dict(color='#333', width=0.5),
            label=data['nodes'],
            color=data['colors'],
            x=data['node_x'],
            y=data['node_y'],
            hovertemplate='%{label}<extra></extra>'
        ),
        link=dict(
            source=data['sources'],
            target=data['targets'],
            value=data['values'],
            color=data['link_colors'],
            hovertemplate='%{source.label} → %{target.label}<br>%{value} violations<extra></extra>'
        )
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=1)),
        font=dict(size=13),
        height=height,
        width=width,
        paper_bgcolor='white',
        margin=dict(l=5, r=5, t=50, b=60)
    )

    headers = [
        (0.01, '<b>App Category</b>'),
        (0.30, '<b>Violation Type</b>'),
        (0.62, '<b>Data Type</b>'),
        (0.99, '<b>Destination</b>')
    ]
    for x, txt in headers:
        fig.add_annotation(x=x, y=1.04, xref='paper', yref='paper',
                          text=txt, showarrow=False, font=dict(size=12, family='Times New Roman'))

    legend = (
        "<b>Link Colors:</b> &nbsp;"
        "<span style='color:#4ECDC4'>━</span> Neglect/Omit &nbsp;&nbsp;"
        "<span style='color:#FF6B6B'>━</span> Contrary &nbsp;&nbsp;"
        "<span style='color:#FFE66D'>━</span> Incorrect &nbsp;&nbsp;"
        "<span style='color:#FFA07A'>━</span> Mismatched Entity &nbsp;&nbsp;"
        "<span style='color:#42A5F5'>━</span> 1st Party &nbsp;&nbsp;"
        "<span style='color:#EF5350'>━</span> 3rd Party"
    )
    fig.add_annotation(x=0.5, y=-0.05, xref='paper', yref='paper',
                      text=legend, showarrow=False, font=dict(size=10, family='Times New Roman'), align='center')

    return fig


def main():
    parser = argparse.ArgumentParser(description='Draw Sankey diagram from exported data')
    parser.add_argument('--data', default='violation_sankey_4col_v2_data.json',
                       help='Path to exported JSON data file')
    parser.add_argument('--output', default='violation_sankey_4col_v2.html',
                       help='Output HTML file path')
    parser.add_argument('--width', type=int, default=1400, help='Figure width')
    parser.add_argument('--height', type=int, default=700, help='Figure height')
    parser.add_argument('--title', default='', help='Figure title')

    args = parser.parse_args()

    print(f"Loading data from: {args.data}")
    sankey_data = load_sankey_data(args.data)

    print(f"Creating figure...")
    print(f"  Nodes: {len(sankey_data['nodes'])}")
    print(f"  Links: {len(sankey_data['sources'])}")

    fig = create_figure(sankey_data, title=args.title, width=args.width, height=args.height)

    print(f"Saving to: {args.output}")
    fig.write_html(args.output)
    print("Done!")


if __name__ == "__main__":
    main()
