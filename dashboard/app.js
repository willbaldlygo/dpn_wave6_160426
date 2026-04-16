document.addEventListener('DOMContentLoaded', () => {
    
    // Config
    let FILES = {
        reflections: '../layer2_layer3_clean_matrix.csv',
        milestones: '../milestone_matrix.csv'
    };
    
    let globalData = [];
    let currentMode = 'reflections';
    let currentSort = { column: 'learner_id', direction: 'asc' };
    let currentHash = ''; // Stores the password hash if locked

    // Helper: SHA-256 Hashing for Password
    async function sha256(message) {
        const msgUint8 = new TextEncoder().encode(message);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        return hashHex;
    }

    // Chart References
    let summaryChart1 = null;
    let summaryChart2 = null;
    let drilldownBloomChartObj = null;
    let drilldownSophChartObj = null;

    // Check if lock is active
    checkLockStatus();

    async function checkLockStatus() {
        try {
            const resp = await fetch('lock_active.json');
            const status = await resp.json();
            if (status.locked) {
                setupGateInteractions();
            } else {
                unlockDashboard('');
            }
        } catch (e) {
            // No lock file found, proceed as normal
            unlockDashboard('');
        }
    }

    function setupGateInteractions() {
        const btn = document.getElementById('unlock-btn');
        const input = document.getElementById('dashboard-password');
        
        const attemptUnlock = async () => {
            const pw = input.value;
            if (!pw) return;
            currentHash = await sha256(pw);
            
            // Re-map files to hashed versions
            FILES.reflections = `data_${currentHash}_r.csv`;
            FILES.milestones = `data_${currentHash}_m.csv`;
            
            initializeDashboard(true);
        };

        btn.onclick = attemptUnlock;
        input.onkeydown = (e) => { if (e.key === 'Enter') attemptUnlock(); };
    }

    function unlockDashboard(hash) {
        document.getElementById('password-gate').classList.add('hidden');
        if (hash) {
            FILES.reflections = `data_${hash}_r.csv`;
            FILES.milestones = `data_${hash}_m.csv`;
        }
        initializeDashboard();
    }

    function initializeDashboard(isAttempt = false) {
        const url = FILES[currentMode];
        
        document.getElementById('data-status').innerText = "Loading...";
        document.querySelector('.pulse-dot').style.backgroundColor = 'var(--text-secondary)';

        Papa.parse(url, {
            download: true,
            header: true,
            dynamicTyping: true,
            skipEmptyLines: true,
            complete: function(results) {
                // If this was an attempt to unlock, hide the gate
                document.getElementById('password-gate').classList.add('hidden');
                document.getElementById('login-error').style.display = 'none';

                globalData = results.data;
                document.getElementById('data-status').innerText = "Live";
                document.querySelector('.pulse-dot').style.backgroundColor = 'var(--success)';
                
                setupInteractions();
                renderTableHeaders();
                processDataAndRender();
            },
            error: function(err) {
                if (isAttempt) {
                    document.getElementById('login-error').style.display = 'block';
                }
                document.getElementById('data-status').innerText = "Access Denied / Not Found";
                document.querySelector('.pulse-dot').style.backgroundColor = 'red';
                console.warn("Access Error:", err);
            }
        });
    }

    function setupInteractions() {
        // 1. Cohort Selector Population
        const cohorts = [...new Set(globalData.map(r => r.course_id))].filter(c => c).sort();
        const selector = document.getElementById('cohortSelect');
        selector.innerHTML = '<option value="">Select Cohort...</option>';
        cohorts.forEach(cid => {
            let opt = document.createElement('option');
            opt.value = cid;
            opt.innerText = `Cohort ${cid}`;
            selector.appendChild(opt);
        });

        // 2. Mode Toggles
        document.getElementById('mode-reflections').onclick = () => switchMode('reflections');
        document.getElementById('mode-milestones').onclick = () => switchMode('milestones');

        // 3. Drill-down Visibility
        selector.onchange = (e) => {
            const val = e.target.value;
            if(val) {
                renderDrilldown(val);
                document.getElementById('cohort-drilldown').style.display = 'grid';
                document.getElementById('drilldown-id').innerText = val;
            } else {
                document.getElementById('cohort-drilldown').style.display = 'none';
            }
        };
    }

    function switchMode(newMode) {
        if (currentMode === newMode) return;
        currentMode = newMode;
        
        // UI Updates
        document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`mode-${newMode}`).classList.add('active');
        
        // Clear State
        globalData = [];
        if(summaryChart1) summaryChart1.destroy();
        if(summaryChart2) summaryChart2.destroy();
        document.getElementById('cohort-drilldown').style.display = 'none';
        
        // Fix for Issue #1: Clear Evaluation Narrative on Mode Switch
        const narrativeContent = document.getElementById('narrative-content');
        narrativeContent.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <p>Mode switched. Select a learner in the new directory to read their narrative evaluation.</p>
            </div>
        `;
        
        // Reset sorting to default for new dataset
        currentSort = { column: 'learner_id', direction: 'asc' };
        
        // Reload
        initializeDashboard();
    }

    function renderTableHeaders() {
        const headerRow = document.getElementById('dynamic-table-header');
        // Fix for Issue #2: Separate Learner ID and Cohort
        if (currentMode === 'reflections') {
            headerRow.innerHTML = `
                <th data-col="learner_id">ID</th>
                <th data-col="course_id">Cohort</th>
                <th data-col="peak_bloom_score">Peak Bloom</th>
                <th data-col="peak_sophistication">Peak Soph.</th>
                <th data-col="mean_sophistication">Mean Soph.</th>
            `;
        } else {
            headerRow.innerHTML = `
                <th data-col="learner_id">ID</th>
                <th data-col="course_id">Cohort</th>
                <th data-col="base_bloom">Base Bloom</th>
                <th data-col="out_bloom">Out Bloom</th>
                <th data-col="base_sophistication">Base Soph.</th>
                <th data-col="out_sophistication">Out Soph.</th>
            `;
        }
        
        // Add click listeners back to new headers
        headerRow.querySelectorAll('th').forEach(th => {
            if (currentSort.column === th.dataset.col) {
                th.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            }
            th.onclick = () => {
                const col = th.dataset.col;
                if(currentSort.column === col) {
                    currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSort.column = col;
                    currentSort.direction = 'asc';
                }
                // Refresh visuals
                headerRow.querySelectorAll('th').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
                th.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
                populateTable();
            };
        });
    }

    function processDataAndRender() {
        const totalLearners = globalData.length;
        document.getElementById('kpi-total').innerText = totalLearners;

        if (currentMode === 'reflections') {
            renderReflectionsDashboard();
        } else {
            renderMilestonesDashboard();
        }
        populateTable();
    }

    function renderReflectionsDashboard() {
        let sumMeanSoph = 0;
        let bloomCounts = { 'L1':0, 'L2':0, 'L3':0, 'L4':0, 'L5':0, 'L6':0 };
        let cohortData = {}; 
        const bloomMap = { 'L1':1, 'L2':2, 'L3':3, 'L4':4, 'L5':5, 'L6':6 };

        // Reset KPI Labels for Reflections
        document.getElementById('kpi-2-label').innerText = "Overall Avg Sophistication Score";
        document.getElementById('kpi-3-label').innerText = "Primary Bloom Ceiling";
        document.getElementById('kpi-3-subtitle').innerText = "Most frequent cognitive level";

        globalData.forEach(row => {
            sumMeanSoph += row.mean_sophistication || 0;
            if(row.peak_bloom_score) {
                let match = row.peak_bloom_score.match(/(L[1-6])/);
                if(match) bloomCounts[match[1]]++;
            }
            const cid = row.course_id;
            if(cid) {
                if(!cohortData[cid]) cohortData[cid] = { sophSum: 0, bloomSum: 0, count: 0 };
                cohortData[cid].sophSum += row.mean_sophistication || 0;
                let match = (row.peak_bloom_score || "").match(/(L[1-6])/);
                cohortData[cid].bloomSum += match ? bloomMap[match[1]] : 0;
                cohortData[cid].count++;
            }
        });

        document.getElementById('kpi-score').innerText = (sumMeanSoph / (globalData.length || 1)).toFixed(2);
        
        let primaryBloom = '-'; let maxCount = 0;
        for(let [level, count] of Object.entries(bloomCounts)) {
            if(count > maxCount) { maxCount = count; primaryBloom = level; }
        }
        document.getElementById('kpi-bloom').innerText = primaryBloom;

        const cids = Object.keys(cohortData).sort();
        renderSummaryCharts(
            cids.map(cid => `Cohort ${cid}`), 
            cids.map(cid => (cohortData[cid].bloomSum / cohortData[cid].count).toFixed(2)),
            cids.map(cid => (cohortData[cid].sophSum / cohortData[cid].count).toFixed(2)),
            'Mean Bloom Level', 'Mean Sophistication'
        );
    }

    function renderMilestonesDashboard() {
        let cohortData = {}; // { cid: { baseSophSum, outSophSum, baseBloomSum, outBloomSum, count } }
        const bloomMap = { 'L1':1, 'L2':2, 'L3':3, 'L4':4, 'L5':5, 'L6':6 };
        
        // Update KPI Labels for Milestones
        document.getElementById('kpi-2-label').innerText = "Avg Final Sophistication Score";
        document.getElementById('kpi-3-label').innerText = "AVG Sophistication Improvement";
        document.getElementById('kpi-3-subtitle').innerText = "Average difference between first and last milestone scores";
        let totalBaseSoph = 0, totalOutSoph = 0;

        globalData.forEach(row => {
            totalBaseSoph += row.base_sophistication || 0;
            totalOutSoph += row.out_sophistication || 0;
            
            const cid = row.course_id;
            if(cid) {
                if(!cohortData[cid]) cohortData[cid] = { bS: 0, oS: 0, bB: 0, oB: 0, count: 0 };
                cohortData[cid].bS += row.base_sophistication || 0;
                cohortData[cid].oS += row.out_sophistication || 0;
                cohortData[cid].bB += bloomMap[row.base_bloom] || 0;
                cohortData[cid].oB += bloomMap[row.out_bloom] || 0;
                cohortData[cid].count++;
            }
        });

        const avgFinal = (totalOutSoph / (globalData.length || 1)).toFixed(2);
        document.getElementById('kpi-score').innerText = avgFinal;
        document.getElementById('kpi-bloom').innerText = "+" + ((totalOutSoph - totalBaseSoph) / (globalData.length || 1)).toFixed(2);

        const cids = Object.keys(cohortData).sort();
        const labels = cids.map(cid => `Cohort ${cid}`);
        
        renderClusteredCharts(
            labels,
            cids.map(cid => (cohortData[cid].bB / cohortData[cid].count).toFixed(2)),
            cids.map(cid => (cohortData[cid].oB / cohortData[cid].count).toFixed(2)),
            cids.map(cid => (cohortData[cid].bS / cohortData[cid].count).toFixed(2)),
            cids.map(cid => (cohortData[cid].oS / cohortData[cid].count).toFixed(2))
        );
    }

    function renderSummaryCharts(labels, data1, data2, label1, label2) {
        const ctx1 = document.getElementById('bloomChart').getContext('2d');
        const ctx2 = document.getElementById('trajectoryChart').getContext('2d');
        
        summaryChart1 = new Chart(ctx1, {
            type: 'bar',
            data: { labels, datasets: [{ label: label1, data: data1, backgroundColor: 'rgba(59, 130, 246, 0.8)', borderRadius: 6 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
                       scales: { y: { min: 1, max: 6, ticks: { callback: v => 'L' + v } }, x: { grid: { display: false } } } }
        });
        
        summaryChart2 = new Chart(ctx2, {
            type: 'bar',
            data: { labels, datasets: [{ label: label2, data: data2, backgroundColor: 'rgba(139, 92, 246, 0.8)', borderRadius: 6 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
                       scales: { y: { min: 1, max: 4 }, x: { grid: { display: false } } } }
        });
    }

    function renderClusteredCharts(labels, bB, oB, bS, oS) {
        summaryChart1 = new Chart(document.getElementById('bloomChart'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Baseline', data: bB, backgroundColor: 'rgba(203, 213, 225, 0.8)', borderRadius: 4 },
                    { label: 'Outcomes', data: oB, backgroundColor: 'rgba(59, 130, 246, 0.8)', borderRadius: 4 }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 1, max: 6, ticks: { callback: v => 'L' + v } } } }
        });

        summaryChart2 = new Chart(document.getElementById('trajectoryChart'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Baseline', data: bS, backgroundColor: 'rgba(203, 213, 225, 0.8)', borderRadius: 4 },
                    { label: 'Outcomes', data: oS, backgroundColor: 'rgba(139, 92, 246, 0.8)', borderRadius: 4 }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 1, max: 4 } } }
        });
    }

    function populateTable() {
        const tbody = document.getElementById('learnerTableBody');
        tbody.innerHTML = "";
        
        const bloomOrder = { 'L1':1, 'L2':2, 'L3':3, 'L4':4, 'L5':5, 'L6':6, 'N/A':0, '':0 };

        const sorted = [...globalData].sort((a, b) => {
            let valA = a[currentSort.column];
            let valB = b[currentSort.column];
            if(currentSort.column.includes('bloom')) {
                valA = bloomOrder[valA] || 0;
                valB = bloomOrder[valB] || 0;
            }
            if(valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
            if(valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
            return 0;
        });

        sorted.forEach(row => {
            let tr = document.createElement('tr');
            if (currentMode === 'reflections') {
                tr.innerHTML = `
                    <td>L${row.learner_id}</td>
                    <td>C${row.course_id}</td>
                    <td><span class="badge">${row.peak_bloom_score || 'N/A'}</span></td>
                    <td><b>${row.peak_sophistication || 0}</b></td>
                    <td>${row.mean_sophistication || 0}</td>
                `;
            } else {
                tr.innerHTML = `
                    <td>L${row.learner_id}</td>
                    <td>C${row.course_id}</td>
                    <td>${row.base_bloom || '-'}</td>
                    <td><span class="badge highlight">${row.out_bloom || '-'}</span></td>
                    <td>${row.base_sophistication || 0}</td>
                    <td><b>${row.out_sophistication || 0}</b></td>
                `;
            }
            tr.onclick = () => {
                document.querySelectorAll('#learnerTableBody tr').forEach(el => el.classList.remove('selected'));
                tr.classList.add('selected');
                displayNarrative(row);
            };
            tbody.appendChild(tr);
        });
    }

    function renderDrilldown(cohortId) {
        const cohortLearners = globalData.filter(r => r.course_id == cohortId).sort((a,b) => a.learner_id - b.learner_id);
        const labels = cohortLearners.map(r => `L${r.learner_id}`);
        const bloomMap = { 'L1':1, 'L2':2, 'L3':3, 'L4':4, 'L5':5, 'L6':6 };

        if(drilldownBloomChartObj) drilldownBloomChartObj.destroy();
        if(drilldownSophChartObj) drilldownSophChartObj.destroy();

        const commonOptions = {
            responsive: true, maintainAspectRatio: false,
            scales: { x: { ticks: { font: { size: 9 }, autoSkip: false } } }
        };

        if (currentMode === 'reflections') {
            drilldownBloomChartObj = new Chart(document.getElementById('drilldownBloomChart'), {
                type: 'bar',
                data: { labels, datasets: [{ label: 'Bloom', data: cohortLearners.map(r => bloomMap[r.peak_bloom_score] || 0), backgroundColor: 'rgba(59, 130, 246, 0.6)' }] },
                options: { ...commonOptions, plugins: { legend: { display: false } }, scales: { ...commonOptions.scales, y: { min: 1, max: 6, ticks: { callback: v => 'L' + v } } } }
            });
            drilldownSophChartObj = new Chart(document.getElementById('drilldownSophChart'), {
                type: 'bar',
                data: { labels, datasets: [{ label: 'Soph', data: cohortLearners.map(r => r.mean_sophistication || 0), backgroundColor: 'rgba(139, 92, 246, 0.6)' }] },
                options: { ...commonOptions, plugins: { legend: { display: false } }, scales: { ...commonOptions.scales, y: { min: 1, max: 4 } } }
            });
        } else {
            drilldownBloomChartObj = new Chart(document.getElementById('drilldownBloomChart'), {
                type: 'bar',
                data: { labels, datasets: [
                    { label: 'Base', data: cohortLearners.map(r => bloomMap[r.base_bloom] || 0), backgroundColor: 'rgba(203, 213, 225, 0.6)' },
                    { label: 'Out', data: cohortLearners.map(r => bloomMap[r.out_bloom] || 0), backgroundColor: 'rgba(59, 130, 246, 0.6)' }
                ]},
                options: { ...commonOptions, scales: { ...commonOptions.scales, y: { min: 1, max: 6, ticks: { callback: v => 'L' + v } } } }
            });
            drilldownSophChartObj = new Chart(document.getElementById('drilldownSophChart'), {
                type: 'bar',
                data: { labels, datasets: [
                    { label: 'Base', data: cohortLearners.map(r => r.base_sophistication || 0), backgroundColor: 'rgba(203, 213, 225, 0.6)' },
                    { label: 'Out', data: cohortLearners.map(r => r.out_sophistication || 0), backgroundColor: 'rgba(139, 92, 246, 0.6)' }
                ]},
                options: { ...commonOptions, scales: { ...commonOptions.scales, y: { min: 1, max: 4 } } }
            });
        }
    }

    function displayNarrative(row) {
        const contentDiv = document.getElementById('narrative-content');
        let narrativeText = currentMode === 'reflections' ? (row.overall_arc_summary || "") : (row.progression_narrative || "");
        
        let narrative = (narrativeText || "").replace(/(Week\s*\d+|Step\s*\d+|Phase\s*\d+|BASELINE|OUTCOMES)/gi, '<div class="narrative-section"><h5 style="margin-bottom:0.4rem; color: var(--accent-secondary)">$1</h5>');
        narrative = narrative.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>').replace(/\|/g, '<br>').replace(/---/g, '<hr>');
        narrative = narrative.split('\n\n').map(p => `<p style="margin-bottom: 0.8rem;">${p}</p>`).join('');

        let rawHtml = "";
        try {
            if (currentMode === 'reflections') {
                const rawAnswers = JSON.parse(row.raw_responses_json || "{}");
                if (Object.keys(rawAnswers).length > 0) {
                    rawHtml = '<div class="raw-responses-container"><h5>Learner Raw Responses</h5>' + 
                        Object.entries(rawAnswers).map(([wk, ans]) => `<details><summary>${wk}</summary><p>${ans.replace(/\n/g, '<br>')}</p></details>`).join('') + '</div>';
                }
            } else {
                const base = JSON.parse(row.raw_baseline_json || "{}");
                const out = JSON.parse(row.raw_outcomes_json || "{}");
                rawHtml = '<div class="raw-responses-container"><h5>Baseline vs Outcomes Raw Text</h5>';
                rawHtml += '<details><summary>Day 1 Baseline Profile</summary>' + Object.entries(base).map(([q, a]) => `<p><b>${q}</b><br>${a}</p>`).join('') + '</details>';
                rawHtml += '<details><summary>End-of-Course Outcomes Profile</summary>' + Object.entries(out).map(([q, a]) => `<p><b>${q}</b><br>${a}</p>`).join('') + '</details>';
                rawHtml += '</div>';
            }
        } catch (e) {}
        
        contentDiv.innerHTML = `<div style="margin-bottom: 1.5rem; padding-bottom: 0.5rem; border-bottom: 1px solid #f1f5f9;"><span style="font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase;">Selected Profile</span><h4 style="font-size: 1.1rem; color: var(--accent-primary); margin-top: 0.1rem;">Learner ${row.learner_id} (Course ${row.course_id})</h4></div><div class="narrative-body">${narrative}</div>${rawHtml}`;
    }
});
