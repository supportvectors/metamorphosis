"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";

// Import types for Plotly.js configuration
import { Layout, Data, Config } from "plotly.js";

// Dynamically import default export from react-plotly.js to avoid SSR issues
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface RadarChartProps {
    labels: string[];
    values: number[];
}

export function RadarChart({ labels, values }: RadarChartProps) {
    const data: Data[] = useMemo(() => {
        // "Writing Goal" trace (Target)
        const goalValues = new Array(labels.length).fill(90);

        return [
            {
                type: "scatterpolar",
                r: goalValues,
                theta: labels,
                fill: "toself",
                name: "Writing Goal (90%)",
                line: {
                    color: "rgba(255, 165, 0, 0.8)", // Orange
                    dash: "dash",
                    width: 2,
                },
                fillcolor: "rgba(255, 165, 0, 0.1)",
                hovertemplate: "%{text}",
                opacity: 0.7,
            },
            {
                type: "scatterpolar",
                r: values,
                theta: labels,
                fill: "toself",
                name: "Current Score",
                line: {
                    color: "rgb(59, 130, 246)", // Blue-500 equivalent
                    width: 3,
                },
                fillcolor: "rgba(59, 130, 246, 0.3)",
                hovertemplate: "%{r}/100<extra></extra>",
            },
        ];
    }, [labels, values]);

    const layout: Partial<Layout> = {
        polar: {
            radialaxis: {
                visible: true,
                range: [0, 100],
                tickfont: { size: 10, color: "#666" },
                tickvals: [20, 40, 60, 80, 100],
                gridcolor: "rgba(229, 231, 235, 0.5)", // gray-200
            },
            angularaxis: {
                tickfont: { size: 12, color: "#374151", family: "inherit" }, // gray-700
                gridcolor: "rgba(229, 231, 235, 0.5)",
                // Map labels to match theta order if needed or rely on theta prop
            },
            bgcolor: "rgba(255,255,255,0)",
        },
        width: undefined, // undefined allows autosize container fitting via style/Plotly responsive
        height: undefined,
        margin: { t: 40, b: 40, l: 60, r: 60 },
        showlegend: true,
        legend: {
            orientation: "h",
            yanchor: "bottom",
            y: -0.2, // Move legend below chart
            xanchor: "center",
            x: 0.5
        },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        autosize: true,
        font: { family: "inherit" }
    };

    const config: Partial<Config> = {
        displayModeBar: false,
        responsive: true
    };

    return (
        <div className="w-full h-[450px] flex items-center justify-center relative z-0">
            <Plot
                data={data}
                layout={layout}
                config={config}
                // UseclassName for styling the container div created by Plotly if needed, 
                // but style prop on Plot component applies to the wrapper.
                style={{ width: "100%", height: "100%" }}
                useResizeHandler={true}
            />
        </div>
    );
}
