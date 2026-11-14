// Limits of chat attachments, as the API checks them
export const MAX_IMAGE_MB = 20;
export const MAX_VIDEO_MB = 50;
export const MAX_UPLOAD_BYTES = (MAX_VIDEO_MB + 5) * 1024 * 1024;
export const ACCEPTED_FILES = 'image/jpeg,image/png,image/webp,image/avif,video/mp4,video/quicktime,video/webm';
