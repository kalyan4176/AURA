import React from 'react';
import ReactECharts from 'echarts-for-react';

/**
 * Renders correlation coefficient matrix as an interactive heatmap.
 */
export function CorrelationHeatmap({ columns = [], matrix = [] }) {
  // Format correlation matrix for ECharts heatmap series: [[x_idx, y_idx, coef], ...]
  const data = [];
  matrix.forEach((row, rIdx) => {
    row.forEach((val, cIdx) => {
      data.push([cIdx, rIdx, val]);
    });
  });

  const option = {
    tooltip: {
      position: 'top',
      formatter: (params) => {
        const x = columns[params.data[0]];
        const y = columns[params.data[1]];
        return `${x} x ${y}: <b>${params.data[2]}</b>`;
      }
    },
    grid: {
      height: '75%',
      top: '10%',
      bottom: '15%',
      left: '15%',
      right: '5%'
    },
    xAxis: {
      type: 'category',
      data: columns,
      splitArea: { show: true },
      axisLabel: { color: '#9ca3af', rotate: 30 }
    },
    yAxis: {
      type: 'category',
      data: columns,
      splitArea: { show: true },
      axisLabel: { color: '#9ca3af' }
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#ef4444', '#1f2937', '#10b981'] // Red (negative) -> Gray (neutral) -> Emerald (positive)
      },
      textStyle: { color: '#9ca3af' }
    },
    series: [
      {
        name: 'Correlation',
        type: 'heatmap',
        data: data,
        label: {
          show: true,
          color: '#f3f4f6',
          formatter: (params) => String(params.data[2])
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '350px', width: '100%' }} />;
}

/**
 * Renders data points scatter plot, highlighting anomalies.
 */
export function AnomalyScatter({ rows = [], columns = [], anomalyIndices = [] }) {
  if (columns.length === 0 || rows.length === 0) return null;
  
  // Plot first column on X, second column on Y (default to X if 1D)
  const colX = columns[0];
  const colY = columns[1] || columns[0];
  
  const normalPoints = [];
  const anomalyPoints = [];

  rows.forEach((row, idx) => {
    const point = [row[colX], row[colY], idx];
    if (anomalyIndices.includes(idx)) {
      anomalyPoints.push(point);
    } else {
      normalPoints.push(point);
    }
  });

  const option = {
    legend: {
      data: ['Normal Data', 'Flagged Outliers'],
      textStyle: { color: '#9ca3af' },
      top: '0%'
    },
    grid: { left: '10%', right: '10%', bottom: '15%', top: '15%' },
    xAxis: {
      name: colX,
      type: 'value',
      nameTextStyle: { color: '#9ca3af' },
      axisLabel: { color: '#9ca3af' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    yAxis: {
      name: colY,
      type: 'value',
      nameTextStyle: { color: '#9ca3af' },
      axisLabel: { color: '#9ca3af' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    tooltip: {
      formatter: (params) => {
        return `Row: ${params.data[2]}<br/>X (${colX}): ${params.data[0]}<br/>Y (${colY}): ${params.data[1]}`;
      }
    },
    series: [
      {
        name: 'Normal Data',
        type: 'scatter',
        data: normalPoints,
        itemStyle: { color: '#6366f1', opacity: 0.6 },
        symbolSize: 8
      },
      {
        name: 'Flagged Outliers',
        type: 'scatter',
        data: anomalyPoints,
        itemStyle: { color: '#ef4444' },
        symbolSize: 12,
        label: {
          show: true,
          position: 'top',
          color: '#ef4444',
          formatter: (params) => `Index ${params.data[2]}`
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '350px', width: '100%' }} />;
}

/**
 * Time series line chart rendering forecasts with upper/lower bounds.
 */
export function ForecastAreaLine({ timeline = [], historicalValues = [], forecastTimeline = [], forecastValues = [], lowerBounds = [], upperBounds = [] }) {
  const fullTimeline = [...timeline, ...forecastTimeline];
  
  // Pad historical values with nulls for the forecast range
  const histSeries = [...historicalValues, ...Array(forecastValues.length).fill(null)];
  
  // Pad forecast values with nulls for the historical range
  // We repeat the last historical point to make line continuous
  const lastHistVal = historicalValues[historicalValues.length - 1];
  const forecastSeries = [...Array(historicalValues.length - 1).fill(null), lastHistVal, ...forecastValues];

  const lowerSeries = [...Array(historicalValues.length - 1).fill(null), lastHistVal, ...lowerBounds];
  const upperSeries = [...Array(historicalValues.length - 1).fill(null), lastHistVal, ...upperBounds];

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['Historical Trend', 'Forecast Prediction', 'Prediction Boundary'],
      textStyle: { color: '#9ca3af' },
      top: '0%'
    },
    grid: { left: '8%', right: '8%', bottom: '15%', top: '15%' },
    xAxis: {
      type: 'category',
      data: fullTimeline,
      axisLabel: { color: '#9ca3af', rotate: 30 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#9ca3af' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    series: [
      {
        name: 'Historical Trend',
        type: 'line',
        data: histSeries,
        itemStyle: { color: '#10b981' },
        lineStyle: { width: 3 },
        symbol: 'none'
      },
      {
        name: 'Forecast Prediction',
        type: 'line',
        data: forecastSeries,
        itemStyle: { color: '#6366f1' },
        lineStyle: { width: 3, type: 'dashed' },
        symbol: 'circle'
      },
      // Lower and Upper series bounds to render predicted range area
      {
        name: 'Prediction Boundary',
        type: 'line',
        data: upperSeries,
        lineStyle: { opacity: 0 },
        symbol: 'none',
        stack: 'confidence'
      },
      {
        name: 'Prediction Boundary',
        type: 'line',
        data: lowerSeries,
        lineStyle: { opacity: 0 },
        symbol: 'none',
        stack: 'confidence',
        areaStyle: {
          color: 'rgba(99, 102, 241, 0.15)'
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '350px', width: '100%' }} />;
}
