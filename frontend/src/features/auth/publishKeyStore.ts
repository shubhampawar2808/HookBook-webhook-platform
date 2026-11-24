/** In-memory publish API key (never persisted to sessionStorage/localStorage). */

let publishApiKey: string | null = null;

export function setPublishApiKey(key: string | null): void {
  publishApiKey = key && key.startsWith("hfk_") ? key : null;
}

export function getPublishApiKey(): string | null {
  return publishApiKey;
}

export function clearPublishApiKey(): void {
  publishApiKey = null;
}
