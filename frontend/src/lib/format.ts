export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png"];

/** Vietnamese number formatting with a decimal comma. */
export function fixed(value: number, digits = 2) { return value.toFixed(digits).replace(".", ","); }

/** Thousands separated with dots, as written in Vietnamese. */
export function count(value: number) { return Math.round(value).toLocaleString("vi-VN"); }

export function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${fixed(bytes / 1024 / 1024, 1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/** Return a Vietnamese error message, or an empty string when the file is acceptable. */
export function validate(file: File) {
  if (!ACCEPTED_TYPES.includes(file.type)) return "Chỉ hỗ trợ ảnh JPG, JPEG hoặc PNG.";
  if (file.size > MAX_UPLOAD_BYTES) return `Ảnh ${fileSize(file.size)} vượt quá giới hạn 10 MB. Hãy chọn ảnh nhỏ hơn.`;
  return "";
}
