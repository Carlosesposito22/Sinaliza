export interface PoseSequence {
  fps: number;
  layout: Record<string, [number, number]>;
  frames: number[][][];
}

export interface TranslateResponse {
  text: string;
  glosses: string[];
  pose: PoseSequence;
}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function translate(text: string): Promise<TranslateResponse> {
  const response = await fetch(`${API_URL}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    throw new Error(`A API respondeu ${response.status}`);
  }
  return response.json();
}
