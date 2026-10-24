<script setup lang="ts">
import { t } from "../i18n";
import {
  NAlert,
  NButton,
  NCard,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NInput,
  NSelect,
  NSpace,
  NSwitch,
  NTag,
  useMessage,
} from "naive-ui";
import { computed, onMounted, reactive, ref } from "vue";

import { getFrontendSettings, saveFrontendSettings, type FrontendSettings } from "../api/client";
import AsrCandidateSelector from "../components/AsrCandidateSelector.vue";
import AsrLanguageSelector from "../components/AsrLanguageSelector.vue";
import type { AsrLanguage } from "../api/client";
import { isAsrLanguage, incompatibleCandidates } from "../composables/asrLanguage";
import FastModeSwitch from "../components/FastModeSwitch.vue";
import { useConfigOptions } from "../composables/useConfigOptions";
const { asrCandidates, asrLanguages, defaultAsrLanguage, loading: configLoading } = useConfigOptions();

const message = useMessage();
const loading = ref(false);
const saving = ref(false);
const loadedSettings = ref<FrontendSettings | null>(null);
const loadError = ref("");

const form = reactive({
  codex_lb_base_url: "",
  codex_lb_api_key: "",
  clear_codex_lb_api_key: false,
  codex_lb_bypass_proxy: false,
  model: "",
  asr_candidate: "",
  asr_language: null as AsrLanguage | null,
  secondary_asr_candidate: "",
  reasoning_effort: "high",
  fast_mode: false,
  ocr_fast_mode: false,
  ocr_model: "",
  ocr_reasoning_effort: "high",
});

const reasoningOptions = computed(() => ([
  { label: t('低'), value: "low" },
  { label: t('中'), value: "medium" },
  { label: t('高'), value: "high" },
  { label: t('很高'), value: "xhigh" },
  { label: t('最高'), value: "max" },
]));

const modelOptions = computed(() => ([
  { label: t('GPT-6.1 Sol（阶段 6 精修）'), value: "gpt-6.1-sol" },
  { label: "GPT-6 Luna（PDF OCR）", value: "gpt-6-luna" },
]));

const apiKeyStatus = computed(() => {
  if (form.codex_lb_api_key.trim()) {
    return t('本次会写入新 API key');
  }
  if (form.clear_codex_lb_api_key) {
    return t('保存后会清除已保存 API key');
  }
  if (loadedSettings.value?.has_codex_lb_api_key) {
    return t('已保存或已通过环境变量提供');
  }
  return t('尚未配置');
});

function applySettings(settings: FrontendSettings) {
  loadedSettings.value = settings;
  form.codex_lb_base_url = settings.codex_lb_base_url;
  form.codex_lb_api_key = "";
  form.clear_codex_lb_api_key = false;
  form.codex_lb_bypass_proxy = settings.codex_lb_bypass_proxy ?? false;
  form.model = settings.model;
  form.asr_candidate = settings.asr_candidate || "whisper-existing";
  form.asr_language = isAsrLanguage(settings.asr_language) ? settings.asr_language : settings.asr_language ? null : "zh";
  form.secondary_asr_candidate = settings.secondary_asr_candidate || "";
  form.reasoning_effort = settings.reasoning_effort;
  form.fast_mode = settings.fast_mode ?? false;
  form.ocr_fast_mode = settings.ocr_fast_mode ?? false;
  form.ocr_model = settings.ocr_model;
  form.ocr_reasoning_effort = settings.ocr_reasoning_effort;
}

async function loadSettings() {
  loading.value = true;
  loadError.value = "";
  try {
    applySettings(await getFrontendSettings());
  } catch (caught) {
    loadError.value = caught instanceof Error ? caught.message : t('加载设置失败');
    message.error(caught instanceof Error ? caught.message : t('加载设置失败'));
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  if (incompatibleCandidates(asrCandidates.value, form.asr_language, form.asr_candidate, form.secondary_asr_candidate).length) { message.warning(t('所选模型不支持此音频语言，请更改语言或显式选择兼容模型。')); return; }
  saving.value = true;
  try {
    const settings = await saveFrontendSettings({
      codex_lb_base_url: form.codex_lb_base_url,
      codex_lb_api_key: form.codex_lb_api_key || null,
      clear_codex_lb_api_key: form.clear_codex_lb_api_key,
      codex_lb_bypass_proxy: form.codex_lb_bypass_proxy,
      model: form.model,
      asr_candidate: form.asr_candidate,
      asr_language: form.asr_language,
      secondary_asr_candidate: form.secondary_asr_candidate,
      reasoning_effort: form.reasoning_effort,
      fast_mode: form.fast_mode,
      ocr_fast_mode: form.ocr_fast_mode,
      ocr_model: form.ocr_model,
      ocr_reasoning_effort: form.ocr_reasoning_effort,
    });
    applySettings(settings);
    message.success(t('设置已保存'));
  } catch (caught) {
    message.error(caught instanceof Error ? caught.message : t('保存设置失败'));
  } finally {
    saving.value = false;
  }
}

onMounted(loadSettings);
</script>

<template>
  <div class="workbench-page settings-view">
    <section class="page-heading">
      <div><h2>{{ t('连接与模型默认值') }}</h2><p>{{ t('全局设置用于后续任务；任务页中的参数覆盖不会回写到这里。') }}</p></div>
      <n-button type="primary" ghost :loading="loading" @click="loadSettings">{{ t('刷新') }}</n-button>
    </section>

    <n-alert v-if="loadError" type="error" :title="t('无法读取设置')" :bordered="false">{{ loadError }}{{ t('。请刷新后重试。') }}</n-alert>
    <p v-if="loading" role="status" class="prompt-hint">{{ t('正在读取已保存的设置…') }}</p>
    <n-alert type="info" :title="t('API key 存储位置')">
      {{ t('API key 会保存到') }} {{ loadedSettings?.settings_path || "data/jobs/frontend-settings.json" }}{{ t('。该目录已被 .gitignore 忽略。') }}
    </n-alert>

    <n-grid :cols="2" :x-gap="40" :y-gap="32" responsive="screen" item-responsive>
      <n-grid-item span="2 m:1">
        <n-card :title="t('CPA / OpenAI 兼容 API 连接')" class="view-card settings-card">
          <n-form label-placement="top">
            <n-form-item label="Base URL">
              <n-input
                v-model:value="form.codex_lb_base_url"
                :placeholder="t('http://127.0.0.1:8317/v1 或 https://你的网关域名/v1')"
              />
            </n-form-item>
            <p class="prompt-hint">
              {{ t('支持网关根地址或带 /v1 的地址；校对与 OCR 均调用 /v1/responses。模型名称须与 CPA 提供的一致。') }}
            </p>
            <n-form-item label="API Key">
              <n-input
                v-model:value="form.codex_lb_api_key"
                type="password"
                show-password-on="click"
                :placeholder="t('填写 CPA 客户端 API Key；留空则保持现有 key')"
              />
            </n-form-item>
            <details class="advanced-options">
              <summary>{{ t('连接选项与密钥管理') }}</summary>
            <n-form-item :label="t('API 直连（绕过代理）')">
              <n-space vertical :size="4" style="width: 100%;">
                <n-switch v-model:value="form.codex_lb_bypass_proxy" />
                <div class="prompt-hint">
                  {{ t('开启后仅 API 网关地址绕过系统代理；其他网站仍使用原代理。保存后对新任务生效。') }}
                </div>
              </n-space>
            </n-form-item>
            <div class="settings-card__meta">
              <n-tag :type="loadedSettings?.has_codex_lb_api_key ? 'success' : 'warning'" round>
                {{ apiKeyStatus }}
              </n-tag>
              <n-button text type="error" @click="form.clear_codex_lb_api_key = !form.clear_codex_lb_api_key">
                {{ form.clear_codex_lb_api_key ? t('取消清除') : t('清除已保存 key') }}
              </n-button>
            </div>
            </details>
          </n-form>
        </n-card>
      </n-grid-item>

      <n-grid-item span="2 m:1">
        <n-card :title="t('模型默认值')" class="view-card settings-card">
          <n-form label-placement="top">
            <n-form-item :label="t('默认语音转文字模型')">
              <div class="w-full">
                <AsrLanguageSelector v-model="form.asr_language" :languages="asrLanguages" :inherited-language="loadedSettings?.asr_language || defaultAsrLanguage" />
                <AsrCandidateSelector :language="form.asr_language" v-model="form.asr_candidate" v-model:secondary-candidate="form.secondary_asr_candidate" :options="asrCandidates" :loading="configLoading" />
              </div>
            </n-form-item>
            <n-form-item :label="t('阶段 6 模型')">
              <n-select v-model:value="form.model" :options="modelOptions" />
            </n-form-item>
            <n-form-item :label="t('阶段 6 推理强度')">
              <n-select v-model:value="form.reasoning_effort" :options="reasoningOptions" />
            </n-form-item>
            <FastModeSwitch v-model="form.fast_mode" :label="t('AI 精修快速模式（默认）')" :disabled="loading || saving || !!loadError" />
            <n-form-item :label="t('PDF OCR 模型')">
              <n-select v-model:value="form.ocr_model" :options="modelOptions" />
            </n-form-item>
            <n-form-item :label="t('PDF OCR 推理强度')">
              <n-select v-model:value="form.ocr_reasoning_effort" :options="reasoningOptions" />
            </n-form-item>
            <FastModeSwitch v-model="form.ocr_fast_mode" :label="t('PDF OCR 快速模式（默认）')" :disabled="loading || saving || !!loadError" />
            <p class="prompt-hint">{{ t('两个默认开关独立，仅供新任务使用。快速服务可能增加额度消耗或费用，不改变模型或推理强度。') }}</p>
          </n-form>
        </n-card>
      </n-grid-item>
    </n-grid>

    <div class="settings-actions">
      <n-button type="primary" size="large" :loading="saving" :disabled="loading || !!loadError" @click="saveSettings">{{ t('保存设置') }}</n-button>
      <p>{{ t('保存后供新任务使用，不更改已提交的任务。') }}</p>
    </div>
  </div>
</template>
