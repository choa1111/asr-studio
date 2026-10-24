import type { AsrCandidate, AsrLanguage } from "../api/client";

export const ASR_LANGUAGES: AsrLanguage[] = ["auto", "zh", "en", "ja"];
export function isAsrLanguage(value: unknown): value is AsrLanguage {
  return ASR_LANGUAGES.includes(value as AsrLanguage);
}
export function supportedLanguages(candidate: AsrCandidate): string[] {
  // Older servers only guaranteed the original Chinese configuration.
  return candidate.supported_languages ?? ["zh"];
}
export function incompatibleCandidates(candidates: AsrCandidate[], language: AsrLanguage | null | undefined, primary: string, secondary = ""): AsrCandidate[] {
  if (!language) return [];
  return candidates.filter(candidate => (candidate.id === primary || candidate.id === secondary) && !supportedLanguages(candidate).includes(language));
}
export function languageOverride(language: AsrLanguage | null | undefined): { asr_language?: AsrLanguage } {
  // Omitting a rerun override preserves its original snapshot rather than today's Web default.
  return language ? { asr_language: language } : {};
}
