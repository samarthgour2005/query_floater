import altair as alt
import pandas as pd

# Create some data
data = pd.DataFrame({
    'x': [1, 2, 3, 4, 5],
    'y': [2, 4, 6, 8, 10]
})

# Create a chart
chart = alt.Chart(data).mark_line(point=True).encode(
    x='x',
    y='y'
)

chart.show()
