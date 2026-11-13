import { Notice } from './ui';

export function ErrorFromQuery({ erro }: { erro?: string }) {
  return erro ? <Notice tone="error">{erro}</Notice> : null;
}
