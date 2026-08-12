(() => {
    const formatUSD = (value) => Number.isFinite(value)
        ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        : '$0.00';

    const colorFromIdentifier = (identifier, fallbackIndex = 0) => {
        const value = String(identifier ?? `fallback-${fallbackIndex}`);
        let hash = 0;
        for (let index = 0; index < value.length; index += 1) {
            hash = ((hash << 5) - hash + value.charCodeAt(index)) | 0;
        }
        hash = Math.abs(hash);
        const hue = (hash * 137.508) % 360;
        const saturation = 88 + (hash % 13);
        const lightness = 38 + ((hash >> 3) % 15);
        return {
            base: `hsl(${hue.toFixed(1)}, ${saturation}%, ${lightness}%)`,
            hover: `hsl(${hue.toFixed(1)}, ${saturation}%, ${Math.min(88, lightness + 28)}%)`,
        };
    };

    const aggregateMonthlyTotals = (rows) => {
        const monthly = new Map();
        let firstVisibleDay = null;
        rows.forEach((row) => {
            const day = String(row.day || '');
            if (!day) return;
            if (!firstVisibleDay || day < firstVisibleDay) firstVisibleDay = day;
            const key = day.slice(0, 7);
            const bucket = monthly.get(key) || { incoming: 0, outgoing: 0, lastDay: day };
            bucket.incoming += Number(row.incoming_total_usd || 0);
            bucket.outgoing += Number(row.outgoing_total_usd || 0);
            if (day > bucket.lastDay) bucket.lastDay = day;
            monthly.set(key, bucket);
        });
        const keys = Array.from(monthly.keys()).sort();
        const series = (field) => {
            const points = keys.map((key) => ({
                x: monthly.get(key).lastDay,
                y: monthly.get(key)[field],
                marker: true,
            }));
            if (firstVisibleDay && keys.length) {
                points.unshift({ x: firstVisibleDay, y: monthly.get(keys[0])[field], marker: false });
            }
            return points;
        };
        return { incoming: series('incoming'), outgoing: series('outgoing') };
    };

    const renderBalanceChart = (prefix, balanceData) => {
        const container = document.getElementById(`${prefix}-balance-chart`);
        if (!container || typeof Plotly === 'undefined') return;
        const currencies = new Set();
        balanceData.forEach((row) => {
            Object.keys(row.balance_changes || {}).forEach((currency) => currencies.add(currency));
        });
        const traces = Array.from(currencies).sort().map((currency) => {
            const color = colorFromIdentifier(currency).base;
            return {
                type: 'scatter', mode: 'lines+markers', name: currency.toUpperCase(),
                visible: 'legendonly',
                x: balanceData.map((row) => row.day),
                y: balanceData.map((row) => Number((row.balance_changes || {})[currency] || 0)),
                line: { width: 2, color }, marker: { size: 4, color },
                hovertemplate: `%{x}<br>${currency.toUpperCase()}: %{y:.2f}<extra></extra>`,
            };
        });
        traces.push({
            type: 'scatter', mode: 'lines+markers', name: 'Total (USD)',
            x: balanceData.map((row) => row.day),
            y: balanceData.map((row) => Number(row.total_usd || 0)),
            line: { width: 2.5, color: 'rgba(37, 99, 235, 0.95)' },
            marker: { size: 5, color: 'rgba(37, 99, 235, 0.95)' },
            hovertemplate: '%{x}<br>Total (USD): %{y:.2f}<extra></extra>',
        });
        Plotly.newPlot(container, traces, {
            margin: { l: 52, r: 16, t: 8, b: 42 },
            paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(248, 250, 252, 0.6)',
            hovermode: 'x unified', dragmode: 'pan',
            legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'left', x: 0 },
            xaxis: {
                type: 'date', rangeslider: { visible: true }, showspikes: true,
                spikemode: 'across', spikecolor: '#94a3b8', spikethickness: 1,
                gridcolor: 'rgba(203, 213, 225, 0.5)',
            },
            yaxis: {
                type: 'linear', rangemode: 'tozero', autorange: true, zeroline: true,
                showspikes: true, spikemode: 'across', spikecolor: '#94a3b8',
                spikethickness: 1, gridcolor: 'rgba(203, 213, 225, 0.5)',
            },
        }, {
            responsive: true, displaylogo: false,
            modeBarButtonsToAdd: ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape'],
        });

        const linearButton = document.getElementById(`${prefix}-scale-linear`);
        const logButton = document.getElementById(`${prefix}-scale-log`);
        const setScale = (scale) => {
            Plotly.relayout(container, scale === 'log'
                ? { 'yaxis.type': 'log', 'yaxis.autorange': true, 'yaxis.rangemode': undefined }
                : { 'yaxis.type': 'linear', 'yaxis.autorange': true, 'yaxis.rangemode': 'tozero' });
            linearButton?.classList.toggle('active', scale === 'linear');
            logButton?.classList.toggle('active', scale === 'log');
        };
        linearButton?.addEventListener('click', () => setScale('linear'));
        logButton?.addEventListener('click', () => setScale('log'));
    };

    const renderMoneyFlowChart = (prefix, rows) => {
        const canvas = document.getElementById(`${prefix}-money-flow-chart`);
        if (!canvas || typeof Chart === 'undefined') return;
        const monthly = aggregateMonthlyTotals(rows);
        const dailySeries = (field) => rows.map((row) => ({ x: row.day, y: Number(row[field] || 0) }));
        new Chart(canvas, {
            type: 'bar',
            data: { datasets: [
                { label: 'Income (USD)', data: dailySeries('incoming_total_usd'), backgroundColor: 'rgba(34, 197, 94, 0.75)', borderColor: 'rgba(22, 163, 74, 0.9)', borderWidth: 1 },
                { label: 'Spending (USD)', data: dailySeries('outgoing_total_usd'), backgroundColor: 'rgba(239, 68, 68, 0.70)', borderColor: 'rgba(220, 38, 38, 0.9)', borderWidth: 1 },
                { type: 'line', label: 'Monthly Income (USD)', data: monthly.incoming, borderColor: 'rgba(22, 163, 74, 0.95)', backgroundColor: 'rgba(22, 163, 74, 0.12)', borderWidth: 2, tension: 0.15, pointRadius: (ctx) => ctx.raw?.marker ? 3 : 0, pointHoverRadius: (ctx) => ctx.raw?.marker ? 4 : 0 },
                { type: 'line', label: 'Monthly Spending (USD)', data: monthly.outgoing, borderColor: 'rgba(220, 38, 38, 0.95)', backgroundColor: 'rgba(220, 38, 38, 0.10)', borderWidth: 2, tension: 0.15, pointRadius: (ctx) => ctx.raw?.marker ? 3 : 0, pointHoverRadius: (ctx) => ctx.raw?.marker ? 4 : 0 },
            ] },
            options: {
                parsing: { xAxisKey: 'x', yAxisKey: 'y' }, responsive: true, maintainAspectRatio: false,
                scales: {
                    x: { type: 'time', time: { parser: 'yyyy-MM-dd', unit: 'day', tooltipFormat: 'PP' } },
                    y: { beginAtZero: true, ticks: { callback: (value) => formatUSD(Number(value)) } },
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${formatUSD(Number(context.parsed.y ?? context.parsed))}` } },
                },
            },
        });
    };

    const renderHistoryStats = ({ prefix, balanceData, moneyFlowData }) => {
        renderBalanceChart(prefix, balanceData);
        renderMoneyFlowChart(prefix, moneyFlowData);
        const grid = document.getElementById(`${prefix}-charts-grid`);
        const oneButton = document.getElementById(`${prefix}-width-one`);
        const fullButton = document.getElementById(`${prefix}-width-full`);
        const setWidth = (mode) => {
            if (!grid) return;
            grid.classList.toggle('balance-width-one', mode === 'one');
            grid.classList.toggle('balance-width-full', mode === 'full');
            oneButton?.classList.toggle('active', mode === 'one');
            fullButton?.classList.toggle('active', mode === 'full');
            requestAnimationFrame(() => {
                grid.querySelectorAll('.js-plotly-plot').forEach((chart) => Plotly.Plots.resize(chart));
                if (Chart.instances) Object.values(Chart.instances).forEach((chart) => chart.resize());
            });
        };
        oneButton?.addEventListener('click', () => setWidth('one'));
        fullButton?.addEventListener('click', () => setWidth('full'));
        window.addEventListener('resize', () => {
            grid?.querySelectorAll('.js-plotly-plot').forEach((chart) => Plotly.Plots.resize(chart));
        });
    };

    window.StatsCharts = { formatUSD, colorFromIdentifier, renderHistoryStats };
})();
