import { ref, watch } from "vue";
import { translations } from "./messages";

export type Locale = "zh-CN" | "en" | "ja";
export type MessageKey = keyof typeof translations;
export const LOCALE_STORAGE_KEY = "asr-studio:locale";
export const localeOptions = [
  { label: "简体中文", value: "zh-CN" },
  { label: "English", value: "en" },
  { label: "日本語", value: "ja" },
] as const;
export function isLocale(value: unknown): value is Locale {
  return value === "zh-CN" || value === "en" || value === "ja";
}
export function readStoredLocale(): Locale {
  try {
    const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
    return isLocale(stored) ? stored : "zh-CN";
  } catch { return "zh-CN"; }
}
function dictionary(index: 0 | 1 | null): Record<MessageKey, string> {
  return Object.fromEntries(Object.entries(translations).map(([key, values]) => [key, index === null ? key : values[index]])) as Record<MessageKey, string>;
}
export const messages: Record<Locale, Record<MessageKey, string>> = {
  "zh-CN": dictionary(null), en: dictionary(0), ja: dictionary(1),
};
export const locale = ref<Locale>(readStoredLocale());
export function t(key: MessageKey, params: Record<string, unknown> = {}): string {
  return messages[locale.value][key].replace(/\{(\w+)\}/g, (match, name: string) => String(params[name] ?? match));
}
export function setLocale(value: unknown) {
  if (isLocale(value)) locale.value = value;
}
watch(locale, value => {
  try { localStorage.setItem(LOCALE_STORAGE_KEY, value); } catch { /* Private browsing can deny storage; switching still works. */ }
  if (typeof document !== "undefined") {
    document.documentElement.lang = value;
    document.title = `ASR Studio · ${t("语音转文字")}`;
  }
}, { immediate: true, flush: "sync" });

const stateKeys: Record<string, MessageKey> = {
  pending: "等待中", running: "运行中", success: "成功", failed: "失败", partial: "部分完成",
  completed: "已完成", active: "运行中", done: "已完成", job: "单任务", batch: "批量任务", "stage-run": "单阶段",
  "extract-audio": "音频提取", transcribe: "语音转写", "prepare-reference": "准备参考", align: "文本对齐", classify: "段落分类", refine: "校对润色", "export-markdown": "导出文档",
  "prepare-job": "准备任务", "staggered-pipeline": "交错流水线处理", ocr: "OCR 识别结果", "pdf-ocr": "PDF OCR 任务",
  reference: "参考材料校对", conversation: "对谈转录", auto: "自动检测", zh: "中文", en: "英语", ja: "日语",
  manifest: "Manifest 清单", "paired-dir": "目录自动配对", "shared-reference": "目录共享参考", "conversation-dir": "对谈录屏目录",
};
// Only known UI metadata is localized. File content, IDs, paths and unknown server details remain intact.
export function labelFor(value: unknown): string {
  const text = String(value ?? "");
  const key = stateKeys[text] ?? (Object.prototype.hasOwnProperty.call(translations, text) ? text as MessageKey : undefined);
  return key ? t(key) : text;
}
export function formatDate(value: unknown): string {
  const raw = String(value ?? "");
  if (!raw) return "-";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return new Intl.DateTimeFormat(locale.value, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
}
export function slotLabel(key: string, fallback: string): string {
  const keys: Record<string, MessageKey> = { video: "视频文件", audio: "音频文件", asr: "ASR 转录文本", asr_text: "ASR 转录文本", asr_txt: "ASR 转录文本", asr_json: "转录 JSON", reference_txt: "参考 TXT", aligned_json: "对齐 JSON", refined_json: "校对 JSON", reference: "参考文本", reference_text: "参考文本", aligned: "对齐结果", classified: "分类结果", refined: "精修结果" };
  return keys[key] ? t(keys[key]) : labelFor(fallback);
}
