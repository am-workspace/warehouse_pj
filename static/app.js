const STORAGE_KEYS = {
  logs: "wms-lite.logs",
  lastSku: "wms-lite.lastSku",
  autoSubmit: "wms-lite.autoSubmit",
  imagePromptSkips: "wms-lite.imagePromptSkips"
};

const state = {
  activeScreen: "home",
  operationMode: "add",
  inventoryItems: [],
  searchItems: [],
  currentProduct: null,
  currentImages: [],
  batchResults: [],
  logs: loadLogs(),
  apiOnline: false,
  cameraStream: null,
  cameraTimerId: null,
  lastScanText: "",
  imagePreviewUrl: null,
  activeCameraContext: null,
  imagePromptPreviewUrl: null,
  pendingImagePromptSku: "",
  imagePromptSkips: loadImagePromptSkips()
};

const elements = {
  screens: [...document.querySelectorAll(".screen")],
  navItems: [...document.querySelectorAll(".nav-item")],
  shortcutButtons: [...document.querySelectorAll("[data-shortcut]")],
  refreshStatus: document.getElementById("refresh-status"),
  homeStatusDot: document.getElementById("home-status-dot"),
  homeStatusText: document.getElementById("home-status-text"),
  homeStatusDetail: document.getElementById("home-status-detail"),
  statSkus: document.getElementById("stat-skus"),
  statUnits: document.getElementById("stat-units"),
  homeOpenSearch: document.getElementById("home-open-search"),
  homeActivityList: document.getElementById("home-activity-list"),
  searchInput: document.getElementById("search-product-id"),
  searchScan: document.getElementById("search-scan"),
  searchLoad: document.getElementById("search-load"),
  searchMessage: document.getElementById("search-message"),
  searchList: document.getElementById("search-list"),
  searchResult: document.getElementById("search-result"),
  searchScanModal: document.getElementById("search-scan-modal"),
  searchScanStart: document.getElementById("search-scan-start"),
  searchScanClose: document.getElementById("search-scan-close"),
  imagePromptModal: document.getElementById("image-prompt-modal"),
  imagePromptDetail: document.getElementById("image-prompt-detail"),
  imagePromptPreview: document.getElementById("image-prompt-preview"),
  imagePromptFile: document.getElementById("image-prompt-file"),
  imagePromptCamera: document.getElementById("image-prompt-camera"),
  imagePromptChoose: document.getElementById("image-prompt-choose"),
  imagePromptCapture: document.getElementById("image-prompt-capture"),
  imagePromptUpload: document.getElementById("image-prompt-upload"),
  imagePromptSkip: document.getElementById("image-prompt-skip"),
  imagePromptMessage: document.getElementById("image-prompt-message"),
  operationForm: document.getElementById("operation-form"),
  operationPreview: document.getElementById("operation-preview"),
  operationSubmit: document.getElementById("operation-submit"),
  operationMessage: document.getElementById("operation-message"),
  modeButtons: [...document.querySelectorAll(".mode-button")],
  batchResults: document.getElementById("batch-results"),
  imageProductId: document.getElementById("image-product-id"),
  imageLoad: document.getElementById("image-load"),
  imageFile: document.getElementById("image-file"),
  imagePreview: document.getElementById("image-preview"),
  imageUpload: document.getElementById("image-upload"),
  imageMessage: document.getElementById("image-message"),
  imageList: document.getElementById("image-list"),
  settingsStatus: document.getElementById("settings-status"),
  settingsCheck: document.getElementById("settings-check"),
  clearHistory: document.getElementById("clear-history")
};

const cameraContexts = {
  operation: {
    previewId: "camera-preview",
    emptyId: "camera-empty",
    idleText: "等待扫描。打开摄像头或在下方粘贴 JSON。",
    onDetect(rawValue) {
      const scanRaw = document.getElementById("scan-raw");
      if (scanRaw) {
        scanRaw.value = rawValue;
        updateOperationPreview();
      }

      if (document.getElementById("auto-submit-scan")?.checked) {
        return submitOperation();
      }

      setMessage(elements.operationMessage, "扫描已捕获。提交前请检查数据。", false, true);
      return Promise.resolve();
    }
  },
  search: {
    previewId: "search-camera-preview",
    emptyId: "search-camera-empty",
    idleText: "打开摄像头扫描 SKU，将自动加载产品。",
    async onDetect(rawValue) {
      elements.searchInput.value = rawValue;
      closeSearchScanModal();
      await loadProductDetail(rawValue);
      setMessage(elements.searchMessage, `已扫描并加载 ${rawValue}`, false, true);
    }
  }
};

function loadLogs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.logs);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function loadImagePromptSkips() {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.imagePromptSkips);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveLogs() {
  localStorage.setItem(STORAGE_KEYS.logs, JSON.stringify(state.logs.slice(0, 20)));
}

function saveImagePromptSkips() {
  localStorage.setItem(STORAGE_KEYS.imagePromptSkips, JSON.stringify(state.imagePromptSkips.slice(0, 50)));
}

function rememberSku(productId) {
  if (!productId) {
    return;
  }
  localStorage.setItem(STORAGE_KEYS.lastSku, productId);
}

function getRememberedSku() {
  return localStorage.getItem(STORAGE_KEYS.lastSku) || "";
}

function getAutoSubmitEnabled() {
  return localStorage.getItem(STORAGE_KEYS.autoSubmit) === "true";
}

function setAutoSubmitEnabled(value) {
  localStorage.setItem(STORAGE_KEYS.autoSubmit, String(Boolean(value)));
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof data === "object" && data && "detail" in data ? data.detail : "Request failed.";
    throw new Error(detail);
  }

  return data;
}

async function checkHealth() {
  try {
    await requestJson("/health");
    state.apiOnline = true;
  } catch {
    state.apiOnline = false;
  }

  const now = new Date().toLocaleTimeString();
  elements.homeStatusDot.className = `status-dot ${state.apiOnline ? "online" : "offline"}`;
  elements.homeStatusText.textContent = state.apiOnline ? "API 在线" : "离线";
  elements.homeStatusDetail.textContent = state.apiOnline
    ? `健康检查通过 ${now}`
    : `上次检查失败 ${now}`;

  elements.settingsStatus.innerHTML = `
    <div>
      <div class="status-row">
        <span class="status-dot ${state.apiOnline ? "online" : "offline"}"></span>
        <strong>${state.apiOnline ? "API 在线" : "离线"}</strong>
      </div>
      <p class="muted" style="margin-top:8px;">应用正在使用 FastAPI 后端，未使用前端模拟数据。</p>
    </div>
  `;
}

async function loadInventorySummary() {
  try {
    const items = await requestJson("/items");
    state.inventoryItems = items;
    const totalUnits = items.reduce((sum, item) => sum + item.quantity, 0);
    elements.statSkus.textContent = String(items.length);
    elements.statUnits.textContent = String(totalUnits);
  } catch (error) {
    elements.statSkus.textContent = "-";
    elements.statUnits.textContent = "-";
    setMessage(elements.searchMessage, error.message, true);
  }
}

function switchScreen(target) {
  state.activeScreen = target;

  for (const screen of elements.screens) {
    screen.classList.toggle("active", screen.dataset.screen === target);
  }
  for (const button of elements.navItems) {
    button.classList.toggle("active", button.dataset.target === target);
  }
}

function openSearchScanModal() {
  elements.searchScanModal.classList.remove("hidden");
  elements.searchScanModal.setAttribute("aria-hidden", "false");
}

function closeSearchScanModal() {
  stopCameraScan();
  elements.searchScanModal.classList.add("hidden");
  elements.searchScanModal.setAttribute("aria-hidden", "true");
}

function resetImagePromptSelection() {
  if (state.imagePromptPreviewUrl) {
    URL.revokeObjectURL(state.imagePromptPreviewUrl);
    state.imagePromptPreviewUrl = null;
  }
  elements.imagePromptFile.value = "";
  elements.imagePromptCamera.value = "";
  elements.imagePromptPreview.className = "image-preview empty-state";
  elements.imagePromptPreview.textContent = "选择图片或拍照。";
}

function renderImagePromptPreview(file) {
  if (state.imagePromptPreviewUrl) {
    URL.revokeObjectURL(state.imagePromptPreviewUrl);
    state.imagePromptPreviewUrl = null;
  }

  if (!file) {
    resetImagePromptSelection();
    return;
  }

  state.imagePromptPreviewUrl = URL.createObjectURL(file);
  elements.imagePromptPreview.className = "image-preview";
  elements.imagePromptPreview.innerHTML = `<img class="local-image-preview" src="${state.imagePromptPreviewUrl}" alt="Primary image preview">`;
}

function openImagePromptModal(productId) {
  state.pendingImagePromptSku = productId;
  elements.imagePromptDetail.textContent = `${productId} 尚未设置主图。如有图片请立即添加。`;
  resetImagePromptSelection();
  setMessage(elements.imagePromptMessage, "");
  elements.imagePromptModal.classList.remove("hidden");
  elements.imagePromptModal.setAttribute("aria-hidden", "false");
}

function closeImagePromptModal() {
  state.pendingImagePromptSku = "";
  resetImagePromptSelection();
  setMessage(elements.imagePromptMessage, "");
  elements.imagePromptModal.classList.add("hidden");
  elements.imagePromptModal.setAttribute("aria-hidden", "true");
}

function setMessage(element, text, isError = false, isSuccess = false) {
  element.textContent = text;
  element.className = "message";
  if (isError) {
    element.classList.add("error");
  }
  if (isSuccess) {
    element.classList.add("success");
  }
}

function pushLog(type, productId, quantity, success, source = "web") {
  state.logs.unshift({
    timestamp: new Date().toISOString(),
    type,
    product_id: productId,
    quantity,
    success,
    source
  });
  state.logs = state.logs.slice(0, 20);
  saveLogs();
  renderLogs();
}

function renderLogs() {
  const recent = state.logs.slice(0, 5);
  if (!recent.length) {
    elements.homeActivityList.className = "stack-list empty-state";
    elements.homeActivityList.textContent = "No recent actions yet.";
    return;
  }

  elements.homeActivityList.className = "stack-list";
  elements.homeActivityList.innerHTML = recent.map((item) => {
    const time = new Date(item.timestamp).toLocaleString();
    const status = item.success ? "Success" : "Failed";
    return `
      <article class="activity-item">
        <strong>${item.type} | ${item.product_id || "N/A"} x ${item.quantity || 0}</strong>
        <p class="muted small-text">${time} | ${status} | ${item.source}</p>
      </article>
    `;
  }).join("");
}

function renderSearchResult(product) {
  if (!product) {
    elements.searchResult.className = "empty-state";
    elements.searchResult.textContent = "尚未加载产品";
    return;
  }

  const primaryLabel = product.primary_image ? product.primary_image.filename : "无主图";
  const imageCount = Array.isArray(product.images) ? product.images.length : 0;
  elements.searchResult.className = "";
  elements.searchResult.innerHTML = `
    <article class="result-card">
      <div class="result-hero">
        <div class="image-placeholder">${imageCount > 0 ? "IMG" : "SKU"}</div>
        <div>
          <p class="section-label">当前产品</p>
          <h2>${product.product_id}</h2>
          <span class="pill">库存 ${product.quantity}</span>
        </div>
      </div>
      <div class="meta-list">
        <div><strong>主图：</strong> ${primaryLabel}</div>
        <div><strong>图片数量：</strong> ${imageCount}</div>
      </div>
      <div class="list-actions">
        <button type="button" class="secondary-button" data-jump="operation">调整库存</button>
        <button type="button" class="secondary-button" data-jump="images">管理图片</button>
      </div>
    </article>
  `;
}

function renderSearchList(items) {
  state.searchItems = items;
  if (!items.length) {
    elements.searchList.className = "stack-list empty-state";
    elements.searchList.textContent = "未找到匹配的产品";
    return;
  }

  elements.searchList.className = "stack-list";
  elements.searchList.innerHTML = items.map((item) => `
    <article class="activity-item">
      <strong>${item.product_id}</strong>
      <p class="muted small-text">库存 ${item.quantity}</p>
      <div class="list-actions">
        <button type="button" class="secondary-button" data-search-product="${item.product_id}">打开</button>
      </div>
    </article>
  `).join("");
}

async function searchItems(query = "") {
  const params = new URLSearchParams();
  if (query.trim()) {
    params.set("query", query.trim());
  }

  const url = params.size ? `/items?${params.toString()}` : "/items";
  const items = await requestJson(url);
  renderSearchList(items);

  const normalizedQuery = query.trim().toUpperCase();
  if (!normalizedQuery) {
    renderSearchResult(null);
    setMessage(elements.searchMessage, `已加载 ${items.length} 个产品`, false, true);
    return items;
  }

  const exactMatch = items.find((item) => item.product_id === normalizedQuery);
  if (exactMatch) {
    await loadProductDetail(exactMatch.product_id, { silentMessage: true });
    setMessage(elements.searchMessage, `已加载 ${exactMatch.product_id}`, false, true);
  } else {
    renderSearchResult(null);
    setMessage(elements.searchMessage, `找到 ${items.length} 个匹配 ${normalizedQuery} 的结果`, false, true);
  }

  return items;
}

async function loadProductDetail(productId, opts = {}) {
  const normalized = String(productId || "").trim();
  if (!normalized) {
    throw new Error("产品 ID 不能为空");
  }

  const product = await requestJson(`/products/${encodeURIComponent(normalized)}`);
  state.currentProduct = product;
  rememberSku(normalized);
  renderSearchResult(product);
  if (!opts.silentMessage) {
    setMessage(elements.searchMessage, `已加载 ${normalized}`, false, true);
  }
  return product;
}

async function maybePromptForPrimaryImage(productId) {
  const normalized = String(productId || "").trim();
  if (!normalized || state.imagePromptSkips.includes(normalized)) {
    return;
  }

  try {
    const product = await requestJson(`/products/${encodeURIComponent(normalized)}`);
    if (!product.primary_image) {
      openImagePromptModal(normalized);
    }
  } catch {
    // 即使图片检查失败，也保持库存提交流畅
  }
}

function renderOperationForm() {
  const rememberedSku = getRememberedSku();
  const autoSubmitChecked = getAutoSubmitEnabled() ? "checked" : "";

  if (state.operationMode === "add" || state.operationMode === "remove") {
    const defaultActionLabel = state.operationMode === "add" ? "入库" : "出库";
    elements.operationForm.innerHTML = `
      <div class="form-row">
        <label class="field-label" for="operation-product-id">产品 ID</label>
        <input id="operation-product-id" type="text" value="${escapeHtml(rememberedSku)}" placeholder="输入产品 ID">
      </div>
      <div class="form-row">
        <label class="field-label" for="operation-quantity">数量</label>
        <div class="quantity-stepper">
          <button type="button" data-quantity-step="-1">-</button>
          <input id="operation-quantity" type="number" min="1" value="1" inputmode="numeric">
          <button type="button" data-quantity-step="1">+</button>
        </div>
      </div>
      <div class="preview-card">
        <strong>${defaultActionLabel}</strong>
        <p class="muted small-text" style="margin-top:8px;">使用此模式直接通过后端接口修改库存</p>
      </div>
    `;
  } else if (state.operationMode === "scan") {
    elements.operationForm.innerHTML = `
      <div class="camera-shell">
        <video id="camera-preview" autoplay playsinline muted hidden></video>
        <div id="camera-empty">等待扫描。打开摄像头或在下方粘贴 JSON</div>
      </div>
      <div class="camera-actions">
        <button type="button" class="secondary-button" id="start-camera">打开摄像头</button>
        <button type="button" class="secondary-button" id="stop-camera">停止摄像头</button>
      </div>
      <div class="form-row">
        <label class="field-label" for="scan-raw">扫描 JSON</label>
        <textarea id="scan-raw" placeholder='{"action":"add","product_id":"SKU-001","quantity":1}'></textarea>
      </div>
      <label class="field-label" style="display:flex;align-items:center;gap:8px;">
        <input id="auto-submit-scan" type="checkbox" style="width:auto;" ${autoSubmitChecked}>
        自动提交有效的扫描结果
      </label>
    `;
  } else {
    elements.operationForm.innerHTML = `
      <div class="form-row">
        <label class="field-label" for="batch-input">批量输入</label>
        <textarea id="batch-input" placeholder='[{"action":"add","product_id":"SKU-100","quantity":2}]'></textarea>
      </div>
      <div class="preview-card">
        <strong>支持的格式</strong>
        <p class="muted small-text" style="margin-top:8px;">粘贴 JSON 数组，或每行一个 JSON 对象。每项将发送到 /scan 接口</p>
      </div>
    `;
  }

  updateOperationPreview();
}

function getOperationPayload() {
  if (state.operationMode === "add" || state.operationMode === "remove") {
    const productId = document.getElementById("operation-product-id")?.value.trim() || "";
    const quantity = Number(document.getElementById("operation-quantity")?.value || 1);
    return {
      action: state.operationMode,
      product_id: productId,
      quantity
    };
  }

  if (state.operationMode === "scan") {
    const raw = document.getElementById("scan-raw")?.value.trim() || "";
    try {
      const parsed = JSON.parse(raw);
      return {
        action: parsed.action,
        product_id: parsed.product_id,
        quantity: parsed.quantity,
        source: parsed.source || "mobile-web-scan",
        raw_code: raw
      };
    } catch {
      return {
        raw_code: raw,
        invalid: true
      };
    }
  }

  const batchRaw = document.getElementById("batch-input")?.value.trim() || "";
  return { batch_raw: batchRaw };
}

function updateOperationPreview() {
  const payload = getOperationPayload();
  elements.operationPreview.innerHTML = `<code>${escapeHtml(JSON.stringify(payload, null, 2))}</code>`;
}

function parseBatchInput(raw) {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error("批量输入不能为空");
  }

  try {
    const parsed = JSON.parse(trimmed);
    if (!Array.isArray(parsed)) {
      throw new Error("批量 JSON 必须是数组");
    }
    return parsed;
  } catch (arrayError) {
    const lines = trimmed.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (!lines.length) {
      throw new Error("批量输入为空");
    }
    return lines.map((line) => JSON.parse(line));
  }
}

function renderBatchResults() {
  if (!state.batchResults.length) {
    elements.batchResults.className = "stack-list empty-state";
    elements.batchResults.textContent = "批量操作结果将显示在这里";
    return;
  }

  elements.batchResults.className = "stack-list";
  elements.batchResults.innerHTML = state.batchResults.map((item) => `
    <article class="batch-item">
      <strong>${item.ok ? "成功" : "失败"} | 第 ${item.line} 行</strong>
      <p class="muted small-text">${escapeHtml(item.summary)}</p>
    </article>
  `).join("");
}

async function submitOperation() {
  const payload = getOperationPayload();

  if (state.operationMode === "add" || state.operationMode === "remove") {
    if (!payload.product_id || !payload.quantity || payload.quantity < 1) {
      throw new Error("产品 ID 和正数数量不能为空");
    }

    await requestJson(`/items/${state.operationMode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    pushLog(state.operationMode === "add" ? "入库" : "出库", payload.product_id, payload.quantity, true);
    rememberSku(payload.product_id);
    await loadInventorySummary();
    try {
      await loadProductDetail(payload.product_id, { silentMessage: true });
    } catch {
      state.currentProduct = null;
    }
    setMessage(elements.operationMessage, "操作成功完成", false, true);
    if (state.operationMode === "add") {
      await maybePromptForPrimaryImage(payload.product_id);
    }
    return;
  }

  if (state.operationMode === "scan") {
    if (payload.invalid) {
      throw new Error("扫描 JSON 格式无效");
    }
    await requestJson("/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    pushLog("扫码", payload.product_id, payload.quantity, true, payload.source || "scan");
    rememberSku(payload.product_id);
    await loadInventorySummary();
    setMessage(elements.operationMessage, "扫描提交成功", false, true);
    return;
  }

  const items = parseBatchInput(payload.batch_raw || "");
  const results = [];

  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    try {
      await requestJson("/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: item.action,
          product_id: item.product_id,
          quantity: item.quantity,
          source: item.source || "batch-web",
          raw_code: JSON.stringify(item)
        })
      });

      results.push({
        line: index + 1,
        ok: true,
        summary: `${item.action === 'add' ? '入库' : '出库'} ${item.product_id} x ${item.quantity}`
      });
      pushLog("批量", item.product_id, item.quantity, true, "batch");
    } catch (error) {
      results.push({
        line: index + 1,
        ok: false,
        summary: error.message || "批量请求失败"
      });
    }
  }

  state.batchResults = results;
  renderBatchResults();
  await loadInventorySummary();
  setMessage(
    elements.operationMessage,
    `批量完成。${results.filter((item) => item.ok).length}/${results.length} 成功`,
    false,
    true
  );
}

function renderImagePreview() {
  if (!state.imagePreviewUrl) {
    elements.imagePreview.className = "image-preview empty-state";
    elements.imagePreview.textContent = "选择图片预览后再上传";
    return;
  }

  elements.imagePreview.className = "image-preview";
  elements.imagePreview.innerHTML = `<img class="local-image-preview" src="${state.imagePreviewUrl}" alt="Selected preview">`;
}

function renderImageList(images) {
  if (!images.length) {
    elements.imageList.className = "stack-list empty-state";
    elements.imageList.textContent = "该产品暂无图片";
    return;
  }

  elements.imageList.className = "stack-list";
  elements.imageList.innerHTML = images.map((image) => `
    <article class="image-card">
      <strong>${escapeHtml(image.filename)}</strong>
      <p class="muted small-text">${escapeHtml(image.relative_path)}</p>
      <p class="muted small-text">${image.size_bytes} 字节${image.is_primary ? " | 主图" : ""}</p>
      <div class="list-actions">
        <button type="button" class="secondary-button" data-image-action="primary" data-image-id="${image.id}" ${image.is_primary ? "disabled" : ""}>
          ${image.is_primary ? "主图" : "设为主图"}
        </button>
        <button type="button" class="danger-button" data-image-action="delete" data-image-id="${image.id}">删除</button>
      </div>
    </article>
  `).join("");
}

async function loadImagesForProduct(productId) {
  const normalized = String(productId || "").trim();
  if (!normalized) {
    throw new Error("产品 ID 不能为空");
  }

  const images = await requestJson(`/images/${encodeURIComponent(normalized)}`);
  state.currentImages = images;
  rememberSku(normalized);
  renderImageList(images);
  setMessage(elements.imageMessage, `已加载 ${images.length} 张图片`, false, true);
}

async function uploadImage() {
  const productId = elements.imageProductId.value.trim();
  const file = elements.imageFile.files[0];
  if (!productId) {
    throw new Error("产品 ID 不能为空");
  }
  if (!file) {
    throw new Error("请先选择图片");
  }

  const formData = new FormData();
  formData.append("product_id", productId);
  formData.append("image", file);

  await requestJson("/images", {
    method: "POST",
    body: formData
  });

  pushLog("图片", productId, 1, true, "upload");
  elements.imageFile.value = "";
  if (state.imagePreviewUrl) {
    URL.revokeObjectURL(state.imagePreviewUrl);
    state.imagePreviewUrl = null;
  }
  renderImagePreview();
  await loadImagesForProduct(productId);
}

async function uploadPromptImage() {
  const productId = state.pendingImagePromptSku;
  const file = elements.imagePromptFile.files[0] || elements.imagePromptCamera.files[0];
  if (!productId) {
    throw new Error("没有待上传图片的产品");
  }
  if (!file) {
    throw new Error("请先选择图片或拍照");
  }

  const formData = new FormData();
  formData.append("product_id", productId);
  formData.append("image", file);

  await requestJson("/images", {
    method: "POST",
    body: formData
  });

  pushLog("图片", productId, 1, true, "post-stock-prompt");
  state.imagePromptSkips = state.imagePromptSkips.filter((sku) => sku !== productId);
  saveImagePromptSkips();
  elements.imageProductId.value = productId;
  await loadImagesForProduct(productId);
  closeImagePromptModal();
}

async function setPrimaryImage(imageId) {
  const productId = elements.imageProductId.value.trim();
  await requestJson(`/images/${encodeURIComponent(productId)}/primary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_id: imageId })
  });
  await loadImagesForProduct(productId);
}

async function deleteImage(imageId) {
  const productId = elements.imageProductId.value.trim();
  await requestJson(`/images/${encodeURIComponent(productId)}/${imageId}`, {
    method: "DELETE"
  });
  await loadImagesForProduct(productId);
}

async function startCameraScan(contextName = "operation") {
  const context = cameraContexts[contextName];
  if (!context) {
    throw new Error("未知的摄像头上下文");
  }

  const preview = document.getElementById(context.previewId);
  const empty = document.getElementById(context.emptyId);

  if (!preview || !empty) {
    return;
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error("此浏览器不支持摄像头访问");
  }

  if (!("BarcodeDetector" in window)) {
    throw new Error("此设备不支持 BarcodeDetector");
  }

  stopCameraScan();
  state.activeCameraContext = contextName;
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: "environment" } },
    audio: false
  });

  state.cameraStream = stream;
  preview.srcObject = stream;
  preview.hidden = false;
  empty.hidden = true;
  await preview.play();

  const detector = new BarcodeDetector({
    formats: ["qr_code", "code_128", "ean_13", "ean_8", "upc_a", "upc_e"]
  });

  state.cameraTimerId = window.setInterval(async () => {
    if (!state.cameraStream) {
      return;
    }

    const codes = await detector.detect(preview);
    if (!codes.length) {
      return;
    }

    const rawValue = String(codes[0].rawValue || "").trim();
    if (!rawValue || rawValue === state.lastScanText) {
      return;
    }

    state.lastScanText = rawValue;
    await context.onDetect(rawValue);
  }, 700);
}

function stopCameraScan() {
  if (state.cameraTimerId) {
    window.clearInterval(state.cameraTimerId);
    state.cameraTimerId = null;
  }

  if (state.cameraStream) {
    state.cameraStream.getTracks().forEach((track) => track.stop());
    state.cameraStream = null;
  }

  const context = cameraContexts[state.activeCameraContext] || cameraContexts.operation;
  state.activeCameraContext = null;
  const preview = document.getElementById(context.previewId);
  const empty = document.getElementById(context.emptyId);
  if (preview) {
    preview.srcObject = null;
    preview.hidden = true;
  }
  if (empty) {
    empty.hidden = false;
    empty.textContent = context.idleText;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function bindEvents() {
  elements.refreshStatus.addEventListener("click", async () => {
    await checkHealth();
    await loadInventorySummary();
  });

  elements.homeOpenSearch.addEventListener("click", async () => {
    switchScreen("search");
    elements.searchInput.value = "";
    try {
      await searchItems("");
    } catch (error) {
      setMessage(elements.searchMessage, error.message, true);
    }
  });

  for (const button of elements.navItems) {
    button.addEventListener("click", () => {
      switchScreen(button.dataset.target);
    });
  }

  for (const button of elements.shortcutButtons) {
    button.addEventListener("click", () => {
      const shortcut = button.dataset.shortcut;
      if (shortcut === "search") {
        switchScreen("search");
      } else if (shortcut === "add" || shortcut === "remove" || shortcut === "scan" || shortcut === "batch") {
        switchScreen("operation");
        state.operationMode = shortcut;
        syncModeButtons();
        renderOperationForm();
      }
    });
  }

  elements.searchLoad.addEventListener("click", async () => {
    try {
      await searchItems(elements.searchInput.value);
    } catch (error) {
      renderSearchList([]);
      renderSearchResult(null);
      setMessage(elements.searchMessage, error.message, true);
    }
  });

  elements.searchScan.addEventListener("click", () => {
    openSearchScanModal();
    setMessage(elements.searchMessage, "打开摄像头扫描 SKU，将自动加载产品");
  });

  elements.searchScanStart.addEventListener("click", async () => {
    try {
      await startCameraScan("search");
    } catch (error) {
      setMessage(elements.searchMessage, error.message, true);
    }
  });

  elements.searchScanClose.addEventListener("click", () => {
    closeSearchScanModal();
  });

  elements.searchList.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-search-product]");
    if (!button) {
      return;
    }

    const productId = button.dataset.searchProduct;
    elements.searchInput.value = productId;
    try {
      await loadProductDetail(productId);
    } catch (error) {
      renderSearchResult(null);
      setMessage(elements.searchMessage, error.message, true);
    }
  });

  for (const button of elements.modeButtons) {
    button.addEventListener("click", () => {
      state.operationMode = button.dataset.mode;
      syncModeButtons();
      renderOperationForm();
      setMessage(elements.operationMessage, "");
    });
  }

  elements.operationForm.addEventListener("input", (event) => {
    if (event.target.id === "auto-submit-scan") {
      setAutoSubmitEnabled(event.target.checked);
    }
    updateOperationPreview();
  });

  elements.operationForm.addEventListener("click", async (event) => {
    const quantityButton = event.target.closest("[data-quantity-step]");
    if (quantityButton) {
      const quantityInput = document.getElementById("operation-quantity");
      const current = Number(quantityInput.value || 1);
      const nextValue = Math.max(1, current + Number(quantityButton.dataset.quantityStep));
      quantityInput.value = String(nextValue);
      updateOperationPreview();
      return;
    }

    if (event.target.id === "start-camera") {
      try {
        await startCameraScan("operation");
      } catch (error) {
        setMessage(elements.operationMessage, error.message, true);
      }
      return;
    }

    if (event.target.id === "stop-camera") {
      stopCameraScan();
      setMessage(elements.operationMessage, "摄像头已停止", false, true);
    }
  });

  elements.operationSubmit.addEventListener("click", async () => {
    try {
      setMessage(elements.operationMessage, "正在提交...");
      await submitOperation();
    } catch (error) {
      setMessage(elements.operationMessage, error.message, true);
    }
  });

  elements.searchResult.addEventListener("click", (event) => {
    const button = event.target.closest("[data-jump]");
    if (!button || !state.currentProduct) {
      return;
    }

    if (button.dataset.jump === "operation") {
      switchScreen("operation");
      state.operationMode = "add";
      syncModeButtons();
      renderOperationForm();
      const input = document.getElementById("operation-product-id");
      if (input) {
        input.value = state.currentProduct.product_id;
        updateOperationPreview();
      }
      return;
    }

    switchScreen("images");
    elements.imageProductId.value = state.currentProduct.product_id;
    loadImagesForProduct(state.currentProduct.product_id).catch((error) => {
      setMessage(elements.imageMessage, error.message, true);
    });
  });

  elements.imageLoad.addEventListener("click", async () => {
    try {
      await loadImagesForProduct(elements.imageProductId.value);
    } catch (error) {
      setMessage(elements.imageMessage, error.message, true);
    }
  });

  elements.imageFile.addEventListener("change", () => {
    if (state.imagePreviewUrl) {
      URL.revokeObjectURL(state.imagePreviewUrl);
      state.imagePreviewUrl = null;
    }
    const file = elements.imageFile.files[0];
    if (file) {
      state.imagePreviewUrl = URL.createObjectURL(file);
    }
    renderImagePreview();
  });

  elements.imagePromptChoose.addEventListener("click", () => {
    elements.imagePromptFile.click();
  });

  elements.imagePromptCapture.addEventListener("click", () => {
    elements.imagePromptCamera.click();
  });

  elements.imagePromptFile.addEventListener("change", () => {
    elements.imagePromptCamera.value = "";
    renderImagePromptPreview(elements.imagePromptFile.files[0]);
  });

  elements.imagePromptCamera.addEventListener("change", () => {
    elements.imagePromptFile.value = "";
    renderImagePromptPreview(elements.imagePromptCamera.files[0]);
  });

  elements.imagePromptUpload.addEventListener("click", async () => {
    try {
      setMessage(elements.imagePromptMessage, "Uploading...");
      await uploadPromptImage();
      setMessage(elements.imageMessage, "Primary image uploaded.", false, true);
    } catch (error) {
      setMessage(elements.imagePromptMessage, error.message, true);
    }
  });

  elements.imagePromptSkip.addEventListener("click", () => {
    const productId = state.pendingImagePromptSku;
    if (productId && !state.imagePromptSkips.includes(productId)) {
      state.imagePromptSkips.unshift(productId);
      saveImagePromptSkips();
    }
    closeImagePromptModal();
  });

  elements.imageUpload.addEventListener("click", async () => {
    try {
      setMessage(elements.imageMessage, "正在上传...");
      await uploadImage();
      setMessage(elements.imageMessage, "图片上传成功", false, true);
    } catch (error) {
      setMessage(elements.imageMessage, error.message, true);
    }
  });

  elements.imageList.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-image-action]");
    if (!button) {
      return;
    }

    const imageId = Number(button.dataset.imageId);
    try {
      if (button.dataset.imageAction === "primary") {
        await setPrimaryImage(imageId);
        setMessage(elements.imageMessage, "主图已更新", false, true);
      } else {
        await deleteImage(imageId);
        setMessage(elements.imageMessage, "图片已删除", false, true);
      }
    } catch (error) {
      setMessage(elements.imageMessage, error.message, true);
    }
  });

  elements.settingsCheck.addEventListener("click", async () => {
    await checkHealth();
  });

  elements.clearHistory.addEventListener("click", () => {
    stopCameraScan();
    localStorage.removeItem(STORAGE_KEYS.logs);
    localStorage.removeItem(STORAGE_KEYS.lastSku);
    localStorage.removeItem(STORAGE_KEYS.autoSubmit);
    localStorage.removeItem(STORAGE_KEYS.imagePromptSkips);
    state.logs = [];
    state.imagePromptSkips = [];
    renderLogs();
  });
}

function syncModeButtons() {
  for (const button of elements.modeButtons) {
    button.classList.toggle("active", button.dataset.mode === state.operationMode);
  }
}

async function bootstrap() {
  bindEvents();
  renderLogs();
  renderSearchList([]);
  renderSearchResult(null);
  renderOperationForm();
  renderBatchResults();
  renderImagePreview();
  elements.searchInput.value = getRememberedSku();
  elements.imageProductId.value = getRememberedSku();
  await checkHealth();
  await loadInventorySummary();
}

bootstrap().catch((error) => {
  console.error(error);
});
