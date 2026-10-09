const $ = (id) => document.getElementById(id);
let current = null,
  view = "overview",
  offset = 0,
  totalMatching = 0,
  busy = false;
function message(text, error = false) {
  $("message").textContent = text;
  $("message").classList.toggle("error", error);
}
async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = response.statusText;
    }
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail),
    );
  }
  return response.json();
}
function cell(row, value, className = "") {
  const td = document.createElement("td");
  td.textContent = value;
  if (className) td.className = className;
  row.append(td);
  return td;
}
function categories(target, counts, fraction = false) {
  const element = $(target);
  element.replaceChildren();
  const max = Math.max(...Object.values(counts), 1);
  for (const [name, value] of Object.entries(counts)) {
    const row = document.createElement("div");
    row.className = "category";
    const label = document.createElement("span");
    label.textContent = name;
    const track = document.createElement("div");
    track.className = "category-track";
    const fill = document.createElement("div");
    fill.className = "category-fill";
    fill.style.width = `${(100 * value) / (fraction ? 1 : max)}%`;
    track.append(fill);
    const number = document.createElement("span");
    number.textContent = fraction ? `${(value * 100).toFixed(1)}%` : value;
    row.append(label, track, number);
    element.append(row);
  }
  if (!Object.keys(counts).length) element.textContent = "No flagged flows.";
}
function summary(batch) {
  current = batch.id;
  const s = batch.summary;
  $("total").textContent = s.total_flows.toLocaleString();
  $("flagged").textContent = s.flagged_flows.toLocaleString();
  $("normal").textContent = s.normal_flows.toLocaleString();
  $("rate").textContent = `${(s.flag_rate * 100).toFixed(1)}% flagged`;
  $("version").textContent = s.model_version;
  $("threshold").textContent = `Flag threshold: ${s.threshold.toFixed(4)}`;
  $("batch-description").textContent =
    `${batch.source} · ${new Date(batch.created_at).toLocaleString()}`;
  $("export").hidden = false;
  $("export").href = `/api/batches/${current}/export`;
  const chart = $("timeline");
  chart.replaceChildren();
  const max = Math.max(...s.timeline.map((x) => x.flows), 1);
  for (const point of s.timeline) {
    const group = document.createElement("div");
    group.className = "bar-group";
    group.title = `Rows from ${point.start_row}: ${point.flows} flows, ${point.flagged} flagged`;
    for (const [value, kind] of [
      [point.flows, "bar"],
      [point.flagged, "bar alert"],
    ]) {
      const bar = document.createElement("div");
      bar.className = kind;
      bar.style.height = `${(100 * value) / max}%`;
      group.append(bar);
    }
    chart.append(group);
  }
  categories("categories", s.category_counts);
}
async function renderRows() {
  if (!current) return;
  const data = await request(
    `/api/batches/${current}?offset=${offset}&limit=50&flagged_only=${view === "alerts"}`,
  );
  totalMatching = data.matching_flows;
  const body = $("rows");
  body.replaceChildren();
  for (const result of data.results) {
    const tr = document.createElement("tr");
    cell(tr, result.row_number);
    cell(tr, result.protocol);
    cell(tr, result.service);
    cell(tr, result.category_suggestion);
    cell(tr, result.attack_score.toFixed(4), result.flagged ? "red" : "");
    const td = document.createElement("td"),
      pill = document.createElement("span");
    pill.className = "pill" + (result.flagged ? " attack" : "");
    pill.textContent = result.flagged ? "Flagged" : "Unflagged";
    td.append(pill);
    tr.append(td);
    cell(
      tr,
      result.actual_label === undefined
        ? "—"
        : result.actual_label
          ? "Attack"
          : "Normal",
    );
    const explainCell = document.createElement("td");
    const explainButton = document.createElement("button");
    explainButton.textContent = "Explain";
    explainButton.setAttribute(
      "aria-label",
      `Explain flow ${result.row_number}`,
    );
    explainButton.onclick = () =>
      guard(() => showExplanation(result.row_number));
    explainCell.append(explainButton);
    tr.append(explainCell);
    body.append(tr);
  }
  if (!data.results.length) {
    const tr = document.createElement("tr");
    cell(tr, "No matching flows.").colSpan = 8;
    body.append(tr);
  }
  $("page-info").textContent = totalMatching
    ? `${offset + 1}–${Math.min(offset + 50, totalMatching)} of ${totalMatching}`
    : "0 flows";
  $("previous").disabled = offset === 0;
  $("next").disabled = offset + 50 >= totalMatching;
}
async function history() {
  const items = await request("/api/batches");
  $("history").replaceChildren();
  for (const batch of items) {
    const button = document.createElement("button");
    button.textContent = `${new Date(batch.created_at).toLocaleString()} · ${batch.summary.total_flows} flows`;
    button.onclick = () =>
      guard(async () => {
        summary(batch);
        offset = 0;
        await renderRows();
        message("Saved batch loaded.");
      });
    $("history").append(button);
  }
  return items;
}
async function guard(action) {
  if (busy) return;
  busy = true;
  $("replay").disabled = true;
  $("upload").disabled = true;
  try {
    await action();
  } catch (error) {
    message(error.message, true);
  } finally {
    busy = false;
    $("replay").disabled = false;
    $("upload").disabled = false;
  }
}
$("replay").onclick = () =>
  guard(async () => {
    message("Scoring held-out benchmark flows…");
    const batch = await request("/api/replay", { method: "POST" });
    summary(batch);
    offset = 0;
    await renderRows();
    await history();
    message(
      "Held-out sample scored. Flags are model predictions; actual labels are shown for comparison.",
    );
  });
$("upload").onchange = () => {
  const file = $("upload").files[0];
  if (!file) return;
  guard(async () => {
    if (file.size > 10 * 1024 * 1024)
      throw new Error(
        "CSV exceeds 10 MiB. Use the prediction CLI for larger files.",
      );
    const form = new FormData();
    form.append("file", file);
    message("Validating and scoring uploaded flows…");
    const batch = await request("/api/upload", { method: "POST", body: form });
    summary(batch);
    offset = 0;
    await renderRows();
    await history();
    message(
      `Scored ${batch.summary.total_flows} flows; flagged ${batch.summary.flagged_flows}.`,
    );
  }).finally(() => {
    $("upload").value = "";
  });
};
for (const button of document.querySelectorAll("nav button"))
  button.onclick = () =>
    guard(async () => {
      view = button.dataset.view;
      offset = 0;
      for (const b of document.querySelectorAll("nav button"))
        b.classList.toggle("selected", b === button);
      $("page-title").textContent = {
        overview: "Network overview",
        flows: "Network flows",
        alerts: "Flagged flows",
        model: "Model performance",
        dataset: "Dataset quality",
      }[view];
      $("overview").hidden = view !== "overview";
      $("model").hidden = view !== "model";
      $("table-panel").hidden = ["model", "dataset"].includes(view);
      $("dataset").hidden = view !== "dataset";
      $("explanation-panel").hidden = true;
      $("table-title").textContent =
        view === "alerts" ? "Flagged flow predictions" : "Flow predictions";
      if (!["model", "dataset"].includes(view)) await renderRows();
      window.scrollTo({ top: 0, behavior: "auto" });
      if (view === "dataset")
        message(
          "Dataset audit loaded. Measurements use the pinned training/test CSVs.",
        );
      else if (view === "model")
        message(
          "Held-out evaluation loaded. Models and threshold were frozen before testing.",
        );
    });
$("previous").onclick = () =>
  guard(async () => {
    offset = Math.max(0, offset - 50);
    await renderRows();
  });
$("next").onclick = () =>
  guard(async () => {
    offset += 50;
    await renderRows();
  });
async function initialize() {
  const [meta, report, quality] = await Promise.all([
    request("/api/model-info"),
    request("/api/metrics"),
    request("/api/dataset-quality"),
  ]);
  renderDatasetQuality(quality);
  $("version").textContent = meta.model_version;
  $("threshold").textContent = `Flag threshold: ${meta.threshold.toFixed(4)}`;
  for (const [name, key] of [
    ["Attack precision", "precision"],
    ["Attack recall", "recall"],
    ["F1 score", "f1"],
    ["False-positive rate", "false_positive_rate"],
    ["PR-AUC (AP)", "pr_auc_average_precision"],
    ["Accuracy", "accuracy"],
  ]) {
    const card = document.createElement("div");
    card.className = "metric";
    const label = document.createElement("small");
    label.textContent = name;
    const score = document.createElement("strong");
    score.textContent = `${(100 * report.test[key]).toFixed(2)}%`;
    card.append(label, score);
    $("metrics").append(card);
  }
  $("category-quality").textContent =
    `Multiclass accuracy ${(100 * report.category_classification.accuracy).toFixed(2)}%; macro-F1 ${(100 * report.category_classification["macro avg"]["f1-score"]).toFixed(2)}%. Some rare categories are poorly distinguished. Category suggestions are experimental; binary flag decisions are evaluated separately.`;
  const table = document.createElement("table");
  table.className = "matrix";
  for (const row of [
    ["Actual / Predicted", "Normal", "Attack"],
    ["Normal", ...report.test.confusion_matrix[0]],
    ["Attack", ...report.test.confusion_matrix[1]],
  ]) {
    const tr = document.createElement("tr");
    for (const v of row) cell(tr, v);
    table.append(tr);
  }
  $("confusion").append(table);
  categories(
    "attack-recall",
    Object.fromEntries(
      Object.entries(report.per_attack_flag_rates)
        .filter(([k]) => k !== "Normal")
        .map(([k, v]) => [k, v.flag_rate]),
    ),
    true,
  );
  $("audit").textContent =
    `${report.test.rows.toLocaleString()} official test flows. ${report.audit.test_rows_matching_training_features.toLocaleString()} match training feature records; novel-flow F1: ${(100 * report.novel_test.f1).toFixed(2)}%.`;
  const items = await history();
  if (items.length) {
    summary(items[0]);
    await renderRows();
  }
  message(
    "Trained models ready. Replay sample traffic or upload compatible flow features.",
  );
  $("previous").disabled = true;
  $("next").disabled = !current || totalMatching <= 50;
}
guard(initialize);

/** Render a selected prediction's signed TreeSHAP contributions safely as text. */
async function showExplanation(rowNumber) {
  message("Computing feature contributions…");
  const explanation = await request(
    `/api/batches/${current}/flows/${rowNumber}/explain`,
  );
  $("explanation-title").textContent =
    `Why flow ${rowNumber} was ${explanation.flagged ? "flagged" : "unflagged"}`;
  const truth =
    explanation.actual_label === undefined
      ? ""
      : ` Supplied label: ${explanation.actual_label ? "Attack" : "Normal"}${explanation.flagged && !explanation.actual_label ? " — this flag is a false positive." : "."}`;
  $("explanation-summary").textContent =
    `Attack score ${explanation.attack_score.toFixed(4)} vs threshold ${explanation.threshold.toFixed(4)}.${truth}`;
  const container = $("explanation-features");
  container.replaceChildren();
  const max = Math.max(
    ...explanation.top_features.map((x) => Math.abs(x.contribution)),
    1e-10,
  );
  for (const feature of explanation.top_features) {
    const row = document.createElement("div");
    row.className = "shap-row";
    const label = document.createElement("span");
    label.textContent = `${feature.feature} = ${feature.value}`;
    const track = document.createElement("div");
    track.className = "category-track";
    const bar = document.createElement("div");
    bar.className = `shap-bar ${feature.contribution >= 0 ? "positive" : "negative"}`;
    bar.style.width = `${(100 * Math.abs(feature.contribution)) / max}%`;
    track.append(bar);
    const value = document.createElement("span");
    value.textContent = `${feature.contribution >= 0 ? "+" : ""}${feature.contribution.toFixed(3)} (${feature.direction})`;
    row.append(label, track, value);
    container.append(row);
  }
  const sum = explanation.top_features.reduce(
    (value, feature) => value + feature.contribution,
    0,
  );
  $("explanation-reconstruction").textContent =
    `Base ${explanation.base_log_odds.toFixed(4)} + displayed contributions ${sum.toFixed(4)} + remaining features ${explanation.other_contribution.toFixed(4)} = raw score ${explanation.raw_log_odds.toFixed(4)}. Sigmoid(raw score) gives the attack score. Model ${explanation.model_version}.`;
  $("explanation-panel").hidden = false;
  $("explanation-panel").scrollIntoView({ behavior: "auto", block: "start" });
  message(
    "Explanation ready. Feature contributions describe this model’s decision.",
  );
}

/** Dataset measurements come from the pinned CSV audit, not illustrative data. */
function renderDatasetQuality(quality) {
  const training = quality.splits.training,
    testing = quality.splits.testing;
  for (const [label, value] of [
    ["Training flows", training.rows.toLocaleString()],
    ["Test flows", testing.rows.toLocaleString()],
    ["Input features", quality.input_features],
    [
      "Missing feature values",
      training.feature_missing_values + testing.feature_missing_values,
    ],
    [
      "Duplicate training rows",
      `${(100 * training.duplicate_fraction).toFixed(2)}%`,
    ],
    [
      "Test rows matching training",
      `${quality.test_rows_matching_training.toLocaleString()} (${(100 * quality.test_match_fraction).toFixed(2)}%)`,
    ],
  ]) {
    const card = document.createElement("div");
    card.className = "metric";
    const title = document.createElement("small");
    title.textContent = label;
    const number = document.createElement("strong");
    number.textContent = value;
    card.append(title, number);
    $("dataset-metrics").append(card);
  }
  const table = document.createElement("table");
  const header = document.createElement("tr");
  for (const value of ["True category", "Training rows", "Test rows"])
    cell(header, value);
  table.append(header);
  for (const [category, count] of Object.entries(training.class_counts)) {
    const row = document.createElement("tr");
    cell(row, category);
    cell(row, count.toLocaleString());
    cell(row, testing.class_counts[category].toLocaleString());
    table.append(row);
  }
  $("dataset-classes").append(table);
  $("dataset-summary").textContent =
    `There are ${training.conflicting_binary_label_groups} training feature groups with conflicting binary labels, affecting ${training.rows_in_conflicting_binary_groups.toLocaleString()} rows. Attack prevalence changes from ${(100 * training.attack_fraction).toFixed(2)}% in training to ${(100 * testing.attack_fraction).toFixed(2)}% in testing. The benchmark is useful for research; operational quality needs fresh network-specific evaluation.`;
}
