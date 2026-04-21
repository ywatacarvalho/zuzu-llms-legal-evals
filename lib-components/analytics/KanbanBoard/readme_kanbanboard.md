# KanbanBoard Component

## Overview
A lightweight, dependency-free (other than Framer Motion) HTML5 drag-and-drop Kanban board layout perfectly tailored for the dark mode CRM/Lead Tracking interface.

## Props
- `columns` (Array of Strings): The names of the board columns. Default: `['New', 'In Progress', 'Done']`.
- `initialItems` (Array of Objects): The task items. Must contain `{ id, title, description, column, tag, date }`.
- `onItemMove` (Function): Callback fired when an item is dropped into a new column. Exposes the `movedItem` and the `targetColumn`.

## Usage
```jsx
<KanbanBoard 
  columns={['New', 'Contacted', 'Closed']}
  initialItems={[
    { id: '1', title: 'Lead: John Doe', description: 'Enterprise consulting', column: 'New', tag: 'Lead' }
  ]}
  onItemMove={(item, col) => console.log('Moved', item.title, 'to', col)}
/>
```
