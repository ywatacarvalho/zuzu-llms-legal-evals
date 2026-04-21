import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ColumnDef } from '@tanstack/react-table';
import { DataTable } from './DataTable';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: string | Record<string, unknown>) => {
      if (typeof opts === 'string') return opts;
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) return String(opts.defaultValue);
      return key;
    },
  }),
}));

interface Row { name: string; score: number }

const columns: ColumnDef<Row, unknown>[] = [
  { accessorKey: 'name', header: 'Name', enableSorting: true },
  { accessorKey: 'score', header: 'Score', enableSorting: true },
];

const makeData = (count: number): Row[] =>
  Array.from({ length: count }, (_, i) => ({ name: `User ${i + 1}`, score: (i + 1) * 10 }));

describe('DataTable', () => {
  it('renders column headers', () => {
    render(<DataTable data={makeData(3)} columns={columns} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Score')).toBeInTheDocument();
  });

  it('renders all data rows', () => {
    render(<DataTable data={makeData(3)} columns={columns} />);
    expect(screen.getByText('User 1')).toBeInTheDocument();
    expect(screen.getByText('User 2')).toBeInTheDocument();
    expect(screen.getByText('User 3')).toBeInTheDocument();
  });

  it('shows empty state message when data is empty', () => {
    render(<DataTable data={[]} columns={columns} />);
    expect(screen.getByText('No data available.')).toBeInTheDocument();
  });

  it('renders search input when searchable=true', () => {
    render(<DataTable data={makeData(3)} columns={columns} searchable />);
    expect(screen.getByPlaceholderText('Search all columns...')).toBeInTheDocument();
  });

  it('does not render search input when searchable is omitted', () => {
    render(<DataTable data={makeData(3)} columns={columns} />);
    expect(screen.queryByPlaceholderText('Search all columns...')).not.toBeInTheDocument();
  });

  it('respects paginationSize — only first page rows visible', () => {
    render(<DataTable data={makeData(15)} columns={columns} paginationSize={5} />);
    expect(screen.getByText('User 1')).toBeInTheDocument();
    expect(screen.queryByText('User 6')).not.toBeInTheDocument();
  });

  it('next page button navigates to second page', async () => {
    render(<DataTable data={makeData(15)} columns={columns} paginationSize={5} />);
    const nextBtn = screen.getByRole('button', { name: 'Next page' });
    await userEvent.click(nextBtn);
    expect(screen.getByText('User 6')).toBeInTheDocument();
    expect(screen.queryByText('User 1')).not.toBeInTheDocument();
  });

  it('prev page button is disabled on the first page', () => {
    render(<DataTable data={makeData(15)} columns={columns} paginationSize={5} />);
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeDisabled();
  });

  it('next page button is disabled on the last page', async () => {
    render(<DataTable data={makeData(3)} columns={columns} paginationSize={5} />);
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled();
  });
});
