const jsonHeaders = { "Content-Type": "application/json" };
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const MAX_WIRE_BYTES = 4.4 * 1024 * 1024;

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

async function gzipFile(file) {
  if (typeof CompressionStream === "undefined") return file;
  const stream = file.stream().pipeThrough(new CompressionStream("gzip"));
  return new Response(stream).blob();
}

export async function uploadCsv(file) {
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error("CSV is larger than 10 MB. Please use a smaller file.");
  }
  const body = await gzipFile(file);
  if (body.size > MAX_WIRE_BYTES && file.size > MAX_WIRE_BYTES) {
    throw new Error("CSV is larger than 10 MB. Please use a smaller file.");
  }
  const gzipped = body.size < file.size;
  const res = await fetch("/api/upload", {
    method: "POST",
    headers: {
      "Content-Type": gzipped ? "application/gzip" : "text/csv",
      "X-Filename": encodeURIComponent(file.name || "upload.csv"),
      "X-Original-Size": String(file.size),
    },
    body: gzipped ? body : file,
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export function loadSample() {
  return postJson("/api/sample", {});
}
