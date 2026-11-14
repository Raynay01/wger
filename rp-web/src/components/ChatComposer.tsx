'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { ACCEPTED_FILES, MAX_IMAGE_MB, MAX_VIDEO_MB } from '@/lib/chat';
import { Button, inputClass } from './ui';

function describe(data: unknown): string {
  if (!data) {
    return '';
  }
  if (typeof data === 'string') {
    return data;
  }
  if (Array.isArray(data)) {
    return data.map(describe).filter(Boolean).join(' ');
  }
  if (typeof data === 'object') {
    return Object.values(data as Record<string, unknown>).map(describe).filter(Boolean).join(' ');
  }
  return String(data);
}

export function ChatComposer({ relationship, otherSide }: { relationship: string; otherSide: string }) {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(0);

  // Reloads the conversation only after the form was reset, not in the same render
  useEffect(() => {
    if (sent) {
      router.refresh();
    }
  }, [sent, router]);

  function pick(chosen: File | null) {
    setError('');
    if (chosen) {
      const limit = chosen.type.startsWith('video/') ? MAX_VIDEO_MB : MAX_IMAGE_MB;
      if (chosen.size > limit * 1024 * 1024) {
        setError(`O arquivo passa do limite de ${limit} MB.`);
        chosen = null;
        if (fileInput.current) {
          fileInput.current.value = '';
        }
      }
    }
    setFile(chosen);
  }

  async function send() {
    if (sending || (!text.trim() && !file)) {
      return;
    }
    const body = new FormData();
    body.set('relationship', relationship);
    body.set('text', text);
    if (file) {
      body.set('attachment', file);
    }
    setSending(true);
    setError('');
    try {
      const response = await fetch('/api/mensagens', { method: 'POST', body });
      if (!response.ok) {
        setError(describe(await response.json().catch(() => null)) || 'Não foi possível enviar. Tente de novo.');
        return;
      }
      setText('');
      pick(null);
      if (fileInput.current) {
        fileInput.current.value = '';
      }
      setSent(count => count + 1);
    } catch {
      setError('Sem conexão. Tente de novo.');
    } finally {
      setSending(false);
    }
  }

  return (
    <form
      className="flex flex-col gap-2 border-t border-navy-100 pt-3"
      onSubmit={event => {
        event.preventDefault();
        send();
      }}
    >
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {file && (
        <p className="flex items-center gap-2 text-sm text-navy-800">
          <span className="truncate">📎 {file.name}</span>
          <button type="button" className="text-red-700 underline" onClick={() => pick(null)}>
            remover
          </button>
        </p>
      )}
      <div className="flex items-end gap-2">
        <label className="cursor-pointer rounded-xl border border-navy-100 px-3 py-2 text-sm text-navy-700 hover:bg-navy-100" title="Anexar foto ou vídeo">
          📷<span className="sr-only">Anexar foto ou vídeo</span>
          <input
            ref={fileInput}
            type="file"
            name="attachment"
            accept={ACCEPTED_FILES}
            className="sr-only"
            onChange={event => pick(event.target.files?.[0] ?? null)}
          />
        </label>
        <textarea
          name="text"
          aria-label="Mensagem"
          rows={1}
          maxLength={4000}
          placeholder="Escreva uma mensagem"
          value={text}
          onChange={event => setText(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              send();
            }
          }}
          className={`${inputClass} min-h-10 flex-1 resize-y`}
        />
        <Button type="submit" variant="secondary" disabled={sending || (!text.trim() && !file)}>
          {sending ? 'Enviando…' : 'Enviar'}
        </Button>
      </div>
      <p className="text-xs text-gray-500">
        Fotos até {MAX_IMAGE_MB} MB e vídeos até {MAX_VIDEO_MB} MB. Só você e {otherSide} veem.
      </p>
    </form>
  );
}
