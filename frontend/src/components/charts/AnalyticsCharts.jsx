import React from 'react';
import ReactECharts from 'echarts-for-react';

/**
 * Renders correlation coefficient matrix as an interactive heatmap.
 */
export const CorrelationHeatmap = React.memo(function CorrelationHeatmap({ columns = [], matrix = [] }) {
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
      axisLabel: { color: '#4A5568', rotate: 30 }
    },
    yAxis: {
      type: 'category',
      data: columns,
      splitArea: { show: true },
      axisLabel: { color: '#4A5568' }
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#C53030', '#F1F5F9', '#1E3A5F'] // Crimson (negative) -> Off-White (neutral) -> Deep Navy (positive)
      },
      textStyle: { color: '#4A5568' }
    },
    series: [
      {
        name: 'Correlation',
        type: 'heatmap',
        data: data,
        label: {
          show: true,
          color: '#1A202C',
          formatter: (params) => String(params.data[2])
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.15)'
          }
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '350px', width: '100%' }} />;
});

/**
 * Renders data points scatter plot, highlighting anomalies.
 */
export const AnomalyScatter = React.memo(function AnomalyScatter({ rows = [], columns = [], anomalyIndices = [], plotData = [] }) {
  if (columns.length === 0) return null;
  
  // Plot first column on X, second column on Y (default to X if 1D)
  const colX = columns[0];
  const colY = columns[1] || columns[0];
  
  const normalPoints = [];
  const anomalyPoints = [];

  if (plotData && plotData.length > 0) {
    plotData.forEach((point) => {
      const p = [point.x, point.y, point.original_index !== undefined ? point.original_index : point.row_index];
      if (point.is_anomaly) {
        anomalyPoints.push(p);
      } else {
        normalPoints.push(p);
      }
    });
  } else {
    if (rows.length === 0) return null;
    rows.forEach((row, idx) => {
      const point = [row[colX], row[colY], idx];
      if (anomalyIndices.includes(idx)) {
        anomalyPoints.push(point);
      } else {
        normalPoints.push(point);
      }
    });
  }

  const option = {
    legend: {
      data: ['Normal Data', 'Flagged Outliers'],
      textStyle: { color: '#4A5568' },
      top: '0%'
    },
    grid: { left: '10%', right: '10%', bottom: '15%', top: '15%' },
    xAxis: {
      name: colX,
      type: 'value',
      nameTextStyle: { color: '#4A5568' },
      axisLabel: { color: '#4A5568' },
      splitLine: { lineStyle: { color: '#E2E8F0' } }
    },
    yAxis: {
      name: colY,
      type: 'value',
      nameTextStyle: { color: '#4A5568' },
      axisLabel: { color: '#4A5568' },
      splitLine: { lineStyle: { color: '#E2E8F0' } }
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
        itemStyle: { color: '#4F6D8A', opacity: 0.6 },
        symbolSize: 8
      },
      {
        name: 'Flagged Outliers',
        type: 'scatter',
        data: anomalyPoints,
        itemStyle: { color: '#C53030' },
        symbolSize: 12,
        label: {
          show: false
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '350px', width: '100%' }} />;
});

/**
 * Time series line chart rendering forecasts with upper/lower bounds.
 */
export const ForecastAreaLine = React.memo(function ForecastAreaLine({ timeline = [], historicalValues = [], forecastTimeline = [], forecastValues = [], lowerBounds = [], upperBounds = [] }) {
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
      textStyle: { color: '#4A5568' },
      top: '0%'
    },
    grid: { left: '8%', right: '8%', bottom: '15%', top: '15%' },
    xAxis: {
      type: 'category',
      data: fullTimeline,
      axisLabel: { color: '#4A5568', rotate: 30 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#4A5568' },
      splitLine: { lineStyle: { color: '#E2E8F0' } }
    },
    series: [
      {
        name: 'Historical Trend',
        type: 'line',
        data: histSeries,
        itemStyle: { color: '#2F855A' },
        lineStyle: { width: 3 },
        symbol: 'none'
      },
      {
        name: 'Forecast Prediction',
        type: 'line',
        data: forecastSeries,
        itemStyle: { color: '#1E3A5F' },
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
          color: 'rgba(30, 58, 95, 0.1)'
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '350px', width: '100%' }} />;
});


/**
 * Dynamic AI generated chart renderer for natural language plot requests.
 */
export const DynamicAIChart = React.memo(function DynamicAIChart({ spec }) {
  if (!spec || !spec.points || spec.points.length === 0) return null;

  const chartType = spec.type || 'scatter';
  const isBar = chartType === 'bar';

  const xAxisConfig = isBar
    ? {
        type: 'category',
        data: spec.points.map(p => String(p[0])),
        name: spec.x_col || 'Category',
        axisLabel: { interval: 0, rotate: 15, fontSize: 11 }
      }
    : {
        type: 'value',
        name: spec.x_col || 'X',
        nameLocation: 'middle',
        nameGap: 25,
        splitLine: { lineStyle: { type: 'dashed', opacity: 0.3 } }
      };

  const seriesData = isBar
    ? spec.points.map(p => p[1])
    : spec.points;

  const option = {
    title: {
      text: spec.title || `${spec.y_col || 'Y'} vs ${spec.x_col || 'X'}`,
      left: 'center',
      textStyle: { fontSize: 14, color: '#1E3A5F', fontWeight: 600 }
    },
    tooltip: {
      trigger: isBar ? 'item' : 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: { left: '8%', right: '5%', bottom: '20%', top: '15%' },
    xAxis: xAxisConfig,
    yAxis: {
      type: 'value',
      name: spec.y_col || 'Value',
      splitLine: { lineStyle: { type: 'dashed', opacity: 0.3 } }
    },
    series: [
      {
        name: spec.title || 'Data Points',
        type: chartType,
        data: seriesData,
        itemStyle: { color: isBar ? '#0070F3' : '#0F52BA', borderRadius: isBar ? [6, 6, 0, 0] : 0, opacity: 0.85 },
        barWidth: isBar ? '40%' : undefined,
        symbolSize: 8
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '340px', width: '100%' }} />;
});

