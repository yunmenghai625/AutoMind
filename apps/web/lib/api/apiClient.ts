/**
 * Central API client.
 * - mock mode: resolves from lib/mock, no network, small latency simulated
 * - live mode: fetch() against NEXT_PUBLIC_API_BASE_URL, JSON or FormData
 *
 * Components never call fetch() directly — always via a service in lib/api.
 */

import { API_BASE_URL, API_MODE } from "@/lib/config";
import { delay } from "@/lib/utils";
import type { ApiError } from "@/types/api";

export class HttpClientError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
  toApiError(): ApiError {
    return { status: this.status, code: this.code, message: this.message };
  }
}

export interface FetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  body?: unknown;
  headers?: Record<string, string>;
}

export async function http<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  if (API_MODE === "mock") {
    throw new HttpClientError(
      400,
      "MOCK_CALL",
      "模拟模式下不能直接调用网络接口，请使用模拟数据服务。",
    );
  }

  const { method = "GET", body, headers = {} } = opts;
  const isFormData = body instanceof FormData;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: isFormData
        ? headers
        : {
            "Content-Type": "application/json",
            ...headers,
          },
      body:
        body === undefined
          ? undefined
          : isFormData
            ? body
            : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new HttpClientError(0, "NETWORK", "无法连接 AutoMind API。");
  }

  if (!res.ok) {
    let message = `请求失败，状态码：${res.status}`;
    let code = "HTTP_ERROR";
    try {
      const data = (await res.json()) as {
        detail?: string;
        code?: string;
        error?: { code?: string; message?: string };
      };
      if (data.detail) message = data.detail;
      if (data.code) code = data.code;
      if (data.error?.message) message = data.error.message;
      if (data.error?.code) code = data.error.code;
    } catch {
      // ignore
    }
    throw new HttpClientError(res.status, code, message);
  }
  return (await res.json()) as T;
}

/**
 * Wrapper used by mock providers to simulate network latency + a shallow
 * failure surface (offline simulation).
 */
export async function simulate<T>(fn: () => T, latency = 300): Promise<T> {
  await delay(latency);
  return fn();
}
