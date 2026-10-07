/* TestFlow 前端逻辑：需求详情页的生成入口 + 测试用例 / 测试点 / 评审 / 相似用例渲染。 */
(function () {
    const requirementId = window.REQUIREMENT_ID;

    const TYPE_LABEL = { normal: "正常", exception: "异常", boundary: "边界" };
    const TYPE_BADGE = { normal: "success", exception: "danger", boundary: "warning" };
    const PRIORITY_BADGE = { P0: "danger", P1: "warning", P2: "primary", P3: "secondary" };
    const METHOD_LABEL = {
        equivalence_partitioning: "等价类",
        boundary_value: "边界值",
        scenario: "场景法",
        state_transition: "状态迁移",
        other: "其他",
    };

    const TP_CATEGORY_LABEL = {
        normal: "功能测试",
        exception: "异常测试",
        boundary: "边界测试",
        input_validation: "输入校验",
        state_transition: "状态测试",
        permission: "权限测试",
        data_consistency: "数据一致性",
        security: "安全测试",
        performance: "性能测试",
        compatibility: "兼容性测试",
        usability: "可用性测试",
        other: "其他",
    };
    const TP_CATEGORY_ORDER = [
        "normal", "exception", "boundary", "input_validation", "state_transition",
        "permission", "data_consistency", "security", "performance",
        "compatibility", "usability", "other",
    ];

    let testPoints = []; // 当前测试点缓存

    function esc(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    }

    async function api(path, options) {
        options = options || {};
        options.headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
        const resp = await fetch(path, options);
        const body = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            throw new Error(body.message || `请求失败（HTTP ${resp.status}）`);
        }
        return body.data;
    }

    function stripNumbering(s) {
        return String(s).replace(/^\s*\d+[.、)）]\s*/, "").trim();
    }

    function listToHtml(items) {
        if (!items || !items.length) return "—";
        return "<ol class='mb-0 ps-3'>" + items.map((s) => `<li>${esc(stripNumbering(s))}</li>`).join("") + "</ol>";
    }

    function badge(text, color) {
        return `<span class="badge bg-${color}">${esc(text)}</span>`;
    }

    function emptyHtml(msg) {
        return `<div class="alert alert-light border text-muted">${esc(msg)}</div>`;
    }

    function switchTab(target) {
        const tabEl = document.querySelector(`button[data-bs-target="${target}"]`);
        if (tabEl) bootstrap.Tab.getOrCreateInstance(tabEl).show();
    }

    // ---------------- 测试用例 ----------------
    async function loadTestcases() {
        const params = new URLSearchParams();
        const type = document.getElementById("filterType").value;
        const priority = document.getElementById("filterPriority").value;
        const method = document.getElementById("filterMethod").value;
        if (type) params.set("test_type", type);
        if (priority) params.set("priority", priority);
        if (method) params.set("design_method", method);

        const container = document.getElementById("testcaseList");
        container.innerHTML = "<div class='text-muted'>加载中…</div>";
        try {
            const cases = await api(`/api/requirements/${requirementId}/testcases/?${params}`);
            if (!cases.length) {
                container.innerHTML = emptyHtml("暂无测试用例，点击上方「生成测试点」或「直接生成测试用例」。");
                return;
            }
            const rows = cases.map((tc) => `
                <tr>
                    <td class="text-nowrap">${esc(tc.case_id)}</td>
                    <td>${esc(tc.title)}</td>
                    <td class="text-nowrap">${esc(tc.test_point_title || "—")}</td>
                    <td>${listToHtml(tc.preconditions)}</td>
                    <td>${listToHtml(tc.steps)}</td>
                    <td>${esc(tc.test_data)}</td>
                    <td>${esc(tc.expected_result)}</td>
                    <td>${badge(TYPE_LABEL[tc.test_type] || tc.test_type, TYPE_BADGE[tc.test_type] || "secondary")}</td>
                    <td>${badge(tc.priority, PRIORITY_BADGE[tc.priority] || "secondary")}</td>
                    <td class="text-nowrap">${esc(METHOD_LABEL[tc.design_method] || tc.design_method)}</td>
                </tr>`).join("");

            container.innerHTML = `
                <table class="table table-bordered table-hover align-top small bg-white">
                    <thead class="table-light">
                        <tr>
                            <th>编号</th><th>标题</th><th>测试点</th><th>前置条件</th><th>测试步骤</th>
                            <th>测试数据</th><th>预期结果</th><th>类型</th><th>优先级</th><th>设计方法</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>`;
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
        }
    }

    // ---------------- 测试点 ----------------
    async function loadTestpoints() {
        const container = document.getElementById("testpointList");
        container.innerHTML = "<div class='text-muted'>加载中…</div>";
        try {
            testPoints = await api(`/api/requirements/${requirementId}/testpoints/`);
            renderTestpoints();
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
        }
    }

    function renderTpItem(tp) {
        const checked = tp.selected ? "checked" : "";
        const desc = tp.description
            ? `<div class="text-muted small mt-1">${esc(tp.description)}</div>`
            : "";
        return `
            <div class="list-group-item d-flex align-items-start gap-2">
                <input class="form-check-input mt-1 tp-check" type="checkbox" ${checked} data-id="${tp.id}">
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center gap-2">
                        <span class="fw-semibold">${esc(tp.title)}</span>
                        ${badge(tp.priority, PRIORITY_BADGE[tp.priority] || "secondary")}
                        ${badge(METHOD_LABEL[tp.design_method] || tp.design_method, "dark")}
                    </div>
                    ${desc}
                </div>
                <div class="text-nowrap">
                    <button class="btn btn-sm btn-outline-secondary tp-edit" data-id="${tp.id}" title="编辑">✎</button>
                    <button class="btn btn-sm btn-outline-danger tp-del" data-id="${tp.id}" title="删除">🗑</button>
                </div>
            </div>`;
    }

    function renderTestpoints() {
        const container = document.getElementById("testpointList");
        if (!testPoints.length) {
            container.innerHTML = emptyHtml("暂无测试点，点击上方「生成测试点」。");
            updateTestpointCount();
            return;
        }
        const groups = {};
        testPoints.forEach((tp) => {
            (groups[tp.category] = groups[tp.category] || []).push(tp);
        });
        let html = "";
        TP_CATEGORY_ORDER.forEach((cat) => {
            const items = groups[cat];
            if (!items) return;
            html += `
                <div class="mb-3">
                    <div class="fw-bold small text-muted mb-1">${TP_CATEGORY_LABEL[cat] || cat}（${items.length}）</div>
                    <div class="list-group shadow-sm">${items.map(renderTpItem).join("")}</div>
                </div>`;
        });
        container.innerHTML = html;
        updateTestpointCount();
    }

    function updateTestpointCount() {
        const selected = testPoints.filter((tp) => tp.selected).length;
        const total = testPoints.length;
        document.getElementById("tpCount").textContent = total ? `已选择 ${selected} / ${total} 个测试点` : "";
        const btn = document.getElementById("tpGenerateCasesBtn");
        btn.disabled = selected === 0;
        btn.innerHTML = `根据已选测试点生成测试用例（${selected}）`;
    }

    async function generateTestpoints() {
        const btn = document.getElementById("generatePointsBtn");
        const status = document.getElementById("generateStatus");
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 生成测试点中…';
        status.innerHTML = "<div class='alert alert-info'>AI 正在解析需求并生成测试点，请稍候…</div>";
        try {
            const points = await api(`/api/requirements/${requirementId}/testpoints/generate/`, { method: "POST" });
            status.innerHTML = `<div class="alert alert-success">已生成 ${points.length} 个测试点，请在「测试点」Tab 勾选后生成测试用例。</div>`;
            testPoints = points;
            renderTestpoints();
            switchTab("#tab-testpoints");
        } catch (err) {
            status.innerHTML = `<div class="alert alert-danger">生成测试点失败：${esc(err.message)}</div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = "🧩 生成测试点";
        }
    }

    async function toggleTestpoint(id, checked) {
        try {
            await api(`/api/requirements/${requirementId}/testpoints/${id}/`, {
                method: "PATCH",
                body: JSON.stringify({ selected: checked }),
            });
            const tp = testPoints.find((t) => t.id === id);
            if (tp) tp.selected = checked;
            updateTestpointCount();
        } catch (err) {
            alert("更新失败：" + err.message);
            renderTestpoints();
        }
    }

    async function deleteTestpoint(id) {
        if (!confirm("确定删除该测试点？")) return;
        try {
            await api(`/api/requirements/${requirementId}/testpoints/${id}/`, { method: "DELETE" });
            testPoints = testPoints.filter((t) => t.id !== id);
            renderTestpoints();
        } catch (err) {
            alert("删除失败：" + err.message);
        }
    }

    async function setAllSelected(selected) {
        try {
            await api(`/api/requirements/${requirementId}/testpoints/select/`, {
                method: "POST",
                body: JSON.stringify({ selected: selected }),
            });
            testPoints.forEach((t) => { t.selected = selected; });
            renderTestpoints();
        } catch (err) {
            alert("操作失败：" + err.message);
        }
    }

    function openTpModal(tp) {
        document.getElementById("tpModalTitle").textContent = tp ? "编辑测试点" : "新增测试点";
        document.getElementById("tpId").value = tp ? tp.id : "";
        document.getElementById("tpTitle").value = tp ? tp.title : "";
        document.getElementById("tpDescription").value = tp ? (tp.description || "") : "";
        document.getElementById("tpCategory").value = tp ? tp.category : "normal";
        document.getElementById("tpPriority").value = tp ? tp.priority : "P1";
        bootstrap.Modal.getOrCreateInstance(document.getElementById("tpModal")).show();
    }

    async function submitTpForm(e) {
        e.preventDefault();
        const id = document.getElementById("tpId").value;
        const payload = {
            title: document.getElementById("tpTitle").value.trim(),
            description: document.getElementById("tpDescription").value.trim(),
            category: document.getElementById("tpCategory").value,
            priority: document.getElementById("tpPriority").value,
        };
        if (!payload.title) { alert("标题不能为空"); return; }
        try {
            if (id) {
                const updated = await api(`/api/requirements/${requirementId}/testpoints/${id}/`, {
                    method: "PATCH",
                    body: JSON.stringify(payload),
                });
                const idx = testPoints.findIndex((t) => t.id === Number(id));
                if (idx >= 0) testPoints[idx] = updated;
            } else {
                const created = await api(`/api/requirements/${requirementId}/testpoints/`, {
                    method: "POST",
                    body: JSON.stringify(payload),
                });
                testPoints.push(created);
            }
            renderTestpoints();
            bootstrap.Modal.getOrCreateInstance(document.getElementById("tpModal")).hide();
        } catch (err) {
            alert("保存失败：" + err.message);
        }
    }

    async function generateFromTestpoints() {
        const selected = testPoints.filter((t) => t.selected);
        if (!selected.length) { alert("请先选择测试点"); return; }
        const btn = document.getElementById("tpGenerateCasesBtn");
        const status = document.getElementById("generateStatus");
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 生成用例中…';
        status.innerHTML = "<div class='alert alert-info'>AI 正在根据已选测试点生成测试用例，请稍候…</div>";
        try {
            const data = await api(`/api/requirements/${requirementId}/testcases/generate/`, {
                method: "POST",
                body: JSON.stringify({ test_point_ids: selected.map((t) => t.id) }),
            });
            status.innerHTML = `<div class="alert alert-success">生成完成：${data.test_case_count} 条测试用例（耗时 ${data.generation.duration_ms} ms）。</div>`;
            await Promise.all([loadTestcases(), loadReview(), loadSimilar()]);
            switchTab("#tab-testcases");
        } catch (err) {
            status.innerHTML = `<div class="alert alert-danger">生成失败：${esc(err.message)}</div>`;
        } finally {
            btn.disabled = false;
            updateTestpointCount();
        }
    }

    // ---------------- 质量检查 ----------------
    const REVIEW_SECTIONS = [
        ["coverage_issues", "覆盖性 / 完整性问题"],
        ["missing_scenarios", "遗漏的场景"],
        ["duplicate_candidates", "疑似重复用例"],
        ["ambiguous_cases", "模糊 / 不可执行用例"],
        ["suggestions", "改进建议"],
    ];

    async function loadReview() {
        const container = document.getElementById("reviewResult");
        container.innerHTML = "<div class='text-muted'>加载中…</div>";
        try {
            const review = await api(`/api/requirements/${requirementId}/review/`);
            const blocks = REVIEW_SECTIONS.map(([key, label]) => {
                const items = review[key] || [];
                const body = items.length
                    ? "<ul class='mb-0'>" + items.map((s) => `<li>${esc(s)}</li>`).join("") + "</ul>"
                    : "<span class='text-muted'>无</span>";
                return `<h6>${esc(label)}</h6>${body}`;
            }).join("");
            container.innerHTML = `<div class="alert alert-warning small mb-2">⚠️ AI 评审仅供辅助，不能保证覆盖完整，需测试人员 Review。</div><div class="card border-0 shadow-sm p-3">${blocks}</div>`;
        } catch (err) {
            container.innerHTML = emptyHtml(err.message);
        }
    }

    // ---------------- 相似用例 ----------------
    async function loadSimilar() {
        const container = document.getElementById("similarList");
        container.innerHTML = "<div class='text-muted'>加载中…</div>";
        try {
            const cases = await api(`/api/requirements/${requirementId}/similar/`);
            if (!cases.length) {
                container.innerHTML = emptyHtml("暂无相似历史用例。");
                return;
            }
            const rows = cases.map((tc) => `
                <tr>
                    <td>${esc(tc.case_id)}</td>
                    <td>${esc(tc.title)}</td>
                    <td>${badge(TYPE_LABEL[tc.test_type] || tc.test_type, TYPE_BADGE[tc.test_type] || "secondary")}</td>
                    <td>${badge(tc.priority, PRIORITY_BADGE[tc.priority] || "secondary")}</td>
                    <td>${esc(tc.expected_result)}</td>
                </tr>`).join("");
            container.innerHTML = `
                <table class="table table-bordered table-hover align-middle small bg-white">
                    <thead class="table-light"><tr><th>编号</th><th>标题</th><th>类型</th><th>优先级</th><th>预期结果</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>`;
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
        }
    }

    // ---------------- 直接生成测试用例 ----------------
    async function generate() {
        const btn = document.getElementById("generateBtn");
        const status = document.getElementById("generateStatus");
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 生成中…';
        status.innerHTML = "<div class='alert alert-info'>AI 正在解析需求并生成测试用例，请稍候…</div>";
        try {
            const data = await api(`/api/requirements/${requirementId}/generate/`, { method: "POST" });
            status.innerHTML = `<div class="alert alert-success">生成完成：${data.test_point_count} 个测试点，${data.test_case_count} 条测试用例（耗时 ${data.generation.duration_ms} ms）。</div>`;
            await Promise.all([loadTestcases(), loadTestpoints(), loadReview(), loadSimilar()]);
        } catch (err) {
            status.innerHTML = `<div class="alert alert-danger">生成失败：${esc(err.message)}</div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = "⚡ 直接生成测试用例";
        }
    }

    function bindEvents() {
        document.getElementById("generateBtn").addEventListener("click", generate);
        document.getElementById("generatePointsBtn").addEventListener("click", generateTestpoints);
        ["filterType", "filterPriority", "filterMethod"].forEach((id) => {
            document.getElementById(id).addEventListener("change", loadTestcases);
        });

        // 测试点工具栏
        document.getElementById("tpSelectAllBtn").addEventListener("click", () => setAllSelected(true));
        document.getElementById("tpSelectNoneBtn").addEventListener("click", () => setAllSelected(false));
        document.getElementById("tpAddBtn").addEventListener("click", () => openTpModal(null));
        document.getElementById("tpGenerateCasesBtn").addEventListener("click", generateFromTestpoints);

        // 测试点列表事件委托
        const tpList = document.getElementById("testpointList");
        tpList.addEventListener("change", (e) => {
            if (e.target.classList.contains("tp-check")) {
                toggleTestpoint(Number(e.target.dataset.id), e.target.checked);
            }
        });
        tpList.addEventListener("click", (e) => {
            const edit = e.target.closest(".tp-edit");
            const del = e.target.closest(".tp-del");
            if (edit) {
                const tp = testPoints.find((t) => t.id === Number(edit.dataset.id));
                openTpModal(tp);
            } else if (del) {
                deleteTestpoint(Number(del.dataset.id));
            }
        });

        // 测试点表单
        document.getElementById("tpForm").addEventListener("submit", submitTpForm);
    }

    document.addEventListener("DOMContentLoaded", () => {
        bindEvents();
        loadTestcases();
        loadTestpoints();
        loadReview();
        loadSimilar();

        // 从新建需求页跳转过来时，按所选入口自动触发对应生成
        const mode = new URLSearchParams(location.search).get("generate");
        if (mode === "points") {
            generateTestpoints();
        } else if (mode === "cases") {
            generate();
        }
    });
})();
