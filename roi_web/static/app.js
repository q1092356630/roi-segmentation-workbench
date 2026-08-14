const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const ui = {
  workspace: $('.workspace'), leftPanel: $('.left-panel'), rightPanel: $('.right-panel'),
  moduleTabs: $$('.module-tab'), moduleContext: $('#module-context'), roiModulePanel: $('#roi-module-panel'),
  vascularModulePanel: $('#vascular-module-panel'), roiEditToolbar: $('#roi-edit-toolbar'),
  leftPanelResizer: $('#left-panel-resizer'), rightPanelResizer: $('#right-panel-resizer'),
  rootPath: $('#root-path'), scanRoot: $('#scan-root'), caseList: $('#case-list'), caseCount: $('#case-count'),
  caseSearch: $('#case-search'), statusFilter: $('#status-filter'), roiFileCountFilter: $('#roi-file-count-filter'), viewport: $('#viewport'), content: $('#viewport-content'),
  empty: $('#viewport-empty'), loading: $('#loading'), image: $('#slice-image'), canvas: $('#interaction-canvas'),
  themeSelect: $('#theme-select'), visualizationLayout: $('#visualization-layout'), render3d: $('#render-3d'),
  standardViewerToolbar: $('#standard-viewer-toolbar'), standardViewerFooter: $('#standard-viewer-footer'),
  roi3dPanel: $('#roi-3d-panel'), roi3dCanvas: $('#roi-3d-canvas'), roi3dEmpty: $('#roi-3d-empty'),
  roi3dLoading: $('#roi-3d-loading'), roi3dOpacity: $('#roi-3d-opacity'),
  roi3dOpacityValue: $('#roi-3d-opacity-value'), roi3dStatus: $('#roi-3d-status'),
  roi3dRoiList: $('#roi-3d-roi-list'), roi3dSelectionCount: $('#roi-3d-selection-count'),
  roi3dSelectAll: $('#roi-3d-select-all'), roi3dClearAll: $('#roi-3d-clear-all'),
  reset3dView: $('#reset-3d-view'), close3d: $('#close-3d'),
  sliceSlider: $('#slice-slider'), sliceText: $('#slice-text'), level: $('#window-level'), width: $('#window-width'),
  displaySummary: $('#display-summary'), modalityMode: $('#modality-mode'), modalityBadge: $('#modality-badge'),
  ctControls: $('#ct-display-controls'), mrControls: $('#mr-display-controls'), windowPreset: $('#window-preset'),
  mrBrightness: $('#mr-brightness'), mrBrightnessValue: $('#mr-brightness-value'), mrContrast: $('#mr-contrast'),
  mrContrastValue: $('#mr-contrast-value'), mrWindowHint: $('#mr-window-hint'), pinDisplay: $('#pin-display'),
  clearPinnedDisplay: $('#clear-pinned-display'), resetDisplay: $('#reset-display'), displayStatus: $('#display-status'),
  geometry: $('#geometry-text'), labelSelect: $('#label-select'), labelLock: $('#label-lock'), labelColor: $('#label-color'),
  roiFileSelection: $('#roi-file-selection'), maskSelect: $('#mask-select'), importMask: $('#import-mask'), loadEditableRoi: $('#load-editable-roi'), loadInteractiveReference: $('#load-interactive-reference'), brushSize: $('#brush-size'), brushValue: $('#brush-size-value'), promptRadius: $('#prompt-radius'), promptRadiusValue: $('#prompt-radius-value'),
  activateKeepComponent: $('#activate-keep-component'), intensityPreset: $('#intensity-preset'), intensityMin: $('#intensity-min'), intensityMax: $('#intensity-max'), intensityScope: $('#intensity-scope'), excludeIntensity: $('#exclude-intensity'),
  opacity: $('#roi-opacity'), opacityNumber: $('#roi-opacity-number'), overlayMode: $('#overlay-mode'),
  overlayModeButtons: $('#overlay-mode-buttons'), boundaryWidthControls: $('#boundary-width-controls'),
  boundaryWidth: $('#boundary-width'), boundaryWidthValue: $('#boundary-width-value'),
  modelSelect: $('#model-select'), modelStatus: $('#model-status'),
  addPositivePoint: $('#add-positive-point'), addNegativePoint: $('#add-negative-point'), runPointRefine: $('#run-point-refine'), clearPointPrompts: $('#clear-point-prompts'), pointPromptStatus: $('#point-prompt-status'),
  taskDot: $('#task-dot'), cancelTask: $('#cancel-task'), toast: $('#toast'),
  workflowCaseStep: $('#workflow-case-step'), workflowReferenceStep: $('#workflow-reference-step'),
  workflowEditStep: $('#workflow-edit-step'), workflowSaveStep: $('#workflow-save-step'),
  workflowCaption: $('#workflow-caption'),
  markerTop: $('#marker-top'), markerBottom: $('#marker-bottom'), markerLeft: $('#marker-left'), markerRight: $('#marker-right'),
  roiName: $('#roi-name'), roiLayerList: $('#roi-layer-list'), roiVisibilityCount: $('#roi-visibility-count'),
  showAllRoi: $('#show-all-roi'), hideAllRoi: $('#hide-all-roi'),
  restoreOriginal: $('#restore-original'), workspaceState: $('#workspace-state'),
  trimRoiLeft: $('#trim-roi-left'), trimRoiRight: $('#trim-roi-right'), rangeOperationLog: $('#range-operation-log'),
  vascularTaskDot: $('#vascular-task-dot'), vascularCurrentCase: $('#vascular-current-case'),
  vascularModelButtons: $$('.vascular-model-switch [data-vascular-model]'),
  vascularModelKicker: $('#vascular-model-kicker'), vascularModelTitle: $('#vascular-model-title'),
  vascularModelDescription: $('#vascular-model-description'), vascularModelContract: $('#vascular-model-contract'),
  vascularContractModel: $('#vascular-contract-model'), vascularContractInput: $('#vascular-contract-input'),
  vascularContractOutput: $('#vascular-contract-output'), vascularContractPurpose: $('#vascular-contract-purpose'),
  vascularExecutionDescription: $('#vascular-execution-description'), vascularSafetyNote: $('#vascular-safety-note'),
  vascularFooterTitle: $('#vascular-footer-title'), vascularFooterDescription: $('#vascular-footer-description'),
  vascularReadiness: $('#vascular-readiness'), vascularCurrentPath: $('#vascular-current-path'),
  vascularRunCurrent: $('#vascular-run-current'), vascularRunBatch: $('#vascular-run-batch'),
  vascularBatchSummary: $('#vascular-batch-summary'), vascularTaskPanel: $('#vascular-task-panel'),
  vascularTaskState: $('#vascular-task-state'), vascularProgress: $('#vascular-progress'),
  vascularProgressLabel: $('#vascular-progress-label'), vascularStage: $('#vascular-stage'),
  vascularCurrentPatient: $('#vascular-current-patient'), vascularCountCompleted: $('#vascular-count-completed'),
  vascularCountFailed: $('#vascular-count-failed'), vascularCountSkipped: $('#vascular-count-skipped'),
  vascularOutputBlock: $('#vascular-output-block'), vascularOutputPath: $('#vascular-output-path'),
  vascularBackupPath: $('#vascular-backup-path'), vascularQualityAlert: $('#vascular-quality-alert'),
  vascularQualityFlag: $('#vascular-quality-flag'), vascularQualityNote: $('#vascular-quality-note'), vascularError: $('#vascular-error'),
  vascularResults: $('#vascular-results'), vascularResultList: $('#vascular-result-list'),
  vascularCancel: $('#vascular-cancel'),
  vascularRoiSelect: $('#vascular-roi-select'), vascularRoiLoad: $('#vascular-roi-load'),
  vascularRender3d: $('#vascular-render-3d'), vascularRoiVisualStatus: $('#vascular-roi-visual-status'),
  vascularRoiLayerList: $('#vascular-roi-layer-list'), vascularRoiVisibilityCount: $('#vascular-roi-visibility-count'),
  vascularRoiShowAll: $('#vascular-roi-show-all'), vascularRoiHideAll: $('#vascular-roi-hide-all'),
};

const state = {
  cases: [], session: null, orientation: 'axial', indices: { axial: 0, coronal: 0, sagittal: 0 },
  tool: 'pan', zoom: 1, panX: 0, panY: 0, pointerMode: null, pointerId: null,
  startPoint: null, draftPoints: [], polygonPoints: [], promptVisuals: [], hoverPoint: null,
  wwStart: null, level: 40, width: 400, mrBrightness: 0, mrContrast: 100,
  displayModality: 'CT', activeTask: null, renderToken: 0, imageUrl: null,
  sliceRequestControllers: new Map(), sliceCommittedToken: 0,
  sliceSliderInteracting: false, sliceSliderPointerId: null, roiSelectionRequestId: 0,
  displayedSlice: { caseId: '', orientation: '', index: -1 },
  expandedPatients: new Set(), loadedRoiPath: '', selectedRoiFiles: new Set(),
  hiddenLayerKeys: new Set(), hiddenLabelIds: new Set(), layerOpacities: new Map(),
  panelWidths: { left: null, right: null },
  renderer3d: null, mesh3d: null, mesh3dLoading: false, mesh3dRequestToken: 0,
  roi3dSelectedLayerKeys: new Set(), roi3dColors: new Map(), roi3dSessionToken: '',
  activeModule: 'roi', vascularModel: 'hepatic_artery', vascularStatus: null, vascularRequestToken: 0,
  vascularTaskId: null, vascularHandledTasks: new Set(),
  vascularTaskLaunchIdentities: new Map(), vascularPendingVisualizations: new Map(),
  vascularPollTaskId: '', vascularPollGeneration: 0, vascularAutoVisualizeInFlight: false,
  vascularModuleRefreshInFlight: false,
};

const CASE_STORAGE_KEY = 'roi-web-active-case';
const SESSION_STORAGE_KEY = 'roi-web-session-token';
const DISPLAY_PROFILE_KEY = 'roi-web-fixed-display-v1';
const ROOT_STORAGE_KEY = 'roi-web-last-root-v1';
const ROI_NAME_KEY = 'roi-web-roi-name-v1';
const ROI_OPACITY_KEY = 'roi-web-roi-opacity-v1';
const ROI_OVERLAY_MODE_KEY = 'roi-web-overlay-mode-v1';
const ROI_BOUNDARY_WIDTH_KEY = 'roi-web-boundary-width-v1';
const PANEL_LAYOUT_KEY = 'roi-web-panel-layout-v3';
const THEME_KEY = 'roi-web-theme-v1';
const ROI_3D_STYLE_KEY = 'roi-web-3d-style-v1';
const ACTIVE_MODULE_KEY = 'roi-web-active-module-v1';
const VASCULAR_MODEL_CONFIG = {
  hepatic_artery: {
    key: 'hepatic_artery', label: '肝动脉分割', kicker: 'HEPATIC ARTERY · ORIGINAL',
    title: '肝动脉自动勾画', description: '原 HA 专用 nnU-Net 与肝脏约束后处理，生成肝动脉及肝内可见分支。',
    model: 'HA 专用 nnU-Net', input: '腹部动脉期增强 CT', output: '肝动脉二值 ROI', purpose: '原工作流 · 需人工复核',
    outputFilename: 'roi.nii.gz', runLabel: '一键生成肝动脉 ROI', runningLabel: '肝动脉分割运行中',
    execution: '运行原肝动脉模型；批量模式按患者串行占用 GPU，单例失败不影响后续患者。',
    safety: '<strong>原功能已恢复：</strong>肝动脉结果保存为 <code>roi.nii.gz</code>；已有结果会先备份，再通过几何与连续性质控后原子替换。',
    visual: '肝动脉分割完成后会载入 roi.nii.gz；也可选择全腹动脉或其它 ROI 对照。',
    taskIdle: '尚未启动肝动脉分割。', footerTitle: '肝动脉专用分割 + 肝脏约束与连续性修补',
    footer: '原工作流完整保留，输出肝动脉及肝内可见分支；厚层恢复结果和远端细小分支必须逐层复核。',
    batchConfirm: '腹部动脉期 CT',
  },
  abdominal_artery: {
    key: 'abdominal_artery', label: '全腹动脉分割', kicker: 'ABDOMINAL ARTERIES · BVM 2026',
    title: '全腹动脉自动勾画', description: 'SkeletonRecall 五折 ensemble + TTA，从薄层动脉期腹部增强 CT 生成全腹动脉二值树。',
    model: 'BVM 2026 · SkeletonRecall', input: '薄层动脉期增强 CT', output: '全腹动脉二值预标注', purpose: '科研初稿 · 必须人工复核',
    outputFilename: 'abdominal_arteries_roi.nii.gz', runLabel: '一键生成全腹动脉树', runningLabel: '全腹动脉分割运行中',
    execution: '确认当前影像为薄层动脉期后运行；批量模式按患者串行占用 GPU，单例失败不影响后续患者。',
    safety: '<strong>新增功能：</strong>全腹动脉结果保存为 <code>abdominal_arteries_roi.nii.gz</code>；已有同名结果先备份，原肝动脉 <code>roi.nii.gz</code> 不会被覆盖。',
    visual: '全腹动脉分割完成后会载入 abdominal_arteries_roi.nii.gz；也可选择原肝动脉 ROI 对照。',
    taskIdle: '尚未启动全腹动脉分割。', footerTitle: '全腹动脉预标注 + 几何与连续性质控',
    footer: '覆盖主动脉、腹腔干、SMA、IMA 及可见分支；不自动命名分支，也不识别肿瘤供血支，必须逐层复核。',
    batchConfirm: '薄层动脉期腹部增强 CT',
  },
};
const VASCULAR_OUTPUT_FILENAME = VASCULAR_MODEL_CONFIG.abdominal_artery.outputFilename;
const VASCULAR_LEGACY_OUTPUT_FILENAME = VASCULAR_MODEL_CONFIG.hepatic_artery.outputFilename;
const PANEL_DEFAULTS = { left: 256, right: 520 };
const PANEL_LIMITS = { left: [210, 520], right: [300, 720], center: 420 };
const STATUS_CLASS = { '未开始': 'not-started', '待审核': 'pending', '修补中': 'repairing', '已完成': 'reviewed', '失败': 'failed' };
const MANUAL_EDIT_TOOLS = new Set(['brush', 'eraser', 'polygon', 'fill', 'keep_component']);

function activeCaseId() { return state.session?.case_id || sessionStorage.getItem(CASE_STORAGE_KEY) || ''; }
function activeSessionToken() { return state.session?.session_token || sessionStorage.getItem(SESSION_STORAGE_KEY) || ''; }
function normalizeLocalPath(value) {
  return String(value || '').trim().replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase();
}
function caseHeaders() {
  const caseId = activeCaseId(), token = activeSessionToken();
  return caseId && token ? { 'X-ROI-Case-ID': caseId, 'X-ROI-Session-ID': token } : {};
}

function readDisplayProfiles() {
  try {
    const value = JSON.parse(localStorage.getItem(DISPLAY_PROFILE_KEY) || '{}');
    return value && typeof value === 'object' ? value : {};
  } catch (_error) { return {}; }
}

function writeDisplayProfiles(profiles) {
  localStorage.setItem(DISPLAY_PROFILE_KEY, JSON.stringify(profiles));
}

function requestError(message, { status = 0, networkError = false, cause = null, details = null } = {}) {
  const error = new Error(message);
  error.status = Number(status) || 0;
  error.networkError = Boolean(networkError);
  error.details = details && typeof details === 'object' ? details : {};
  if (cause) error.cause = cause;
  return error;
}

function isAbortError(error) {
  return error?.name === 'AbortError';
}

async function api(path, options = {}) {
  const headers = { ...caseHeaders(), ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) };
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers,
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw requestError(error?.message || '网络请求失败', { networkError: true, cause: error });
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw requestError(body.detail || `请求失败 (${response.status})`, { status: response.status, details: body.meta });
  }
  if (response.status === 204) return null;
  return response.json();
}

function post(path, data = {}) { return api(path, { method: 'POST', body: JSON.stringify(data) }); }

let toastTimer = null;
function toast(message, error = false) {
  clearTimeout(toastTimer);
  ui.toast.textContent = message;
  ui.toast.classList.toggle('error', error);
  ui.toast.setAttribute('role', error ? 'alert' : 'status');
  ui.toast.setAttribute('aria-live', error ? 'assertive' : 'polite');
  ui.toast.classList.remove('hidden');
  toastTimer = setTimeout(() => ui.toast.classList.add('hidden'), error ? 6500 : 3500);
}

function setLoading(visible, text = '正在读取') {
  ui.loading.classList.toggle('hidden', !visible);
  const label = ui.loading.querySelector('b');
  if (label) label.textContent = text;
}

function currentOrientation() { return state.session?.orientations?.[state.orientation]; }
function currentIndex() { return state.indices[state.orientation] || 0; }
function displayRoiSource(sourceFile) {
  return String(sourceFile || '').startsWith('@working/') ? '新建半自动 ROI' : sourceFile;
}
function syncSliceSliderValue(index = currentIndex(), force = false) {
  if (state.sliceSliderInteracting && !force) return;
  ui.sliceSlider.value = String(index);
}
function beginSliceSliderInteraction(event) {
  state.sliceSliderInteracting = true;
  state.sliceSliderPointerId = Number.isFinite(event?.pointerId) ? event.pointerId : null;
}
function finishSliceSliderInteraction(event) {
  const pointerId = Number.isFinite(event?.pointerId) ? event.pointerId : null;
  if (pointerId !== null && state.sliceSliderPointerId !== null && pointerId !== state.sliceSliderPointerId) return;
  if (!state.sliceSliderInteracting) return;
  state.sliceSliderInteracting = false;
  state.sliceSliderPointerId = null;
  syncSliceSliderValue(currentIndex(), true);
  scheduleSlice(0);
}
function currentLabelId() { return Number(ui.labelSelect.value || 1); }
function currentLayer() {
  const option = ui.labelSelect.selectedOptions?.[0];
  const layerKey = option?.dataset?.layerKey || '';
  return (state.session?.layers || state.session?.labels || []).find(layer => layer.layer_key === layerKey)
    || (state.session?.layers || state.session?.labels || []).find(layer => Number(layer.id) === currentLabelId());
}
function currentLayerKey() { return currentLayer()?.layer_key || ''; }
function layerIdentityPayload() { return { label_id: currentLabelId(), layer_key: currentLayerKey() }; }
function sessionLayers() { return state.session?.layers || state.session?.labels || []; }
function visibleRoiLabelIds() {
  return sessionLayers()
    .map(label => Number(label.id))
    .filter(labelId => {
      const layer = sessionLayers().find(item => Number(item.id) === labelId);
      return layer?.layer_key ? !state.hiddenLayerKeys.has(layer.layer_key) : !state.hiddenLabelIds.has(labelId);
    })
    .sort((left, right) => left - right);
}
function allRoiLabelIds() { return sessionLayers().map(label => Number(label.id)).sort((left, right) => left - right); }
function allRoiLayerKeys() { return sessionLayers().map(layer => layer.layer_key || String(layer.id)); }
function ensure3dSelectionState() {
  const sessionToken = state.session?.session_token || '';
  const labels = sessionLayers();
  if (state.roi3dSessionToken !== sessionToken) {
    state.roi3dSessionToken = sessionToken;
    state.roi3dSelectedLayerKeys = new Set(labels.filter(layer => !state.hiddenLayerKeys.has(layer.layer_key)).map(layer => layer.layer_key));
    state.roi3dColors = new Map(labels.map(label => [label.layer_key || String(label.id), label.color || '#2cb7a4']));
    return;
  }
  const validKeys = new Set(labels.map(label => label.layer_key || String(label.id)));
  state.roi3dSelectedLayerKeys = new Set([...state.roi3dSelectedLayerKeys].filter(layerKey => validKeys.has(layerKey)));
  labels.forEach(label => {
    const layerKey = label.layer_key || String(label.id);
    if (!state.roi3dColors.has(layerKey)) state.roi3dColors.set(layerKey, label.color || '#2cb7a4');
  });
}
function selectedRoi3dLayers() {
  ensure3dSelectionState();
  return sessionLayers().filter(layer => state.roi3dSelectedLayerKeys.has(layer.layer_key || String(layer.id)));
}
function selectedRoi3dLabelIds() { return selectedRoi3dLayers().map(layer => Number(layer.id)); }
function roi3dColorFor(layerOrId) {
  const label = typeof layerOrId === 'object' ? layerOrId : sessionLayers().find(item => Number(item.id) === Number(layerOrId));
  const layerKey = label?.layer_key || String(label?.id ?? layerOrId);
  return state.roi3dColors.get(layerKey) || label?.color || '#2cb7a4';
}
function render3dRoiSelector() {
  ensure3dSelectionState();
  const labels = sessionLayers();
  const selectedLayers = selectedRoi3dLayers();
  const selectedIds = selectedLayers.map(layer => Number(layer.id));
  ui.roi3dSelectionCount.textContent = `${selectedIds.length} / ${labels.length}`;
  ui.roi3dSelectAll.disabled = !labels.length || selectedIds.length === labels.length;
  ui.roi3dClearAll.disabled = !selectedIds.length;
  ui.roi3dRoiList.innerHTML = labels.length ? labels.map(label => {
    const labelId = Number(label.id);
    const layerKey = label.layer_key || String(label.id);
    const selected = state.roi3dSelectedLayerKeys.has(layerKey);
    const name = label.display_name || label.name;
    const visibilityId = `roi-3d-visible-${encodeURIComponent(layerKey).replace(/%/g, '')}`;
    return `<div class="roi-3d-roi-row ${selected ? 'is-selected' : ''}" title="${selected ? '取消 3D 显示' : '加入 3D 显示'}：${escapeHtml(name)}">
      <input id="${visibilityId}" type="checkbox" data-roi-3d-visibility="${escapeHtml(layerKey)}" data-layer-key="${escapeHtml(layerKey)}" ${selected ? 'checked' : ''} aria-label="3D 显示 ${escapeHtml(name)}">
      <input type="color" data-roi-3d-color="${escapeHtml(layerKey)}" data-layer-key="${escapeHtml(layerKey)}" value="${escapeHtml(roi3dColorFor(label))}" aria-label="${escapeHtml(name)} 的 3D 颜色" title="设置 ${escapeHtml(name)} 的 3D 颜色">
      <label class="roi-3d-roi-name" for="${visibilityId}">${escapeHtml(displayRoiSource(label.source_file))} · ${label.source_label_id ?? labelId}: ${escapeHtml(name)}</label>
    </div>`;
  }).join('') : '<span class="roi-3d-selector-empty">当前病例没有 ROI 标签</span>';
}
function currentLabelColor() {
  return state.session?.labels.find(label => label.id === currentLabelId())?.color || '#ff3b30';
}

function read3dStyle() {
  try {
    const value = JSON.parse(localStorage.getItem(ROI_3D_STYLE_KEY) || '{}');
    return value && typeof value === 'object' ? value : {};
  } catch (_error) { return {}; }
}

function persist3dStyle() {
  localStorage.setItem(ROI_3D_STYLE_KEY, JSON.stringify({
    opacity: Number(ui.roi3dOpacity.value),
  }));
}

function applyTheme(theme, persist = true) {
  const value = theme === 'light' ? 'light' : 'dark';
  document.documentElement.dataset.theme = value;
  ui.themeSelect.value = value;
  state.renderer3d?.setTheme(value);
  if (persist) localStorage.setItem(THEME_KEY, value);
}

function set3dEmpty(title, detail) {
  const heading = ui.roi3dEmpty.querySelector('strong');
  const copy = ui.roi3dEmpty.querySelector('span');
  if (heading) heading.textContent = title;
  if (copy) copy.textContent = detail;
  ui.roi3dEmpty.classList.remove('hidden');
}

function set3dLoading(visible) {
  state.mesh3dLoading = visible;
  ui.roi3dLoading.classList.toggle('hidden', !visible);
  const disabled = visible || !state.session || allRoiLabelIds().length === 0;
  ui.render3d.disabled = disabled;
  ui.vascularRender3d.disabled = disabled;
  ui.render3d.textContent = visible ? '正在生成…' : state.mesh3d ? '重新渲染 3D' : '3D 渲染';
  ui.vascularRender3d.textContent = visible ? '正在生成…' : state.mesh3d ? '重新渲染 3D' : '3D 渲染';
}

function ensure3dRenderer() {
  if (state.renderer3d) return state.renderer3d;
  if (typeof window.Roi3DRenderer !== 'function') throw new Error('本地 3D 渲染模块未加载；请刷新页面后重试');
  state.renderer3d = new window.Roi3DRenderer(ui.roi3dCanvas);
  state.renderer3d.setOpacity(Number(ui.roi3dOpacity.value) / 100);
  state.renderer3d.setTheme(document.documentElement.dataset.theme || 'dark');
  return state.renderer3d;
}

function show3dPanel() {
  render3dRoiSelector();
  ui.roi3dPanel.classList.remove('hidden');
  ui.visualizationLayout.classList.add('show-3d');
  requestAnimationFrame(() => {
    fitViewport();
    state.renderer3d?.resize();
  });
}

function close3dPanel(clear = false) {
  clearTimeout(roi3dSelectionTimer);
  ui.roi3dPanel.classList.add('hidden');
  ui.visualizationLayout.classList.remove('show-3d');
  state.mesh3dRequestToken += 1;
  if (clear) {
    state.mesh3d = null;
    state.renderer3d?.clearMesh();
    state.roi3dSelectedLayerKeys.clear();
    state.roi3dColors.clear();
    state.roi3dSessionToken = '';
    render3dRoiSelector();
    ui.roi3dStatus.textContent = '尚未生成';
    set3dEmpty('选择需要显示的 ROI', '在上方列表中可单选或多选，并为每个 ROI 设置独立颜色。');
  }
  set3dLoading(false);
  requestAnimationFrame(fitViewport);
}

function sync3dSnapshotState() {
  const disabled = state.mesh3dLoading || !state.session || allRoiLabelIds().length === 0;
  ui.render3d.disabled = disabled;
  ui.vascularRender3d.disabled = disabled;
  if (!state.mesh3d || ui.roi3dPanel.classList.contains('hidden')) return;
  const selectedLayers = selectedRoi3dLayers();
  const selectedIds = selectedLayers.map(layer => Number(layer.id));
  const selectionChanged = state.mesh3d.layerKeys?.join(',') !== selectedLayers.map(layer => layer.layer_key).join(',');
  const revisionChanged = state.mesh3d.revision !== state.session?.revision;
  const suffix = selectionChanged ? ' · 3D 选择已改变，正在刷新' : revisionChanged ? ' · 工作层已更新，请重新渲染' : '';
  ui.roi3dStatus.textContent = `${state.mesh3d.summary}${suffix}`;
}

async function renderCurrentRoi3d() {
  if (!roiVisualizationEnabled()) return toast('当前模块不能生成 3D', true);
  if (!state.session) return toast('请先载入病例', true);
  show3dPanel();
  const selectedLayers = selectedRoi3dLayers();
  const labelIds = selectedLayers.map(layer => Number(layer.id));
  if (!selectedLayers.length) {
    state.mesh3dRequestToken += 1;
    state.mesh3d = null;
    state.renderer3d?.clearMesh();
    ui.roi3dStatus.textContent = '尚未选择 3D ROI';
    set3dEmpty('选择需要显示的 ROI', '在上方列表中勾选一个或多个 ROI。');
    set3dLoading(false);
    return;
  }
  set3dLoading(true);
  ui.roi3dEmpty.classList.add('hidden');
  const requestToken = ++state.mesh3dRequestToken;
  const requestCaseId = state.session.case_id;
  const requestSessionToken = state.session.session_token;
  try {
    const results = await Promise.allSettled(selectedLayers.map(layer => api(`/api/roi-mesh?label_id=${layer.id}&layer_key=${encodeURIComponent(layer.layer_key || '')}`)));
    if (
      requestToken !== state.mesh3dRequestToken
      || state.session?.case_id !== requestCaseId
      || state.session?.session_token !== requestSessionToken
    ) return;
    const meshes = results.filter(result => result.status === 'fulfilled').map(result => result.value);
    if (!meshes.length) {
      const firstFailure = results.find(result => result.status === 'rejected');
      throw firstFailure?.reason || new Error('已选择 ROI 中没有可生成的三维区域');
    }
    const meshRevisions = new Set(meshes.map(mesh => Number(mesh.revision)));
    if (meshRevisions.size !== 1 || !meshRevisions.has(Number(state.session.revision))) {
      throw new Error('工作层在生成 3D 期间已更新，请重新渲染');
    }
    const renderer = ensure3dRenderer();
    renderer.setMeshes(meshes.map(mesh => ({
      ...mesh,
      render_color: roi3dColorFor(sessionLayers().find(layer => layer.layer_key === mesh.layer_key) || mesh.label_id),
    })));
    renderer.setOpacity(Number(ui.roi3dOpacity.value) / 100);
    ui.roi3dEmpty.classList.add('hidden');
    const voxelCount = meshes.reduce((sum, mesh) => sum + Number(mesh.voxel_count || 0), 0);
    const triangleCount = meshes.reduce((sum, mesh) => sum + Number(mesh.triangle_count || 0), 0);
    const meshNames = meshes.map(mesh => `${mesh.source_file || ''} [${mesh.source_label_id}]: ${mesh.label_name}`).join(' / ');
    const skippedCount = results.length - meshes.length;
    const approximation = meshes.some(mesh => mesh.downsampled) ? ' · 已降采样' : '';
    const skipped = skippedCount ? ` · 跳过 ${skippedCount} 个空 ROI` : '';
    const shownCount = skippedCount ? `显示 ${meshes.length} / 选择 ${labelIds.length} 个 ROI` : `3D 显示 ${meshes.length} 个 ROI`;
    const summary = `${shownCount} · ${meshNames} · R${state.session.revision} · ${voxelCount.toLocaleString('zh-CN')} 体素 · ${triangleCount.toLocaleString('zh-CN')} 面${approximation}${skipped}`;
    state.mesh3d = { labelIds: [...labelIds], layerKeys: selectedLayers.map(layer => layer.layer_key), revision: state.session.revision, summary, meshCount: meshes.length };
    ui.roi3dStatus.textContent = summary;
    ui.render3d.textContent = '重新渲染 3D';
    ui.vascularRender3d.textContent = '重新渲染 3D';
  } catch (error) {
    if (requestToken !== state.mesh3dRequestToken) return;
    state.mesh3d = null;
    state.renderer3d?.clearMesh();
    set3dEmpty('暂时无法生成 3D', error.message);
    ui.roi3dStatus.textContent = '生成失败';
    toast(error.message, true);
  } finally {
    if (requestToken === state.mesh3dRequestToken) set3dLoading(false);
  }
}

let roi3dSelectionTimer = null;
function schedule3dSelectionRender(delay = 120) {
  sync3dSnapshotState();
  if (ui.roi3dPanel.classList.contains('hidden')) return;
  clearTimeout(roi3dSelectionTimer);
  state.mesh3dRequestToken += 1;
  state.mesh3d = null;
  state.renderer3d?.clearMesh();
  const selectedLayers = selectedRoi3dLayers();
  if (!selectedLayers.length) {
    ui.roi3dStatus.textContent = '尚未选择 3D ROI';
    set3dEmpty('选择需要显示的 ROI', '在上方列表中勾选一个或多个 ROI。');
    set3dLoading(false);
    return;
  }
  ui.roi3dStatus.textContent = '正在同步 3D ROI 选择';
  set3dEmpty('正在同步 3D ROI', '未选择的表面已清除。');
  set3dLoading(true);
  roi3dSelectionTimer = setTimeout(renderCurrentRoi3d, delay);
}

function setWorkflowStep(element, stepState = '') {
  if (!element) return;
  element.classList.remove('is-complete', 'is-current', 'is-attention');
  if (stepState) element.classList.add(`is-${stepState}`);
}

function setStatusChip(element, ready, readyText, missingText) {
  if (!element) return;
  element.classList.toggle('is-ready', Boolean(ready));
  element.classList.toggle('is-missing', !ready);
  element.textContent = ready ? readyText : missingText;
}

const VASCULAR_TERMINAL_STATES = new Set(['completed', 'completed_with_failures', 'failed', 'cancelled']);

function currentVascularModel() {
  return VASCULAR_MODEL_CONFIG[state.vascularModel] || VASCULAR_MODEL_CONFIG.hepatic_artery;
}

function vascularModelForOutput(relativePath) {
  const name = String(relativePath || '').replace(/\\/g, '/').split('/').at(-1)?.toLowerCase() || '';
  return name === VASCULAR_OUTPUT_FILENAME ? 'abdominal_artery' : 'hepatic_artery';
}

function vascularApiUrl(path, model = state.vascularModel) {
  const separator = path.includes('?') ? '&' : '?';
  return `${path}${separator}model=${encodeURIComponent(model)}`;
}

function renderVascularModelContext() {
  const config = currentVascularModel();
  ui.vascularModulePanel.dataset.vascularModel = config.key;
  ui.vascularModelButtons.forEach(button => {
    const active = button.dataset.vascularModel === config.key;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  ui.vascularModelKicker.textContent = config.kicker;
  ui.vascularModelTitle.textContent = config.title;
  ui.vascularModelDescription.textContent = config.description;
  ui.vascularModelContract.setAttribute('aria-label', `${config.label}模型契约`);
  ui.vascularContractModel.textContent = config.model;
  ui.vascularContractInput.textContent = config.input;
  ui.vascularContractOutput.textContent = config.output;
  ui.vascularContractPurpose.textContent = config.purpose;
  ui.vascularExecutionDescription.textContent = config.execution;
  ui.vascularSafetyNote.innerHTML = config.safety;
  ui.vascularFooterTitle.textContent = config.footerTitle;
  ui.vascularFooterDescription.textContent = config.footer;
  ui.vascularRunCurrent.querySelector('span').textContent = config.runLabel;
  ui.vascularRoiVisualStatus.textContent = config.visual;
  ui.vascularTaskState.textContent = config.taskIdle;
  if (state.activeModule === 'vascular') ui.moduleContext.textContent = `当前：${config.label} · ROI 质检`;
}

async function setVascularModel(modelKey) {
  if (!VASCULAR_MODEL_CONFIG[modelKey] || modelKey === state.vascularModel) return;
  const active = state.vascularStatus?.active_task;
  if (state.vascularTaskId || (active && !VASCULAR_TERMINAL_STATES.has(active.status))) {
    toast('血管模型任务运行中，完成或取消后才能切换', true);
    return;
  }
  state.vascularModel = modelKey;
  state.vascularStatus = null;
  renderVascularModelContext();
  renderVascularTaskIdle();
  await refreshVascularStatus();
  await maybeAutoVisualizeVascularRoi({ allowExisting: true });
}

function renderVascularTaskIdle() {
  const config = currentVascularModel();
  ui.vascularTaskPanel.dataset.status = 'idle';
  ui.vascularTaskState.textContent = config.taskIdle;
  ui.vascularProgress.style.setProperty('--vascular-progress', '0%');
  ui.vascularProgress.setAttribute('aria-valuenow', '0');
  ui.vascularProgressLabel.textContent = '0%';
  ui.vascularStage.textContent = '等待运行';
  ui.vascularCurrentPatient.textContent = '—';
  ui.vascularCountCompleted.textContent = '0';
  ui.vascularCountFailed.textContent = '0';
  ui.vascularCountSkipped.textContent = '0';
  ui.vascularCancel.disabled = true;
  ui.vascularResults.classList.add('hidden');
  ui.vascularResultList.innerHTML = '';
  ui.vascularOutputBlock.classList.add('hidden');
  ui.vascularQualityAlert.classList.add('hidden');
  ui.vascularError.classList.add('hidden');
  ui.vascularError.textContent = '';
}

function patientNameFromPath(path) {
  return String(path || '').split(/[\\/]/).filter(Boolean).at(-1) || '未知患者';
}

function isCoarseDegradedResult(result) {
  return Boolean(result && (result.quality_status === 'coarse_degraded' || result.review_required === true));
}

function vascularQualityFlag(result) {
  if (result?.quality_status === 'research_preannotation') return '研究预标注 / 必须人工复核';
  if (result?.quality_status === 'source_unverified') return '来源序列未确认 / 需重点复核';
  if (result?.quality_status === 'legacy_unverified') return '旧版结果 / 需重点复核';
  return '粗层恢复 / 需重点复核';
}

function coarseQualityNote(result) {
  if (result?.quality_note) return String(result.quality_note);
  if (result?.quality_status === 'research_preannotation') return '全腹动脉二值结果仅作为研究预标注；请逐层确认主动脉及各级分支的遗漏、断裂和误纳入。';
  if (result?.quality_status === 'source_unverified') return '当前 ROI 的来源影像序列无法确认，请复核或重新运行。';
  if (result?.quality_status === 'legacy_unverified') return '旧版结果缺少输入影像指纹，请重点复核。';
  return '厚层数据已启用粗层恢复；请重点复核肝内远端分支的连续性与误纳入。';
}

function renderVascularResults(results = []) {
  ui.vascularResults.classList.toggle('hidden', !results.length);
  ui.vascularResultList.innerHTML = results.map(item => {
    const status = item.status || 'unknown';
    const labels = { completed: '成功', failed: '失败', skipped: '跳过' };
    const identity = patientNameFromPath(item.patient_dir) || item.case_id || '患者';
    const detail = item.output_path || item.error || '';
    const recovery = item.backup_path
      ? `旧 ROI 备份：${item.backup_path}`
      : item.recovery || (item.coarse_slice_warning ? '粗层数据：结果已按几何策略处理，建议重点复核末端分支。' : '');
    const coarseDegraded = isCoarseDegradedResult(item);
    const qualityNote = coarseDegraded ? coarseQualityNote(item) : '';
    return `<div class="vascular-result-row" data-status="${escapeHtml(status)}">
      <span class="result-state">${escapeHtml(labels[status] || status)}</span>
      <strong title="${escapeHtml(item.patient_dir || item.case_id || '')}">${escapeHtml(identity)}</strong>
      ${coarseDegraded ? `<span class="result-quality-flag">${escapeHtml(vascularQualityFlag(item))}</span>` : ''}
      ${qualityNote ? `<p class="result-quality-note" title="${escapeHtml(qualityNote)}">${escapeHtml(qualityNote)}</p>` : ''}
      ${detail ? `<code title="${escapeHtml(detail)}">${escapeHtml(detail)}</code>` : ''}
      ${recovery ? `<small title="${escapeHtml(recovery)}">${escapeHtml(recovery)}</small>` : ''}
    </div>`;
  }).join('');
}

function renderVascularTask(task) {
  if (!task) return;
  const details = task.details || {};
  const progress = details.progress || {};
  const counts = details.counts || {};
  const status = task.status || 'queued';
  const busy = !VASCULAR_TERMINAL_STATES.has(status);
  ui.vascularModelButtons.forEach(button => { button.disabled = busy; });
  const percent = Math.max(0, Math.min(100, Number(progress.percent ?? (VASCULAR_TERMINAL_STATES.has(status) ? 100 : 0))));
  ui.vascularTaskPanel.dataset.status = status;
  ui.vascularTaskState.textContent = task.error || task.message || '等待运行';
  ui.vascularProgress.style.setProperty('--vascular-progress', `${percent}%`);
  ui.vascularProgress.setAttribute('aria-valuenow', String(Math.round(percent)));
  ui.vascularProgressLabel.textContent = `${Math.round(percent)}%`;
  ui.vascularStage.textContent = progress.message || task.message || '等待运行';
  ui.vascularCurrentPatient.textContent = progress.patient
    ? `${progress.current || 1}/${progress.total || 1} · ${progress.patient}${progress.case_id ? ` · ${progress.case_id}` : ''}`
    : '—';
  ui.vascularCountCompleted.textContent = String(counts.completed || 0);
  ui.vascularCountFailed.textContent = String(counts.failed || 0);
  ui.vascularCountSkipped.textContent = String(counts.skipped || 0);
  ui.vascularCancel.disabled = !['queued', 'running'].includes(status);
  ui.vascularTaskDot.className = `task-dot ${status === 'running' || status === 'queued' || status === 'cancelling' ? 'running' : status === 'completed' ? 'completed' : status === 'failed' || status === 'completed_with_failures' ? 'failed' : ''}`;

  const results = details.results || [];
  renderVascularResults(results);
  const result = details.result || (details.mode === 'current' ? results.find(item => item.status === 'completed') : null);
  ui.vascularOutputBlock.classList.toggle('hidden', !result?.output_path);
  if (result?.output_path) {
    ui.vascularOutputPath.textContent = result.output_path;
    ui.vascularOutputPath.title = result.output_path;
    ui.vascularBackupPath.textContent = result.backup_path ? `旧 ROI 已备份：${result.backup_path}` : '本次没有需要备份的旧 ROI';
    ui.vascularBackupPath.title = result.backup_path || '';
  }
  const coarseDegraded = Boolean(result?.output_path && isCoarseDegradedResult(result));
  ui.vascularQualityAlert.classList.toggle('hidden', !coarseDegraded);
  if (coarseDegraded) {
    const qualityNote = coarseQualityNote(result);
    ui.vascularQualityFlag.textContent = vascularQualityFlag(result);
    ui.vascularQualityNote.textContent = qualityNote;
    ui.vascularQualityNote.title = qualityNote;
  } else {
    ui.vascularQualityNote.textContent = '';
    ui.vascularQualityNote.title = '';
  }
  const errorText = task.error || (status === 'completed_with_failures' ? '部分患者失败或因多影像序列被跳过；请展开逐患者结果查看原因和恢复方法。' : '');
  ui.vascularError.classList.toggle('hidden', !errorText);
  ui.vascularError.textContent = errorText;
}

function renderVascularStatus(status) {
  if (status?.model_key && status.model_key !== state.vascularModel) return;
  state.vascularStatus = status;
  if (!status) {
    ui.vascularCurrentCase.textContent = '状态暂不可用';
    ui.vascularCurrentPath.textContent = '—';
    setStatusChip(ui.vascularReadiness, false, '可以运行', '状态异常');
    ui.vascularRunCurrent.disabled = true;
    ui.vascularRunBatch.disabled = true;
    ui.vascularModelButtons.forEach(button => { button.disabled = false; });
    return;
  }
  const current = status.current || {};
  const config = currentVascularModel();
  const active = status.active_task;
  const busy = Boolean(active && !VASCULAR_TERMINAL_STATES.has(active.status));
  ui.vascularModelButtons.forEach(button => { button.disabled = busy; });
  const targetOutputPath = current.target_output_path || current.output_path || '';
  const targetOutputExists = Boolean(current.target_output_exists);
  ui.vascularCurrentCase.textContent = current.case_id || '尚未载入病例';
  ui.vascularCurrentPath.textContent = targetOutputPath || '载入病例后显示当前模型输出路径';
  ui.vascularCurrentPath.title = targetOutputPath;
  setStatusChip(
    ui.vascularReadiness,
    Boolean(current.ready && !busy),
    targetOutputExists ? '可重新分割' : '可以运行',
    current.dirty ? '请先保存修改' : busy ? '任务运行中' : '等待病例',
  );
  ui.vascularRunCurrent.disabled = !current.ready || busy;
  ui.vascularRunBatch.disabled = !status.eligible_patient_count || busy || current.dirty;
  ui.vascularBatchSummary.textContent = status.patient_count
    ? `共 ${status.patient_count} 个患者；${status.eligible_patient_count} 个可自动处理${status.ambiguous_patient_count ? `，${status.ambiguous_patient_count} 个多序列患者将安全跳过` : ''}。`
    : '扫描总文件夹后显示可处理患者数。';
  ui.vascularRunCurrent.querySelector('span').textContent = busy && active.details?.mode === 'current' ? config.runningLabel : config.runLabel;
  ui.vascularRunBatch.querySelector('span').textContent = busy && active.details?.mode === 'batch' ? '批量处理运行中' : '批量处理所有患者';
  if (active) {
    renderVascularTask(active);
    if (!VASCULAR_TERMINAL_STATES.has(active.status)) ensureVascularTaskPolling(active.id);
  } else {
    const hasOutput = Boolean(current.output_exists && current.output_path);
    ui.vascularOutputBlock.classList.toggle('hidden', !hasOutput);
    if (hasOutput) {
      ui.vascularOutputPath.textContent = current.output_path;
      ui.vascularOutputPath.title = current.output_path;
      ui.vascularBackupPath.textContent = current.backup_path
        ? `旧 ROI 已备份：${current.backup_path}`
        : `当前病例已有 ${current.output_path?.split(/[\\/]/).pop() || config.outputFilename}`;
      ui.vascularBackupPath.title = current.backup_path || '';
    }
    const coarseDegraded = hasOutput && isCoarseDegradedResult(current);
    ui.vascularQualityAlert.classList.toggle('hidden', !coarseDegraded);
    if (coarseDegraded) {
      const qualityNote = coarseQualityNote(current);
      ui.vascularQualityFlag.textContent = vascularQualityFlag(current);
      ui.vascularQualityNote.textContent = qualityNote;
      ui.vascularQualityNote.title = qualityNote;
    } else {
      ui.vascularQualityNote.textContent = '';
      ui.vascularQualityNote.title = '';
    }
  }
}

let vascularStatusTimer = null;
let vascularPollTimer = null;
function scheduleVascularStatusRefresh(delay = 120) {
  clearTimeout(vascularStatusTimer);
  if (state.activeModule !== 'vascular') return;
  vascularStatusTimer = setTimeout(refreshVascularStatus, delay);
}

async function refreshVascularStatus() {
  const token = ++state.vascularRequestToken;
  try {
    const status = await api(vascularApiUrl('/api/vascular/status'));
    if (token === state.vascularRequestToken) renderVascularStatus(status);
  } catch (error) {
    if (token === state.vascularRequestToken) {
      renderVascularStatus(null);
      ui.vascularError.classList.remove('hidden');
      ui.vascularError.textContent = `${error.message}；请检查本机 ROI 服务后重试。`;
    }
  }
}

function isCurrentVascularPoll(taskId, generation) {
  return Boolean(
    taskId
    && state.vascularTaskId === taskId
    && state.vascularPollTaskId === taskId
    && state.vascularPollGeneration === generation
  );
}

function stopVascularTaskPolling(taskId, generation) {
  if (!isCurrentVascularPoll(taskId, generation)) return;
  clearTimeout(vascularPollTimer);
  vascularPollTimer = null;
  state.vascularTaskId = null;
  state.vascularPollTaskId = '';
  state.vascularPollGeneration += 1;
}

function scheduleVascularTaskPoll(taskId, generation, delay = 900) {
  if (!isCurrentVascularPoll(taskId, generation)) return;
  clearTimeout(vascularPollTimer);
  vascularPollTimer = setTimeout(() => {
    vascularPollTimer = null;
    pollVascularTask(taskId, generation);
  }, delay);
}

function ensureVascularTaskPolling(taskId) {
  if (!taskId) return;
  if (state.vascularPollTaskId === taskId && state.vascularTaskId === taskId) return;
  clearTimeout(vascularPollTimer);
  vascularPollTimer = null;
  state.vascularPollGeneration += 1;
  state.vascularPollTaskId = taskId;
  state.vascularTaskId = taskId;
  pollVascularTask(taskId, state.vascularPollGeneration);
}

function vascularTaskCompletedCurrentCase(task, launchIdentity) {
  if (!launchIdentity || !task || !['completed', 'completed_with_failures'].includes(task.status)) return false;
  if (task.id !== launchIdentity.taskId || task.case_id !== launchIdentity.caseId) return false;
  if (task.details?.mode !== 'current') return false;
  const result = task.details?.result || {};
  const completed = [result, ...(task.details?.results || [])].find(
    item => item.status !== 'failed' && item.case_id === launchIdentity.caseId && item.output_path && item.patient_dir,
  );
  if (!completed) return false;
  const launchRoot = normalizeLocalPath(launchIdentity.dataRoot);
  const patientDir = normalizeLocalPath(completed.patient_dir);
  const outputPath = normalizeLocalPath(completed.output_path);
  if (!launchRoot || (patientDir !== launchRoot && !patientDir.startsWith(`${launchRoot}/`))) return false;
  const outputName = String(task.details?.output_filename || launchIdentity.outputFilename || '').toLowerCase();
  if (!outputName || outputPath !== `${patientDir}/${outputName}`) return false;
  return completed;
}

async function pollVascularTask(taskId, generation) {
  if (!isCurrentVascularPoll(taskId, generation)) return;
  try {
    const task = await api(`/api/vascular/tasks/${taskId}`);
    if (!isCurrentVascularPoll(taskId, generation)) return;
    renderVascularTask(task);
    if (!VASCULAR_TERMINAL_STATES.has(task.status)) {
      scheduleVascularTaskPoll(taskId, generation);
      return;
    }
    const launchIdentity = state.vascularTaskLaunchIdentities.get(taskId) || null;
    const completedResult = vascularTaskCompletedCurrentCase(task, launchIdentity);
    if (completedResult) {
      state.vascularPendingVisualizations.set(taskId, {
        taskId,
        caseId: launchIdentity.caseId,
        dataRoot: launchIdentity.dataRoot,
        launchSessionToken: launchIdentity.sessionToken,
        patientDir: completedResult.patient_dir,
        outputPath: completedResult.output_path,
        outputSha256: completedResult.output_sha256,
        modelKey: task.details?.model_key || launchIdentity.modelKey,
        relativePath: completedResult.output_path.split(/[\\/]/).pop() || task.details?.output_filename || currentVascularModel().outputFilename,
      });
    }
    if (!state.vascularHandledTasks.has(taskId)) {
      state.vascularHandledTasks.add(taskId);
      state.cases = (await api('/api/cases')).items;
      if (!isCurrentVascularPoll(taskId, generation)) return;
      renderCases();
      if (task.status === 'completed') toast(task.message || '血管分割完成');
      else if (task.status === 'completed_with_failures') toast(task.message || '批量任务部分完成', true);
      else if (task.status === 'failed') toast(task.error || task.message || '血管分割失败', true);
      else toast('血管分割已取消');
    }
    await refreshVascularStatus();
    if (!isCurrentVascularPoll(taskId, generation)) return;
    await maybeAutoVisualizeVascularRoi();
    if (!isCurrentVascularPoll(taskId, generation)) return;
    state.vascularTaskLaunchIdentities.delete(taskId);
    stopVascularTaskPolling(taskId, generation);
  } catch (error) {
    if (!isCurrentVascularPoll(taskId, generation)) return;
    state.vascularTaskLaunchIdentities.delete(taskId);
    stopVascularTaskPolling(taskId, generation);
    ui.vascularError.classList.remove('hidden');
    ui.vascularError.textContent = `${error.message}；可刷新状态后重试。`;
  }
}

async function launchVascularCurrent() {
  const config = currentVascularModel();
  const launchIdentity = state.session
    ? {
        caseId: state.session.case_id,
        sessionToken: state.session.session_token,
        dataRoot: state.session.data_root || state.vascularStatus?.data_root || '',
        modelKey: config.key,
        outputFilename: config.outputFilename,
      }
    : null;
  try {
    const task = await post(vascularApiUrl('/api/vascular/tasks/current'));
    if (launchIdentity) {
      state.vascularTaskLaunchIdentities.set(task.id, { ...launchIdentity, taskId: task.id });
    }
    renderVascularTask(task);
    ensureVascularTaskPolling(task.id);
    await refreshVascularStatus();
  } catch (error) { toast(error.message, true); }
}

async function launchVascularBatch() {
  const status = state.vascularStatus;
  const config = currentVascularModel();
  if (!status?.eligible_patient_count) return toast('当前总文件夹没有可自动处理的患者', true);
  const isolation = config.key === 'abdominal_artery'
    ? '原肝动脉 roi.nii.gz 不会被覆盖。'
    : '新增的 abdominal_arteries_roi.nii.gz 不会被覆盖。';
  const message = `将使用“${config.label}”按患者串行处理 ${status.eligible_patient_count} 例 ${config.batchConfirm}。已有 ${status.output_filename || config.outputFilename} 会先备份，只有几何与 QC 通过才会替换；${isolation}${status.ambiguous_patient_count ? `\n另有 ${status.ambiguous_patient_count} 个多序列患者将安全跳过。` : ''}\n\n确认这些病例均为目标动脉期并继续吗？`;
  if (!window.confirm(message)) return;
  try {
    const task = await post(vascularApiUrl('/api/vascular/tasks/batch'));
    renderVascularTask(task);
    ensureVascularTaskPolling(task.id);
    await refreshVascularStatus();
  } catch (error) { toast(error.message, true); }
}

async function cancelVascularTask() {
  if (!state.vascularTaskId) return;
  try {
    const task = await post(`/api/vascular/tasks/${state.vascularTaskId}/cancel`);
    renderVascularTask(task);
  } catch (error) { toast(error.message, true); }
}

async function loadVascularVisualRoi(relativePath = ui.vascularRoiSelect.value, options = {}) {
  if (!state.session) return toast('请先载入病例', true);
  if (!relativePath) return toast('当前患者没有可加载的血管 ROI', true);
  const caseId = state.session.case_id;
  const sessionToken = state.session.session_token;
  const dataRoot = state.session.data_root || '';
  if (
    (options.expectedCaseId && options.expectedCaseId !== caseId)
    || (options.expectedSessionToken && options.expectedSessionToken !== sessionToken)
    || (options.expectedDataRoot && normalizeLocalPath(options.expectedDataRoot) !== normalizeLocalPath(dataRoot))
  ) return null;
  const normalizedPath = String(relativePath).replace(/\\/g, '/').toLowerCase();
  const normalizedName = normalizedPath.split('/').at(-1) || '';
  let expectedRoiSha256 = String(options.expectedOutputSha256 || '').toLowerCase();
  if ([VASCULAR_OUTPUT_FILENAME, VASCULAR_LEGACY_OUTPUT_FILENAME].includes(normalizedName)) {
    const outputModel = options.expectedModelKey || vascularModelForOutput(relativePath);
    let status;
    try {
      status = await api(vascularApiUrl('/api/vascular/status', outputModel));
    } catch (error) {
      ui.vascularRoiVisualStatus.textContent = `无法校验 ${relativePath} 的来源：${error.message}`;
      toast('无法校验血管 ROI 来源，已阻止载入', true);
      return null;
    }
    if (state.session?.case_id !== caseId || state.session?.session_token !== sessionToken) return null;
    if (status.model_key === state.vascularModel) renderVascularStatus(status);
    const current = status.current || {};
    if (current.case_id !== caseId) {
      ui.vascularRoiVisualStatus.textContent = '当前病例状态已改变，已取消本次 ROI 载入。';
      return null;
    }
    if (
      (options.expectedPatientDir && normalizeLocalPath(options.expectedPatientDir) !== normalizeLocalPath(current.patient_dir))
      || (options.expectedOutputPath && normalizeLocalPath(options.expectedOutputPath) !== normalizeLocalPath(current.output_path))
      || (expectedRoiSha256 && expectedRoiSha256 !== String(current.output_sha256 || '').toLowerCase())
    ) {
      ui.vascularRoiVisualStatus.textContent = '血管任务输出身份或文件哈希与当前病例不一致，已取消自动载入。';
      return null;
    }
    if (current.output_identity_mismatch) {
      const message = `${relativePath} 的来源指纹不属于当前影像序列，已阻止载入；请切换到对应动脉期或重新运行对应血管模型。`;
      ui.vascularRoiVisualStatus.textContent = message;
      toast(message, true);
      return null;
    }
    expectedRoiSha256 = String(current.output_sha256 || '').toLowerCase();
  }
  if (state.session?.case_id !== caseId || state.session?.session_token !== sessionToken) return null;
  const session = await loadCase(caseId, relativePath, {
    preserveView: true,
    expectedRoiSha256,
  });
  if (!session) return null;
  const referenceIds = new Set(session.reference_label_ids || []);
  const primaryLabels = (session.labels || []).map(label => Number(label.id)).filter(labelId => !referenceIds.has(labelId));
  const focused = await focusLabels(primaryLabels.length ? primaryLabels : (session.labels || []).map(label => Number(label.id)));
  renderMaskOptions(session);
  renderRoiLayers();
  ui.vascularRoiVisualStatus.textContent = focused
    ? `已显示 ${relativePath}，定位到第 ${focused.index + 1} 层；可切换图层或生成 3D。`
    : `已载入 ${relativePath}，但当前方向没有可定位的非空层。`;
  if (options.automatic) toast(`血管分割完成，已自动显示 ${relativePath}`);
  else toast(`已加载并显示 ${relativePath}`);
  return session;
}

async function maybeAutoVisualizeVascularRoi({ allowExisting = false } = {}) {
  if (
    state.vascularAutoVisualizeInFlight
    || state.activeModule !== 'vascular'
    || !state.session
    || state.session.dirty
  ) return null;
  const caseId = state.session.case_id;
  const sessionToken = state.session.session_token;
  const current = state.vascularStatus?.current || {};
  const currentRoot = normalizeLocalPath(state.session.data_root || state.vascularStatus?.data_root);
  const currentPatient = normalizeLocalPath(current.patient_dir);
  const currentOutput = normalizeLocalPath(current.output_path);
  const pending = [...state.vascularPendingVisualizations.values()].find(item => (
    item.caseId === caseId
    && (!item.modelKey || item.modelKey === state.vascularModel)
    && normalizeLocalPath(item.dataRoot) === currentRoot
    && normalizeLocalPath(item.patientDir) === currentPatient
    && normalizeLocalPath(item.outputPath) === currentOutput
    && String(item.outputSha256 || '').toLowerCase() === String(current.output_sha256 || '').toLowerCase()
  ));
  const mayLoadExisting = Boolean(
    allowExisting
    && current.case_id === caseId
    && current.output_exists
    && !current.output_identity_mismatch
    && normalizeLocalPath(state.loadedRoiPath) !== normalizeLocalPath(current.output_path?.split(/[\\/]/).pop() || currentVascularModel().outputFilename)
  );
  if (!pending && !mayLoadExisting) return null;
  state.vascularAutoVisualizeInFlight = true;
  try {
    const session = await loadVascularVisualRoi(pending?.relativePath || current.output_path?.split(/[\\/]/).pop() || currentVascularModel().outputFilename, {
      automatic: true,
      expectedModelKey: pending?.modelKey || state.vascularModel,
      expectedCaseId: caseId,
      expectedSessionToken: sessionToken,
      expectedDataRoot: pending?.dataRoot || state.session.data_root || state.vascularStatus?.data_root,
      expectedPatientDir: pending?.patientDir || current.patient_dir,
      expectedOutputPath: pending?.outputPath || current.output_path,
      expectedOutputSha256: pending?.outputSha256 || current.output_sha256,
    });
    if (session && pending) state.vascularPendingVisualizations.delete(pending.taskId);
    return session;
  } finally {
    state.vascularAutoVisualizeInFlight = false;
  }
}

function roiInteractionEnabled() {
  return state.activeModule === 'roi';
}

function roiVisualizationEnabled() {
  return Boolean(state.session && ['roi', 'vascular'].includes(state.activeModule));
}

function standardViewerNavigationEnabled() {
  return Boolean(state.session && ['roi', 'vascular'].includes(state.activeModule));
}

async function refreshCurrentSessionAssets() {
  if (!state.session) return;
  const caseId = state.session.case_id;
  const sessionToken = state.session.session_token;
  try {
    const session = await api('/api/session');
    if (state.session?.case_id !== caseId || state.session?.session_token !== sessionToken) return;
    updateSession(session);
  } catch (_error) { /* 血管状态卡会显示服务错误；保留当前可视化。 */ }
}

async function refreshVascularModuleAssets() {
  if (state.vascularModuleRefreshInFlight) return;
  state.vascularModuleRefreshInFlight = true;
  try {
    await refreshCurrentSessionAssets();
    await refreshVascularStatus();
    await maybeAutoVisualizeVascularRoi({ allowExisting: true });
  } finally {
    state.vascularModuleRefreshInFlight = false;
  }
}

function setActiveModule(module, persist = true) {
  // The public build intentionally exposes only the ROI workbench.
  const value = 'roi';
  state.activeModule = value;
  document.body.classList.toggle('vascular-module-active', value === 'vascular');
  ui.canvas.setAttribute('aria-disabled', 'false');
  ui.canvas.setAttribute(
    'aria-label',
    value === 'vascular'
      ? '血管只读阅片区：左键拖动平移，右键拖动调整窗宽窗位，滚轮连续翻层'
      : 'ROI 交互编辑与阅片区',
  );
  ui.roiEditToolbar.inert = value !== 'roi';
  if (value !== 'roi') {
    state.pointerMode = null;
    state.pointerId = null;
    state.startPoint = null;
    state.draftPoints = [];
    state.polygonPoints = [];
    state.hoverPoint = null;
    drawDraft();
  }
  ui.moduleTabs.forEach(tab => {
    const active = tab.dataset.workbenchModule === value;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  });
  ui.roiModulePanel.classList.toggle('hidden', value !== 'roi');
  ui.vascularModulePanel.classList.toggle('hidden', value !== 'vascular');
  ui.roiEditToolbar.classList.toggle('hidden', value !== 'roi');
  ui.moduleContext.textContent = value === 'vascular'
    ? `当前：${currentVascularModel().label} · ROI 质检`
    : '当前：肿瘤 ROI 勾画与确认';
  if (persist) localStorage.setItem(ACTIVE_MODULE_KEY, value);
  if (value === 'vascular') {
    renderVascularModelContext();
    void refreshVascularModuleAssets();
  }
  requestAnimationFrame(fitViewport);
}

function syncWorkflowRail() {
  const session = state.session;
  document.body.classList.toggle('has-active-case', Boolean(session));
  if (!session) {
    setWorkflowStep(ui.workflowCaseStep, 'current');
    setWorkflowStep(ui.workflowReferenceStep);
    setWorkflowStep(ui.workflowEditStep);
    setWorkflowStep(ui.workflowSaveStep);
    if (ui.workflowCaption) ui.workflowCaption.textContent = '先载入一个影像病例。';
    return;
  }
  const hasSource = Boolean(
    session.reference_label_ids?.length
    || session.interactive_reference?.relative_path
    || session.editable_roi_source
    || session.auto_baseline_labels?.length
  );
  const isSaved = session.status === '已完成' && !session.dirty;
  setWorkflowStep(ui.workflowCaseStep, 'complete');
  setWorkflowStep(ui.workflowReferenceStep, hasSource ? 'complete' : '');
  setWorkflowStep(ui.workflowEditStep, isSaved ? 'complete' : session.dirty ? 'attention' : 'current');
  setWorkflowStep(ui.workflowSaveStep, isSaved ? 'complete' : session.dirty ? 'current' : '');
  if (!ui.workflowCaption) return;
  if (isSaved) ui.workflowCaption.textContent = '正式 ROI 已保存；继续编辑会重新进入工作层。';
  else if (session.dirty) ui.workflowCaption.textContent = '当前 ROI 有未保存修改；检查后保存 NIfTI。';
  else if (hasSource) ui.workflowCaption.textContent = 'ROI 来源已载入，可继续检查和精修。';
  else ui.workflowCaption.textContent = '影像已载入；可手工勾画或载入 ROI 来源。';
}

function syncWorkspaceState() {
  syncWorkflowRail();
  const label = state.session?.labels.find(item => item.id === currentLabelId());
  const hasOriginal = Boolean(state.session?.auto_baseline_labels?.includes(currentLabelId()));
  const isReference = Boolean(state.session?.reference_label_ids?.includes(currentLabelId()));
  const hasInteractiveReference = Boolean(state.session?.interactive_reference?.relative_path);
  ui.restoreOriginal.disabled = !hasOriginal || Boolean(label?.locked);
  if (!state.session) ui.workspaceState.textContent = '请先载入病例。';
  else if (isReference) ui.workspaceState.textContent = '当前是既往 ROI 只读对比图层：可调整颜色和显隐，但不会写入新 ROI 保存文件。';
  else if (hasOriginal && label?.locked) ui.workspaceState.textContent = '当前 ROI 已锁定；解锁后才能编辑或恢复模型原样。';
  else if (state.session.dirty) ui.workspaceState.textContent = '当前为可编辑内存工作层，修改已进入撤销与自动恢复缓存，尚未保存为 NIfTI。';
  else if (hasInteractiveReference) ui.workspaceState.textContent = `已载入 ${state.session.interactive_reference.relative_path} 作为 nnInteractive 锁定参考；半自动结果会写入当前可编辑 ROI，不会覆盖右侧对比层。`;
  else if (state.session.working_layer_kind === 'new_auto') ui.workspaceState.textContent = '当前是新建自动肿瘤工作层：尚未写入任何患者 ROI 文件；半自动修补和确认保存都只作用于该层。';
  else if (state.session.working_layer_kind === 'new_interactive') ui.workspaceState.textContent = '当前是新建半自动肿瘤工作层：尚未写入任何患者 ROI 文件；确认后保存才会生成新的 roi_*.nii.gz。';
  else if (state.session.editable_roi_source) ui.workspaceState.textContent = `已载入 ${state.session.editable_roi_source} 作为可编辑起点；源文件保持不变，修改后请保存新的 roi_*.nii.gz。`;
  else if (hasOriginal) ui.workspaceState.textContent = '当前 ROI 可直接修改；“恢复模型原样”会撤销手工修补并恢复本次模型输出。';
  else ui.workspaceState.textContent = '当前 ROI 可直接使用画笔、橡皮擦或多边形修改。';
  sync3dSnapshotState();
}

function renderRangeOperationLog(session = state.session) {
  const entries = session?.range_operation_log || [];
  ui.rangeOperationLog.innerHTML = entries.length
    ? entries.slice().reverse().map(entry => `<div class="range-operation-item">
        <span>${escapeHtml(entry.message)}</span>
        <small>ROI ${entry.label_id}: ${escapeHtml(entry.label_name)}</small>
      </div>`).join('')
    : '<p class="hint">尚无范围删除记录</p>';
}

function applyToolSelection(tool) {
  state.tool = tool; state.polygonPoints = []; state.draftPoints = []; state.hoverPoint = null;
  $$('#tool-buttons button').forEach(item => item.classList.toggle('active', item.dataset.tool === tool));
  updateCanvasToolClass(); drawDraft();
}

function clamp(value, minimum, maximum) { return Math.max(minimum, Math.min(maximum, Number(value))); }

let panelFitFrame = null;
function schedulePanelFit() {
  if (panelFitFrame !== null) return;
  panelFitFrame = requestAnimationFrame(() => {
    panelFitFrame = null;
    fitViewport();
  });
}

function currentPanelWidth(side) {
  const panel = side === 'left' ? ui.leftPanel : ui.rightPanel;
  const measured = panel?.getBoundingClientRect().width;
  return measured > 0 ? measured : PANEL_DEFAULTS[side];
}

function persistPanelLayout() {
  localStorage.setItem(PANEL_LAYOUT_KEY, JSON.stringify({
    left: Math.round(state.panelWidths.left ?? currentPanelWidth('left')),
    right: Math.round(state.panelWidths.right ?? currentPanelWidth('right')),
  }));
}

function setPanelWidth(side, value, persist = true) {
  const [minimum, hardMaximum] = PANEL_LIMITS[side];
  const otherSide = side === 'left' ? 'right' : 'left';
  const otherWidth = currentPanelWidth(otherSide);
  const handlesWidth = (ui.leftPanelResizer?.offsetWidth || 8) + (ui.rightPanelResizer?.offsetWidth || 8);
  const availableMaximum = ui.workspace.clientWidth > 0
    ? ui.workspace.clientWidth - otherWidth - handlesWidth - PANEL_LIMITS.center
    : hardMaximum;
  const maximum = Math.max(minimum, Math.min(hardMaximum, availableMaximum));
  const width = Math.round(clamp(Number(value) || minimum, minimum, maximum));
  document.documentElement.style.setProperty(`--${side}-panel-width`, `${width}px`);
  state.panelWidths[side] = width;
  if (state.panelWidths[otherSide] === null) state.panelWidths[otherSide] = Math.round(otherWidth);
  const resizer = side === 'left' ? ui.leftPanelResizer : ui.rightPanelResizer;
  resizer.setAttribute('aria-valuenow', String(width));
  if (persist) persistPanelLayout();
  schedulePanelFit();
  return width;
}

function restorePanelLayout() {
  let stored = {};
  try { stored = JSON.parse(localStorage.getItem(PANEL_LAYOUT_KEY) || '{}') || {}; }
  catch (_error) { stored = {}; }
  const left = Number.isFinite(Number(stored.left)) ? Number(stored.left) : currentPanelWidth('left');
  const right = Number.isFinite(Number(stored.right)) ? Number(stored.right) : currentPanelWidth('right');
  setPanelWidth('right', right, false);
  setPanelWidth('left', left, false);
}

function beginPanelResize(event) {
  if (event.button !== 0) return;
  event.preventDefault();
  const resizer = event.currentTarget;
  const side = resizer.dataset.panelResizer;
  const workspaceRect = ui.workspace.getBoundingClientRect();
  resizer.setPointerCapture(event.pointerId);
  resizer.classList.add('dragging');
  document.body.classList.add('resizing-panels');

  const move = moveEvent => {
    const width = side === 'left'
      ? moveEvent.clientX - workspaceRect.left
      : workspaceRect.right - moveEvent.clientX;
    setPanelWidth(side, width, false);
  };
  const finish = finishEvent => {
    resizer.removeEventListener('pointermove', move);
    resizer.removeEventListener('pointerup', finish);
    resizer.removeEventListener('pointercancel', finish);
    resizer.classList.remove('dragging');
    document.body.classList.remove('resizing-panels');
    if (resizer.hasPointerCapture(finishEvent.pointerId)) resizer.releasePointerCapture(finishEvent.pointerId);
    persistPanelLayout();
  };
  resizer.addEventListener('pointermove', move);
  resizer.addEventListener('pointerup', finish);
  resizer.addEventListener('pointercancel', finish);
}

function resizePanelWithKeyboard(event) {
  const side = event.currentTarget.dataset.panelResizer;
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  if (event.key === 'Home') return void setPanelWidth(side, PANEL_LIMITS[side][0]);
  if (event.key === 'End') return void setPanelWidth(side, PANEL_LIMITS[side][1]);
  const direction = side === 'left'
    ? (event.key === 'ArrowRight' ? 1 : -1)
    : (event.key === 'ArrowLeft' ? 1 : -1);
  setPanelWidth(side, currentPanelWidth(side) + direction * 12);
}

function setRoiOpacity(value, persist = true) {
  const numeric = Number(value);
  const opacity = Math.round(clamp(Number.isFinite(numeric) ? numeric : 49, 0, 100));
  ui.opacity.value = String(opacity);
  ui.opacityNumber.value = String(opacity);
  if (persist) localStorage.setItem(ROI_OPACITY_KEY, String(opacity));
  scheduleSlice(60);
}

function setOverlayMode(mode, persist = true, refresh = true) {
  const selected = mode === 'boundary' ? 'boundary' : 'fill';
  ui.overlayMode.value = selected;
  $$('[data-overlay-mode]').forEach(button => button.classList.toggle('active', button.dataset.overlayMode === selected));
  ui.boundaryWidthControls.classList.toggle('hidden', selected !== 'boundary');
  if (persist) localStorage.setItem(ROI_OVERLAY_MODE_KEY, selected);
  if (refresh) scheduleSlice(0);
}

function setBoundaryWidth(value, persist = true) {
  const width = Math.round(clamp(value, 1, 10));
  ui.boundaryWidth.value = String(width);
  ui.boundaryWidthValue.textContent = `${width} px`;
  if (persist) localStorage.setItem(ROI_BOUNDARY_WIDTH_KEY, String(width));
  if (ui.overlayMode.value === 'boundary') scheduleSlice(40);
}

function roiLayerListMarkup(labels) {
  const grouped = new Map();
  labels.forEach(label => {
    const sourceFile = label.source_file || state.session?.editable_roi_source || '@working';
    if (!grouped.has(sourceFile)) grouped.set(sourceFile, []);
    grouped.get(sourceFile).push(label);
  });
  return labels.length ? [...grouped.entries()].map(([sourceFile, fileLabels]) => `<div class="roi-layer-file" data-source-file="${escapeHtml(sourceFile)}">
    <div class="roi-layer-file-title"><span>${escapeHtml(displayRoiSource(sourceFile))}</span><small>${fileLabels.length} 标签</small></div>
    ${fileLabels.map(label => {
    const layerKey = label.layer_key || String(label.id);
    const hidden = state.hiddenLayerKeys.has(layerKey) || state.hiddenLabelIds.has(label.id);
    const name = label.display_name || label.name;
    const isReference = state.session?.reference_label_ids?.includes(label.id);
    const isInteractiveReference = state.session?.interactive_reference_label_ids?.includes(label.id);
    const isEditableSource = Boolean(state.session?.editable_roi_source) && !isReference;
    const layerSuffix = isInteractiveReference
      ? ' · nnInteractive参考'
      : isReference
        ? ' · 对比'
        : isEditableSource
          ? ' · 当前编辑'
          : '';
    const opacity = Math.round((state.layerOpacities.get(layerKey) ?? 1) * 100);
    return `<label class="roi-layer-row ${hidden ? 'hidden-roi' : ''} ${label.id === currentLabelId() ? 'current' : ''}" title="${hidden ? '点击打开显示' : '点击关闭显示'}" data-layer-key="${escapeHtml(layerKey)}">
      <input type="checkbox" data-roi-visibility="${escapeHtml(layerKey)}" data-layer-key="${escapeHtml(layerKey)}" ${hidden ? '' : 'checked'} aria-label="显示 ${escapeHtml(name)}">
      <span class="roi-layer-swatch" style="background:${escapeHtml(label.color)}"></span>
      <span class="roi-layer-name">${label.source_label_id ?? label.id}: ${escapeHtml(name)}${layerSuffix}</span>
      <input class="roi-layer-opacity" type="range" min="0" max="100" value="${opacity}" data-roi-opacity="${escapeHtml(layerKey)}" data-layer-key="${escapeHtml(layerKey)}" aria-label="${escapeHtml(name)} 透明度">
    </label>`;
    }).join('')}
  </div>`).join('') : '<div class="hint">当前没有可显示的 ROI</div>';
}

function renderRoiLayers() {
  const labels = sessionLayers();
  const validKeys = new Set(labels.map(label => label.layer_key || String(label.id)));
  state.hiddenLayerKeys = new Set([...state.hiddenLayerKeys].filter(layerKey => validKeys.has(layerKey)));
  const visibleCount = labels.filter(label => !state.hiddenLayerKeys.has(label.layer_key || String(label.id))).length;
  const countText = `${visibleCount} / ${labels.length}`;
  ui.roiVisibilityCount.textContent = countText;
  ui.vascularRoiVisibilityCount.textContent = countText;
  ui.showAllRoi.disabled = !labels.length || state.hiddenLayerKeys.size === 0;
  ui.hideAllRoi.disabled = !labels.length || state.hiddenLayerKeys.size === labels.length;
  ui.vascularRoiShowAll.disabled = ui.showAllRoi.disabled;
  ui.vascularRoiHideAll.disabled = ui.hideAllRoi.disabled;
  ui.render3d.disabled = state.mesh3dLoading || !state.session || labels.length === 0;
  ui.vascularRender3d.disabled = ui.render3d.disabled;
  const markup = roiLayerListMarkup(labels);
  ui.roiLayerList.innerHTML = markup;
  ui.vascularRoiLayerList.innerHTML = markup;
}

function populateRoiFileSelect(select, files, preferred = '') {
  const selected = select.value;
  select.innerHTML = files.length
    ? files.map(file => `<option value="${escapeHtml(file.relative_path)}">${escapeHtml(file.name)} · ${escapeHtml(file.relative_path)}</option>`).join('')
    : '<option value="">当前患者文件夹没有可加载的 ROI / NIfTI 标签图</option>';
  const activeOutput = currentVascularModel().outputFilename;
  const fallback = files.find(file => normalizeLocalPath(file.relative_path) === activeOutput)?.relative_path
    || files.find(file => [VASCULAR_OUTPUT_FILENAME, VASCULAR_LEGACY_OUTPUT_FILENAME].includes(normalizeLocalPath(file.relative_path)))?.relative_path
    || files[0]?.relative_path
    || '';
  const next = [selected, preferred, fallback].find(value => files.some(file => file.relative_path === value)) || '';
  if (next) select.value = next;
  select.disabled = !files.length;
}

function renderMaskOptions(session = state.session) {
  const files = session?.available_roi_files || [];
  renderRoiFileSelection(session);
  populateRoiFileSelect(ui.maskSelect, files);
  populateRoiFileSelect(ui.vascularRoiSelect, files, state.loadedRoiPath);
  ui.maskSelect.disabled = !files.length;
  ui.importMask.disabled = !files.length;
  if (ui.loadEditableRoi) ui.loadEditableRoi.disabled = !files.length;
  if (ui.loadInteractiveReference) ui.loadInteractiveReference.disabled = !files.length;
  ui.vascularRoiLoad.disabled = !files.length || !state.session;
  ui.vascularRender3d.disabled = state.mesh3dLoading || !state.session || !(state.session?.labels || []).length;
  ui.vascularRoiVisualStatus.textContent = state.loadedRoiPath
    ? `当前显示：${state.loadedRoiPath}；可在列表中切换二维图层或生成 3D。`
    : files.length
      ? `选择一个 ROI 后点击“加载并显示”；当前模型完成后会优先载入 ${currentVascularModel().outputFilename}。`
      : '当前患者还没有可视化 ROI；自动分割完成后会在这里出现。';
}

function renderRoiFileSelection(session = state.session) {
  if (!ui.roiFileSelection) return;
  const files = (session?.available_roi_files || []).filter(file => file.role !== 'image' && file.role !== 'project');
  const validPaths = new Set(files.map(file => file.relative_path));
  state.selectedRoiFiles = new Set(session?.selected_roi_files || []);
  state.selectedRoiFiles = new Set([...state.selectedRoiFiles].filter(path => validPaths.has(path)));
  ui.roiFileSelection.innerHTML = files.length ? files.map(file => {
    const checked = state.selectedRoiFiles.has(file.relative_path);
    const editable = session?.editable_roi_source === file.relative_path;
    const role = editable ? '当前编辑' : session?.interactive_reference?.relative_path === file.relative_path ? 'nnInteractive参考' : file.role === 'source_roi' ? '源 ROI' : '参考';
    return `<div class="roi-file-row ${checked ? 'is-selected' : ''} ${editable ? 'is-editable' : ''}" data-roi-file-row="${escapeHtml(file.relative_path)}">
      <input type="checkbox" data-roi-file="${escapeHtml(file.relative_path)}" ${checked ? 'checked' : ''} aria-label="显示 ${escapeHtml(file.name)}">
      <span class="roi-file-copy"><strong>${escapeHtml(file.name)}</strong><small>${escapeHtml(file.relative_path)}</small></span>
      <span class="roi-file-role">${role}</span>
      <button type="button" class="roi-file-delete" data-delete-roi-file="${escapeHtml(file.relative_path)}" ${checked ? '' : 'disabled'} aria-label="删除 ${escapeHtml(file.name)}">删除</button>
    </div>`;
  }).join('') : '<p class="hint">当前患者没有可选 ROI 文件</p>';
}

function updateCanvasToolClass() {
  ui.canvas.classList.remove('tool-pan', 'tool-brush', 'tool-eraser', 'tool-keep-component');
  if (['pan', 'brush', 'eraser', 'keep_component'].includes(state.tool)) ui.canvas.classList.add(`tool-${state.tool.replace('_', '-')}`);
}

function effectiveModality(session = state.session) {
  if (ui.modalityMode.value === 'CT' || ui.modalityMode.value === 'MR') return ui.modalityMode.value;
  const suggested = session?.display?.suggested_modality;
  return suggested === 'CT' || suggested === 'MR' ? suggested : 'UNKNOWN';
}

function mrDefaults() {
  const display = state.session?.display || {};
  const width = Math.max(1, Number(display.mr_default_width || 1));
  return { level: Number(display.mr_default_level || width / 2), width };
}

function applyMrWindow() {
  const defaults = mrDefaults();
  state.mrContrast = clamp(state.mrContrast, 25, 300);
  state.mrBrightness = clamp(state.mrBrightness, -100, 100);
  state.width = Math.max(1, defaults.width * 100 / state.mrContrast);
  state.level = defaults.level - state.mrBrightness * defaults.width / 200;
}

function setCtWindow(level, width) {
  state.level = Number.isFinite(Number(level)) ? Number(level) : 40;
  state.width = Math.max(1, Number(width) || 400);
}

function applyDisplayDefaults(modality) {
  if (modality !== 'CT') {
    state.mrBrightness = 0;
    state.mrContrast = 100;
    applyMrWindow();
  } else {
    const display = state.session?.display || {};
    setCtWindow(display.ct_default_level ?? 40, display.ct_default_width ?? 400);
  }
}

function applyDisplayProfile(modality) {
  if (modality === 'UNKNOWN') return false;
  const profile = readDisplayProfiles()[modality];
  if (!profile) return false;
  if (modality === 'MR') {
    state.mrBrightness = clamp(profile.brightness ?? 0, -100, 100);
    state.mrContrast = clamp(profile.contrast ?? 100, 25, 300);
    applyMrWindow();
  } else setCtWindow(profile.level, profile.width);
  return true;
}

function updateDisplayUi() {
  const modality = state.displayModality;
  const automatic = ui.modalityMode.value === 'auto';
  ui.modalityBadge.textContent = modality === 'UNKNOWN' ? '未识别' : automatic ? `${modality} 自动` : modality;
  ui.ctControls.classList.toggle('hidden', modality !== 'CT');
  ui.mrControls.classList.toggle('hidden', modality === 'CT');
  if (modality === 'CT') {
    ui.level.value = String(Math.round(state.level));
    ui.width.value = String(Math.round(state.width));
    const matched = [...ui.windowPreset.options].find(option => {
      if (option.value === 'custom') return false;
      const [level, width] = option.value.split(',').map(Number);
      return Math.abs(level - state.level) < .5 && Math.abs(width - state.width) < .5;
    });
    ui.windowPreset.value = matched?.value || 'custom';
    ui.displaySummary.textContent = `CT · W${Math.round(state.width)}/L${Math.round(state.level)}`;
  } else {
    ui.mrBrightness.value = String(Math.round(state.mrBrightness));
    ui.mrContrast.value = String(Math.round(state.mrContrast));
    ui.mrBrightnessValue.textContent = `${Math.round(state.mrBrightness)}`;
    ui.mrContrastValue.textContent = `${Math.round(state.mrContrast)}%`;
    ui.mrWindowHint.textContent = `显示范围：${Math.round(state.level - state.width / 2)} 至 ${Math.round(state.level + state.width / 2)}`;
    ui.displaySummary.textContent = `${modality === 'MR' ? 'MR' : '通用'} · 亮度 ${Math.round(state.mrBrightness)} · 对比度 ${Math.round(state.mrContrast)}%`;
  }
  const pinned = readDisplayProfiles()[modality];
  ui.pinDisplay.disabled = modality === 'UNKNOWN';
  ui.clearPinnedDisplay.disabled = modality === 'UNKNOWN' || !pinned;
  const matchesPinned = pinned && (modality === 'MR'
    ? Math.abs(Number(pinned.brightness) - state.mrBrightness) < .5 && Math.abs(Number(pinned.contrast) - state.mrContrast) < .5
    : Math.abs(Number(pinned.level) - state.level) < .5 && Math.abs(Number(pinned.width) - state.width) < .5);
  ui.displayStatus.textContent = modality === 'UNKNOWN'
    ? '无法可靠识别模态；当前使用稳健强度范围。请手动选择 CT 或 MR 后再固定。'
    : matchesPinned
    ? `${modality} 已固定；以后读取的 ${modality} 将自动使用该显示参数。`
    : pinned
      ? `当前显示已偏离固定值；点击“固定当前显示”可更新。`
      : '显示参数只影响画面，不改变模型输入。';
}

function initializeDisplay(session) {
  state.displayModality = effectiveModality(session);
  if (!applyDisplayProfile(state.displayModality)) applyDisplayDefaults(state.displayModality);
  updateDisplayUi();
}

function renderCases() {
  const query = ui.caseSearch.value.trim().toLowerCase();
  const status = ui.statusFilter.value;
  const roiFileCount = ui.roiFileCountFilter?.value || 'all';
  const visible = state.cases.filter(item => {
    const searchable = [item.patient_id, item.case_id, item.series_description, ...(item.files || []).flatMap(file => [file.name, file.relative_path])]
      .filter(Boolean).join(' ').toLowerCase();
    const fileCountMatches = roiFileCount === 'all' || String((item.files || []).length) === roiFileCount;
    return (!query || searchable.includes(query)) && (status === '全部' || item.status === status) && fileCountMatches;
  });
  const patients = new Map();
  visible.forEach(item => {
    const patientId = item.patient_id || item.case_id.split('/')[0];
    if (!patients.has(patientId)) patients.set(patientId, []);
    patients.get(patientId).push(item);
  });
  ui.caseCount.textContent = String(patients.size);
  ui.caseList.classList.toggle('empty-state', !patients.size);
  if (!patients.size) {
    ui.caseList.innerHTML = '<div class="empty-list-copy"><strong>没有匹配结果</strong><span>调整搜索、工作状态或 ROI 文件数</span></div>';
    return;
  }
  ui.caseList.innerHTML = [...patients.entries()].map(([patientId, cases], patientIndex) => {
    const active = cases.some(item => item.case_id === state.session?.case_id);
    const expanded = Boolean(query) || active || state.expandedPatients.has(patientId);
    const seenFiles = new Set();
    const fileRows = cases.flatMap(item => (item.files || []).filter(file => {
      const key = `${file.role}:${file.relative_path}:${file.role === 'image' ? item.case_id : ''}`;
      if (seenFiles.has(key)) return false;
      seenFiles.add(key); return true;
    }).map(file => renderFileRow(file, item)));
    const expanderId = `patient-expander-${patientIndex}`;
    return `<section class="patient-node ${active ? 'active' : ''}" data-patient-id="${escapeHtml(patientId)}">
      <input id="${expanderId}" class="patient-expander" type="checkbox" ${expanded ? 'checked' : ''} aria-label="展开 ${escapeHtml(patientId)}">
      <div class="patient-toggle">
        <span class="tree-chevron"></span><span class="folder-icon" aria-hidden="true"></span>
        <span class="patient-name" title="${escapeHtml(patientId)}">${escapeHtml(patientId)}</span>
        <span class="patient-file-count">${fileRows.length}</span>
      </div>
      <div class="patient-files">${fileRows.join('')}</div>
    </section>`;
  }).join('');
}

function handleCaseTreeClick(event) {
  const closestTarget = event.target instanceof Element
    ? event.target.closest('.patient-toggle, .case-file')
    : null;
  const path = typeof event.composedPath === 'function' ? event.composedPath() : [event.target];
  const target = closestTarget || path.find(node => node?.classList?.contains('patient-toggle') || node?.classList?.contains('case-file'));
  if (!target || !ui.caseList.contains(target)) return;
  if (target.classList.contains('case-file') && target.dataset.caseId) {
    event.preventDefault();
    loadCase(target.dataset.caseId, target.dataset.roiPath || '');
  }
}

const FILE_ROLE = {
  image: { label: '影像', icon: 'IMG', className: 'image' },
  mask: { label: '原始 Mask', icon: 'MSK', className: 'mask' },
  source_roi: { label: '导入 ROI', icon: 'ROI', className: 'mask' },
  saved_roi: { label: '已保存 ROI', icon: 'SVD', className: 'saved-roi' },
  workspace_roi: { label: '工作区 ROI', icon: 'TMP', className: 'workspace-roi' },
  baseline: { label: '自动基线', icon: 'AI', className: 'baseline' },
  project: { label: '项目记录', icon: 'LOG', className: 'project' },
};

function formatBytes(value) {
  if (!Number.isFinite(value)) return '';
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 ** 2).toFixed(1)} MB`;
}

function renderFileRow(file, item) {
  const meta = FILE_ROLE[file.role] || { label: '文件', icon: 'FILE', className: 'other' };
  const details = [file.relative_path, formatBytes(file.size_bytes)].filter(Boolean).join(' · ');
  const clickable = ['image', 'mask', 'source_roi', 'saved_roi', 'workspace_roi'].includes(file.role);
  if (clickable) {
    const roiPath = file.role === 'image' ? '' : file.relative_path;
    const active = state.session?.case_id === item.case_id && state.loadedRoiPath === roiPath;
    return `<button type="button" class="case-file file-${meta.className} ${active ? 'active' : ''}" data-case-id="${escapeHtml(item.case_id)}" data-roi-path="${escapeHtml(roiPath)}" title="${escapeHtml(details)}">
      <span class="file-icon">${meta.icon}</span><span class="file-main"><b>${escapeHtml(file.name)}</b><small>${meta.label}</small></span>
      ${file.role === 'image' ? `<span class="case-status status-${STATUS_CLASS[item.status] || 'not-started'}">${escapeHtml(STATUS_CLASS[item.status] ? item.status : '未开始')}</span>` : ''}
    </button>`;
  }
  return `<div class="case-file file-${meta.className}" title="${escapeHtml(details)}">
    <span class="file-icon">${meta.icon}</span><span class="file-main"><b>${escapeHtml(file.name)}</b><small>${meta.label}</small></span>
  </div>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

async function scanRoot() {
  const path = ui.rootPath.value.trim();
  if (!path) return toast('请输入患者总文件夹路径', true);
  const discardDirty = Boolean(state.session?.dirty);
  if (discardDirty && !confirm('当前病例有未保存修改，扫描新目录会放弃这些修改，确定继续吗？')) return;
  try {
    abortSliceRequests();
    setLoading(true, '正在扫描病例');
    const result = await post('/api/root', { path, discard_dirty: discardDirty });
    ui.rootPath.value = result.root;
    localStorage.setItem(ROOT_STORAGE_KEY, result.root);
    state.cases = (await api('/api/cases')).items;
    state.session = null;
    state.loadedRoiPath = '';
    state.expandedPatients.clear();
    sessionStorage.removeItem(CASE_STORAGE_KEY);
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    renderCases();
    showEmpty();
    toast(`发现 ${result.case_count} 个影像序列`);
  } catch (error) { toast(error.message, true); }
  finally { setLoading(false); }
}

async function loadCase(caseId, roiRelativePath = '', options = {}) {
  const discardDirty = Boolean(state.session?.dirty);
  if (discardDirty && !confirm('当前病例有未保存修改，确定切换病例吗？')) return;
  const preserveView = Boolean(options.preserveView && state.session?.case_id === caseId);
  const previousOrientation = state.orientation;
  const previousIndices = { ...state.indices };
  try {
    abortSliceRequests();
    setLoading(true, '正在读取三维影像');
    const session = await post('/api/cases/load', {
      case_id: caseId,
      discard_dirty: discardDirty,
      roi_relative_path: roiRelativePath,
      expected_roi_sha256: options.expectedRoiSha256 || '',
    });
    close3dPanel(true);
    sessionStorage.setItem(CASE_STORAGE_KEY, session.case_id);
    sessionStorage.setItem(SESSION_STORAGE_KEY, session.session_token);
    state.indices = Object.fromEntries(Object.entries(session.orientations).map(([key, value]) => {
      const centered = Math.floor((value.count - 1) / 2);
      const previous = Number(previousIndices[key]);
      return [key, preserveView && Number.isFinite(previous) ? Math.max(0, Math.min(value.count - 1, previous)) : centered];
    }));
    if (preserveView && session.orientations[previousOrientation]) state.orientation = previousOrientation;
    state.promptVisuals = []; state.polygonPoints = []; state.loadedRoiPath = roiRelativePath; state.zoom = 1; state.panX = 0; state.panY = 0;
    updateSession(session, true);
    // Boundary-only display can make a solid vessel mask look hollow. Start
    // every newly loaded case in filled mode without touching ROI data.
    setOverlayMode('fill', true, false);
    renderCases();
    await refreshSlice();
    if (session.warnings?.length) toast(session.warnings.join('；'));
    return session;
  } catch (error) { toast(error.message, true); return null; }
  finally { setLoading(false); }
}

function updateSession(session, resetLabels = false) {
  state.session = session;
  const validLayerKeys = new Set(sessionLayers().map(layer => layer.layer_key || String(layer.id)));
  state.selectedRoiFiles = new Set(session.selected_roi_files || []);
  if (resetLabels) {
    state.hiddenLayerKeys.clear();
    state.layerOpacities.clear();
    state.selectedRoiFiles = new Set(session.selected_roi_files || []);
    const selected = new Set(session.selected_roi_files || []);
    state.hiddenLayerKeys = new Set(sessionLayers().filter(layer => layer.source_file && !selected.has(layer.source_file)).map(layer => layer.layer_key));
  }
  state.hiddenLayerKeys = new Set([...state.hiddenLayerKeys].filter(layerKey => validLayerKeys.has(layerKey)));
  state.roi3dSelectedLayerKeys = new Set([...state.roi3dSelectedLayerKeys].filter(layerKey => validLayerKeys.has(layerKey)));
  if (!state.loadedRoiPath && session.loaded_roi_source) state.loadedRoiPath = session.loaded_roi_source;
  if (resetLabels) state.hiddenLabelIds.clear();
  const caseRecord = state.cases.find(item => item.case_id === session.case_id);
  if (caseRecord) {
    caseRecord.status = session.status;
    state.expandedPatients.add(caseRecord.patient_id || caseRecord.case_id.split('/')[0]);
  }
  ui.empty.classList.add('hidden');
  ui.content.classList.remove('hidden');
  const orientation = currentOrientation();
  state.indices[state.orientation] = Math.min(Math.max(state.indices[state.orientation] || 0, 0), orientation.count - 1);
  ui.sliceSlider.max = String(orientation.count - 1);
  syncSliceSliderValue();
  ui.sliceText.textContent = `${currentIndex() + 1} / ${orientation.count}`;
  ui.geometry.textContent = `${session.case_id} · ${session.shape_zyx.join('×')} · ${session.spacing_xyz.map(v => Number(v).toFixed(3)).join(' / ')} mm · ${session.status}`;
  const selected = Number(ui.labelSelect.value || session.labels[0]?.id || 1);
  ui.labelSelect.innerHTML = sessionLayers().map(label => {
    const reference = session.reference_label_ids?.includes(label.id)
      ? (session.interactive_reference_label_ids?.includes(label.id) ? '（nnInteractive参考）' : '（对比）')
      : session.editable_roi_source ? '（当前编辑）' : '';
    return `<option value="${label.id}" data-layer-key="${escapeHtml(label.layer_key || String(label.id))}">${label.source_file ? `${escapeHtml(displayRoiSource(label.source_file))} · ${label.source_label_id}` : label.id}: ${escapeHtml(label.display_name || label.name)}${reference}</option>`;
  }).join('');
  ui.labelSelect.value = String(sessionLayers().some(label => label.id === selected) ? selected : sessionLayers()[0]?.id || 1);
  syncLabelLock();
  renderRoiLayers();
  if (!ui.roi3dPanel.classList.contains('hidden')) render3dRoiSelector();
  renderMaskOptions(session);
  if (state.activeModule === 'vascular' && state.loadedRoiPath) {
    ui.vascularRoiVisualStatus.textContent = `已显示 ${state.loadedRoiPath}；可切换图层或生成 3D。`;
  }
  renderRangeOperationLog(session);
  if (ui.pointPromptStatus) {
    ui.pointPromptStatus.textContent = session.prompt_count
      ? `已添加 ${session.prompt_count} 个点提示；点击“补充分割”继续修补。`
      : '先选择“添加正点”或“添加负点”，再在影像上点击需要补修的位置。';
  }
  const modelValue = ui.modelSelect.value;
  ui.modelSelect.innerHTML = session.models.map(name => `<option>${escapeHtml(name)}</option>`).join('');
  if (session.models.includes(modelValue)) ui.modelSelect.value = modelValue;
  ui.modelStatus.textContent = session.prompt_count
    ? `已添加 ${session.prompt_count} 个提示；运行结果写入当前可编辑 ROI。`
    : session.interactive_reference?.relative_path && session.interactive_reference_pending
      ? `已载入 nnInteractive 参考：${session.interactive_reference.relative_path}；下一次运行会把完整三维 ROI 作为初始模板。`
      : session.interactive_reference?.relative_path
        ? `nnInteractive 参考仍作为锁定对比层保留；后续运行默认从当前可编辑 ROI 继续修补。`
    : session.working_layer_kind === 'new_auto'
      ? '自动肿瘤分割已创建独立工作层；nnInteractive 将继续写入该层，不会写入体成分或既有 ROI。'
      : session.working_layer_kind === 'new_interactive'
        ? '当前没有选中既有 ROI；nnInteractive 将结果写入新建半自动肿瘤工作层。确认后保存才会生成新的 ROI 文件。'
    : session.editable_roi_source
        ? `已载入可编辑 ROI：${session.editable_roi_source}；模型会把当前三维 ROI 作为初始模板，结果写回当前编辑层。`
        : '请先添加提示，或载入 ROI 作为 nnInteractive 参考；结果会写入当前可编辑 ROI。';
  syncWorkspaceState();
  scheduleVascularStatusRefresh();
  if (resetLabels) initializeDisplay(session);
  if (state.activeModule === 'vascular' && !state.loadedRoiPath && !state.vascularModuleRefreshInFlight) {
    void refreshVascularModuleAssets();
  }
  setMarkers(orientation.markers);
  fitViewport();
  drawDraft();
}

function showEmpty() {
  abortSliceRequests();
  state.session = null;
  close3dPanel(true);
  ui.empty.classList.remove('hidden');
  ui.content.classList.add('hidden');
  ui.geometry.textContent = '未加载病例';
  state.hiddenLabelIds.clear();
  renderRoiLayers();
  renderMaskOptions(null);
  renderRangeOperationLog(null);
  syncWorkspaceState();
  scheduleVascularStatusRefresh(0);
}

function setMarkers(markers) {
  [ui.markerTop.textContent, ui.markerBottom.textContent, ui.markerLeft.textContent, ui.markerRight.textContent] = markers;
}

function syncLabelLock() {
  const label = currentLayer();
  const isReference = Boolean(label && !label.editable);
  ui.labelLock.checked = Boolean(label?.locked);
  ui.labelLock.disabled = !label || isReference;
  ui.labelColor.value = label?.color || '#ff3b30';
  ui.labelColor.disabled = !label;
  const rangeDeleteDisabled = !label || Boolean(label.locked) || !label.editable;
  ui.trimRoiLeft.disabled = rangeDeleteDisabled;
  ui.trimRoiRight.disabled = rangeDeleteDisabled;
}

function fitViewport() {
  if (!state.session) return;
  const info = currentOrientation();
  const availableWidth = Math.max(100, ui.viewport.clientWidth - 42);
  const availableHeight = Math.max(100, ui.viewport.clientHeight - 42);
  const ratio = (info.cols * info.col_spacing) / (info.rows * info.row_spacing);
  let width = availableWidth, height = width / ratio;
  if (height > availableHeight) { height = availableHeight; width = height * ratio; }
  ui.content.style.width = `${width}px`;
  ui.content.style.height = `${height}px`;
  applyViewTransform();
  ui.canvas.width = info.cols;
  ui.canvas.height = info.rows;
  drawDraft();
}

function applyViewTransform() {
  ui.content.style.transform = `translate(-50%, -50%) translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
}

function abortSliceRequests() {
  state.sliceRequestControllers.forEach(controller => {
    if (!controller.signal.aborted) controller.abort();
  });
  state.sliceRequestControllers.clear();
  sliceDynamicPending = false;
  state.renderToken += 1;
}

function decodeSliceUrl(url) {
  return new Promise((resolve, reject) => {
    const preview = new Image();
    preview.onload = () => resolve();
    preview.onerror = () => reject(new Error('切片图像解码失败'));
    preview.src = url;
  });
}

async function refreshSlice(showIntermediate = false) {
  if (!state.session) return;
  if (showIntermediate && state.sliceRequestControllers.size) {
    sliceDynamicPending = true;
    return;
  }
  if (!showIntermediate) abortSliceRequests();
  const requestToken = ++state.renderToken;
  const controller = new AbortController();
  state.sliceRequestControllers.set(requestToken, controller);
  const requestCaseId = state.session.case_id;
  const requestSessionToken = state.session.session_token;
  const requestRevision = state.session.revision;
  const requestOrientation = state.orientation;
  const requestIndex = currentIndex();
  const requestDisplay = {
    level: Number(state.level),
    width: Number(state.width),
    opacity: Number(ui.opacity.value) / 100,
    mode: ui.overlayMode.value,
    boundaryWidth: Number(ui.boundaryWidth.value),
    hiddenLabels: '',
    hiddenLayers: [...state.hiddenLayerKeys].sort().join(','),
    layerOpacities: JSON.stringify(Object.fromEntries(state.layerOpacities)),
  };
  const params = new URLSearchParams({
    orientation: requestOrientation, index: requestIndex, level: requestDisplay.level, width: requestDisplay.width,
    opacity: requestDisplay.opacity, mode: requestDisplay.mode,
    boundary_width: requestDisplay.boundaryWidth,
    baseline: false, proposal: false, v: state.session.revision,
    hidden_labels: requestDisplay.hiddenLabels,
    hidden_layers: requestDisplay.hiddenLayers,
    layer_opacities: requestDisplay.layerOpacities,
  });
  let nextUrl = '';
  try {
    const response = await fetch(`/api/slice?${params}`, { headers: caseHeaders(), signal: controller.signal });
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || '切片读取失败'); }
    const blob = await response.blob();
    nextUrl = URL.createObjectURL(blob);
    await decodeSliceUrl(nextUrl);
    if (
      controller.signal.aborted
      || requestToken !== state.renderToken
      || requestToken < state.sliceCommittedToken
      || state.session?.case_id !== requestCaseId
      || state.session?.session_token !== requestSessionToken
      || state.session?.revision !== requestRevision
      || state.orientation !== requestOrientation
      || currentIndex() !== requestIndex
      || Number(state.level) !== requestDisplay.level
      || Number(state.width) !== requestDisplay.width
      || Number(ui.opacity.value) / 100 !== requestDisplay.opacity
      || ui.overlayMode.value !== requestDisplay.mode
      || Number(ui.boundaryWidth.value) !== requestDisplay.boundaryWidth
      || [...state.hiddenLayerKeys].sort().join(',') !== requestDisplay.hiddenLayers
      || JSON.stringify(Object.fromEntries(state.layerOpacities)) !== requestDisplay.layerOpacities
    ) return;
    if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
    state.imageUrl = nextUrl;
    nextUrl = '';
    state.sliceCommittedToken = requestToken;
    state.displayedSlice = { caseId: requestCaseId, orientation: requestOrientation, index: requestIndex };
    ui.image.src = state.imageUrl;
    syncSliceSliderValue(requestIndex);
    ui.sliceText.textContent = `${requestIndex + 1} / ${currentOrientation().count}`;
    drawDraft();
  } catch (error) {
    if (error?.name !== 'AbortError') toast(error.message, true);
  }
  finally {
    state.sliceRequestControllers.delete(requestToken);
    if (nextUrl) URL.revokeObjectURL(nextUrl);
    if (showIntermediate && sliceDynamicPending) {
      sliceDynamicPending = false;
      scheduleDynamicSlice();
    }
  }
}

let renderTimer = null;
function scheduleSlice(delay = 40) {
  clearTimeout(renderTimer);
  clearTimeout(sliceThrottleTimer);
  sliceThrottleTimer = null;
  if (sliceAnimationFrame !== null) cancelAnimationFrame(sliceAnimationFrame);
  sliceAnimationFrame = null;
  renderTimer = setTimeout(() => refreshSlice(false), delay);
}
let sliceAnimationFrame = null;
let sliceThrottleTimer = null;
let sliceLastDispatchAt = 0;
let sliceDynamicPending = false;
function scheduleDynamicSlice() {
  if (state.sliceRequestControllers.size) {
    sliceDynamicPending = true;
    return;
  }
  if (sliceAnimationFrame !== null || sliceThrottleTimer !== null) return;
  const wait = Math.max(0, 70 - (performance.now() - sliceLastDispatchAt));
  const dispatch = () => {
    sliceThrottleTimer = null;
    sliceAnimationFrame = requestAnimationFrame(() => {
      sliceAnimationFrame = null;
      sliceLastDispatchAt = performance.now();
      refreshSlice(true);
    });
  };
  if (wait > 0) sliceThrottleTimer = setTimeout(dispatch, wait);
  else dispatch();
}

function canvasPoint(event) {
  const rect = ui.canvas.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(ui.canvas.width - 1, (event.clientX - rect.left) * ui.canvas.width / rect.width)),
    y: Math.max(0, Math.min(ui.canvas.height - 1, (event.clientY - rect.top) * ui.canvas.height / rect.height)),
  };
}

function drawDraft() {
  const ctx = ui.canvas.getContext('2d');
  ctx.clearRect(0, 0, ui.canvas.width, ui.canvas.height);
  const visuals = state.promptVisuals.filter(item => item.orientation === state.orientation && item.index === currentIndex());
  visuals.forEach(item => drawVisual(ctx, item.kind, item.points, true, item.radius));
  if (state.polygonPoints.length) drawVisual(ctx, state.tool, state.polygonPoints, false);
  if (state.draftPoints.length) drawVisual(ctx, state.tool, state.draftPoints, false);
  drawBrushCursor(ctx);
}

function drawBrushCursor(ctx) {
  if (!state.hoverPoint || !['brush', 'eraser', 'positive', 'negative'].includes(state.tool)) return;
  const isPrompt = ['positive', 'negative'].includes(state.tool);
  const radius = Math.max(1, Number(isPrompt ? ui.promptRadius.value : ui.brushSize.value));
  const color = state.tool === 'eraser' || state.tool === 'negative' ? '#ff4d5d' : currentLabelColor();
  ctx.save();
  ctx.beginPath(); ctx.arc(state.hoverPoint.x, state.hoverPoint.y, radius, 0, Math.PI * 2);
  ctx.globalAlpha = .18; ctx.fillStyle = color; ctx.fill();
  ctx.globalAlpha = .95; ctx.strokeStyle = color; ctx.lineWidth = Math.max(1.25, ui.canvas.width / 420); ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(state.hoverPoint.x - Math.min(radius, 4), state.hoverPoint.y);
  ctx.lineTo(state.hoverPoint.x + Math.min(radius, 4), state.hoverPoint.y);
  ctx.moveTo(state.hoverPoint.x, state.hoverPoint.y - Math.min(radius, 4));
  ctx.lineTo(state.hoverPoint.x, state.hoverPoint.y + Math.min(radius, 4));
  ctx.stroke();
  ctx.restore();
}

function drawVisual(ctx, kind, points, completed, radius = 1) {
  if (!points.length) return;
  const negative = kind.includes('negative');
  ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  ctx.strokeStyle = kind === 'eraser' ? '#ff4d5d' : kind === 'brush' ? currentLabelColor() : negative ? '#ff4d5d' : (kind === 'box' || kind === 'lasso' ? '#ffd60a' : '#38e681');
  ctx.fillStyle = ctx.strokeStyle; ctx.lineWidth = Math.max(1.5, ui.canvas.width / 320);
  if (kind === 'brush' || kind === 'eraser') {
    ctx.globalAlpha = .65; ctx.lineWidth = Number(ui.brushSize.value) * 2; ctx.beginPath(); ctx.moveTo(points[0].x, points[0].y); points.slice(1).forEach(p => ctx.lineTo(p.x, p.y)); ctx.stroke();
  } else if (kind.includes('scribble') || kind === 'polygon' || kind === 'lasso') {
    ctx.beginPath(); ctx.moveTo(points[0].x, points[0].y); points.slice(1).forEach(p => ctx.lineTo(p.x, p.y)); if (completed || kind === 'polygon' || kind === 'lasso') ctx.closePath(); ctx.stroke();
  } else if (kind === 'box' && points.length > 1) {
    const a = points[0], b = points[points.length - 1]; ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
  } else {
    const pointRadius = Math.max(3, Number(radius) || 1);
    points.forEach(p => { ctx.beginPath(); ctx.arc(p.x, p.y, pointRadius, 0, Math.PI * 2); ctx.globalAlpha = .2; ctx.fill(); ctx.globalAlpha = .95; ctx.stroke(); });
  }
  ctx.restore();
}

async function sendStroke(tool, points) {
  if (!roiInteractionEnabled()) return;
  const session = await post('/api/edit/stroke', { orientation: state.orientation, index: currentIndex(), ...layerIdentityPayload(), tool, radius: Number(ui.brushSize.value), points });
  state.promptVisuals = [];
  updateSession(session); await refreshSlice();
}

async function sendPrompt(kind, points) {
  if (!roiInteractionEnabled()) return;
  const radius = Number(ui.promptRadius.value);
  const session = await post('/api/prompts', { orientation: state.orientation, index: currentIndex(), kind, points, radius });
  state.promptVisuals.push({ orientation: state.orientation, index: currentIndex(), kind, points: [...points], radius });
  updateSession(session); drawDraft();
}

ui.canvas.addEventListener('contextmenu', event => { if (standardViewerNavigationEnabled()) event.preventDefault(); });
ui.canvas.addEventListener('pointerdown', async event => {
  if (!standardViewerNavigationEnabled()) return;
  ui.canvas.setPointerCapture(event.pointerId); state.pointerId = event.pointerId;
  if (event.button === 2) {
    state.pointerMode = 'ww'; state.wwStart = {
      x: event.clientX, y: event.clientY, level: state.level, width: state.width,
      brightness: state.mrBrightness, contrast: state.mrContrast, modality: state.displayModality,
    }; return;
  }
  if (state.activeModule === 'vascular') {
    if (event.button !== 0) return;
    state.pointerMode = 'pan';
    state.startPoint = { x: event.clientX, y: event.clientY, panX: state.panX, panY: state.panY };
    return;
  }
  if (!roiInteractionEnabled()) return;
  const point = canvasPoint(event);
  if (['brush', 'eraser', 'positive', 'negative'].includes(state.tool)) state.hoverPoint = point;
  if (state.tool === 'keep_component') {
    try {
      const session = await post('/api/edit/keep-component', {
        orientation: state.orientation,
        index: currentIndex(),
        ...layerIdentityPayload(),
        point,
      });
      updateSession(session);
      await refreshSlice();
      toast(session.removed_voxels ? `已保留当前层所选 ROI，并扩展保留其 3D 连通分支；删除 ${session.removed_voxels} 个其它体素，可撤销` : '当前层和整卷都只有所选 ROI');
    } catch (error) { toast(error.message, true); }
    return;
  }
  if (state.tool === 'pan') { state.pointerMode = 'pan'; state.startPoint = { x: event.clientX, y: event.clientY, panX: state.panX, panY: state.panY }; return; }
  if (state.tool === 'polygon' || state.tool === 'lasso') { state.polygonPoints.push(point); drawDraft(); return; }
  if (state.tool === 'positive' || state.tool === 'negative') {
    try { await sendPrompt(state.tool, [point]); } catch (error) { toast(error.message, true); } return;
  }
  if (state.tool === 'fill') {
    try { const session = await post('/api/edit/fill', { orientation: state.orientation, index: currentIndex(), ...layerIdentityPayload(), point }); updateSession(session); await refreshSlice(); }
    catch (error) { toast(error.message, true); } return;
  }
  state.pointerMode = state.tool; state.startPoint = point; state.draftPoints = [point]; drawDraft();
});

ui.canvas.addEventListener('pointermove', event => {
  if (!standardViewerNavigationEnabled()) return;
  const editingEnabled = roiInteractionEnabled();
  const tracksBrush = editingEnabled && ['brush', 'eraser', 'positive', 'negative'].includes(state.tool);
  if (tracksBrush) state.hoverPoint = canvasPoint(event);
  if (state.pointerMode === 'ww') {
    if (state.wwStart.modality !== 'CT') {
      state.mrContrast = clamp(state.wwStart.contrast + event.clientX - state.wwStart.x, 25, 300);
      state.mrBrightness = clamp(state.wwStart.brightness + (state.wwStart.y - event.clientY) * .5, -100, 100);
      applyMrWindow();
    } else {
      state.width = Math.max(1, state.wwStart.width + (event.clientX - state.wwStart.x) * 2);
      state.level = state.wwStart.level + (event.clientY - state.wwStart.y);
    }
    updateDisplayUi(); scheduleSlice(70); return;
  }
  if (state.pointerMode === 'pan') {
    state.panX = state.startPoint.panX + event.clientX - state.startPoint.x;
    state.panY = state.startPoint.panY + event.clientY - state.startPoint.y;
    applyViewTransform(); return;
  }
  if (!editingEnabled) return;
  if (state.pointerMode && !['positive', 'negative', 'fill'].includes(state.pointerMode)) {
    const point = canvasPoint(event);
    if (state.pointerMode === 'box') state.draftPoints = [state.startPoint, point]; else state.draftPoints.push(point);
    drawDraft();
  } else if (tracksBrush) drawDraft();
});

ui.canvas.addEventListener('pointerenter', event => {
  if (!roiInteractionEnabled()) return;
  if (!['brush', 'eraser', 'positive', 'negative'].includes(state.tool)) return;
  state.hoverPoint = canvasPoint(event); drawDraft();
});
ui.canvas.addEventListener('pointerleave', () => {
  if (!roiInteractionEnabled()) return;
  if (state.pointerMode) return;
  state.hoverPoint = null; drawDraft();
});

ui.canvas.addEventListener('pointerup', async event => {
  if (!standardViewerNavigationEnabled()) return;
  const mode = state.pointerMode; state.pointerMode = null;
  if (!mode || mode === 'pan' || mode === 'ww') return;
  if (!roiInteractionEnabled()) return;
  const points = [...state.draftPoints]; state.draftPoints = []; drawDraft();
  try {
    if (mode === 'brush' || mode === 'eraser') await sendStroke(mode, points);
    else if (mode === 'box' || mode.includes('scribble')) await sendPrompt(mode, points);
  } catch (error) { toast(error.message, true); }
});

async function completePolygonOrLasso() {
  if (!roiInteractionEnabled()) return false;
  if (!['polygon', 'lasso'].includes(state.tool) || state.polygonPoints.length < 3) return false;
  const tool = state.tool;
  const points = [...state.polygonPoints]; state.polygonPoints = []; drawDraft();
  try {
    if (tool === 'polygon') {
      const session = await post('/api/edit/polygon', { orientation: state.orientation, index: currentIndex(), ...layerIdentityPayload(), points });
      updateSession(session); await refreshSlice();
    } else await sendPrompt('lasso', points);
  } catch (error) { toast(error.message, true); }
  return true;
}

ui.canvas.addEventListener('dblclick', async event => {
  if (!roiInteractionEnabled()) return;
  event.preventDefault();
  await completePolygonOrLasso();
});

ui.viewport.addEventListener('wheel', event => {
  if (!standardViewerNavigationEnabled()) return;
  event.preventDefault();
  if (event.ctrlKey) {
    state.zoom = Math.max(.35, Math.min(8, state.zoom * (event.deltaY < 0 ? 1.15 : 1 / 1.15)));
    applyViewTransform();
  } else changeSlice(event.deltaY > 0 ? 1 : -1);
}, { passive: false });

function changeSlice(delta) {
  if (!state.session) return;
  const max = currentOrientation().count - 1;
  state.indices[state.orientation] = Math.max(0, Math.min(max, currentIndex() + delta));
  state.polygonPoints = []; ui.sliceSlider.value = currentIndex(); scheduleSlice(0); drawDraft();
}

async function startTask(kind) {
  try {
    const payload = kind === 'auto' ? { model_name: ui.modelSelect.value } : layerIdentityPayload();
    const task = await post(`/api/tasks/${kind}`, payload);
    state.activeTask = task.id; ui.cancelTask.disabled = false; setTaskState('running', '模型运行中…'); pollTask(task.id);
  } catch (error) { toast(error.message, true); }
}

async function pollTask(taskId) {
  if (state.activeTask !== taskId) return;
  try {
    const task = await api(`/api/tasks/${taskId}`); setTaskState(task.status, task.message || task.error);
    if (task.status === 'completed') {
      state.activeTask = null; ui.cancelTask.disabled = true; state.promptVisuals = [];
      let session = await api('/api/session');
      if (session.prompt_count) session = await post('/api/prompts/reset');
      updateSession(session);
      const focused = await focusModelResult(session);
      if (focused) {
        toast(`模型 ROI 已显示在第 ${focused.index + 1} 层，可直接使用画笔或橡皮擦修补`);
      } else if (session.empty_model_output_labels?.length) {
        toast(`模型返回空 ROI（标签 ${session.empty_model_output_labels.join('、')}），已有 ROI 未被覆盖；请调整套索或提示后重试`, true);
      } else {
        await refreshSlice();
        toast('模型没有返回可显示的 ROI，请检查模型输出', true);
      }
      return;
    }
    if (task.status === 'failed' || task.status === 'cancelled') {
      state.activeTask = null; ui.cancelTask.disabled = true; if (task.error) toast(task.error, true); return;
    }
    setTimeout(() => pollTask(taskId), 900);
  } catch (error) { state.activeTask = null; ui.cancelTask.disabled = true; toast(error.message, true); }
}

async function focusModelResult(session) {
  const outputLabels = [...new Set((session.model_output_labels || []).map(Number).filter(Number.isFinite))];
  return focusLabels(outputLabels);
}

async function focusLabels(labelIds) {
  const outputLabels = [...new Set(labelIds.map(Number).filter(Number.isFinite))];
  if (!outputLabels.length) return null;
  outputLabels.forEach(labelId => state.hiddenLabelIds.delete(labelId));
  if (Number(ui.opacity.value) < 20) setRoiOpacity(55);

  const selected = currentLabelId();
  const orderedLabels = outputLabels.includes(selected)
    ? [selected, ...outputLabels.filter(labelId => labelId !== selected)]
    : outputLabels;
  for (const labelId of orderedLabels) {
    const { indices } = await api(`/api/roi-slices?orientation=${state.orientation}&label_id=${labelId}`);
    if (!indices.length) continue;
    ui.labelSelect.value = String(labelId);
    syncLabelLock();
    renderRoiLayers();
    syncWorkspaceState();
    const index = indices[Math.floor(indices.length / 2)];
    state.indices[state.orientation] = index;
    ui.sliceSlider.value = String(index);
    ui.sliceText.textContent = `${index + 1} / ${currentOrientation().count}`;
    await refreshSlice();
    return { labelId, index };
  }
  renderRoiLayers();
  return null;
}

async function importPatientMask() {
  const relativePath = ui.maskSelect.value;
  if (!relativePath) return toast('当前患者文件夹没有可加载的 ROI / NIfTI 标签图', true);
  try {
    setLoading(true, '正在校验并加载 Mask');
    const session = await post('/api/roi/import', { relative_path: relativePath });
    const importedLabelIds = session.imported_label_ids || [];
    updateSession(session);
    importedLabelIds.forEach(labelId => state.hiddenLabelIds.delete(labelId));
    const focused = await focusLabels(importedLabelIds);
    renderRoiLayers();
    toast(focused
      ? `既往 ROI 已作为只读对比图层显示，并定位到第 ${focused.index + 1} 层`
      : '既往 ROI 已作为只读对比图层加载');
  } catch (error) { toast(error.message, true); }
  finally { setLoading(false); }
}

async function loadEditablePatientRoi() {
  const relativePath = ui.maskSelect.value;
  if (!relativePath) return toast('当前患者文件夹没有可加载的 ROI', true);
  const request = { relative_path: relativePath, discard_dirty: false };
  try {
    setLoading(true, '正在载入可编辑 ROI');
    let session;
    try {
      session = await post('/api/roi/load-editable', request);
    } catch (error) {
      if (!/未保存|未落盘|dirty|修改/.test(error.message) || !window.confirm('当前 ROI 有未保存修改。继续载入会丢弃这些内存修改，是否继续？')) throw error;
      session = await post('/api/roi/load-editable', { ...request, discard_dirty: true });
    }
    updateSession(session);
    const editable = (session.labels || []).filter(label => !session.reference_label_ids?.includes(label.id));
    if (editable.length) {
      editable.forEach(label => state.hiddenLabelIds.delete(label.id));
      ui.labelSelect.value = String(editable[0].id);
      syncLabelLock();
    }
    renderRoiLayers();
    syncWorkspaceState();
    await refreshSlice();
    toast(`已载入 ${relativePath} 作为当前可编辑 ROI；可直接画笔/橡皮擦修改，源文件不会被改写`);
  } catch (error) { toast(error.message, true); }
  finally { setLoading(false); }
}

async function loadInteractiveReference() {
  const relativePath = ui.maskSelect.value;
  if (!relativePath) return toast('当前患者文件夹没有可加载的 ROI', true);
  const currentEditable = currentLabelId();
  try {
    setLoading(true, '正在载入 nnInteractive 参考');
    const session = await post('/api/roi/load-interactive-reference', { relative_path: relativePath });
    const importedLabelIds = session.imported_label_ids || session.interactive_reference_label_ids || [];
    updateSession(session);
    importedLabelIds.forEach(labelId => state.hiddenLabelIds.delete(Number(labelId)));
    const editableLabel = (session.labels || []).find(label => !session.reference_label_ids?.includes(label.id) && label.id === currentEditable)
      || (session.labels || []).find(label => !session.reference_label_ids?.includes(label.id));
    if (editableLabel) {
      ui.labelSelect.value = String(editableLabel.id);
      syncLabelLock();
    }
    renderRoiLayers();
    syncWorkspaceState();
    const focusId = Number(importedLabelIds[0]);
    if (Number.isFinite(focusId)) {
      const { indices } = await api(`/api/roi-slices?orientation=${state.orientation}&label_id=${focusId}`);
      if (indices.length) state.indices[state.orientation] = indices[Math.floor(indices.length / 2)];
    }
    await refreshSlice();
    toast(`已载入 ${relativePath} 为 nnInteractive 锁定参考；右侧图层已单独标记，运行结果写入当前编辑 ROI`);
  } catch (error) { toast(error.message, true); }
  finally { setLoading(false); }
}

function applyIntensityPreset() {
  const preset = ui.intensityPreset.value;
  if (preset === 'air') {
    ui.intensityMin.value = '';
    ui.intensityMax.value = '-500';
  } else if (preset === 'fat') {
    ui.intensityMin.value = '-190';
    ui.intensityMax.value = '-30';
  }
}

function optionalNumber(input) {
  const value = String(input.value ?? '').trim();
  if (!value) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : NaN;
}

async function excludeIntensityFromRoi() {
  if (!state.session) return toast('请先载入病例', true);
  const minimum = optionalNumber(ui.intensityMin);
  const maximum = optionalNumber(ui.intensityMax);
  if (Number.isNaN(minimum) || Number.isNaN(maximum)) return toast('阈值必须是有效数字', true);
  const scope = ui.intensityScope.value;
  if (scope === 'volume' && !window.confirm('这会从当前 ROI 的整个三维范围中排除符合阈值的体素，操作可撤销。继续吗？')) return;
  try {
    const session = await post('/api/edit/exclude-intensity', {
      orientation: state.orientation,
      index: currentIndex(),
      ...layerIdentityPayload(),
      scope,
      minimum,
      maximum,
    });
    updateSession(session);
    await refreshSlice();
    toast(session.removed_voxels ? `已排除 ${session.removed_voxels} 个体素；可撤销` : '当前 ROI 内没有符合阈值的体素');
  } catch (error) { toast(error.message, true); }
}

async function keepClickedComponent() {
  if (!state.session) return toast('请先载入病例', true);
  toast('请在当前影像中点击要保留的连通区');
}

function setTaskState(status, message) { ui.taskDot.className = `task-dot ${status}`; ui.modelStatus.textContent = message; }

async function restoreModelOriginal() {
  try {
    const session = await post('/api/proposals/merge', { ...layerIdentityPayload(), operation: 'restore_baseline' });
    state.hiddenLabelIds.delete(currentLabelId());
    updateSession(session); renderRoiLayers(); await refreshSlice();
    toast('当前 ROI 已恢复为本次模型原始结果');
  } catch (error) { toast(error.message, true); }
}

async function saveRoi() {
  const roiName = ui.roiName.value.trim();
  if (!roiName) return toast('请先填写 ROI 名称', true);
  try {
    localStorage.setItem(ROI_NAME_KEY, roiName);
    const result = await post('/api/export', { reviewed: false, roi_name: roiName });
    updateSession(await api('/api/session'));
    state.loadedRoiPath = result.relative_path;
    state.cases = (await api('/api/cases')).items;
    const current = state.cases.find(item => item.case_id === state.session?.case_id);
    if (current) state.expandedPatients.add(current.patient_id || current.case_id.split('/')[0]);
    renderCases();
    const overlap = result.overlap_count ? `；${result.overlap_count} 个重叠体素已按标签优先级合并` : '';
    toast(`${result.filename} 已保存；本轮修补已结束，可从左侧再次打开${overlap}`);
  }
  catch (error) { toast(error.message, true); }
}

async function jumpRoi(where) {
  if (!state.session) return;
  try {
    const { indices } = await api(`/api/roi-slices?orientation=${state.orientation}&label_id=${currentLabelId()}&layer_key=${encodeURIComponent(currentLayerKey())}`);
    if (!indices.length) return toast('当前标签没有 ROI');
    let target;
    if (where === 'first') target = indices[0]; else if (where === 'middle') target = indices[Math.floor(indices.length / 2)]; else if (where === 'last') target = indices.at(-1);
    else if (where === 'prev') target = [...indices].reverse().find(value => value < currentIndex()) ?? indices[0];
    else target = indices.find(value => value > currentIndex()) ?? indices.at(-1);
    state.indices[state.orientation] = target; scheduleSlice(0);
  } catch (error) { toast(error.message, true); }
}

async function trimRoiRange(direction) {
  if (!state.session) return toast('请先载入病例', true);
  const labelId = currentLabelId();
  const index = currentIndex();
  try {
    const session = await post('/api/edit/trim', {
      orientation: state.orientation,
      index,
      label_id: labelId,
      layer_key: currentLayerKey(),
      direction,
    });
    updateSession(session);
    state.draftPoints = [];
    state.polygonPoints = [];
    drawDraft();
    await refreshSlice();
    const entry = session.range_operation_log?.[session.range_operation_log.length - 1];
    if (!entry?.removed_voxels) toast('所选范围内没有可删除的 ROI');
    else toast(`${entry.message}；可点击“撤销”恢复`);
  } catch (error) { toast(error.message, true); }
}

ui.moduleTabs.forEach(tab => tab.addEventListener('click', () => setActiveModule(tab.dataset.workbenchModule)));
ui.vascularModelButtons.forEach(button => button.addEventListener('click', () => setVascularModel(button.dataset.vascularModel)));
ui.vascularRunCurrent.addEventListener('click', launchVascularCurrent);
ui.vascularRunBatch.addEventListener('click', launchVascularBatch);
ui.vascularCancel.addEventListener('click', cancelVascularTask);
ui.scanRoot.addEventListener('click', scanRoot); ui.rootPath.addEventListener('keydown', event => { if (event.key === 'Enter') scanRoot(); });
ui.caseList.addEventListener('click', handleCaseTreeClick, true);
ui.caseSearch.addEventListener('input', renderCases); ui.statusFilter.addEventListener('change', renderCases); ui.roiFileCountFilter?.addEventListener('change', renderCases);
$$('#orientation-tabs button').forEach(button => button.addEventListener('click', () => {
  if (!standardViewerNavigationEnabled()) return;
  state.orientation = button.dataset.orientation; $$('#orientation-tabs button').forEach(item => item.classList.toggle('active', item === button));
  state.polygonPoints = []; setMarkers(currentOrientation()?.markers || ['A', 'P', 'R', 'L']); fitViewport(); scheduleSlice(0);
}));
$$('#tool-buttons button').forEach(button => button.addEventListener('click', async () => {
  if (!roiInteractionEnabled()) return;
  applyToolSelection(button.dataset.tool);
  if (MANUAL_EDIT_TOOLS.has(state.tool)) {
    state.promptVisuals = [];
    if (state.session?.prompt_count && !state.activeTask) {
      try {
        updateSession(await post('/api/prompts/reset'));
      } catch (error) { toast(error.message, true); }
    }
    scheduleSlice(0);
  }
  syncWorkspaceState(); drawDraft();
}));
document.addEventListener('keydown', async event => {
  if (!roiInteractionEnabled() || event.key !== 'Enter' || event.repeat || event.isComposing || !state.session) return;
  const target = event.target;
  if (target instanceof HTMLElement && (target.matches('input, select, textarea, button') || target.isContentEditable)) return;
  if (state.tool === 'polygon' || state.tool === 'lasso') {
    event.preventDefault();
    if (state.polygonPoints.length < 3) return toast('至少标记 3 个点后按 Enter 完成');
    await completePolygonOrLasso();
    return;
  }
  if (MANUAL_EDIT_TOOLS.has(state.tool) && state.tool !== 'keep_component') {
    event.preventDefault();
    state.draftPoints = []; state.promptVisuals = []; drawDraft();
    toast('当前层 ROI 已生成；画笔、橡皮擦和填充为即时写入');
  }
});
$('#reset-view').addEventListener('click', () => { state.zoom = 1; state.panX = 0; state.panY = 0; fitViewport(); });
$('#slice-prev').addEventListener('click', () => changeSlice(-1)); $('#slice-next').addEventListener('click', () => changeSlice(1));
ui.sliceSlider.addEventListener('pointerdown', beginSliceSliderInteraction);
ui.sliceSlider.addEventListener('input', () => {
  state.sliceSliderInteracting = true;
  state.indices[state.orientation] = Number(ui.sliceSlider.value);
  const displayed = state.displayedSlice.caseId === state.session?.case_id
    && state.displayedSlice.orientation === state.orientation
    && state.displayedSlice.index >= 0
    ? state.displayedSlice.index + 1
    : '—';
  ui.sliceText.textContent = `${displayed} / ${currentOrientation().count} · 读取 ${currentIndex() + 1}`;
  state.polygonPoints = []; drawDraft(); scheduleDynamicSlice();
});
ui.sliceSlider.addEventListener('change', finishSliceSliderInteraction);
ui.sliceSlider.addEventListener('blur', finishSliceSliderInteraction);
window.addEventListener('pointerup', finishSliceSliderInteraction);
window.addEventListener('pointercancel', finishSliceSliderInteraction);
ui.level.addEventListener('change', () => { setCtWindow(ui.level.value, state.width); updateDisplayUi(); scheduleSlice(0); });
ui.width.addEventListener('change', () => { setCtWindow(state.level, ui.width.value); updateDisplayUi(); scheduleSlice(0); });
ui.windowPreset.addEventListener('change', event => {
  if (event.target.value === 'custom') return;
  const [level, width] = event.target.value.split(',').map(Number);
  setCtWindow(level, width); updateDisplayUi(); scheduleSlice(0);
});
ui.modalityMode.addEventListener('change', () => {
  state.displayModality = effectiveModality();
  if (!applyDisplayProfile(state.displayModality)) applyDisplayDefaults(state.displayModality);
  updateDisplayUi(); scheduleSlice(0);
});
ui.mrBrightness.addEventListener('input', () => {
  state.mrBrightness = Number(ui.mrBrightness.value); applyMrWindow(); updateDisplayUi(); scheduleSlice(60);
});
ui.mrContrast.addEventListener('input', () => {
  state.mrContrast = Number(ui.mrContrast.value); applyMrWindow(); updateDisplayUi(); scheduleSlice(60);
});
ui.pinDisplay.addEventListener('click', () => {
  if (!state.session) return toast('请先载入病例', true);
  if (state.displayModality === 'UNKNOWN') return toast('请先手动选择 CT 或 MR，再固定显示参数', true);
  const profiles = readDisplayProfiles();
  profiles[state.displayModality] = state.displayModality === 'MR'
    ? { brightness: state.mrBrightness, contrast: state.mrContrast }
    : { level: state.level, width: state.width };
  writeDisplayProfiles(profiles); updateDisplayUi();
  toast(`已固定 ${state.displayModality} 显示参数，后续同模态病例会自动应用`);
});
ui.clearPinnedDisplay.addEventListener('click', () => {
  const profiles = readDisplayProfiles();
  delete profiles[state.displayModality]; writeDisplayProfiles(profiles); updateDisplayUi();
  toast(`已取消 ${state.displayModality} 固定显示参数`);
});
ui.resetDisplay.addEventListener('click', () => {
  if (!state.session) return;
  applyDisplayDefaults(state.displayModality); updateDisplayUi(); scheduleSlice(0);
});
ui.opacity.addEventListener('input', () => setRoiOpacity(ui.opacity.value));
ui.opacityNumber.addEventListener('input', () => { if (ui.opacityNumber.value !== '') setRoiOpacity(ui.opacityNumber.value); });
ui.opacityNumber.addEventListener('change', () => setRoiOpacity(ui.opacityNumber.value || ui.opacity.value));
$$('[data-overlay-mode]').forEach(button => button.addEventListener('click', () => setOverlayMode(button.dataset.overlayMode)));
ui.boundaryWidth.addEventListener('input', () => setBoundaryWidth(ui.boundaryWidth.value));
ui.brushSize.addEventListener('input', () => { ui.brushValue.textContent = `${ui.brushSize.value} px`; drawDraft(); });
ui.promptRadius.addEventListener('input', () => { ui.promptRadiusValue.textContent = `${ui.promptRadius.value} px`; drawDraft(); });
ui.labelSelect.addEventListener('change', () => {
  const becameVisible = state.hiddenLabelIds.delete(currentLabelId());
  syncLabelLock(); renderRoiLayers(); syncWorkspaceState(); drawDraft();
  if (becameVisible) scheduleSlice(0);
});
ui.themeSelect.addEventListener('change', () => applyTheme(ui.themeSelect.value));
ui.render3d.addEventListener('click', renderCurrentRoi3d);
ui.vascularRender3d.addEventListener('click', renderCurrentRoi3d);
ui.vascularRoiLoad.addEventListener('click', () => loadVascularVisualRoi());
ui.reset3dView.addEventListener('click', () => state.renderer3d?.resetView());
ui.close3d.addEventListener('click', () => close3dPanel(false));
ui.roi3dRoiList.addEventListener('change', event => {
  const checkbox = event.target.closest('[data-roi-3d-visibility]');
  if (!checkbox) return;
  const layerKey = checkbox.dataset.layerKey || checkbox.getAttribute('data-roi-3d-visibility');
  if (checkbox.checked) state.roi3dSelectedLayerKeys.add(layerKey);
  else state.roi3dSelectedLayerKeys.delete(layerKey);
  render3dRoiSelector();
  schedule3dSelectionRender();
});
ui.roi3dRoiList.addEventListener('input', event => {
  const colorInput = event.target.closest('[data-roi-3d-color]');
  if (!colorInput || !/^#[0-9a-f]{6}$/i.test(colorInput.value)) return;
  const layerKey = colorInput.dataset.layerKey || colorInput.getAttribute('data-roi-3d-color');
  state.roi3dColors.set(layerKey, colorInput.value);
  state.renderer3d?.setMeshColor(layerKey, colorInput.value);
});
ui.roi3dSelectAll.addEventListener('click', () => {
  state.roi3dSelectedLayerKeys = new Set(allRoiLayerKeys());
  render3dRoiSelector();
  schedule3dSelectionRender();
});
ui.roi3dClearAll.addEventListener('click', () => {
  state.roi3dSelectedLayerKeys.clear();
  render3dRoiSelector();
  schedule3dSelectionRender(0);
});
ui.roi3dOpacity.addEventListener('input', () => {
  const opacity = Number(ui.roi3dOpacity.value);
  ui.roi3dOpacityValue.value = `${opacity}%`;
  ui.roi3dOpacityValue.textContent = `${opacity}%`;
  state.renderer3d?.setOpacity(opacity / 100);
});
ui.roi3dOpacity.addEventListener('change', persist3dStyle);
function handleRoiVisibilityChange(event) {
  const checkbox = event.target.closest('[data-roi-visibility]');
  if (!checkbox) return;
  const layerKey = checkbox.dataset.layerKey || checkbox.dataset.roiVisibility;
  if (checkbox.checked) state.hiddenLayerKeys.delete(layerKey); else state.hiddenLayerKeys.add(layerKey);
  renderRoiLayers(); scheduleSlice(0);
}
function handleRoiOpacityChange(event) {
  const input = event.target.closest('[data-roi-opacity]');
  if (!input) return;
  state.layerOpacities.set(input.dataset.layerKey || input.dataset.roiOpacity, Number(input.value) / 100);
  scheduleSlice(0);
}

ui.roiLayerList.addEventListener('change', handleRoiVisibilityChange);
ui.vascularRoiLayerList.addEventListener('change', handleRoiVisibilityChange);
ui.roiLayerList.addEventListener('input', handleRoiOpacityChange);
ui.vascularRoiLayerList.addEventListener('input', handleRoiOpacityChange);
function showAllRoiLayers() {
  state.hiddenLayerKeys.clear(); renderRoiLayers(); scheduleSlice(0);
}
function hideAllRoiLayers() {
  state.hiddenLayerKeys = new Set(sessionLayers().map(label => label.layer_key || String(label.id)));
  renderRoiLayers(); scheduleSlice(0);
}
ui.showAllRoi.addEventListener('click', showAllRoiLayers);
ui.vascularRoiShowAll.addEventListener('click', showAllRoiLayers);
ui.hideAllRoi.addEventListener('click', hideAllRoiLayers);
ui.vascularRoiHideAll.addEventListener('click', hideAllRoiLayers);
ui.labelLock.addEventListener('change', async () => { try { updateSession(await post('/api/labels/lock', { ...layerIdentityPayload(), locked: ui.labelLock.checked })); } catch (error) { toast(error.message, true); } });
ui.labelColor.addEventListener('change', async () => {
  try {
    updateSession(await post('/api/labels/color', { ...layerIdentityPayload(), color: ui.labelColor.value }));
    await refreshSlice();
    toast('当前 ROI 颜色已更新');
  } catch (error) { toast(error.message, true); }
});
ui.importMask.addEventListener('click', importPatientMask);
ui.loadEditableRoi.addEventListener('click', loadEditablePatientRoi);
ui.loadInteractiveReference.addEventListener('click', loadInteractiveReference);
ui.roiFileSelection?.addEventListener('change', async event => {
  const checkbox = event.target.closest('[data-roi-file]');
  if (!checkbox) return;
  const relativePaths = [...ui.roiFileSelection.querySelectorAll('[data-roi-file]:checked')].map(input => input.dataset.roiFile);
  const requestId = ++state.roiSelectionRequestId;
  state.selectedRoiFiles = new Set(relativePaths);
  try {
    setLoading(true, '正在同步 ROI 文件选择');
    const session = await post('/api/roi/selection', { relative_paths: relativePaths, discard_dirty: false, request_id: requestId });
    if (requestId !== state.roiSelectionRequestId) return;
    updateSession(session);
    state.hiddenLayerKeys = new Set([...state.hiddenLayerKeys].filter(key => sessionLayers().some(layer => layer.layer_key === key)));
    if (!relativePaths.includes(session.editable_roi_source || '')) {
      ui.labelSelect.value = '';
    }
    syncLabelLock(); renderRoiLayers(); await refreshSlice();
    toast(relativePaths.length ? `已选择 ${relativePaths.length} 个 ROI 文件；显示与 3D 已同步` : '已清空 ROI 文件选择；画布已清理');
  } catch (error) {
    if (requestId !== state.roiSelectionRequestId) return;
    try {
      updateSession(await api('/api/session'));
      state.hiddenLayerKeys = new Set([...state.hiddenLayerKeys].filter(key => sessionLayers().some(layer => layer.layer_key === key)));
      syncLabelLock(); renderRoiLayers(); await refreshSlice();
    } catch (_sessionError) {
      state.selectedRoiFiles = new Set(state.session?.selected_roi_files || []);
      renderRoiFileSelection(state.session);
    }
    toast(error.message, true);
  } finally { setLoading(false); }
});
async function deleteSelectedRoiFile(relativePath) {
  const checkbox = ui.roiFileSelection?.querySelector(`[data-roi-file="${CSS.escape(relativePath)}"]`);
  if (!checkbox?.checked || !relativePath) {
    toast('请先勾选要删除的 ROI 文件', true);
    return;
  }
  if (!window.confirm(`将 ${relativePath} 移至系统回收站？此操作不会永久删除文件。`)) return;
  // Invalidate any earlier asynchronous file-selection response.  Otherwise a
  // slow selection response can arrive after deletion and resurrect stale UI.
  const deleteRequestId = ++state.roiSelectionRequestId;
  try {
    setLoading(true, '正在将 ROI 移至回收站');
    const session = await post('/api/roi/delete', { relative_path: relativePath, confirm: true, request_id: deleteRequestId });
    if (deleteRequestId !== state.roiSelectionRequestId) return;
    updateSession(session);
    state.hiddenLayerKeys = new Set([...state.hiddenLayerKeys].filter(key => sessionLayers().some(layer => layer.layer_key === key)));
    ui.labelSelect.value = '';
    syncLabelLock(); renderRoiLayers(); await refreshSlice();
    toast(`${relativePath} 已移至系统回收站`);
  } catch (error) {
    if (deleteRequestId !== state.roiSelectionRequestId) return;
    try {
      updateSession(await api('/api/session'));
      renderRoiLayers();
    } catch (_sessionError) { /* Preserve the original operation failure below. */ }
    toast(error.message, true);
  } finally { setLoading(false); }
}
ui.roiFileSelection?.addEventListener('click', event => {
  const button = event.target.closest('[data-delete-roi-file]');
  if (!button || !ui.roiFileSelection.contains(button)) return;
  event.preventDefault();
  event.stopPropagation();
  void deleteSelectedRoiFile(button.dataset.deleteRoiFile || '');
});
ui.activateKeepComponent.addEventListener('click', () => { applyToolSelection('keep_component'); keepClickedComponent(); });
ui.addPositivePoint.addEventListener('click', () => {
  applyToolSelection('positive');
  ui.pointPromptStatus.textContent = '已选择添加正点：请在影像上点击需要补充的区域。';
});
ui.addNegativePoint.addEventListener('click', () => {
  applyToolSelection('negative');
  ui.pointPromptStatus.textContent = '已选择添加负点：请在影像上点击需要排除的区域。';
});
ui.runPointRefine.addEventListener('click', () => startTask('interactive'));
ui.clearPointPrompts.addEventListener('click', async () => {
  try {
    state.promptVisuals = [];
    updateSession(await post('/api/prompts/reset'));
    drawDraft();
  } catch (error) { toast(error.message, true); }
});
ui.intensityPreset.addEventListener('change', applyIntensityPreset);
ui.excludeIntensity.addEventListener('click', excludeIntensityFromRoi);
$('#undo-edit').addEventListener('click', async () => { try { updateSession(await post('/api/edit/undo')); await refreshSlice(); } catch (error) { toast(error.message, true); } });
$('#redo-edit').addEventListener('click', async () => { try { updateSession(await post('/api/edit/redo')); await refreshSlice(); } catch (error) { toast(error.message, true); } });
$('#undo-prompt').addEventListener('click', async () => { try { state.promptVisuals.pop(); updateSession(await post('/api/prompts/undo')); drawDraft(); } catch (error) { toast(error.message, true); } });
$('#reset-prompts').addEventListener('click', async () => { try { state.promptVisuals = []; updateSession(await post('/api/prompts/reset')); drawDraft(); } catch (error) { toast(error.message, true); } });
$('#run-auto').addEventListener('click', () => startTask('auto')); $('#run-interactive').addEventListener('click', () => startTask('interactive'));
ui.cancelTask.addEventListener('click', async () => { if (!state.activeTask) return; try { await post(`/api/tasks/${state.activeTask}/cancel`); } catch (error) { toast(error.message, true); } });
ui.restoreOriginal.addEventListener('click', restoreModelOriginal);
$$('[data-nav]').forEach(button => button.addEventListener('click', () => jumpRoi(button.dataset.nav)));
ui.trimRoiLeft.addEventListener('click', () => trimRoiRange('left'));
ui.trimRoiRight.addEventListener('click', () => trimRoiRange('right'));
$('#save-roi').addEventListener('click', saveRoi);
ui.roiName.addEventListener('change', () => { if (ui.roiName.value.trim()) localStorage.setItem(ROI_NAME_KEY, ui.roiName.value.trim()); });
$$('[data-panel-resizer]').forEach(resizer => {
  resizer.addEventListener('pointerdown', beginPanelResize);
  resizer.addEventListener('keydown', resizePanelWithKeyboard);
  resizer.addEventListener('dblclick', () => setPanelWidth(resizer.dataset.panelResizer, PANEL_DEFAULTS[resizer.dataset.panelResizer]));
});
window.addEventListener('resize', () => {
  restorePanelLayout();
  fitViewport();
});
updateCanvasToolClass();

async function bootstrap() {
  try {
    renderVascularModelContext();
    applyTheme(localStorage.getItem(THEME_KEY) || 'dark', false);
    const style3d = read3dStyle();
    ui.roi3dOpacity.value = String(clamp(style3d.opacity ?? ui.roi3dOpacity.value, 10, 100));
    ui.roi3dOpacityValue.value = `${ui.roi3dOpacity.value}%`;
    ui.roi3dOpacityValue.textContent = `${ui.roi3dOpacity.value}%`;
    restorePanelLayout();
    setActiveModule(localStorage.getItem(ACTIVE_MODULE_KEY) || 'roi', false);
    ui.roiName.value = localStorage.getItem(ROI_NAME_KEY) || 'ROI';
    setRoiOpacity(localStorage.getItem(ROI_OPACITY_KEY) || ui.opacity.value, false);
    // Do not restore a stale boundary-only mode across sessions. It is an
    // inspection aid, not a property of the ROI.
    setOverlayMode('fill', true, false);
    setBoundaryWidth(localStorage.getItem(ROI_BOUNDARY_WIDTH_KEY) || ui.boundaryWidth.value, false);
    await api('/health');
    $('#connection').classList.add('online');
    const rootInfo = await api('/api/root');
    const rememberedRoot = rootInfo.root || localStorage.getItem(ROOT_STORAGE_KEY) || '';
    if (rememberedRoot) ui.rootPath.value = rememberedRoot;
    state.cases = (await api('/api/cases')).items;
    const rememberedCase = sessionStorage.getItem(CASE_STORAGE_KEY);
    if (rememberedCase) {
      try {
        let session;
        try { session = await api('/api/session'); }
        catch (_staleSession) {
          if (!state.cases.some(item => item.case_id === rememberedCase)) throw _staleSession;
          session = await post('/api/cases/load', { case_id: rememberedCase, discard_dirty: false });
        }
        sessionStorage.setItem(CASE_STORAGE_KEY, session.case_id);
        sessionStorage.setItem(SESSION_STORAGE_KEY, session.session_token);
        ui.rootPath.value = session.data_root || '';
        state.indices = Object.fromEntries(Object.entries(session.orientations).map(([key, value]) => [key, Math.floor((value.count - 1) / 2)]));
        updateSession(session, true);
        await refreshSlice();
      } catch (_noSession) {
        sessionStorage.removeItem(CASE_STORAGE_KEY);
        sessionStorage.removeItem(SESSION_STORAGE_KEY);
        showEmpty();
      }
    } else showEmpty();
    renderCases();
    if (state.activeModule === 'vascular' && state.session) void refreshVascularModuleAssets();
  } catch (_error) { toast('无法连接本机 ROI 服务', true); }
}

bootstrap();
