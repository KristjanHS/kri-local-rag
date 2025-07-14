# This script is a simple tool to help you decide whether to ventilate your home based on the current indoor and outdoor conditions.
# It calculates the dew point for both indoor and outdoor and displays them in a heatmap.
# It also provides a suggestion for HRV homeowners, based on the difference between the indoor and outdoor dew points.

import numpy as np
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Dew‑point calculation using Magnus‑Tetens approximation
# ---------------------------------------------------------------------------

a_const: float = 17.625
b_const: float = 243.04


def calculate_dew_point(temp_c: float, rh: float) -> float:
    """Return dew‑point (°C) for given temperature (°C) and RH (0‑100 %)."""
    alpha = np.log(rh / 100.0) + (a_const * temp_c) / (b_const + temp_c)
    return (b_const * alpha) / (a_const - alpha)


# ---------------------------------------------------------------------------
# Grid definition — higher resolution for "middle" values
# ---------------------------------------------------------------------------

temperatures = np.arange(15.0, 28.5, 0.5)  # 0.5 °C steps for finer precision
humidities = np.arange(55.0, 79.0, 1.0)  # 1 % RH steps

# Compute dew‑point matrix

dew_points = np.empty((len(humidities), len(temperatures)))
for i, rh in enumerate(humidities):
    for j, t in enumerate(temperatures):
        dew_points[i, j] = calculate_dew_point(float(t), float(rh))

# Create a text matrix for data labels (dew point values)
text_labels = np.empty_like(dew_points, dtype=object)
for i in range(len(humidities)):
    for j in range(len(temperatures)):
        text_labels[i, j] = f"{dew_points[i, j]:.2f}"

# ---------------------------------------------------------------------------
# Plotly heatmap — blue (low DP) ➜ red (high DP)
# ---------------------------------------------------------------------------

blue_red_scale = [[0.0, "blue"], [1.0, "red"]]

fig = go.Figure(
    data=go.Heatmap(
        x=temperatures,
        y=humidities,
        z=dew_points,
        colorscale=blue_red_scale,
        colorbar=dict(title="Dew Point (°C)"),
        hovertemplate=(
            "Temperature: %{x:.1f}°C<br>"  # 0.1 °C precision for T
            "Humidity: %{y:.0f}%<br>"  # whole‑number RH
            "Dew Point: %{z:.2f}°C<extra></extra>"  # 0.01 °C DP
        ),
        text=text_labels,  # Add text labels to each cell
        texttemplate="%{text}",  # Show the text at each cell
        textfont={"size": 10, "color": "black"},  # Adjust font for readability
    )
)

fig.update_layout(
    title="Dew Point Temperature (°C)",
    xaxis_title="Temperature (°C)",
    yaxis_title="Relative Humidity (%)",
    template="plotly_white",
)

# Add more axis labels (show every value)
fig.update_xaxes(
    tickvals=temperatures,
    ticktext=[f"{t:.1f}" for t in temperatures],
    tickangle=0,
)
fig.update_yaxes(
    tickvals=humidities,
    ticktext=[f"{h:.0f}" for h in humidities],
)

if __name__ == "__main__":
    # Get user input for indoor and outdoor conditions
    try:
        indoor_temp = float(input("Enter current INDOOR temperature (°C): "))
        indoor_rh = float(input("Enter current INDOOR relative humidity (%): "))
        outdoor_temp = float(input("Enter current OUTDOOR temperature (°C): "))
        outdoor_rh = float(input("Enter current OUTDOOR relative humidity (%): "))
    except ValueError:
        print("Invalid input. Please enter numeric values.")
        exit(1)

    # Calculate dew points
    indoor_dp = calculate_dew_point(indoor_temp, indoor_rh)
    outdoor_dp = calculate_dew_point(outdoor_temp, outdoor_rh)

    # If points overlap, nudge them slightly for visibility
    nudge = 0.15 if (indoor_temp == outdoor_temp and indoor_rh == outdoor_rh) else 0
    indoor_x = indoor_temp + nudge
    outdoor_x = outdoor_temp - nudge

    # Add large dots for indoor and outdoor points with offset text positions
    fig.add_trace(
        go.Scatter(
            x=[indoor_x],
            y=[indoor_rh],
            mode="markers+text",
            marker=dict(size=18, color="green", line=dict(width=2, color="black")),
            name="Indoor",
            text=[f"Indoor\nDP: {indoor_dp:.2f}°C"],
            textposition="top right",  # Improved alignment
            textfont=dict(size=12, color="black"),
            hovertemplate=(
                f"<b>Indoor</b><br>Temp: %{{x:.1f}}°C<br>RH: %{{y:.0f}}%<br>"
                f"Dew Point: {indoor_dp:.2f}°C<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[outdoor_x],
            y=[outdoor_rh],
            mode="markers+text",
            marker=dict(size=18, color="blue", line=dict(width=2, color="black")),
            name="Outdoor",
            text=[f"Outdoor\nDP: {outdoor_dp:.2f}°C"],
            textposition="bottom left",  # Improved alignment
            textfont=dict(size=12, color="black"),
            hovertemplate=(
                f"<b>Outdoor</b><br>Temp: %{{x:.1f}}°C<br>RH: %{{y:.0f}}%<br>"
                f"Dew Point: {outdoor_dp:.2f}°C<extra></extra>"
            ),
        )
    )

    # Print ventilation suggestion
    print(f"\nIndoor dew point:  {indoor_dp:.2f}°C")
    print(f"Outdoor dew point: {outdoor_dp:.2f}°C")
    if outdoor_dp <= indoor_dp - 2:
        print("\nSuggestion: ✅ Ventilate (outdoor dew point is at least 2°C lower)")
    else:
        print("\nSuggestion: ❌ Do NOT ventilate (outdoor dew point is not 2°C lower)")

    # Move the legend outside the plot area for better visibility
    fig.update_layout(
        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.2,
            xanchor="center",
            yanchor="top",
            font=dict(size=14),
        )
    )

    fig.show()
