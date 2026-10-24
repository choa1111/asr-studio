<script setup lang="ts">
import { computed } from "vue";
import { NSelect } from "naive-ui";
import type { AsrLanguage } from "../api/client";
import { ASR_LANGUAGES, isAsrLanguage } from "../composables/asrLanguage";
import { t, labelFor } from "../i18n";

const props = defineProps<{ modelValue: AsrLanguage | null; languages?: string[]; inherit?: boolean; inheritedLanguage?: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: AsrLanguage | null] }>();
const inheritedOption = computed(() => {
  if (props.inherit) {
    const language = props.inheritedLanguage ? ` (${labelFor(props.inheritedLanguage)})` : '';
    return [{ label: `${t('沿用任务原语言')}${language}`, value: "" }];
  }
  if (props.inheritedLanguage && !isAsrLanguage(props.inheritedLanguage)) {
    return [{ label: t('继承配置（{p0}）', { p0: props.inheritedLanguage }), value: "" }];
  }
  return [];
});
const options = computed(() => [
  ...inheritedOption.value,
  ...(props.languages ?? ASR_LANGUAGES).filter(isAsrLanguage).map(value => ({ label: labelFor(value), value })),
]);
</script>

<template>
  <div class="asr-language-selector">
    <label class="asr-language-label">{{ inherit ? t('重跑音频语言') : t('音频语言') }}</label>
    <n-select :value="modelValue ?? ''" :options="options" :aria-label="inherit ? t('重跑音频语言') : t('音频语言')" @update:value="emit('update:modelValue', isAsrLanguage($event) ? $event : null)" />
    <p class="prompt-hint">{{ inherit ? t('重跑默认沿用任务快照；仅显式选择时覆盖语言。') : t('转录和校对保留音频原语言，不是翻译目标；与界面语言独立。') }}</p>
  </div>
</template>

<style scoped>
.asr-language-selector { width: 100%; min-width: 0; margin-bottom: 16px; }
.asr-language-label { display: block; margin-bottom: 6px; }
.prompt-hint { margin: 6px 0 0; }
</style>
