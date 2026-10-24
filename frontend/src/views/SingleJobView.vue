<script setup lang="ts">
import { t } from "../i18n";
import {
  NAlert,
  NButton,
  NCard,
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
  useMessage,
} from "naive-ui";
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

import { getJob, getRefineDefaultInstruction, type JobState, submitJob } from "../api/client";
import FastModeSwitch from "../components/FastModeSwitch.vue";
import JobStatusCard from "../components/JobStatusCard.vue";
import ProfileSelector from "../components/ProfileSelector.vue";
import AsrCandidateSelector from "../components/AsrCandidateSelector.vue";
import AsrLanguageSelector from "../components/AsrLanguageSelector.vue";
import type { AsrLanguage } from "../api/client";
import { isAsrLanguage, incompatibleCandidates } from "../composables/asrLanguage";
import RemoteFileUpload from "../components/RemoteFileUpload.vue";
import { useConfigOptions } from "../composables/useConfigOptions";

const message = useMessage();
const {
  asrCandidates,
  asrLanguages,
  defaultAsrLanguage,
  defaultAsrCandidate,
  defaultSecondaryAsrCandidate,
  activeProfile,
  defaultFastMode,
  defaultOcrFastMode,
  defaultOcrMaxConcurrency,
  defaultOcrModel,
  defaultOcrReasoningEffort,
  defaultOcrSubmitIntervalSeconds,
  defaultOutputDir,
  error,
  loading,
  profiles,
  referenceExtensions,
  videoExtensions,
} = useConfigOptions();
const jobState = ref<JobState | null>(null);
const submitting = ref(false);
const promptLoading = ref(false);
const defaultRefinePrompt = ref("");
const pollHandle = ref<number | null>(null);

const form = reactive({
  content_type: "reference",
  video: "",
  reference: "",
  output_dir: "",
  profile: "",
  asr_candidate: "",
  asr_language: null as AsrLanguage | null,
  secondary_asr_candidate: "",
  fast_mode: null as boolean | null,
  ocr_fast_mode: null as boolean | null,
  ocr_model: "",
  ocr_reasoning_effort: "",
  ocr_max_concurrency: 40 as number | null,
  ocr_submit_interval_seconds: 5 as number | null,
  book_name: "",
  chapter: "",
  glossary_file: "",
  refine_prompt: "",
});

const ocrReasoningOptions = computed(() => ([
  { label: t('低'), value: "low" },
  { label: t('中'), value: "medium" },
  { label: t('高'), value: "high" },
  { label: t('很高'), value: "xhigh" },
]));
const contentTypeOptions = computed(() => ([
  { label: t('参考材料校对'), value: "reference" },
  { label: t('对谈转录'), value: "conversation" },
]));
const videoAccept = computed(() => videoExtensions.value.join(","));
const referenceAccept = computed(() => referenceExtensions.value.join(","));
const glossaryAccept = ".txt,.md";
const isConversation = computed(() => form.content_type === "conversation");

watch(defaultAsrLanguage, value => { if (!form.asr_language) form.asr_language = isAsrLanguage(value) ? value : null; });
watch(defaultAsrCandidate, value => { if (!form.asr_candidate) form.asr_candidate = value; });
watch(defaultSecondaryAsrCandidate, value => { form.secondary_asr_candidate = value; });

watch(activeProfile, (value) => {
  if (!form.profile && value) {
    form.profile = value;
  }
});

watch(defaultOutputDir, (value) => {
  if (!form.output_dir && value) {
    form.output_dir = value;
  }
});

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

function stopPolling() {
  if (pollHandle.value !== null) {
    window.clearInterval(pollHandle.value);
    pollHandle.value = null;
  }
}

async function refreshJob(jobId: string) {
  const state = await getJob(jobId);
  jobState.value = state;
  if (state.status === "success" || state.status === "partial" || state.status === "failed") {
    stopPolling();
  }
}

function startPolling(jobId: string) {
  stopPolling();
  pollHandle.value = window.setInterval(() => {
    void refreshJob(jobId).catch((caught) => {
      message.error(caught instanceof Error ? caught.message : t('刷新任务状态失败'));
      stopPolling();
    });
  }, 2000);
}

function effectiveRefinePrompt(): string | null {
  const currentPrompt = form.refine_prompt.trim();
  if (!currentPrompt || currentPrompt === defaultRefinePrompt.value.trim()) {
    return null;
  }
  return form.refine_prompt;
}

function resetRefinePrompt() {
  form.refine_prompt = defaultRefinePrompt.value;
}

async function loadDefaultRefinePrompt() {
  const currentPrompt = form.refine_prompt.trim();
  const previousDefaultPrompt = defaultRefinePrompt.value.trim();
  const shouldReplacePrompt = !currentPrompt || currentPrompt === previousDefaultPrompt;
  promptLoading.value = true;
  try {
    const response = await getRefineDefaultInstruction(form.content_type);
    defaultRefinePrompt.value = response.prompt;
    if (shouldReplacePrompt) {
      form.refine_prompt = response.prompt;
    }
  } catch (caught) {
    message.error(caught instanceof Error ? caught.message : t('读取阶段六默认指令失败'));
  } finally {
    promptLoading.value = false;
  }
}

async function handleJobRerun(jobId: string) {
  await refreshJob(jobId);
  startPolling(jobId);
}

async function submit() {
  if (incompatibleCandidates(asrCandidates.value, form.asr_language, form.asr_candidate, form.secondary_asr_candidate).length) { message.warning(t('所选模型不支持此音频语言，请更改语言或显式选择兼容模型。')); return; }
  if (!form.video || !form.output_dir) {
    message.warning(t('视频和服务器默认输出目录是必填项。'));
    return;
  }
  if (!isConversation.value && !form.reference) {
    message.warning(t('参考材料校对模式下参考源是必填项。'));
    return;
  }
  if (
    !isConversation.value
    && (form.ocr_max_concurrency === null || form.ocr_submit_interval_seconds === null)
  ) {
    message.warning(t('请填写 PDF OCR 投递间隔和最大并发数。'));
    return;
  }
  submitting.value = true;
  try {
    const response = await submitJob({
      video: form.video,
      reference: isConversation.value ? null : form.reference,
      output_dir: form.output_dir,
      content_type: form.content_type,
      profile: form.profile || null,
      asr_candidate: form.asr_candidate || null,
    asr_language: form.asr_language,
      secondary_asr_candidate: form.secondary_asr_candidate,
      backend: "codex_api",
      ocr_backend: "codex_api",
      fast_mode: form.fast_mode,
      ocr_fast_mode: isConversation.value ? false : form.ocr_fast_mode,
      ocr_model: form.ocr_model || null,
      ocr_reasoning_effort: form.ocr_reasoning_effort || null,
      ocr_max_concurrency: form.ocr_max_concurrency,
      ocr_submit_interval_seconds: form.ocr_submit_interval_seconds,
      book_name: form.book_name || null,
      chapter: form.chapter || null,
      glossary_file: form.glossary_file || null,
      refine_prompt: effectiveRefinePrompt(),
    });
    await refreshJob(response.job_id);
    startPolling(response.job_id);
    message.success(t('任务已成功提交：{p0}', { p0: response.job_id }));
  } catch (caught) {
    message.error(caught instanceof Error ? caught.message : t('提交失败'));
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  void loadDefaultRefinePrompt();
});
watch(
  () => form.content_type,
  () => {
    if (isConversation.value) {
      form.reference = "";
    }
    void loadDefaultRefinePrompt();
  }
);
onBeforeUnmount(stopPolling);
</script>

<template>
  <div class="workbench-page single-job-view">
    <section class="page-heading">
      <div><h2>{{ t('新建单任务') }}</h2><p>{{ t('左侧上传录屏与参考源，右侧选择本次配置。提交后在下方查看进度与整理结果。') }}</p></div>
    </section>

    <n-alert v-if="error" type="error" :title="error" :bordered="false" class="glass-alert" />

    <n-form label-placement="top" class="workbench-columns">
      <div class="workspace-primary">
        <n-card class="view-card form-panel" :bordered="false">
            <div class="form-section">
              <h3 class="form-section-title">{{ t('输入文件') }}</h3>
              <n-form-item :label="t('任务类型')" required>
                <n-radio-group v-model:value="form.content_type" size="medium">
                  <n-radio-button
                    v-for="item in contentTypeOptions"
                    :key="item.value"
                    :value="item.value"
                  >
                    {{ item.label }}
                  </n-radio-button>
                </n-radio-group>
              </n-form-item>
              <n-form-item :label="t('视频文件')" required>
                <n-space vertical class="w-full">
                  <RemoteFileUpload
                    v-model="form.video"
                    kind="video"
                    :label="t('视频文件')"
                    :accept="videoAccept"
                    :button-text="t('选择并上传本机视频')"
                  />
                  <n-input v-model:value="form.video" readonly :placeholder="t('上传后自动生成服务器路径')" />
                </n-space>
              </n-form-item>
              <n-form-item v-if="!isConversation" :label="t('参考源文件或 URL')" required>
                <n-space vertical class="w-full">
                  <n-input v-model:value="form.reference" :placeholder="t('可粘贴 https:// 网址，或上传本机参考文件')" />
                  <RemoteFileUpload
                    v-model="form.reference"
                    kind="reference"
                    :label="t('参考源文件')"
                    :accept="referenceAccept"
                    :button-text="t('选择并上传本机参考源')"
                  />
                </n-space>
              </n-form-item>
              <n-form-item :label="t('成果获取方式')" required>
                <n-alert type="info" :bordered="false" class="server-output-note">
                  <div class="server-output-note__body">
                    <span>{{ t('处理完成后，到任务列表点击“下载结果”选择 Markdown 或 TXT。') }}</span>
                    <small>{{ t('服务器默认保存目录：') }}{{ form.output_dir || t('配置加载中...') }}</small>
                  </div>
                </n-alert>
              </n-form-item>
            </div>
        </n-card>
      </div>
      <aside class="workspace-inspector" :aria-label="t('本次任务配置')">
        <n-card class="view-card form-panel" :bordered="false">
            <div class="form-section">
              <h3 class="form-section-title">{{ t('常用配置 · 仅本次任务') }}</h3>
              <n-form-item :label="t('语音转文字模型')">
                <div class="w-full">
                  <AsrLanguageSelector v-model="form.asr_language" :languages="asrLanguages" :inherited-language="defaultAsrLanguage" />
                  <AsrCandidateSelector :language="form.asr_language" v-model="form.asr_candidate" v-model:secondary-candidate="form.secondary_asr_candidate" :options="asrCandidates" :loading="loading" />
                </div>
              </n-form-item>
              <n-form-item :label="t('配置方案')">
                <ProfileSelector v-model="form.profile" :options="profiles" :loading="loading" />
              </n-form-item>
              <section class="fast-mode-options" :aria-label="t('快速模式')">
                <h4>{{ t('快速模式 · 仅本次任务') }}</h4>
                <FastModeSwitch v-model="form.fast_mode" :label="t('AI 精修快速模式')" :disabled="loading" />
                <FastModeSwitch v-if="!isConversation" v-model="form.ocr_fast_mode" :label="t('PDF OCR 快速模式')" :disabled="loading" />
                <p class="prompt-hint">{{ t('通过 CPA 请求快速服务，可能增加额度消耗或费用；不改变模型或推理强度。PDF 开关仅在实际执行 OCR 时生效。') }}</p>
              </section>
              <details class="advanced-options">
                <summary>{{ t('高级参数 · OCR、术语与整理指令') }}</summary>
                <n-grid :cols="2" :x-gap="12" :y-gap="0" responsive="screen" item-responsive>
                  <n-grid-item span="2">
                    <n-form-item :label="t('术语词表')">
                      <n-space vertical class="w-full">
                        <RemoteFileUpload v-model="form.glossary_file" kind="glossary" :label="t('术语词表')" :accept="glossaryAccept" :button-text="t('选择并上传本机词表')" />
                        <n-input v-model:value="form.glossary_file" readonly :placeholder="t('可选，上传后自动生成服务器路径')" />
                      </n-space>
                    </n-form-item>
                  </n-grid-item>
                <n-grid-item v-if="!isConversation" span="2 m:1">
                  <n-form-item :label="t('PDF OCR 模型')">
                    <n-input v-model:value="form.ocr_model" :placeholder="t('例如 gpt-6-luna')" />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item v-if="!isConversation" span="2 m:1">
                  <n-form-item :label="t('PDF OCR 推理强度')">
                    <n-select v-model:value="form.ocr_reasoning_effort" :options="ocrReasoningOptions" />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item v-if="!isConversation" span="2 m:1">
                  <n-form-item :label="t('页面投递间隔（秒）')" required>
                    <n-input-number
                      v-model:value="form.ocr_submit_interval_seconds"
                      :min="0"
                      :step="0.5"
                      class="w-full"
                    />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item v-if="!isConversation" span="2 m:1">
                  <n-form-item :label="t('最大在途请求数')" required>
                    <n-input-number
                      v-model:value="form.ocr_max_concurrency"
                      :min="1"
                      :precision="0"
                      class="w-full"
                    />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item span="2 m:1">
                  <n-form-item :label="t('材料名称')">
                    <n-input v-model:value="form.book_name" :placeholder="t('例如：示例材料；可选，用于 ASR 提示词')" />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item span="2">
                  <n-form-item :label="t('章节或部分')">
                    <n-input v-model:value="form.chapter" :placeholder="t('例如：第一部分；可选，用于 ASR 提示词')" />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item span="2">
                  <n-form-item :label="t('阶段六指令')">
                    <n-space vertical class="w-full">
                      <n-input
                        v-model:value="form.refine_prompt"
                        type="textarea"
                        :autosize="{ minRows: 10, maxRows: 18 }"
                        :loading="promptLoading"
                        :placeholder="t('读取默认阶段六指令中...')"
                      />
                      <n-flex justify="space-between" align="center" :size="12" wrap>
                        <span class="prompt-hint">{{ t('文本框内为当前默认指令，可直接在此基础上调整；不修改时提交会使用项目默认指令。') }}</span>
                        <n-button size="small" secondary :disabled="!defaultRefinePrompt" @click="resetRefinePrompt">
                          {{ t('恢复默认指令') }}
                        </n-button>
                      </n-flex>
                    </n-space>
                  </n-form-item>
                </n-grid-item>
              </n-grid>
              </details>
            </div>

        <n-flex justify="end" class="form-action-area">
          <n-button type="primary" size="large" :loading="submitting" @click="submit" class="submit-btn">
            <template #icon>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </template>
            {{ t('开始整理') }}
          </n-button>
        </n-flex>
        </n-card>
      </aside>
    </n-form>
    <JobStatusCard v-if="jobState" :title="t('当前任务')" :state="jobState" default-expanded @rerun="handleJobRerun" />
  </div>
</template>

<style scoped>
.workbench-columns { grid-template-columns: repeat(2, minmax(0, 1fr)); }
@media (max-width: 1200px) {
  .workbench-columns { grid-template-columns: minmax(0, 1fr); }
}
</style>
