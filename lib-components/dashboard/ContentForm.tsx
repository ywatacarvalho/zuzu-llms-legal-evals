import React, { useState, FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { MathContent } from '../MathContent';
import { Eye, Code } from 'lucide-react';

export interface ContentFormData {
  title: string;
  summary: string;
  content: string;
  category?: string;
  pdf_url?: string;
  tags?: string;
  author?: string;
  is_published: boolean;
  [key: string]: any;
}

export interface ContentFormProps {
  initial?: Partial<ContentFormData>;
  onSubmit: (data: ContentFormData) => void;
  loading?: boolean;
  categories?: string[];
}

const INPUT_CLS = 'bg-muted/10 border border-input p-3 rounded-xl outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors text-foreground placeholder-muted-foreground w-full text-sm';
const LABEL_CLS = 'text-xs uppercase tracking-widest text-muted-foreground mb-1 block';

export function ContentForm({ initial = {}, onSubmit, loading = false, categories }: ContentFormProps) {
  const { t } = useTranslation('common');
  const [form, setForm] = useState<ContentFormData>({
    title: initial.title ?? '',
    summary: initial.summary ?? '',
    content: initial.content ?? '',
    category: initial.category ?? '',
    pdf_url: initial.pdf_url ?? '',
    tags: initial.tags ?? '',
    author: initial.author ?? '',
    is_published: initial.is_published ?? false,
    ...initial,
  });
  
  const [preview, setPreview] = useState(false);

  const set = (k: keyof ContentFormData, v: any) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  const isReport = 'category' in initial || (!('tags' in initial) && !('author' in initial));

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className={LABEL_CLS}>{t('reports_mgr.field_title', 'Title')}</label>
        <input 
          type="text" 
          value={form.title} 
          onChange={e => set('title', e.target.value)}
          required 
          className={INPUT_CLS} 
        />
      </div>

      <div>
        <label className={LABEL_CLS}>{t('reports_mgr.field_summary', 'Summary')}</label>
        <textarea 
          rows={2} 
          value={form.summary} 
          onChange={e => set('summary', e.target.value)}
          className={INPUT_CLS} 
        />
      </div>

      {isReport ? (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={LABEL_CLS}>{t('reports_mgr.field_category', 'Category')}</label>
            <select 
              value={form.category} 
              onChange={e => set('category', e.target.value)}
              className={INPUT_CLS + ' cursor-pointer'}
            >
              {['', ...(categories ?? [])].map(c => (
                <option key={c} value={c}>{c || '—'}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={LABEL_CLS}>{t('reports_mgr.field_pdf_url', 'PDF URL')}</label>
            <input 
              type="url" 
              value={form.pdf_url} 
              onChange={e => set('pdf_url', e.target.value)}
              className={INPUT_CLS} 
            />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={LABEL_CLS}>{t('reports_mgr.field_author', 'Author')}</label>
            <input 
              type="text" 
              value={form.author} 
              onChange={e => set('author', e.target.value)}
              className={INPUT_CLS} 
            />
          </div>
          <div>
            <label className={LABEL_CLS}>{t('reports_mgr.field_tags', 'Tags')}</label>
            <input 
              type="text" 
              value={form.tags} 
              onChange={e => set('tags', e.target.value)}
              placeholder="Tag1,Tag2" 
              className={INPUT_CLS} 
            />
          </div>
        </div>
      )}

      {/* Content editor with preview toggle */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className={LABEL_CLS}>{t('reports_mgr.field_content', 'Content')}</label>
          <button 
            type="button" 
            onClick={() => setPreview(p => !p)}
            className="flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 transition-colors"
          >
            {preview ? <><Code className="w-3.5 h-3.5" /> Markdown</> : <><Eye className="w-3.5 h-3.5" /> Preview</>}
          </button>
        </div>
        {preview ? (
          <div className="min-h-[240px] bg-muted/10 border border-border rounded-xl p-4 overflow-auto">
            <MathContent>{form.content}</MathContent>
          </div>
        ) : (
          <textarea 
            rows={12} 
            value={form.content} 
            onChange={e => set('content', e.target.value)}
            required 
            className={INPUT_CLS + ' font-mono text-xs leading-relaxed'} 
          />
        )}
      </div>

      {/* Published toggle */}
      <label className="flex items-center gap-3 cursor-pointer mt-4">
        <input 
          type="checkbox" 
          checked={form.is_published} 
          onChange={e => set('is_published', e.target.checked)}
          className="accent-primary w-4 h-4 rounded border-border text-primary focus:ring-primary" 
        />
        <span className="text-sm text-foreground">{t('reports_mgr.publish', 'Publish this content')}</span>
      </label>

      <button 
        type="submit" 
        disabled={loading}
        className="mt-6 flex items-center justify-center gap-2 bg-primary text-primary-foreground font-semibold py-3 px-8 rounded-xl hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? t('contact.sending', 'Sending...') : t('reports_mgr.save', 'Save Changes')}
      </button>
    </form>
  );
}
