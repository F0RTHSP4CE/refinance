(() => {
    const toLinkColor = (color) => color.startsWith('hsl(')
        ? color.replace('hsl(', 'hsla(').replace(')', ', 0.38)')
        : color.replace(/[\d.]+\)$/, '0.38)');

    const buildSankeyChart = (
        containerId, incomingData, outgoingData, nameKey, idKey, centerLabel
    ) => {
        const container = document.getElementById(containerId);
        if (!container || (!incomingData.length && !outgoingData.length)) return;
        const nodeLabels = [centerLabel.toUpperCase()];
        const nodeColors = ['#ffffff'];
        const addNodes = (rows, direction) => {
            const indexes = {};
            rows.forEach((item, index) => {
                const name = (item[nameKey] || `#${item[idKey]}`).toUpperCase();
                if (name in indexes) return;
                indexes[name] = nodeLabels.length;
                nodeLabels.push(name);
                nodeColors.push(window.StatsCharts.colorFromIdentifier(
                    item[idKey] ?? `${direction}-${index}`, index
                ).base);
            });
            return indexes;
        };
        const sourceIndexes = addNodes(incomingData, 'in');
        const destinationIndexes = addNodes(outgoingData, 'out');
        const source = [];
        const target = [];
        const value = [];
        const color = [];
        incomingData.forEach((item) => {
            const index = sourceIndexes[(item[nameKey] || `#${item[idKey]}`).toUpperCase()];
            source.push(index); target.push(0); value.push(item.total_usd);
            color.push(toLinkColor(nodeColors[index]));
        });
        outgoingData.forEach((item) => {
            const index = destinationIndexes[(item[nameKey] || `#${item[idKey]}`).toUpperCase()];
            source.push(0); target.push(index); value.push(item.total_usd);
            color.push(toLinkColor(nodeColors[index]));
        });
        Plotly.newPlot(container, [{
            type: 'sankey', orientation: 'h',
            node: {
                pad: 18, thickness: 22,
                line: { color: 'rgba(0,0,0,0.08)', width: 0.5 },
                label: nodeLabels, color: nodeColors,
            },
            link: {
                source, target, value, color,
                hovertemplate: '%{source.label} → %{target.label}: $%{value:,.2f}<extra></extra>',
            },
        }], {
            margin: { l: 16, r: 16, t: 16, b: 16 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            font: { size: 16, family: 'monospace', color: '#000000' },
        }, { responsive: true, displaylogo: false });
    };

    const renderActivityStats = (config) => {
        if (typeof Plotly === 'undefined') return;
        buildSankeyChart(
            'entity-sankey-chart', config.topIncoming, config.topOutgoing,
            'entity_name', 'entity_id', config.entityName
        );
        buildSankeyChart(
            'tag-sankey-chart', config.topIncomingTags, config.topOutgoingTags,
            'tag_name', 'tag_id', config.entityName
        );
    };

    window.StatsCharts.renderActivityStats = renderActivityStats;
})();
