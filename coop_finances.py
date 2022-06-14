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

__all__ = ["Variable", "Range", "generate_plot", "Scenario"]
WIDTH = 800


@dataclasses.dataclass
class Scenario:
    name: str
    monthly_cost: dict[str, object]
    upfront_cost: dict[str, object]
    number_people: dict[str, object]


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


def generate_plot(
    fn: typing.Callable[..., list[Scenario]], subtitle, **variables: Variable
):
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

    scenarios = fn(**current_values)
    names = [s.name for s in scenarios]
    number_people = None
    number_people_data = []
    number_people_by_scenario = {}
    for s in scenarios:
        number_people_by_scenario[s.name] = 0
        for k, v in s.number_people.items():
            number_people_by_scenario[s.name] += v
            number_people_data.append({"category": k, "scenario": s.name})
            number_people = alt.expr.if_(
                (alt.datum.category == k) & (alt.datum.scenario == s.name),
                v,
                number_people,
            )

    monthly_cost = None
    monthly_cost_data = []
    for s in scenarios:
        for k, v in s.monthly_cost.items():
            monthly_cost_data.append({"category": k, "scenario": s.name})
            monthly_cost = alt.expr.if_(
                (alt.datum.category == k) & (alt.datum.scenario == s.name),
                v / number_people_by_scenario[s.name],
                monthly_cost,
            )

    upfront_cost = None
    upfront_cost_data = []
    for s in scenarios:
        for k, v in s.upfront_cost.items():
            upfront_cost_data.append({"category": k, "scenario": s.name})
            upfront_cost = alt.expr.if_(
                (alt.datum.category == k) & (alt.datum.scenario == s.name),
                v,
                upfront_cost,
            )
    charts = [
        (
            alt.Chart(alt.InlineData(monthly_cost_data))
            .transform_calculate(cost=monthly_cost)
            .mark_bar()
            .encode(
                alt.X("scenario:O", sort=names),
                alt.Y(
                    "sum(cost):Q",
                    axis=alt.Axis(format="$.3s", title="Monthly Cost per Resident"),
                ),
                alt.Color("category:N"),
                alt.Tooltip(["category:N", "cost:Q"]),
            )
        ),
        (
            alt.Chart(alt.InlineData(number_people_data))
            .transform_calculate(number_people=number_people)
            .mark_bar()
            .encode(
                alt.X("scenario:O", sort=names),
                alt.Y(
                    "sum(number_people):Q",
                    axis=alt.Axis(title="# Residents", tickMinStep=1),
                ),
                alt.Color("category:N"),
                alt.Tooltip(["category:N", "number_people:Q"]),
            )
        ),
        (
            alt.Chart(alt.InlineData(upfront_cost_data))
            .transform_calculate(upfront_cost=upfront_cost)
            .mark_bar()
            .encode(
                alt.X("scenario:O", sort=names),
                alt.Y(
                    "sum(upfront_cost):Q",
                    axis=alt.Axis(format="$.3s", title="Required Investment"),
                ),
                alt.Color("category:N"),
                alt.Tooltip(["category:N", "upfront_cost:Q"]),
            )
        ),
    ]
    chart = alt.hconcat(*charts)
    for selection in reversed(selections.values()):
        chart = chart.add_selection(selection)
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
