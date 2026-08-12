(() => {
  const cfg = window.ADMIN_SCHEDULE_CONFIG;
  const toast = document.getElementById("toast");
  const selectedTwoPersonSlots = new Set();
  let latestReadiness = null;
  let latestStudentAccess = null;
  let currentScheduleStudentId = null;
  let currentScheduleRecord = null;
  let currentAdminSchedule = null;
  let currentAdminScheduleBackup = null;
  let adminScheduleEditing = false;
  let adminScheduleBrush = "first";

  const showToast = (message, error = false) => {
    toast.textContent = message;
    toast.className = `toast show${error ? " error" : ""}`;
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.className = "toast", 3600);
  };
  const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
  const fmt = value => value ? new Date(value).toLocaleString("ko-KR") : "-";
  const stateLabel = {not_started:"미작성", draft:"임시저장", submitted:"최종 제출"};

  const statusLabel = status => cfg.statusMeta?.[status]?.label || status;
  const statusStyle = status => {
    const item = cfg.statusMeta?.[status] || {};
    return `background:${item.color || "#eef1f5"};color:${item.text || "#526174"}`;
  };

  function renderStudentAccess(access) {
    latestStudentAccess = access;
    const badge = document.getElementById("studentAccessBadge");
    const desc = document.getElementById("studentAccessDescription");
    const start = document.getElementById("studentAccessStart");
    const end = document.getElementById("studentAccessEnd");
    if (start && document.activeElement !== start) start.value = access.start_at || "";
    if (end && document.activeElement !== end) end.value = access.end_at || "";
    if (badge) {
      badge.className = `access-status-badge ${access.is_open ? "open" : "locked"}`;
      badge.textContent = access.is_open ? "학생 로그인 가능" : "학생 로그인 잠금";
    }
    if (desc) {
      const range = access.configured && access.start_at && access.end_at
        ? ` · ${access.start_at.replace("T", " ")} ~ ${access.end_at.replace("T", " ")}`
        : " · 입력기간 미설정(상시 허용)";
      desc.textContent = `${access.message}${range}`;
    }
    const popupBadge = document.getElementById("studentScheduleAccessBadge");
    const editButton = document.getElementById("adminEditScheduleButton");
    const editNotice = document.getElementById("adminScheduleEditNotice");
    if (popupBadge) {
      popupBadge.className = `access-status-badge small ${access.is_open ? "open" : "locked"}`;
      popupBadge.textContent = access.is_open ? "학생 입력 중" : "학생 입력 잠금";
    }
    if (editButton) editButton.disabled = access.is_open;
    if (editNotice) editNotice.textContent = access.is_open
      ? "학생 입력기간 중에는 충돌 방지를 위해 관리자 수정이 잠겨 있습니다."
      : "학생 입력이 잠긴 상태입니다. 관리자만 이 시간표를 수정할 수 있습니다.";
  }

  async function loadStudentAccess() {
    const response = await fetch("/api/admin/student-access");
    if (!response.ok) return;
    renderStudentAccess(await response.json());
  }

  function renderReadiness(readiness) {
    latestReadiness = readiness;
    const box = document.getElementById("rosterReadiness");
    if (!readiness || readiness.active_count === 0) {
      box.innerHTML = '<div class="alert warning"><strong>등록된 근로학생이 없습니다.</strong><br>학생을 직접 추가하거나 CSV 명단을 업로드하면 해당 학생부터 로그인이 가능합니다.</div>';
      return;
    }
    if (readiness.ready) {
      box.innerHTML = `<div class="alert success"><strong>자동배정 준비 완료</strong> · 활성 학생 ${readiness.active_count}명 전원이 최종 제출했습니다.</div>`;
      return;
    }
    const items = [];
    if (readiness.not_submitted?.length) {
      const sample = readiness.not_submitted.slice(0, 8).map(escapeHtml).join(", ");
      items.push(`최종 미제출 ${readiness.not_submitted.length}명${sample ? ` · ${sample}${readiness.not_submitted.length > 8 ? " 외" : ""}` : ""}`);
    }
    if (readiness.untyped?.length) items.push(`근로유형 미지정 ${readiness.untyped.length}명`);
    box.innerHTML = `<div class="alert warning"><strong>전체 시간표 생성 전 확인</strong><ul>${items.map(item => `<li>${item}</li>`).join("")}</ul><p>활성 학생 전원이 최종 제출해야 전체 시간표를 생성할 수 있습니다.</p></div>`;
  }

  async function loadStudents() {
    const response = await fetch("/api/admin/students");
    if (!response.ok) { location.href = "/"; return; }
    const {students, readiness} = await response.json();
    const activeStudents = students.filter(student => student.active);
    const submitted = activeStudents.filter(student => student.state === "submitted").length;
    const draft = activeStudents.filter(student => student.state === "draft").length;
    const inactive = students.length - activeStudents.length;
    document.getElementById("adminMetrics").innerHTML = `
      <div class="metric"><span>등록 학생</span><strong>${students.length}명</strong><small>활성 ${activeStudents.length}명 · 비활성 ${inactive}명</small></div>
      <div class="metric"><span>최종 제출</span><strong>${submitted}/${activeStudents.length}명</strong><small>임시저장 ${draft}명</small></div>
      <div class="metric"><span>자동배정</span><strong>${readiness?.ready ? "준비 완료" : "대기"}</strong><small>${readiness?.ready ? "전원 제출 완료" : "전원 최종제출 필요"}</small></div>`;
    renderReadiness(readiness);

    const tbody = document.getElementById("studentRows");
    if (!students.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty-result">등록된 학생이 없습니다. 위에서 학생을 추가하거나 CSV를 업로드해 주세요.</td></tr>';
      return;
    }
    tbody.innerHTML = students.map(student => `
      <tr class="${student.active ? "" : "inactive-row"}" data-student-id="${student.id}">
        <td><input class="student-name" type="text" maxlength="80" value="${escapeHtml(student.name)}"></td>
        <td><input class="student-no" type="text" maxlength="30" value="${escapeHtml(student.student_no)}"></td>
        <td><select class="student-work-type">
          <option value="" ${!student.work_type ? "selected" : ""}>미지정</option>
          <option value="A" ${student.work_type === "A" ? "selected" : ""}>A형</option>
          <option value="B" ${student.work_type === "B" ? "selected" : ""}>B형</option>
        </select></td>
        <td><select class="student-active">
          <option value="true" ${student.active ? "selected" : ""}>활성</option>
          <option value="false" ${!student.active ? "selected" : ""}>비활성</option>
        </select></td>
        <td><span class="status-pill ${student.state}">${stateLabel[student.state] || student.state}</span></td>
        <td>${fmt(student.saved_at)}</td>
        <td>${fmt(student.submitted_at)}</td>
        <td><button class="btn primary small view-student-schedule" type="button">${student.state === "not_started" ? "시간표 작성" : "시간표 보기"}</button></td>
        <td><button class="btn secondary small save-student" type="button">수정 저장</button></td>
      </tr>`).join("");

    document.querySelectorAll(".view-student-schedule").forEach(button => button.addEventListener("click", () => {
      const row = button.closest("tr");
      openStudentSchedule(row.dataset.studentId).catch(error => showToast(error.message || "시간표를 불러오지 못했습니다.", true));
    }));

    document.querySelectorAll(".save-student").forEach(button => button.addEventListener("click", async () => {
      const row = button.closest("tr");
      const id = row.dataset.studentId;
      const payload = {
        name: row.querySelector(".student-name").value.trim(),
        student_no: row.querySelector(".student-no").value.trim(),
        work_type: row.querySelector(".student-work-type").value,
        active: row.querySelector(".student-active").value === "true",
      };
      button.disabled = true;
      try {
        const response = await fetch(`/api/admin/students/${id}`, {
          method: "PUT",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail);
        showToast("학생 정보를 수정했습니다. 기존 자동배정 결과는 초기화되었습니다.");
        await loadStudents();
        await loadRun();
      } catch (error) {
        showToast(error.message || "학생 정보 수정에 실패했습니다.", true);
      } finally {
        button.disabled = false;
      }
    }));
  }

  const cloneSchedule = schedule => JSON.parse(JSON.stringify(schedule || {}));

  function renderStudentSchedulePopupTable() {
    const table = document.getElementById("studentSchedulePopupTable");
    if (!table || !currentAdminSchedule) return;
    table.classList.toggle("editing", adminScheduleEditing);
    table.innerHTML = `
      <thead><tr><th>시간</th>${cfg.days.map(day => `<th>${day}요일</th>`).join("")}</tr></thead>
      <tbody>${cfg.hours.map(hour => `
        <tr>
          <th>${String(hour).padStart(2,"0")}:00~${String(hour + 1).padStart(2,"0")}:00</th>
          ${cfg.days.map(day => {
            const value = currentAdminSchedule?.[day]?.[String(hour)] || "unselected";
            return `<td><div class="admin-student-schedule-cell ${escapeHtml(value)}" data-day="${escapeHtml(day)}" data-hour="${hour}" data-status="${escapeHtml(value)}" style="${statusStyle(value)}">${escapeHtml(statusLabel(value))}</div></td>`;
          }).join("")}
        </tr>`).join("")}
      </tbody>`;
  }

  function setAdminScheduleEditing(enabled) {
    adminScheduleEditing = enabled;
    const editor = document.getElementById("adminScheduleEditor");
    const saveActions = document.getElementById("adminScheduleSaveActions");
    const editButton = document.getElementById("adminEditScheduleButton");
    editor.hidden = !enabled;
    saveActions.hidden = !enabled;
    editButton.textContent = enabled ? "수정 중" : "관리자 수정";
    editButton.disabled = enabled || Boolean(latestStudentAccess?.is_open);
    renderStudentSchedulePopupTable();
  }

  async function openStudentSchedule(studentId) {
    const response = await fetch(`/api/admin/students/${studentId}/schedule`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "시간표를 불러오지 못했습니다.");
    currentScheduleStudentId = String(studentId);
    currentScheduleRecord = data;
    currentAdminSchedule = cloneSchedule(data.schedule);
    currentAdminScheduleBackup = null;
    adminScheduleEditing = false;
    renderStudentAccess(data.student_access || latestStudentAccess || {is_open:true, message:""});
    const state = data.state || "not_started";
    document.getElementById("studentScheduleModalTitle").textContent = `${data.student.name} 시간표`;
    const stateChip = document.getElementById("studentScheduleState");
    stateChip.className = `status-pill ${state}`;
    stateChip.textContent = stateLabel[state] || state;
    document.getElementById("studentScheduleMeta").innerHTML = `
      <span class="meta-chip">학번 ${escapeHtml(data.student.student_no)}</span>
      <span class="meta-chip">${escapeHtml(data.student.work_type || "유형 미지정")}${data.student.work_type ? "형" : ""}</span>
      <span class="meta-chip">${data.student.active ? "활성" : "비활성"}</span>
      <span class="meta-chip">마지막 저장 ${escapeHtml(fmt(data.saved_at))}</span>`;
    setAdminScheduleEditing(false);
    document.getElementById("studentScheduleModal").classList.add("open");
    document.getElementById("studentScheduleModal").setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeStudentSchedule() {
    if (adminScheduleEditing && currentAdminScheduleBackup) currentAdminSchedule = cloneSchedule(currentAdminScheduleBackup);
    setAdminScheduleEditing(false);
    document.getElementById("studentScheduleModal").classList.remove("open");
    document.getElementById("studentScheduleModal").setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    currentScheduleStudentId = null;
    currentScheduleRecord = null;
    currentAdminSchedule = null;
    currentAdminScheduleBackup = null;
  }

  function startAdminScheduleEdit() {
    if (latestStudentAccess?.is_open) {
      showToast("학생 입력기간 중에는 관리자 수정이 잠겨 있습니다.", true);
      return;
    }
    currentAdminScheduleBackup = cloneSchedule(currentAdminSchedule);
    setAdminScheduleEditing(true);
  }

  function cancelAdminScheduleEdit() {
    if (currentAdminScheduleBackup) currentAdminSchedule = cloneSchedule(currentAdminScheduleBackup);
    currentAdminScheduleBackup = null;
    setAdminScheduleEditing(false);
    showToast("관리자 수정 내용을 취소했습니다.");
  }

  function maxConsecutiveAvailable(day, hour, status) {
    let current = 0, maximum = 0;
    cfg.hours.forEach(h => {
      const value = h === hour ? status : currentAdminSchedule?.[day]?.[String(h)];
      if (["first", "second", "third"].includes(value)) {
        current += 1;
        maximum = Math.max(maximum, current);
      } else current = 0;
    });
    return maximum;
  }

  function editAdminScheduleCell(cell) {
    if (!adminScheduleEditing || !cell || cell.dataset.status === "closed") return;
    const day = cell.dataset.day;
    const hour = Number(cell.dataset.hour);
    if (["first", "second", "third"].includes(adminScheduleBrush) && maxConsecutiveAvailable(day, hour, adminScheduleBrush) > 4) {
      showToast("최대 연속 근로는 4시간까지 가능합니다.", true);
      return;
    }
    currentAdminSchedule[day][String(hour)] = adminScheduleBrush;
    cell.dataset.status = adminScheduleBrush;
    cell.className = `admin-student-schedule-cell ${adminScheduleBrush}`;
    cell.setAttribute("style", statusStyle(adminScheduleBrush));
    cell.textContent = statusLabel(adminScheduleBrush);
  }

  async function saveAdminScheduleEdit() {
    if (!currentScheduleStudentId || !currentScheduleRecord) return;
    const state = currentScheduleRecord.state === "submitted" ? "submitted" : "draft";
    const response = await fetch(`/api/admin/students/${currentScheduleStudentId}/schedule`, {
      method: "PUT",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({schedule: currentAdminSchedule, state}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "관리자 수정사항을 저장하지 못했습니다.");
    currentScheduleRecord = {...currentScheduleRecord, ...data, state};
    currentAdminScheduleBackup = null;
    setAdminScheduleEditing(false);
    document.getElementById("studentScheduleMeta").innerHTML = `
      <span class="meta-chip">학번 ${escapeHtml(currentScheduleRecord.student.student_no)}</span>
      <span class="meta-chip">${escapeHtml(currentScheduleRecord.student.work_type || "유형 미지정")}${currentScheduleRecord.student.work_type ? "형" : ""}</span>
      <span class="meta-chip">${currentScheduleRecord.student.active ? "활성" : "비활성"}</span>
      <span class="meta-chip">마지막 저장 ${escapeHtml(fmt(data.saved_at))}</span>
      <span class="meta-chip">수정자 ${escapeHtml(data.edited_by || "관리자")}</span>`;
    showToast("관리자 수정사항을 저장했습니다. 기존 자동배정 결과는 초기화되었습니다.");
    await loadStudents();
    await loadRun();
  }

  const scheduleCell = people => {
    if (!people) return '<span class="closed-label">운영 안 함</span>';
    if (!people.length) return '<span class="muted">미배정</span>';
    return people.map(person => `<span class="person-chip type-${escapeHtml(person.work_type || "none")}">${escapeHtml(person.name)}</span>`).join("");
  };

  function renderScheduleTable(elementId, schedule) {
    const table = document.getElementById(elementId);
    if (!schedule || !Object.keys(schedule).length) {
      table.innerHTML = '<tbody><tr><td class="empty-result">아직 생성된 시간표가 없습니다.</td></tr></tbody>';
      return;
    }
    table.innerHTML = `
      <thead><tr><th>시간</th>${cfg.days.map(day => `<th>${day}요일</th>`).join("")}</tr></thead>
      <tbody>${cfg.hours.map(hour => `
        <tr><th>${String(hour).padStart(2,"0")}:00~${String(hour + 1).padStart(2,"0")}:00</th>
        ${cfg.days.map(day => `<td>${scheduleCell(schedule?.[day]?.[String(hour)])}</td>`).join("")}
        </tr>`).join("")}
      </tbody>`;
  }

  function restoreDeskSettings(summary) {
    const settings = summary?.desk_settings;
    if (!settings) return;
    document.getElementById("deskWeeklyMaxA").value = settings.weekly_max_a ?? "";
    document.getElementById("deskWeeklyMaxB").value = settings.weekly_max_b ?? "";
    document.getElementById("deskDailyMax").value = settings.daily_max ?? "";
    selectedTwoPersonSlots.clear();
    (settings.two_person_slots || []).forEach(key => selectedTwoPersonSlots.add(key));
    renderTwoPersonGrid();
  }

  function renderRun(run) {
    const download = document.getElementById("downloadScheduleButton");
    if (!run) {
      document.getElementById("scheduleMetrics").innerHTML = "";
      document.getElementById("scheduleWarnings").innerHTML = "";
      renderScheduleTable("fullScheduleTable", null);
      renderScheduleTable("deskScheduleTable", null);
      document.getElementById("studentAssignmentRows").innerHTML = '<tr><td colspan="6" class="empty-result">아직 생성된 배정 결과가 없습니다.</td></tr>';
      download.classList.add("disabled-link");
      return;
    }
    const summary = run.summary || {};
    const hasDesk = run.desk_schedule && Object.keys(run.desk_schedule).length > 0;
    download.classList.toggle("disabled-link", !hasDesk);
    if (summary.full_settings?.min_staff) document.getElementById("fullMinStaff").value = summary.full_settings.min_staff;
    restoreDeskSettings(summary);

    document.getElementById("scheduleMetrics").innerHTML = `
      <div class="metric"><span>학생 수</span><strong>${summary.student_count ?? 0}명</strong></div>
      <div class="metric"><span>전체 시간 인원</span><strong>${summary.full_min_staff ?? 0}~${summary.full_max_staff ?? 0}명</strong><small>최소 설정 ${summary.full_min_staff_setting ?? summary.full_settings?.min_staff ?? "-"}명 · 2·3순위 교체 ${summary.fallback_swap_count ?? 0}회</small></div>
      <div class="metric"><span>데스크 블록</span><strong>${summary.two_hour_blocks ?? 0}개</strong><small>1시간 ${summary.one_hour_blocks ?? 0}개 · 부족 ${summary.desk_shortage_count ?? 0}칸</small></div>`;

    const warnings = summary.warnings || [];
    document.getElementById("scheduleWarnings").innerHTML = warnings.length
      ? `<div class="alert warning"><strong>배정 참고사항</strong><ul>${warnings.slice(0, 14).map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>${warnings.length > 14 ? `<p>외 ${warnings.length - 14}건은 Excel 생성정보 시트에서 확인할 수 있습니다.</p>` : ""}</div>`
      : '<div class="alert success">현재 설정 조건으로 시간표가 생성되었습니다.</div>';

    renderScheduleTable("fullScheduleTable", run.full_schedule);
    renderScheduleTable("deskScheduleTable", run.desk_schedule);
    document.getElementById("studentAssignmentRows").innerHTML = (run.student_summary || []).map(student => `
      <tr><td>${escapeHtml(student.name)}</td><td>${escapeHtml(student.student_no)}</td><td>${escapeHtml(student.work_type)}형</td><td>${student.target_hours ?? student.full_hours}시간</td><td>${student.full_hours}시간</td><td>${student.desk_hours}시간</td></tr>`).join("");
  }

  async function loadRun() {
    const response = await fetch("/api/admin/demo/latest");
    if (!response.ok) return;
    const {run} = await response.json();
    renderRun(run);
  }

  function renderTwoPersonGrid() {
    document.querySelectorAll(".desk-count-cell:not(.closed)").forEach(button => {
      const key = `${button.dataset.day}:${button.dataset.hour}`;
      const selected = selectedTwoPersonSlots.has(key);
      button.classList.toggle("selected", selected);
      button.textContent = selected ? "2명" : "3명";
    });
  }

  document.querySelectorAll(".desk-count-cell:not(.closed)").forEach(button => button.addEventListener("click", () => {
    const key = `${button.dataset.day}:${button.dataset.hour}`;
    if (selectedTwoPersonSlots.has(key)) selectedTwoPersonSlots.delete(key);
    else selectedTwoPersonSlots.add(key);
    renderTwoPersonGrid();
  }));
  document.getElementById("clearTwoPersonSlots").addEventListener("click", () => {
    selectedTwoPersonSlots.clear();
    renderTwoPersonGrid();
  });

  document.getElementById("saveAccessWindowButton").addEventListener("click", async event => {
    const startAt = document.getElementById("studentAccessStart").value;
    const endAt = document.getElementById("studentAccessEnd").value;
    if (!startAt || !endAt) { showToast("입력 시작과 마감 시간을 모두 선택해 주세요.", true); return; }
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const response = await fetch("/api/admin/student-access", {
        method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({start_at:startAt,end_at:endAt})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail);
      renderStudentAccess(data);
      showToast("학생 입력기간을 저장했습니다. 시작 전·마감 후에는 학생 로그인이 자동 잠금됩니다.");
    } catch (error) { showToast(error.message || "입력기간 저장에 실패했습니다.", true); }
    finally { button.disabled = false; }
  });

  document.getElementById("lockStudentAccessButton").addEventListener("click", async () => {
    if (!confirm("지금 학생 로그인을 잠글까요? 이미 로그인한 학생도 다음 요청부터 더 이상 수정할 수 없습니다.")) return;
    const response = await fetch("/api/admin/student-access/lock", {method:"POST"});
    const data = await response.json();
    if (!response.ok) { showToast(data.detail || "잠금에 실패했습니다.", true); return; }
    renderStudentAccess(data); showToast("학생 로그인을 잠갔습니다.");
  });

  document.getElementById("clearAccessWindowButton").addEventListener("click", async () => {
    if (!confirm("입력기간 설정을 해제하면 학생 로그인이 상시 허용됩니다. 계속할까요?")) return;
    const response = await fetch("/api/admin/student-access", {method:"DELETE"});
    const data = await response.json();
    if (!response.ok) { showToast(data.detail || "기간 설정 해제에 실패했습니다.", true); return; }
    renderStudentAccess(data); showToast("입력기간 설정을 해제했습니다. 학생 로그인이 다시 허용됩니다.");
  });

  document.getElementById("adminEditScheduleButton").addEventListener("click", startAdminScheduleEdit);
  document.getElementById("cancelAdminScheduleEdit").addEventListener("click", cancelAdminScheduleEdit);
  document.getElementById("saveAdminScheduleEdit").addEventListener("click", () => saveAdminScheduleEdit().catch(error => showToast(error.message, true)));
  document.getElementById("closeStudentScheduleModal").addEventListener("click", closeStudentSchedule);
  document.getElementById("studentScheduleModal").addEventListener("click", event => { if (event.target.id === "studentScheduleModal") closeStudentSchedule(); });
  document.getElementById("studentSchedulePopupTable").addEventListener("click", event => editAdminScheduleCell(event.target.closest(".admin-student-schedule-cell")));
  document.querySelectorAll(".admin-schedule-brush").forEach(button => button.addEventListener("click", () => {
    adminScheduleBrush = button.dataset.status;
    document.querySelectorAll(".admin-schedule-brush").forEach(item => item.classList.toggle("active", item === button));
  }));
  document.addEventListener("keydown", event => { if (event.key === "Escape" && document.getElementById("studentScheduleModal").classList.contains("open")) closeStudentSchedule(); });

  document.querySelectorAll(".admin-tab").forEach(button => button.addEventListener("click", () => {
    document.querySelectorAll(".admin-tab").forEach(item => item.classList.toggle("active", item === button));
    document.querySelectorAll(".admin-tab-panel").forEach(panel => panel.classList.toggle("active", panel.id === `tab-${button.dataset.tab}`));
  }));

  document.getElementById("addStudentForm").addEventListener("submit", async event => {
    event.preventDefault();
    const form = new FormData(event.target);
    const payload = {
      name: String(form.get("name") || "").trim(),
      student_no: String(form.get("student_no") || "").trim(),
      work_type: String(form.get("work_type") || ""),
      active: true,
    };
    try {
      const response = await fetch("/api/admin/students", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail);
      event.target.reset();
      showToast("학생을 등록했습니다. 이제 해당 이름과 학번으로 로그인할 수 있습니다.");
      await loadStudents();
      await loadRun();
    } catch (error) {
      showToast(error.message || "학생 등록에 실패했습니다.", true);
    }
  });

  document.getElementById("importForm").addEventListener("submit", async event => {
    event.preventDefault();
    const formData = new FormData(event.target);
    const mode = formData.get("mode");
    if (mode === "sync" && !confirm("전체 명단 동기화를 하면 CSV에 없는 기존 학생은 비활성화됩니다. 계속할까요?")) return;
    const response = await fetch("/api/admin/import-users", {method:"POST", body:formData});
    const data = await response.json();
    if (response.ok) {
      showToast(mode === "sync" ? `${data.count}명 기준으로 전체 명단을 동기화했습니다.` : `${data.count}명의 학생을 추가/수정했습니다.`);
      await loadStudents();
      await loadRun();
    } else showToast(data.detail, true);
  });

  document.getElementById("generateDummyButton").addEventListener("click", async event => {
    if (!confirm("현재 활성 명단을 테스트용 더미학생 40명으로 교체하고 가상 제출 데이터를 생성할까요? 실사용 중에는 사용하지 마세요.")) return;
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "생성 중...";
    try {
      const response = await fetch("/api/admin/demo/generate-students", {method:"POST"});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail);
      showToast(`${data.count}명의 테스트용 더미데이터를 생성했습니다.`);
      await loadStudents();
      renderRun(null);
    } catch (error) {
      showToast(error.message || "더미데이터 생성에 실패했습니다.", true);
    } finally {
      button.disabled = false;
      button.textContent = "40명 더미데이터 생성";
    }
  });

  document.getElementById("generateFullButton").addEventListener("click", async event => {
    const minStaff = Number(document.getElementById("fullMinStaff").value);
    if (!Number.isInteger(minStaff) || minStaff < 1) { showToast("시간당 최소 인원을 입력해 주세요.", true); return; }
    if (latestReadiness && !latestReadiness.ready) {
      showToast(latestReadiness.active_count === 0 ? "먼저 학생 명단을 등록해 주세요." : "활성 학생 전원이 최종 제출한 뒤 생성할 수 있습니다.", true);
      return;
    }
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "전체 시간표 계산 중...";
    try {
      const response = await fetch("/api/admin/demo/generate-full", {
        method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({min_staff:minStaff})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail);
      renderRun(data.run);
      showToast("전체 시간표를 생성했습니다. 2·3순위 교체가 필요한 경우 자동 반영됩니다.");
    } catch (error) {
      showToast(error.message || "전체 시간표 생성에 실패했습니다.", true);
    } finally {
      button.disabled = false;
      button.textContent = "전체 시간표 작성";
    }
  });

  document.getElementById("generateDeskButton").addEventListener("click", async event => {
    const weeklyA = Number(document.getElementById("deskWeeklyMaxA").value);
    const weeklyB = Number(document.getElementById("deskWeeklyMaxB").value);
    const dailyMax = Number(document.getElementById("deskDailyMax").value);
    if (![weeklyA, weeklyB, dailyMax].every(value => Number.isInteger(value) && value >= 1)) {
      showToast("A형·B형 주 최대 데스크 시간과 하루 최대 데스크 시간을 모두 입력해 주세요.", true);
      return;
    }
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "데스크 배정 계산 중...";
    try {
      const response = await fetch("/api/admin/demo/generate-desk", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          weekly_max_a:weeklyA,
          weekly_max_b:weeklyB,
          daily_max:dailyMax,
          two_person_slots:[...selectedTwoPersonSlots]
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail);
      renderRun(data.run);
      showToast("데스크 시간표를 생성했습니다.");
    } catch (error) {
      showToast(error.message || "데스크 시간표 생성에 실패했습니다.", true);
    } finally {
      button.disabled = false;
      button.textContent = "데스크 시간표 작성";
    }
  });

  renderTwoPersonGrid();
  loadStudentAccess();
  loadStudents();
  loadRun();
})();
