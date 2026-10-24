<script setup lang="ts">
import { t, labelFor, formatDate, slotLabel } from "../i18n";
import {
  NAlert,
  NButton,
  NCard,
  NEmpty,
  NFlex,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NInput,
  NInputNumber,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NTag,
  useMessage,
} from "naive-ui";
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

import {
  getStageFileContract,
  getStageRun,
  listStageRuns,
  stageFileResultUrl,
  submitStageFileRun,
  submitStageRun,
  type JobState,
  type StageFileContract,
  type StageRunPayload,
} from "../api/client";
import FastModeSwitch from "../components/FastModeSwitch.vue";
import JobStatusCard from "../components/JobStatusCard.vue";
import ProfileSelector from "../components/ProfileSelector.vue";
import AsrCandidateSelector from "../components/AsrCandidateSelector.vue";
import AsrLanguageSelector from "../components/AsrLanguageSelector.vue";
import type { AsrLanguage } from "../api/client";
import { isAsrLanguage, incompatibleCandidates } from "../composables/asrLanguage";
import StageFileUpload from "../components/StageFileUpload.vue";
import { useConfigOptions } from "../composables/useConfigOptions";

const message = useMessage();
const {
  asrCandidates,
  asrLanguages,
  defaultAsrLanguage,
  defaultAsrCandidate,
  defaultSecondaryAsrCandidate,
  defaultFastMode,
  defaultOcrFastMode,
  error: configError,
  loading: configLoading,
  profiles,
  defaultOcrMaxConcurrency,
  defaultOcrModel,
  defaultOcrReasoningEffort,
  defaultOcrSubmitIntervalSeconds,
} = useConfigOptions();
const stageState = ref<JobState | null>(null);
const submitting = ref(false);
const historyLoading = ref(false);
const historyError = ref("");
const stageRuns = ref<JobState[]>([]);
const pollHandle = ref<number | null>(null);
const runMode = ref<"file" | "directory">("file");
const fileContractLoading = ref(false);
const fileContract = ref<StageFileContract | null>(null);
const fileInputPaths = reactive<Record<string, string>>({});
const fileResultName = ref("");

const form = reactive({
  stage: "extract-audio",
  profile: "",
  asr_candidate: "",
  asr_language: null as AsrLanguage | null,
  secondary_asr_candidate: "",
  fast_mode: null as boolean | null,
  ocr_fast_mode: null as boolean | null,
  model: "",
  reasoning_effort: "",
  ocr_model: "",
  ocr_reasoning_effort: "",
  ocr_max_concurrency: 40 as number | null,
  ocr_submit_interval_seconds: 5 as number | null,
});

interface StageGuide {
  label: string;
  value: string;
  description: string;
  input: string;
  output: string;
  testHint: string;
}

const stageGuides = computed<StageGuide[]>(() => ([
  {
    label: t('音频提取 (extract-audio)'),
    value: "extract-audio",
    description: t('从当前视频目录提取统一格式的音频。'),
    input: "data/input/videos/",
    output: "data/input/audio/",
    testHint: t('适合检查视频扫描、ffmpeg 可用性与音频产物。'),
  },
  {
    label: t('语音转写 (transcribe)'),
    value: "transcribe",
    description: t('对当前音频目录执行 ASR 转录。'),
    input: "data/input/audio/",
    output: "data/intermediate/asr/",
    testHint: t('适合检查语音转写配置方案、模型与转录中间结果。'),
  },
  {
    label: t('准备参考 (prepare-reference)'),
    value: "prepare-reference",
    description: t('提取当前参考目录中的 TXT、Markdown 或 PDF 原文。'),
    input: "data/input/reference/",
    output: t('data/intermediate/extracted_text/ 与 data/intermediate/ocr/'),
    testHint: t('测试 PDF OCR 时，在这里覆盖模型、推理强度和快速模式。'),
  },
  {
    label: t('文本对齐 (align)'),
    value: "align",
    description: t('将 ASR 文本与参考原文做块级对齐。'),
    input: t('data/intermediate/asr/ 与 data/intermediate/extracted_text/'),
    output: "data/intermediate/aligned/",
    testHint: t('适合验证参考文本与转录是否可作为对齐输入。'),
  },
  {
    label: t('段落分类 (classify)'),
    value: "classify",
    description: t('对已对齐文本生成保守候选分类。'),
    input: "data/intermediate/aligned/",
    output: "data/intermediate/classified/",
    testHint: t('适合检查分类规则与中间 JSON。'),
  },
  {
    label: t('智能润色 (refine)'),
    value: "refine",
    description: t('基于 ASR 和参考原文执行阶段 6 精修。'),
    input: t('data/intermediate/asr/ 与 data/intermediate/extracted_text/'),
    output: "data/intermediate/refined/",
    testHint: t('测试 AI 精修时，在这里覆盖模型、推理强度和快速模式。'),
  },
  {
    label: t('导出文档 (export-markdown)'),
    value: "export-markdown",
    description: t('将精修结果导出为最终 Markdown 和文本文件。'),
    input: "data/intermediate/refined/",
    output: "data/final/",
    testHint: t('适合检查最终稿导出和文件命名。'),
  },
]));

const stageOptions = computed(() => stageGuides.value.map(({ label, value }) => ({ label, value })));
const currentStageGuide = computed(() => stageGuides.value.find((guide) => guide.value === form.stage) ?? stageGuides.value[0]);
const isFileMode = computed(() => runMode.value === "file");
const usesOcrOverrides = computed(() => form.stage === "prepare-reference");
const usesRefineOverrides = computed(() => form.stage === "refine");
const reasoningOptions = computed(() => ([
  { label: t('低'), value: "low" },
  { label: t('中'), value: "medium" },
  { label: t('高'), value: "high" },
  { label: t('很高'), value: "xhigh" },
  { label: t('最高'), value: "max" },
]));
const modelOptions = [
  { label: "GPT-6.1 Sol", value: "gpt-6.1-sol" },
  { label: "GPT-6 Luna", value: "gpt-6-luna" },
];

function stopPolling() {
  if (pollHandle.value !== null) {
    window.clearInterval(pollHandle.value);
    pollHandle.value = null;
  }
}

function isActiveStageRun(state: JobState): boolean {
  return state.status === "pending" || state.status === "running";
}

function stageRunStatusType(status: string): "success" | "error" | "warning" {
  if (status === "success") {
    return "success";
  }
  if (status === "failed") {
    return "error";
  }
  return "warning";
}

async function loadStageRuns() {
  historyLoading.value = true;
  historyError.value = "";
  try {
    stageRuns.value = (await listStageRuns()).items;
  } catch (caught) {
    historyError.value = caught instanceof Error ? caught.message : t('加载单阶段运行历史失败');
    message.error(caught instanceof Error ? caught.message : t('加载单阶段运行历史失败'));
  } finally {
    historyLoading.value = false;
  }
}

async function refreshStage(runId: string) {
  const state = await getStageRun(runId);
  stageState.value = state;
  if (state.status === "success" || state.status === "partial" || state.status === "failed") {
    stopPolling();
    void loadStageRuns();
  }
}

function startPolling(runId: string) {
  stopPolling();
  pollHandle.value = window.setInterval(() => {
    void refreshStage(runId).catch((caught) => {
      message.error(caught instanceof Error ? caught.message : t('刷新阶段任务状态失败'));
      stopPolling();
    });
  }, 2000);
}

async function loadStageRun(runId: string) {
  try {
    await refreshStage(runId);
    if (stageState.value && isActiveStageRun(stageState.value)) {
      startPolling(runId);
    }
  } catch (caught) {
    message.error(caught instanceof Error ? caught.message : t('加载单阶段运行状态失败'));
  }
}

function optionalValue(value: string): string | null {
  return value.trim() || null;
}

watch(defaultAsrLanguage, value => { if (!form.asr_language) form.asr_language = isAsrLanguage(value) ? value : null; });
watch(defaultAsrCandidate, value => { if (!form.asr_candidate) form.asr_candidate = value; });
watch(defaultSecondaryAsrCandidate, value => { form.secondary_asr_candidate = value; });

function buildStageRunPayload(): StageRunPayload {
  const payload: StageRunPayload = {
    profile: optionalValue(form.profile),
  };
  if (form.stage === "transcribe" || form.stage === "refine") {
    payload.asr_language = form.asr_language;
    payload.asr_candidate = optionalValue(form.asr_candidate);
    payload.secondary_asr_candidate = form.stage === "refine" && runMode.value === "file" ? "" : form.secondary_asr_candidate;
  }
  if (usesOcrOverrides.value) {
    payload.ocr_backend = "codex_api";
    payload.ocr_fast_mode = form.ocr_fast_mode;
    payload.ocr_model = optionalValue(form.ocr_model);
    payload.ocr_reasoning_effort = optionalValue(form.ocr_reasoning_effort);
    payload.ocr_max_concurrency = form.ocr_max_concurrency;
    payload.ocr_submit_interval_seconds = form.ocr_submit_interval_seconds;
  }
  if (usesRefineOverrides.value) {
    payload.backend = "codex_api";
    payload.fast_mode = form.fast_mode;
    payload.model = optionalValue(form.model);
    payload.reasoning_effort = optionalValue(form.reasoning_effort);
  }
  return payload;
}

function clearFileInputs() {
  Object.keys(fileInputPaths).forEach((key) => {
    delete fileInputPaths[key];
  });
}

async function loadFileContract() {
  clearFileInputs();
  fileContract.value = null;
  fileContractLoading.value = true;
  try {
    const response = await getStageFileContract(form.stage);
    fileContract.value = response;
    fileResultName.value = response.default_result_name;
  } catch (caught) {
    message.error(caught instanceof Error ? caught.message : t('加载阶段文件输入要求失败'));
  } finally {
    fileContractLoading.value = false;
  }
}

function downloadStageFileResult() {
  const state = stageState.value;
  if (!state || state.run_mode !== "file" || state.status !== "success") {
    return;
  }
  window.location.assign(stageFileResultUrl(state.id));
}

async function submit() {
  if ((form.stage === "transcribe" || (form.stage === "refine" && runMode.value === "directory")) && incompatibleCandidates(asrCandidates.value, form.asr_language, form.asr_candidate, form.secondary_asr_candidate).length) { message.warning(t('所选模型不支持此音频语言，请更改语言或显式选择兼容模型。')); return; }
  if (
    usesOcrOverrides.value
    && (form.ocr_max_concurrency === null || form.ocr_submit_interval_seconds === null)
  ) {
    message.warning(t('请填写 PDF OCR 投递间隔和最大并发数。'));
    return;
  }
  if (isFileMode.value) {
    if (!fileContract.value) {
      message.warning(t('阶段文件输入要求尚未加载完成。'));
      return;
    }
    const missingSlots = fileContract.value.input_slots.filter((slot) => !fileInputPaths[slot.key]);
    if (missingSlots.length > 0) {
      message.warning(t('请先选择{p0}。', { p0: missingSlots.map((slot) => slotLabel(slot.key, slot.label)).join("、") }));
      return;
    }
    if (!fileResultName.value.trim()) {
      message.warning(t('请填写结果归档名称。'));
      return;
    }
  }

  submitting.value = true;
  try {
    const payload = buildStageRunPayload();
    const response = isFileMode.value && fileContract.value
      ? await submitStageFileRun(form.stage, {
        ...payload,
        input_files: Object.fromEntries(
          fileContract.value.input_slots.map((slot) => [slot.key, fileInputPaths[slot.key]]),
        ),
        result_name: fileResultName.value.trim(),
      })
      : await submitStageRun(form.stage, payload);
    await refreshStage(response.run_id);
    await loadStageRuns();
    if (stageState.value && isActiveStageRun(stageState.value)) {
      startPolling(response.run_id);
    }
    message.success(t('阶段任务已成功提交：{p0}', { p0: response.run_id }));
  } catch (caught) {
    message.error(caught instanceof Error ? caught.message : t('提交失败'));
  } finally {
    submitting.value = false;
  }
}

watch(
  () => form.stage,
  () => {
    if (isFileMode.value) {
      void loadFileContract();
    }
  },
);

watch(defaultFastMode, value => { if (form.fast_mode === null) form.fast_mode = value; });
watch(defaultOcrFastMode, value => { if (form.ocr_fast_mode === null) form.ocr_fast_mode = value; });
watch(defaultOcrModel, (value) => {
  if (!form.ocr_model && value) {
    form.ocr_model = value;
  }
});
watch(defaultOcrReasoningEffort, (value) => {
  if (!form.ocr_reasoning_effort && value) {
    form.ocr_reasoning_effort = value;
  }
});
watch(defaultOcrMaxConcurrency, (value) => {
  if (Number.isFinite(value)) {
    form.ocr_max_concurrency = value;
  }
});
watch(defaultOcrSubmitIntervalSeconds, (value) => {
  if (Number.isFinite(value)) {
    form.ocr_submit_interval_seconds = value;
  }
});

async function handleStageRunRetry(runId: string) {
  await refreshStage(runId);
  startPolling(runId);
}

watch(runMode, (mode) => {
  if (mode === "file") {
    void loadFileContract();
  }
});

onMounted(() => {
  void loadStageRuns();
  void loadFileContract();
});

onBeforeUnmount(stopPolling);
</script>

<template>
  <div class="workbench-page stage-runner-view">
    <section class="page-heading">
      <div><h2>{{ t('单阶段运行') }}</h2><p>{{ t('选择一个处理阶段，测试本机文件或处理当前配置目录。运行参数只对本次生效。') }}</p></div>
    </section>

    <n-alert v-if="isFileMode" type="info" :title="t('本机文件测试模式')" :bordered="false" class="file-mode-alert">
      {{ t('选择的文件只会复制到本次运行的隔离工作区；完成后以 ZIP 下载，不会写入当前配置目录。') }}
    </n-alert>
    <n-alert v-else type="warning" :title="t('全局目录运行警告')" :bordered="false" class="warn-alert">
      {{ t('目录模式会直接对当前系统配置目录下的数据执行对应处理阶段。') }}
    </n-alert>
    <n-alert v-if="configError" type="error" :title="configError" :bordered="false" class="warn-alert" />

    <div class="workbench-columns">
    <div class="workspace-primary">
    <n-card class="view-card form-panel" :bordered="false">

      <n-form label-placement="top">
        <n-space vertical :size="14">
          <n-form-item :label="t('指定流水线阶段')">
            <n-select v-model:value="form.stage" :options="stageOptions" class="w-full select-stage" />
          </n-form-item>

          <section class="run-mode-panel">
            <div>
              <h3>{{ t('运行方式') }}</h3>
              <p>{{ t('文件模式用于单个输入测试；目录模式保留原有批处理行为。') }}</p>
            </div>
            <n-radio-group v-model:value="runMode" name="stage-run-mode">
              <n-radio-button value="file">{{ t('本机文件') }}</n-radio-button>
              <n-radio-button value="directory">{{ t('当前配置目录') }}</n-radio-button>
            </n-radio-group>
          </section>

          <section class="stage-guide">
            <n-flex justify="space-between" align="center" :size="10" wrap>
              <div>
                <p class="stage-guide__eyebrow">{{ t('当前测试阶段') }}</p>
                <h3>{{ currentStageGuide.label }}</h3>
              </div>
              <n-tag :type="isFileMode ? 'success' : 'info'" :bordered="false">
                {{ isFileMode ? t('隔离工作区') : t('当前配置目录') }}
              </n-tag>
            </n-flex>
            <p class="stage-guide__description">
              {{ isFileMode ? t('本次运行只处理下方选择的文件，原有全局目录不会参与。') : currentStageGuide.description }}
            </p>
            <div v-if="!isFileMode" class="stage-guide__paths">
              <div>
                <span>{{ t('输入') }}</span>
                <code>{{ currentStageGuide.input }}</code>
              </div>
              <div>
                <span>{{ t('输出') }}</span>
                <code>{{ currentStageGuide.output }}</code>
              </div>
            </div>
            <p class="stage-guide__hint">
              {{ isFileMode ? t('结果会被打包为 ZIP，由浏览器下载到你选择的本机位置。') : currentStageGuide.testHint }}
            </p>
          </section>

          <section v-if="isFileMode" class="file-input-panel">
            <div class="override-panel__heading">
              <div>
                <h3>{{ t('本次文件输入与输出') }}</h3>
                <p>{{ t('按当前阶段选择所需文件；文件仅在本次运行结束前保存在隔离工作区。') }}</p>
              </div>
              <n-tag size="small" :bordered="false" type="success">{{ t('结果下载') }}</n-tag>
            </div>

            <n-alert v-if="fileContractLoading" type="info" :bordered="false">
              {{ t('正在读取当前阶段的文件要求…') }}
            </n-alert>
            <n-alert v-else-if="!fileContract" type="error" :bordered="false">
              {{ t('无法读取文件输入要求，请重新选择阶段或刷新页面。') }}
            </n-alert>
            <n-grid v-else :cols="2" :x-gap="12" :y-gap="0" responsive="screen" item-responsive>
              <n-grid-item v-for="slot in fileContract.input_slots" :key="slot.key" span="2 m:1">
                <n-form-item :label="slotLabel(slot.key, slot.label)" required>
                  <StageFileUpload
                    v-model="fileInputPaths[slot.key]"
                    :stage-name="form.stage"
                    :slot="slot"
                  />
                </n-form-item>
              </n-grid-item>
              <n-grid-item span="2">
                <n-form-item :label="t('结果归档名称')" required>
                  <n-input v-model:value="fileResultName" :placeholder="t('例如 lesson-asr')">
                    <template #suffix>.zip</template>
                  </n-input>
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </section>

          <details class="advanced-options override-panel">
            <summary>{{ t('高级参数 · 本次运行覆盖') }}</summary>
            <div class="override-panel__heading">
              <div>
                <h3>{{ t('本次运行覆盖') }}</h3>
                <p>{{ t('留空即使用设置页中的默认值；本页选择不会保存为全局设置。') }}</p>
              </div>
              <n-tag size="small" :bordered="false" type="success">{{ t('仅本次生效') }}</n-tag>
            </div>

            <n-grid :cols="2" :x-gap="12" :y-gap="0" responsive="screen" item-responsive>
              <n-grid-item v-if="form.stage === 'transcribe' || (form.stage === 'refine' && runMode === 'directory')" span="2 m:1">
                <n-form-item :label="t('语音转文字模型')">
                  <div class="w-full">
                    <AsrLanguageSelector v-model="form.asr_language" :languages="asrLanguages" :inherited-language="defaultAsrLanguage" />
                    <AsrCandidateSelector :language="form.asr_language" v-model="form.asr_candidate" v-model:secondary-candidate="form.secondary_asr_candidate" :options="asrCandidates" :loading="configLoading" />
                  </div>
                </n-form-item>
              </n-grid-item>
              <n-grid-item span="2 m:1">
                <n-form-item :label="t('配置方案')">
                  <ProfileSelector v-model="form.profile" :options="profiles" :loading="configLoading" />
                </n-form-item>
              </n-grid-item>

              <template v-if="usesOcrOverrides">
                <n-grid-item span="2">
                  <FastModeSwitch v-model="form.ocr_fast_mode" :label="t('PDF OCR 快速模式')" :disabled="configLoading" />
                  <p class="prompt-hint">{{ t('仅实际执行 PDF OCR 时请求快速服务；可能增加额度消耗或费用，不改变推理强度。') }}</p>
                </n-grid-item>
                <n-grid-item span="2 m:1">
                  <n-form-item :label="t('PDF OCR 模型')">
                    <n-select
                      v-model:value="form.ocr_model"
                      :options="modelOptions"
                      clearable
                      :placeholder="t('使用默认 OCR 模型')"
                    />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item span="2">
                  <n-form-item :label="t('PDF OCR 推理强度')">
                    <n-select
                      v-model:value="form.ocr_reasoning_effort"
                      :options="reasoningOptions"
                      clearable
                      :placeholder="t('使用默认 OCR 推理强度')"
                    />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item span="2 m:1">
                  <n-form-item :label="t('页面投递间隔（秒）')" required>
                    <n-input-number
                      v-model:value="form.ocr_submit_interval_seconds"
                      :min="0"
                      :step="0.5"
                      class="w-full"
                    />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item span="2 m:1">
                  <n-form-item :label="t('最大在途请求数')" required>
                    <n-input-number
                      v-model:value="form.ocr_max_concurrency"
                      :min="1"
                      :precision="0"
                      class="w-full"
                    />
                  </n-form-item>
                </n-grid-item>
              </template>

              <template v-else-if="usesRefineOverrides">
                <n-grid-item v-if="runMode === 'file'" span="2">
                  <n-alert type="info" :show-icon="false">{{ t('单 TXT 文件校对仅使用单 ASR，不继承全局第二模型。联合校对请使用完整任务或已完成配对的 CLI 工作区。') }}</n-alert>
                </n-grid-item>
                <n-grid-item span="2">
                  <FastModeSwitch v-model="form.fast_mode" :label="t('AI 精修快速模式')" :disabled="configLoading" />
                  <p class="prompt-hint">{{ t('通过 CPA 请求快速服务；可能增加额度消耗或费用，不改变推理强度。') }}</p>
                </n-grid-item>
                <n-grid-item span="2 m:1">
                  <n-form-item :label="t('阶段 6 模型')">
                    <n-select
                      v-model:value="form.model"
                      :options="modelOptions"
                      clearable
                      :placeholder="t('使用默认阶段 6 模型')"
                    />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item span="2">
                  <n-form-item :label="t('阶段 6 推理强度')">
                    <n-select
                      v-model:value="form.reasoning_effort"
                      :options="reasoningOptions"
                      clearable
                      :placeholder="t('使用默认阶段 6 推理强度')"
                    />
                  </n-form-item>
                </n-grid-item>
              </template>
            </n-grid>
          </details>

          <n-flex justify="end" class="form-action-area">
            <n-button type="primary" size="large" :loading="submitting" @click="submit" class="submit-btn is-stage-btn">
              <template #icon>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              </template>
              {{ isFileMode ? t('运行并生成下载包') : t('运行当前目录阶段') }}
            </n-button>
          </n-flex>
        </n-space>
      </n-form>
    </n-card>
    </div>
    <aside class="workspace-inspector" :aria-label="t('阶段运行状态与结果')">
      <section v-if="stageState?.run_mode === 'file' && stageState.status === 'success' && stageState.download_name" class="file-result-panel">
        <h3>{{ t('文件结果已就绪') }}</h3>
        <p>{{ stageState.download_name }} {{ t('已在本次隔离工作区生成。') }}</p>
        <n-button type="primary" @click="downloadStageFileResult">{{ t('下载结果 ZIP') }}</n-button>
      </section>
      <JobStatusCard v-if="stageState" :title="t('当前阶段状态')" :state="stageState" default-expanded @rerun="handleStageRunRetry" />
      <section v-else class="inspector-empty">
        <h3>{{ t('运行状态与结果') }}</h3><p>{{ t('提交后查看当前阶段进度，或从下方历史记录中恢复查看。') }}</p>
        <p>{{ t('本机文件模式生成独立 ZIP；目录模式的产物保留在配置目录。') }}</p>
      </section>
    </aside>
    </div>

    <n-card class="view-card history-panel" :bordered="false">
      <template #header>
        <n-flex justify="space-between" align="center" :size="12" wrap>
          <div>
            <span>{{ t('单阶段运行历史') }}</span>
            <p class="history-panel__copy">{{ t('选择任一记录可恢复状态查看；运行中的记录会继续刷新。') }}</p>
          </div>
          <n-button size="small" secondary :loading="historyLoading" @click="loadStageRuns">{{ t('刷新历史') }}</n-button>
        </n-flex>
      </template>

      <n-alert v-if="historyError" type="error" :title="t('无法读取运行历史')" :bordered="false">{{ historyError }}{{ t('。请刷新重试。') }}</n-alert>
      <p v-if="historyLoading" role="status" class="prompt-hint">{{ t('正在读取运行历史…') }}</p>
      <n-empty v-if="!historyLoading && !historyError && stageRuns.length === 0" :description="t('还没有单阶段运行记录。')" />
      <div v-if="stageRuns.length" class="stage-history-list">
        <button
          v-for="run in stageRuns"
          :key="run.id"
          type="button"
          class="stage-history-item"
          :class="{ 'is-selected': stageState?.id === run.id }"
          :aria-pressed="stageState?.id === run.id"
          @click="loadStageRun(run.id)"
        >
          <div class="stage-history-item__main">
            <strong>{{ labelFor(run.current_stage) }}</strong>
            <span>{{ run.id }}</span>
          </div>
          <div class="stage-history-item__meta">
            <n-tag v-if="run.run_mode === 'file'" size="small" type="info" :bordered="false">{{ t('文件模式') }}</n-tag>
            <n-tag size="small" :type="stageRunStatusType(run.status)" :bordered="false">{{ labelFor(run.status) }}</n-tag>
            <span>{{ formatDate(run.updated_at) }}</span>
          </div>
        </button>
      </div>
    </n-card>

  </div>
</template>

<style scoped>
.run-mode-panel { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; }
.run-mode-panel h3, .file-input-panel h3, .file-result-panel h3, .override-panel h3, .stage-guide h3 { margin: 0; font-size: 14px; font-weight: 600; }
.run-mode-panel p, .file-input-panel p, .file-result-panel p, .override-panel p, .stage-guide p { margin: 4px 0 12px; font-size: 12px; color: var(--text-secondary); }
.stage-guide { padding: 16px; background: var(--surface-subtle); border-radius: 8px; }
.stage-guide__eyebrow { color: var(--text-muted); }
.stage-guide__paths { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.stage-guide__paths > div { display: grid; gap: 4px; }
.stage-guide__paths span { color: var(--text-muted); font-size: 12px; }
.stage-guide__paths code { color: var(--text-primary); overflow-wrap: anywhere; font-size: 12px; }
.stage-guide .stage-guide__hint { margin: 12px 0 0; }
.override-panel__heading { display: flex; flex-wrap: wrap; gap: 12px; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.file-input-panel { padding-top: 8px; }
.file-result-panel { padding: 16px; background: var(--color-success-bg); border-radius: 8px; }
.history-panel { padding-top: 24px; border-top: 1px solid var(--border-subtle); }
.history-panel__copy { margin: 4px 0 0; font-size: 12px; font-weight: 400; color: var(--text-muted); }
.stage-history-list { display: grid; gap: 4px; }
.stage-history-item { width: 100%; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; padding: 12px; border: 1px solid var(--border-subtle); border-radius: 8px; background: var(--surface-canvas); color: var(--text-primary); text-align: left; cursor: pointer; transition: background-color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out); }
.stage-history-item:hover, .stage-history-item.is-selected { border-color: var(--primary); background: var(--primary-alpha-10); }
.stage-history-item__main, .stage-history-item__meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; min-width: 0; }
.stage-history-item__main span, .stage-history-item__meta span { color: var(--text-muted); font-size: 12px; overflow-wrap: anywhere; }
@media (max-width: 600px) { .stage-guide__paths { grid-template-columns: minmax(0, 1fr); } }
</style>
