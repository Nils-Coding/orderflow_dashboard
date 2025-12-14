<script setup>
import { onMounted, ref, onUnmounted } from 'vue';
import { createChart, ColorType } from 'lightweight-charts';

const chartContainer = ref(null);
const loading = ref(true);
const error = ref(null);

// Configuration (Should be in .env in production)
const API_URL = import.meta.env.PUBLIC_API_URL || 'https://YOUR-CLOUD-RUN-URL/api/v1/candles';
const API_KEY = import.meta.env.PUBLIC_API_KEY || 'YOUR_API_KEY';

onMounted(async () => {
  if (!chartContainer.value) return;

  // 1. Initialize Chart
  const chart = createChart(chartContainer.value, {
    layout: {
      background: { type: ColorType.Solid, color: '#1a1a1a' },
      textColor: '#d1d5db',
    },
    grid: {
      vertLines: { color: '#333' },
      horzLines: { color: '#333' },
    },
    width: chartContainer.value.clientWidth,
    height: 600,
  });

  const candleSeries = chart.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderVisible: false,
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
  });

  // 2. Fetch Data
  try {
    const url = `${API_URL}?symbol=btcusdt&date=2025-12-11&resolution=1m`;
    const response = await fetch(url, {
      headers: { 'X-API-Key': API_KEY }
    });

    if (!response.ok) throw new Error(`API Error: ${response.status}`);

    const json = await response.json();
    const data = json.data;

    // 3. Transform for Lightweight Charts
    const candles = data.map(d => ({
      time: d.time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candleSeries.setData(candles);

    // Fit content
    chart.timeScale().fitContent();

  } catch (err) {
    console.error(err);
    error.value = err.message;
  } finally {
    loading.value = false;
  }

  // Resize handling
  const resizeObserver = new ResizeObserver(() => {
    chart.applyOptions({ width: chartContainer.value.clientWidth });
  });
  resizeObserver.observe(chartContainer.value);

  onUnmounted(() => {
    chart.remove();
    resizeObserver.disconnect();
  });
});
</script>

<template>
  <div class="relative w-full h-[600px] border border-gray-700 rounded-lg overflow-hidden">
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-gray-900 text-white z-10">
      Loading Data...
    </div>
    <div v-if="error" class="absolute inset-0 flex items-center justify-center bg-red-900/50 text-red-200 z-10">
      {{ error }}
    </div>
    <div ref="chartContainer" class="w-full h-full bg-[#1a1a1a]"></div>
  </div>
</template>
