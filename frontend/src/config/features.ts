/**
 * Feature availability. Flip a flag when the backend supports the capability;
 * UI that depends on a disabled flag renders an explicit "unavailable" state
 * instead of a button that pretends to work.
 */
export const featureFlags = {
  excelPreview: false, // Excel files are parsed by the backend, not in the browser
  xlsxExport: false,
  pdfExport: false,
  deleteAccount: false,
  changePassword: false,
  avatarUpload: false,
} as const;

export type FeatureFlag = keyof typeof featureFlags;
