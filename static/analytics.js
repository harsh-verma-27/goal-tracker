
function analyticsApp() {
    return {
        stats: null,
        charts: {},

        async initStats() {
            try {
                const res = await fetch('/api/stats');
                this.stats = await res.json();
                this.$nextTick(() => this.renderCharts());
            } catch (e) { console.error("Error:", e); }
        },

        renderCharts() {
            const getStatusColors = (labels) => {
                return labels.map(label => {
                    label = label.toLowerCase();
                    if (label.includes('completed')) return '#198754';
                    if (label.includes('overdue')) return '#dc3545';
                    if (label.includes('progress')) return '#ffc107';
                    return '#6c757d';
                });
            };

            const ctxCat = document.getElementById('categoryChart').getContext('2d');
            new Chart(ctxCat, {
                type: 'doughnut',
                data: {
                    labels: this.stats.pie_category.labels,
                    datasets: [{
                        data: this.stats.pie_category.data,
                        backgroundColor: ['#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#fd7e14', '#20c997']
                    }]
                },
                options: { responsive: true, plugins: { legend: { position: 'right' } } }
            });

            const ctxStat = document.getElementById('statusChart').getContext('2d');
            new Chart(ctxStat, {
                type: 'pie',
                data: {
                    labels: this.stats.pie_status.labels,
                    datasets: [{
                        data: this.stats.pie_status.data,
                        backgroundColor: getStatusColors(this.stats.pie_status.labels)
                    }]
                },
                options: { responsive: true, plugins: { legend: { position: 'right' } } }
            });

            // 3. Bar Chart (Momentum)
            const ctxBar = document.getElementById('barChart').getContext('2d');
            new Chart(ctxBar, {
                type: 'bar',
                data: {
                    labels: this.stats.bar.labels,
                    datasets: [{
                        label: 'Tasks Completed',
                        data: this.stats.bar.data,
                        backgroundColor: '#0d6efd',
                        borderRadius: 4
                    }]
                },
                options: { 
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
                    plugins: { legend: { display: false } }
                }
            });
        }
    }
}