<script setup lang="ts">
import { t, labelFor } from "../i18n";
import { NSelect } from "naive-ui";
import { computed, watch } from "vue";
import type { AsrCandidate, AsrLanguage } from "../api/client";
import { supportedLanguages, incompatibleCandidates } from "../composables/asrLanguage";

const props = defineProps<{
  modelValue: string;
  options: AsrCandidate[];
  loading?: boolean;
  secondaryCandidate?: string;
  language?: AsrLanguage | null;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: string];
  "update:secondaryCandidate": [value: string];
}>();
const candidateNames: Record<string, string> = {
  "qwen3-asr-1.7b": "Qwen3-ASR 1.7B", "qwen3-asr-0.6b": "Qwen3-ASR 0.6B",
  "paraformer-zh": "Paraformer (zh)", "fun-asr-nano": "Fun-ASR Nano",
};
function candidateLabel(candidate: AsrCandidate) {
  return candidate.id === "whisper-existing" ? t('Whisper（现有配置）') : candidateNames[candidate.id] ?? candidate.id;
}
const incompatible = computed(() => incompatibleCandidates(props.options, props.language, props.modelValue, props.secondaryCandidate));
const selectOptions = computed(() => props.options.map((candidate) => {
  const unsupported = !!props.language && !supportedLanguages(candidate).includes(props.language);
  return {
    label: `${candidateLabel(candidate)}${candidate.dependency_status === "installed" ? "" : t('（依赖不可用）')}${unsupported ? ` · ${t('不支持此语言')}` : ""}`,
    value: candidate.id,
    disabled: candidate.dependency_status !== "installed" || unsupported,
  };
}));
const secondaryOptions = computed(() => [
  { label: t('单 ASR（不运行第二模型）'), value: "", disabled: false },
  ...selectOptions.value.filter(option => option.value !== props.modelValue),
]);
watch(() => props.modelValue, value => {
  if (value && value === props.secondaryCandidate) emit("update:secondaryCandidate", "");
});
</script>

<template>
  <div class="asr-candidate-selector">
    <n-select
      :aria-label="t('语音转文字模型')"
      :value="modelValue || null"
      :options="selectOptions"
      :loading="loading"
      :placeholder="t('选择语音转文字模型')"
      @update:value="emit('update:modelValue', String($event || ''))"
    />
    <template v-if="secondaryCandidate !== undefined">
      <p>{{ t('第二模型（可选）：') }}</p>
      <n-select
        :aria-label="t('第二模型')"
        :value="secondaryCandidate"
        :options="secondaryOptions"
        :loading="loading"
        @update:value="emit('update:secondaryCandidate', String($event || ''))"
      />
      <p>{{ t('选择第二模型后串行运行两次 ASR，保留独立原稿，再由 AI 联合校对；耗时与输入费用会增加。') }}</p>
    </template>
    <p v-if="incompatible.length" role="alert" class="language-error">{{ t('所选模型不支持此音频语言，请更改语言或显式选择兼容模型。') }}</p>
    <p v-for="candidate in options.filter(item => item.id === modelValue || item.id === secondaryCandidate)" :key="candidate.id">{{ candidateLabel(candidate) }} · {{ t('支持语言：{p0}', { p0: supportedLanguages(candidate).map(labelFor).join(' / ') }) }}</p>
    <p>{{ t('依赖已安装不等于模型已验证。其它候选不使用配置方案中的 Whisper 模型、精度或 beam 参数。') }}</p>
  </div>
</template>

<style scoped>
.asr-candidate-selector { width: 100%; min-width: 0; }
.language-error { color: var(--color-error); }
p { margin: 6px 0 0; font-size: 12px; line-height: 1.5; color: var(--n-text-color-3, #888); }
</style>
