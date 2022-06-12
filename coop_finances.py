"""
We want an interctive finance chart for monthyl costs, to see affordability based on factors

Costs:
* Utilities
* Insurance
* Property Taxes

Based on factors
* Sale price
* part that is land cost
* Number of roms


For each factor, have line chart, of value vs monthly cost
"""

import dataclasses
import pathlib
import typing

import altair as alt
import IPython.display

__all__ = ["Variable", "Range", "generate_plots"]
WIDTH = 800

# @dataclasses.dataclass
# class Expr:
#     e: str

#     def __repr__(self):
#         return self.e


@dataclasses.dataclass
class Range:
    """
    like range but allows floats
    """

    start: float
    stop: float
    step: float


@dataclasses.dataclass
class Variable:
    title: str
    label: str
    options: Range | tuple[list, list]
    default: int
    tp: typing.Literal["$", "%", "#", "O", "s"]

    @property
    def axis_format(self):
        return {
            "$": "$.2s",
            "%": ".1%",
            "#": ".2s",
            "O": ".1s",
            "s": "",
        }[self.tp]

    @property
    def mark_options(self):
        return (
            {
                "type": "ordinal",
                "sort": self.options[1],
            }
            if isinstance(self.options, tuple)
            else {"type": "quantitative"}
        )


def generate_plots(fn, subtitle, **variables):
    IPython.display.display(generate_plot(fn, subtitle, variables))


def generate_plot(fn, subtitle, variables):
    # https://altair-viz.github.io/gallery/multiline_tooltip.html
    selections = {
        k: alt.selection_single(
            fields=[k],
            init={k: v.default},
            bind=alt.binding_range(
                min=v.options.start,
                max=v.options.stop,
                step=v.options.step,
                name=f"{v.title} {v.label}",
            )
            if isinstance(v.options, Range)
            else alt.binding_radio(
                options=v.options[0],
                labels=v.options[1],
                name=f"{v.title} {v.label}",
            ),
        )
        for k, v in variables.items()
    }

    current_values = {k: getattr(selections[k], k)[0] for k, v in variables.items()}

    monthly_cost_categories = fn(**current_values)

    monthly_cost = None
    for k, v in monthly_cost_categories.items():
        monthly_cost = alt.expr.if_(alt.datum.category == k, v, monthly_cost)

    base_pie_chart = alt.Chart(
        alt.InlineData([{"category": k} for k in monthly_cost_categories.keys()])
    ).transform_calculate(cost=monthly_cost)

    base_pie_chart_with_theta = base_pie_chart.encode(
        theta=alt.Theta("cost:Q", stack=True),
        tooltip=["category:N", "cost:Q"],
        color=alt.Color(
            "category:N",
            legend=None
            # legend=alt.Legend(
            # orient='left',
            # title='Monthly Costs per Room',
            # direction='vertical',
            # columns=4
            # )
        ),
    )

    pie_arc_chart = base_pie_chart_with_theta.mark_arc(
        innerRadius=30, outerRadius=120
    ).encode()
    pie_text_chart = base_pie_chart_with_theta.mark_text(
        radius=155, size=15, align="center"
    ).encode(alt.Text("category:N"))

    pie_sum_text_chart = base_pie_chart.mark_text(radius=0, size=20).encode(
        alt.Text("cost:Q", aggregate="sum", format="$.2s")
    )
    chart = (
        pie_arc_chart
        + pie_text_chart
        + pie_sum_text_chart.properties(
            width=900,
            height=400,
            title={"text": "Price per room per month", "fontSize": 25},
        )
    )
    for selection in reversed(selections.values()):
        chart = chart.add_selection(selection)
    for i in range(len(subtitle)):
        for k, v in variables.items():
            subtitle[i] = subtitle[i].replace(k, v.title)
    chart = (
        chart.properties(
            title={
                "text": f"👇 Drag the sliders to change 🏡 values ❣️",
                "anchor": "start",
                "fontSize": 40,
                "subtitle": subtitle,
                "align": "left",
            }
        )
        .configure_axis(grid=True)
        .configure_legend(
            titleFontSize=20,
            labelFontSize=16,
            titleLimit=600,
        )
        .configure_axis(titleFontSize=20, labelFontSize=15)
        .configure_view(
            # https://stackoverflow.com/questions/46515327/how-do-i-remove-the-border-around-a-vega-lite-plot
            stroke="transparent"
        )
    )
    pathlib.Path("simple.json").write_text(chart.to_json(validate=False))
    return chart
