import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { MoreHorizontal, GripVertical } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface KanbanItem {
  id: string | number;
  column: string;
  title: string;
  description?: string;
  tag?: string;
  date?: string;
}

export interface KanbanBoardProps {
  columns?: string[];
  initialItems?: KanbanItem[];
  onItemMove?: (item: KanbanItem | undefined, targetColumn: string) => void;
}

export function KanbanBoard({ 
  columns = ['New', 'In Progress', 'Done'], 
  initialItems = [], 
  onItemMove 
}: KanbanBoardProps) {
  const [items, setItems] = useState<KanbanItem[]>(initialItems);
  const [draggedItemId, setDraggedItemId] = useState<string | number | null>(null);
  const { t } = useTranslation('common');

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, id: string | number) => {
    setDraggedItemId(id);
    e.dataTransfer.effectAllowed = 'move';
    // Requires a small delay for the drag ghost to render before adding styling
    setTimeout(() => {
      (e.target as HTMLElement).style.opacity = '0.5';
    }, 0);
  };

  const handleDragEnd = (e: React.DragEvent<HTMLDivElement>) => {
    (e.target as HTMLElement).style.opacity = '1';
    setDraggedItemId(null);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>, targetColumn: string) => {
    e.preventDefault();
    if (!draggedItemId) return;

    setItems((prev) => {
      const newItems = prev.map(item => 
        item.id === draggedItemId ? { ...item, column: targetColumn } : item
      );
      
      const movedItem = newItems.find(i => i.id === draggedItemId);
      if (onItemMove) onItemMove(movedItem, targetColumn);
      
      return newItems;
    });
  };

  return (
    <div className="flex flex-row gap-6 h-full min-h-[500px] overflow-x-auto pb-4 scrollbar-hide">
      {columns.map(col => (
        <div 
          key={col} 
          className="flex-shrink-0 w-80 flex flex-col bg-muted/20 rounded-2xl border border-border overflow-hidden"
          onDragOver={handleDragOver}
          onDrop={(e) => handleDrop(e, col)}
        >
          {/* Column Header */}
          <div className="px-4 py-4 border-b border-border flex items-center justify-between bg-card text-card-foreground shadow-sm">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold tracking-tight">{t(`kanban.column.${col}`, col)}</h3>
              <span className="bg-secondary text-secondary-foreground text-xs px-2 py-0.5 rounded-full font-medium">
                {items.filter(i => i.column === col).length}
              </span>
            </div>
            <button className="text-muted-foreground hover:text-foreground transition-colors" aria-label={t('kanban.moreOptions', 'More Options')}>
              <MoreHorizontal className="w-4 h-4" />
            </button>
          </div>

          {/* Droppable Area */}
          <div className="flex-1 p-3 flex flex-col gap-3 overflow-y-auto min-h-[150px]">
            {items
              .filter(item => item.column === col)
              .map(item => (
                <motion.div
                  layoutId={`kanban-item-${item.id}`}
                  key={item.id}
                  draggable
                  onDragStart={(e: unknown) => handleDragStart(e as React.DragEvent<HTMLDivElement>, item.id)}
                  onDragEnd={(e: unknown) => handleDragEnd(e as React.DragEvent<HTMLDivElement>)}
                  className="bg-card text-card-foreground border border-border hover:border-primary/50 shadow-sm p-4 rounded-xl cursor-grab active:cursor-grabbing transition-colors group relative"
                >
                  <div className="absolute left-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <GripVertical className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div className="pl-4">
                    <h4 className="text-sm font-medium">{item.title}</h4>
                    {item.description && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{item.description}</p>
                    )}
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-[10px] font-semibold tracking-wider uppercase text-primary bg-primary/10 px-2 py-1 rounded-md">
                        {item.tag ? t(`kanban.tag.${item.tag}`, item.tag) : t('kanban.defaultTag', 'Task')}
                      </span>
                      {item.date && (
                        <span className="text-xs text-muted-foreground">{item.date}</span>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
