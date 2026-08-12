(() => {
  const cfg = window.SCHEDULE_CONFIG;
  const meta = cfg.statusMeta;
  const workStatuses = new Set(["first", "second", "third"]);
  const table = document.getElementById("scheduleTable");
  const toast = document.getElementById("toast");
  const saveState = document.getElementById("saveState");
  const agreement = document.getElementById("agreement");
  const submitButton = document.getElementById("submitButton");
  const draftButton = document.getElementById("draftButton");
  const resetButton = document.getElementById("resetButton");
  const workTypeSelect = document.getElementById("studentWorkType");
  const saveWorkTypeButton = document.getElementById("saveWorkType");
  const weeklyHoursNotice = document.getElementById("weeklyHoursNotice");
  const storageKey = `library-schedule-local-${cfg.studentNo}`;
  let brush = "first";
  let schedule = {};
  let painting = false;
  let dirty = false;
  let lastPainted = null;
  let activePointerId = null;
  let currentWorkType = cfg.workType || "";

  const showToast = (message, error=false) => {
    toast.textContent = message;
    toast.className = `toast show${error ? " error" : ""}`;
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.className = "toast", 2800);
  };

  const setStateLabel = (text, kind="") => {
    saveState.textContent = text;
    saveState.className = `save-state ${kind}`;
  };

  const updateSubmitState = () => {
    submitButton.disabled = !(agreement.checked && ["A", "B"].includes(currentWorkType));
  };

  const defaultSchedule = () => Object.fromEntries(cfg.days.map(day => [day, Object.fromEntries(cfg.hours.map(hour => [String(hour), day === "토" && hour >= 15 ? "closed" : "unselected"]))]));

  const normalize = raw => {
    const result = defaultSchedule();
    if (!raw || typeof raw !== "object") return result;
    cfg.days.forEach(day => cfg.hours.forEach(hour => {
      if (day === "토" && hour >= 15) return;
      const value = raw?.[day]?.[String(hour)];
      if (meta[value] && value !== "closed") result[day][String(hour)] = value;
    }));
    return result;
  };

  const consecutiveIfApplied = (day, hour, status) => {
    const test = {...schedule[day], [String(hour)]: status};
    let current=0, maximum=0;
    cfg.hours.forEach(h => {
      if (workStatuses.has(test[String(h)])) { current += 1; maximum = Math.max(maximum, current); }
      else current = 0;
    });
    return maximum;
  };

  const markDirty = () => {
    dirty = true;
    localStorage.setItem(storageKey, JSON.stringify(schedule));
    setStateLabel("저장되지 않은 변경사항", "dirty");
  };

  const paint = cell => {
    if (!cell || cell.dataset.status === "closed") return;
    const day = cell.dataset.day;
    const hour = Number(cell.dataset.hour);
    if (cell === lastPainted) return;
    lastPainted = cell;
    if (workStatuses.has(brush) && consecutiveIfApplied(day, hour, brush) > cfg.maxConsecutive) {
      showToast("최대 연속 근로는 4시간까지 가능합니다.", true);
      return;
    }
    if (schedule[day][String(hour)] === brush) return;
    schedule[day][String(hour)] = brush;
    renderCell(cell, brush);
    markDirty();
    renderSummary();
  };

  const renderCell = (cell, status) => {
    const item = meta[status];
    cell.dataset.status = status;
    cell.textContent = item.label;
    cell.style.backgroundColor = item.color;
    cell.style.color = item.text;
    cell.classList.toggle("closed", status === "closed");
  };

  const renderAll = () => {
    document.querySelectorAll(".slot").forEach(cell => renderCell(cell, schedule[cell.dataset.day][cell.dataset.hour]));
    renderSummary();
  };

  const firstChoiceTotal = () => {
    let total = 0;
    cfg.days.forEach(day => cfg.hours.forEach(hour => {
      if (schedule?.[day]?.[String(hour)] === "first") total += 1;
    }));
    return total;
  };

  const getWeeklyHourWarnings = () => {
    const limits = cfg.workTypeLimits?.[currentWorkType];
    if (!limits) return [];
    const total = firstChoiceTotal();
    const warnings = [];
    if (total < limits.weekly_min) {
      warnings.push(`${currentWorkType}형 1순위가 ${total}시간입니다. 주 ${limits.weekly_min}시간 미만이면 월 최소 ${limits.monthly_min}시간이 부족할 수 있습니다.`);
    }
    if (total > limits.weekly_max) {
      warnings.push(`${currentWorkType}형 1순위가 ${total}시간입니다. 주 ${limits.weekly_max}시간을 초과하면 월 최대 ${limits.monthly_max}시간을 초과할 수 있습니다.`);
    }
    return warnings;
  };

  const renderWeeklyNotice = () => {
    if (!weeklyHoursNotice) return;
    const limits = cfg.workTypeLimits?.[currentWorkType];
    if (!limits) {
      weeklyHoursNotice.className = "weekly-hours-notice muted-notice";
      weeklyHoursNotice.textContent = "근로유형을 선택하면 유형별 주간 권장시간을 확인할 수 있습니다.";
      return;
    }
    const total = firstChoiceTotal();
    const warnings = getWeeklyHourWarnings();
    if (warnings.length) {
      weeklyHoursNotice.className = "weekly-hours-notice warning";
      weeklyHoursNotice.innerHTML = `<strong>${currentWorkType}형 주간 권장 ${limits.weekly_min}~${limits.weekly_max}시간</strong><span>${warnings.join(" ")}</span>`;
    } else {
      weeklyHoursNotice.className = "weekly-hours-notice ok";
      weeklyHoursNotice.innerHTML = `<strong>${currentWorkType}형 권장 범위</strong><span>현재 1순위 ${total}시간 · 주 ${limits.weekly_min}~${limits.weekly_max}시간 권장</span>`;
    }
  };

  const renderSummary = () => {
    const firstHoursByDay = Object.fromEntries(cfg.days.map(day => [day, 0]));
    cfg.days.forEach(day => cfg.hours.forEach(hour => {
      if (schedule[day][String(hour)] === "first") firstHoursByDay[day] += 1;
    }));
    cfg.days.forEach((day, index) => {
      const dayTotal = document.getElementById(`firstTotal-${index}`);
      if (dayTotal) dayTotal.textContent = `${firstHoursByDay[day]}시간`;
    });
    const overall = Object.values(firstHoursByDay).reduce((sum, hours) => sum + hours, 0);
    const overallTotal = document.getElementById("overallFirstTotal");
    if (overallTotal) overallTotal.textContent = `${overall}시간`;
    renderWeeklyNotice();
  };

  const save = async state => {
    if (state === "submitted" && !["A", "B"].includes(currentWorkType)) {
      throw new Error("최종 제출 전에 근로유형 A 또는 B를 선택해 주세요.");
    }
    if (state === "submitted") {
      const warnings = getWeeklyHourWarnings();
      if (warnings.length) {
        const proceed = confirm(`${warnings.join("\n")}\n\n경고를 확인했습니다. 그래도 최종 제출할까요?`);
        if (!proceed) return;
      }
    }
    const response = await fetch("/api/me/schedule", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({schedule, state})});
    const data = await response.json();
    if (!response.ok) {
      if ([401, 423].includes(response.status)) setTimeout(() => { location.href = "/"; }, 900);
      throw new Error(data.detail || "저장하지 못했습니다.");
    }
    schedule = normalize(data.schedule);
    localStorage.removeItem(storageKey);
    dirty = false;
    setStateLabel(state === "submitted" ? "최종 제출 완료" : "임시저장 완료", "saved");
    if (state === "submitted" && data.warnings?.length) {
      showToast("최종 제출되었습니다. 근로시간 경고 내용을 확인해 주세요.");
    } else {
      showToast(state === "submitted" ? "최종 제출되었습니다." : "임시저장되었습니다.");
    }
    renderSummary();
  };

  const saveWorkType = async () => {
    const value = workTypeSelect.value;
    if (!["A", "B"].includes(value)) throw new Error("A형 또는 B형을 선택해 주세요.");
    const response = await fetch("/api/me/work-type", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({work_type:value})});
    const data = await response.json();
    if (!response.ok) {
      if ([401, 423].includes(response.status)) setTimeout(() => { location.href = "/"; }, 900);
      throw new Error(data.detail || "근로유형을 저장하지 못했습니다.");
    }
    currentWorkType = data.work_type;
    updateSubmitState();
    renderWeeklyNotice();
    showToast(`${currentWorkType}형으로 저장했습니다.`);
  };

  const load = async () => {
    const response = await fetch("/api/me/schedule");
    if (!response.ok) { location.href = "/"; return; }
    const data = await response.json();
    currentWorkType = data.work_type || "";
    workTypeSelect.value = currentWorkType;
    schedule = normalize(data.schedule);
    const local = localStorage.getItem(storageKey);
    if (local) {
      try {
        schedule = normalize(JSON.parse(local));
        dirty = true;
        setStateLabel("이 기기의 미저장 변경 복구", "dirty");
        showToast("이 기기에 남아 있던 미저장 내용을 복구했습니다.");
      } catch (_) { localStorage.removeItem(storageKey); }
    } else if (data.state === "submitted") setStateLabel("최종 제출 완료", "saved");
    else if (data.state === "draft") setStateLabel("임시저장 불러옴", "saved");
    else setStateLabel("아직 저장하지 않음");
    renderAll();
    updateSubmitState();
  };

  document.querySelectorAll(".brush").forEach(button => button.addEventListener("click", () => {
    brush = button.dataset.status;
    document.querySelectorAll(".brush").forEach(item => item.classList.toggle("active", item === button));
  }));

  table.addEventListener("pointerdown", event => {
    const cell = event.target.closest(".slot");
    if (!cell || cell.dataset.status === "closed") return;
    event.preventDefault();
    painting = true;
    activePointerId = event.pointerId;
    lastPainted = null;
    try { table.setPointerCapture(event.pointerId); } catch (_) {}
    paint(cell);
  });
  table.addEventListener("pointermove", event => {
    if (!painting || event.pointerId !== activePointerId) return;
    event.preventDefault();
    const cell = document.elementFromPoint(event.clientX,event.clientY)?.closest?.(".slot");
    if (cell) paint(cell);
  });
  const endPainting = event => {
    if (!painting) return;
    painting = false;
    lastPainted = null;
    try { if (activePointerId !== null) table.releasePointerCapture(activePointerId); } catch (_) {}
    activePointerId = null;
  };
  table.addEventListener("pointerup", endPainting);
  table.addEventListener("pointercancel", endPainting);
  window.addEventListener("pointerup", endPainting);
  table.addEventListener("contextmenu", event => event.preventDefault());

  agreement.addEventListener("change", updateSubmitState);
  workTypeSelect.addEventListener("change", () => {
    if (workTypeSelect.value !== currentWorkType) showToast("유형 저장 버튼을 눌러 선택을 확정해 주세요.");
  });
  saveWorkTypeButton.addEventListener("click", () => saveWorkType().catch(error => showToast(error.message, true)));
  draftButton.addEventListener("click", () => save("draft").catch(error => showToast(error.message,true)));
  submitButton.addEventListener("click", () => save("submitted").catch(error => showToast(error.message,true)));
  resetButton.addEventListener("click", () => {
    if (!confirm("모든 선택을 미선택 상태로 되돌릴까요? 서버에 저장하려면 이후 저장 버튼을 눌러야 합니다.")) return;
    schedule = defaultSchedule(); markDirty(); renderAll();
  });

  window.addEventListener("beforeunload", event => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
  load().catch(error => showToast(error.message,true));
})();
