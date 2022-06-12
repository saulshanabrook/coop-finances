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
    tp: typing.Literal['$', '%', '#', 'O', 's']

    @property
    def axis_format(self):
        return {
            '$': '$.2s',
            '%': '.1%',
            '#': '.2s',
            'O': '.1s',
            's': '',
        }[self.tp]

    @property
    def mark_options(self):
        return {
            'type': 'ordinal',
            'sort': self.options[1],
        } if isinstance(self.options, tuple) else {
            'type': 'quantitative'
        }

    
def generate_plots(fn, subtitle, **variables):
    IPython.display.display(generate_plot(fn, subtitle, variables, simple=True))
    IPython.display.display(generate_plot(fn, subtitle, variables, simple=False))

def generate_plot(fn, subtitle, variables, simple):
    sequences = {
        k: alt.sequence(v.options.start, v.options.stop, v.options.step, as_=k)
            if isinstance(v.options, Range)
            else alt.InlineData(values=[{k: o} for o in v.options[0]])
        for k, v in variables.items()
    }
    
    # https://altair-viz.github.io/gallery/multiline_tooltip.html
    selections = {
        k: (alt.selection_single if simple else alt.selection)(
            fields=[k],
            init={k: v.default},
            **({
                "bind": alt.binding_range(
                    min=v.options.start,
                    max=v.options.stop,
                    step=v.options.step,
                    name=f"{v.title} {v.label}",
                ) if isinstance(v.options, Range) else alt.binding_radio(
                    options=v.options[0],
                    labels=v.options[1],
                    name=f"{v.title} {v.label}"
                )
            } if simple else {
                "type": 'single',
                # https://bl.ocks.org/cwickham/6f9d41c401e73dd7ba5c42ff14814ab5
                "on": 'mousedown, [mousedown, mouseup] > mousemove, touchstart, [touchstart, touchend] > touchmove',
                "nearest": True,
            })
        )
        for k, v in variables.items()
    }

    current_values = {
        k: getattr(selections[k], k)[0]
        for k, v in variables.items()
    }
    if not simple:
        line_charts = {
            k: alt.Chart(sequences[k]).transform_calculate(
                # Take the sum of all the returned monthly costs
                monthly_cost=sum(fn(**{
                    # if the input is this variable, use the data field, otherwise use the last selection for it
                    inner_k: getattr(alt.datum, inner_k) if inner_k == k else current_values[inner_k]
                    for inner_k in variables.keys()
                }).values())
            ).mark_line().encode(
                alt.X(
                    field=k,
                    axis=alt.Axis(
                        format=v.axis_format,
                        title=v.label,
                        orient='top',
                        **({"tickMinStep": 1} if v.tp == 'O' else {}),
                    ),
                    scale=alt.Scale(zero=False, nice=False),
                    **v.mark_options
                ),
                alt.Y(
                    'monthly_cost:Q',
                    axis=alt.Axis(
                        title='Monthly Cost',
                        format='$.2s',
                    ),
                    scale=alt.Scale(zero=False)
                ),
            )

            for k, v in variables.items()
        }

        # Transparent selectors across the chart. This is what tells us
        # the x-value of the cursor
        transparent_point_charts = {
            k: alt.Chart(sequences[k]).mark_point().encode(
                alt.X(field=k, **v.mark_options),
                opacity=alt.value(0),
            ).add_selection(
                selections[k]
            ) 
            for k, v in variables.items()
        }

        # Draw points on the line, and highlight based on selection
        point_charts = {
            k: line_charts[k].mark_point(shape='triangle', strokeWidth=10, size=100).encode(
                opacity=alt.condition(selections[k], alt.value(1), alt.value(0))
            )
            for k in variables.keys()
        }
        #     For text chart instead:
        #     point_charts = {
        #     k: line_charts[k].mark_text(fontSize=30).encode(
        #         text='label:N',
        #         opacity=alt.condition(selections[k], alt.value(1), alt.value(0))
        #     ).transform_calculate(
        #         label="'↔'"
        #     )
        #     for k in variables.keys()
        # }

        # Draw text labels near the points, and highlight based on selection
        text_charts = {
            k: line_charts[k].mark_text(align='center', baseline='top', dx=5, dy=20, fontSize=20).encode(
                text=alt.condition(selections[k], 'label:N', alt.value(' ')),

            ).transform_calculate(
                label=alt.expr.format(getattr(alt.datum, k), v.axis_format) if v.axis_format else getattr(alt.datum, k)
            )
            for k, v in variables.items()
        }

        # Draw a rule at the location of the selection
        rule_charts = {
            k: alt.Chart(sequences[k]).mark_rule(
                color='gray'
            ).encode(
                alt.X(field=k, **v.mark_options),
            ).transform_filter(
                selections[k]
            )
            for k, v in variables.items()
        }
    
        additional_charts = alt.concat(
            *(
                alt.layer(line_charts[k], transparent_point_charts[k], point_charts[k], text_charts[k]).properties(
                    title={
                        "text": v.title,
                        "fontSize": 45
                    },
                    width=400,
                    height=400,
                )
                for k, v in variables.items()
            ),
            columns=2
        ).resolve_scale(
            y='shared'
        )
    
    monthly_cost_categories = fn(**current_values)

    monthly_cost = None
    for k, v in monthly_cost_categories.items():
        monthly_cost = alt.expr.if_(alt.datum.category == k, v, monthly_cost)
    
    
    base_pie_chart = alt.Chart(
        alt.InlineData([
            {"category": k}
            for k in monthly_cost_categories.keys()
        ])
    ).transform_calculate(
        cost=monthly_cost
    )


    base_pie_chart_with_theta = base_pie_chart.encode(
        theta=alt.Theta("cost:Q", stack=True),
        tooltip=['category:N', 'cost:Q'],
        color=alt.Color(
            "category:N",
            legend=None
            # legend=alt.Legend(
                # orient='left',
                # title='Monthly Costs per Room',
                # direction='vertical',
                # columns=4
            # )
        )
    )

    pie_arc_chart = base_pie_chart_with_theta.mark_arc(
        innerRadius=30,
        outerRadius=120
    ).encode(
    )
    pie_text_chart = base_pie_chart_with_theta.mark_text(
        radius=155,
        size=15,
        align='center'
    ).encode(alt.Text("category:N"))


    pie_sum_text_chart = base_pie_chart.mark_text(radius=0, size=20).encode(
        alt.Text("cost:Q", aggregate='sum', format='$.2s')
    )
    chart = pie_arc_chart + pie_text_chart + pie_sum_text_chart.properties(
        width=900,
        height=400,
        title={
            "text": "Price per room per month",
            "fontSize": 25
        }
    )
    if simple:
        for selection in reversed(selections.values()):
            chart = chart.add_selection(selection)    
    else:
        chart = alt.vconcat(chart, additional_charts)
    for i in range(len(subtitle)):
        for k, v in variables.items():
            subtitle[i] = subtitle[i].replace(k, v.title)
    chart = chart.properties(
        title={
            "text": f'👇 Drag the {"sliders" if simple else "charts"} to change 🏡 values ❣️',
            "anchor": "start",
            "fontSize": 40,
            "subtitle": subtitle,
            "align": "left",
        }
    ).configure_axis(
        grid=True
    ).configure_legend(
        titleFontSize=20,
        labelFontSize=16,
        titleLimit=600,
    ).configure_axis(
        titleFontSize=20,
        labelFontSize=15
    ).configure_view(
        # https://stackoverflow.com/questions/46515327/how-do-i-remove-the-border-around-a-vega-lite-plot
        stroke='transparent'
    )
    pathlib.Path('simple.json' if simple else 'complex.json').write_text(chart.to_json(validate=False))
    return chart
