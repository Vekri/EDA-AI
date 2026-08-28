const jsonHeaders = { "Content-Type": "application/json" };
const MAX_UPLOAD_BYTES = 4 * 1024 * 1024;

async function readError(res) {
  try {
    const data = await res.json();
    const detail = data.detail ?? data.message;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || item.message || JSON.stringify(item)).join("; ");
    }
    if (detail && typeof detail === "object") return JSON.stringify(detail);
    return res.statusText;
  } catch {
    return res.statusText || "Request failed";
  }
}

export async function postJson(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function uploadCsv(file) {
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error("CSV is larger than 4 MB. Please use a smaller file.");
  }
  const res = await fetch("/api/upload", {
    method: "POST",
    headers: {
      "Content-Type": "text/csv",
      "X-Filename": encodeURIComponent(file.name || "upload.csv"),
    },
    body: file,
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export function loadSample() {
  return postJson("/api/sample", {});
}
