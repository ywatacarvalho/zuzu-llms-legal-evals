import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';

export interface FileUploadZoneProps {
  onFileSelect?: (file: File | null) => void;
  accept?: string;
  maxSizeMB?: number;
  titleKey?: string;
  titleFallback?: string;
  subtitleKey?: string;
  subtitleFallback?: string;
}

export function FileUploadZone({ 
  onFileSelect, 
  accept = "*",
  maxSizeMB = 50,
  titleKey,
  titleFallback = "Upload Data File",
  subtitleKey,
  subtitleFallback = "Drag and drop your dataset here, or click to browse"
}: FileUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { t } = useTranslation('common');

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragging(true);
    } else if (e.type === "dragleave") {
      setIsDragging(false);
    }
  };

  const validateAndProcessFile = (selectedFile: File) => {
    if (!selectedFile) return;
    
    // Check extension
    const ext = `.${selectedFile.name.split('.').pop()?.toLowerCase()}`;
    if (accept && !accept.split(',').includes(ext)) {
      setError(t('upload.invalidType', { accept, defaultValue: `Invalid file type. Accepted: ${accept}` }));
      return;
    }

    // Check size
    if (selectedFile.size > maxSizeMB * 1024 * 1024) {
      setError(t('upload.exceedsSize', { size: maxSizeMB, defaultValue: `File exceeds maximum size of ${maxSizeMB}MB` }));
      return;
    }

    setError('');
    setFile(selectedFile);
    if (onFileSelect) onFileSelect(selectedFile);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndProcessFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndProcessFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full">
      <AnimatePresence mode="wait">
        {!file ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onClick={() => fileInputRef.current?.click()}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`
              relative cursor-pointer w-full p-8 rounded-2xl border-2 border-dashed 
              transition-all duration-300 flex flex-col items-center justify-center gap-4
              ${isDragging 
                ? 'border-primary bg-primary/10 shadow-sm' 
                : 'border-border bg-muted/20 hover:border-border/80 hover:bg-muted/40'
              }
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept={accept}
              onChange={handleChange}
            />
            
            <div className={`p-4 rounded-full ${isDragging ? 'bg-primary/20' : 'bg-muted'} transition-colors`}>
              <UploadCloud className={`w-8 h-8 ${isDragging ? 'text-primary' : 'text-muted-foreground'}`} />
            </div>
            
            <div className="text-center">
              <h4 className="text-foreground font-medium text-lg">
                {titleKey ? t(titleKey, titleFallback) : titleFallback}
              </h4>
              <p className="text-muted-foreground text-sm mt-1">
                {subtitleKey ? t(subtitleKey, subtitleFallback) : subtitleFallback}
              </p>
            </div>
            
            {error && (
              <p className="text-destructive text-sm font-medium bg-destructive/10 py-1 px-3 rounded-full">
                {error}
              </p>
            )}
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full p-6 rounded-2xl border border-secondary bg-secondary/10 flex items-center justify-between"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 bg-secondary/20 rounded-full">
                <CheckCircle className="w-6 h-6 text-secondary-foreground" />
              </div>
              <div>
                <p className="text-foreground font-medium">{file.name}</p>
                <p className="text-muted-foreground text-sm">{(file.size / (1024 * 1024)).toFixed(2)} MB • {t('upload.ready', 'Ready to process')}</p>
              </div>
            </div>
            <button 
              onClick={(e) => { e.stopPropagation(); setFile(null); setError(''); if(onFileSelect) onFileSelect(null); }}
              className="p-2 hover:bg-muted rounded-full transition-colors focus:outline-none"
              aria-label={t('upload.remove', 'Remove file')}
            >
              <X className="w-5 h-5 text-muted-foreground hover:text-foreground" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
