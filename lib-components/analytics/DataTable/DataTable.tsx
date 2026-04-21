import React, { useState } from 'react';
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  useReactTable,
  ColumnDef,
  SortingState
} from '@tanstack/react-table';
import { ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Card, CardContent } from '../../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../ui/table';

// Mocking shadcn/ui generic components for an Antigravity setup
/*
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
*/

// For the sake of this library folder, we substitute HTML with standard semantic classes. 
// In a real Antigravity implementation these map straight to shadcn/ui.

export interface DataTableProps<TData, TValue> {
  data: TData[];
  columns: ColumnDef<TData, TValue>[];
  paginationSize?: number;
  searchable?: boolean;
}

export function DataTable<TData, TValue>({ 
  data, 
  columns, 
  paginationSize = 10, 
  searchable = false 
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const { t } = useTranslation('common');

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize: paginationSize }
    }
  });

  return (
    <Card className="w-full overflow-hidden flex flex-col">
      {/* Header Actions (Search) */}
      {searchable && (
        <div className="p-3 border-b border-border flex justify-end">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
            <Input
              value={globalFilter ?? ''}
              onChange={e => setGlobalFilter(e.target.value)}
              placeholder={t('table.searchPlaceholder', 'Search all columns...')}
              className="h-9 pl-8 pr-3"
            />
          </div>
        </div>
      )}

      {/* Table Content */}
      <CardContent className="overflow-x-auto relative w-full p-0">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead 
                    key={header.id} 
                    className={`h-10 px-4 text-left align-middle font-medium text-muted-foreground ${header.column.getCanSort() ? 'cursor-pointer hover:text-foreground transition-colors select-none group' : ''}`}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        <span className="w-4 h-4 inline-flex items-center justify-center">
                          {{
                            asc: <ChevronUp className="w-4 h-4 text-primary" />,
                            desc: <ChevronDown className="w-4 h-4 text-primary" />
                          }[header.column.getIsSorted() as string] ?? null}
                        </span>
                      )}
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow 
                key={row.id} 
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
            
            {/* Empty State */}
            {table.getRowModel().rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center align-middle text-muted-foreground">
                  {t('table.noData', 'No data available.')}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
      
      {/* Pagination Controls */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-border mt-auto bg-muted/20">
        <div className="text-xs text-muted-foreground">
          {t('table.showing', {
            start: table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1,
            end: Math.min((table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize, data.length),
            total: data.length,
            defaultValue: `Showing ${table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} to ${Math.min((table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize, data.length)} of ${data.length} rows`
          })}
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            variant="outline"
            size="icon"
            aria-label={t('table.prevPage', 'Previous page')}
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <Button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            variant="outline"
            size="icon"
            aria-label={t('table.nextPage', 'Next page')}
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
