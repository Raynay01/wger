import 'server-only';
import { connection } from 'next/server';

export type LegalInfo = {
  /** Company that controls the data (LGPD "controlador") */
  name: string;
  /** CNPJ of the company */
  document: string;
  /** E-mail for privacy requests (the "encarregado") */
  contact: string;
  /** City of the court for the terms of use */
  court: string;
  /** Until the lawyer approves the texts they show as a draft */
  draft: boolean;
};

const MISSING = '[a definir]';

/**
 * The company details of the legal pages, from the server's configuration at
 * request time (the same image serves staging and production)
 */
export async function legalInfo(): Promise<LegalInfo> {
  await connection();
  return {
    name: process.env.ALMOVA_LEGAL_NAME?.trim() || MISSING,
    document: process.env.ALMOVA_LEGAL_DOCUMENT?.trim() || MISSING,
    contact: process.env.ALMOVA_PRIVACY_EMAIL?.trim() || MISSING,
    court: process.env.ALMOVA_LEGAL_COURT?.trim() || MISSING,
    draft: process.env.ALMOVA_LEGAL_APPROVED !== '1',
  };
}
