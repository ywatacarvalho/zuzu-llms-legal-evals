# DataTable Component

## Overview
The `DataTable` is a powerful, highly customizable table wrapper around `@tanstack/react-table`. It supports out-of-the-box sorting, pagination, and global searching while matching the sleek dark-mode glassmorphic aesthetic of the analytics dashboard.

## Props
- `data` (Array of Objects): The row data to feed into the table.
- `columns` (Array of Objects): The column definitions created using Tanstack's `createColumnHelper` or raw objects.
- `paginationSize` (number) _optional_: The number of rows per page. Default is `10`.
- `searchable` (boolean) _optional_: Whether to display the global search input at the top right. Default is `false`.

## Features
1. **Performance**: Handles large arrays effortlessly by paginating.
2. **Global Filtering**: Simply pass `searchable={true}` and a search box will permit fuzzy text searching across all columns.
3. **Sorting**: Columns that are defined as sortable get smooth arrow indicators.

## Usage
```jsx
import { createColumnHelper } from '@tanstack/react-table';
import { DataTable } from './components/analytics/DataTable/DataTable';

const data = [
  { segment: 'Bank Credit', portfolio: 'Real Estate', exposure: 120500 },
  { segment: 'Trade Credit', portfolio: 'Automotive', exposure: 75200 },
];

const columnHelper = createColumnHelper();

const columns = [
  columnHelper.accessor('segment', {
    header: 'Segment',
    cell: info => <span className="font-medium text-white">{info.getValue()}</span>,
  }),
  columnHelper.accessor('portfolio', { header: 'Portfolio' }),
  columnHelper.accessor('exposure', { 
    header: 'Exposure ($)',
    cell: info => info.getValue().toLocaleString() 
  }),
];

function PortfolioTable() {
  return <DataTable data={data} columns={columns} searchable={true} paginationSize={5} />;
}
```
