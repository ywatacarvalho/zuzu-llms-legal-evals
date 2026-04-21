import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ContentForm } from './ContentForm';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: string | Record<string, unknown>) => {
      if (typeof opts === 'string') return opts;
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) return String(opts.defaultValue);
      return key;
    },
  }),
}));

vi.mock('../MathContent', () => ({
  MathContent: ({ children }: { children: string }) => (
    <div data-testid="math-content">{children}</div>
  ),
}));

describe('ContentForm', () => {
  it('renders title and summary field labels', () => {
    render(<ContentForm onSubmit={vi.fn()} />);
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Summary')).toBeInTheDocument();
  });

  it('renders categories injected via prop', () => {
    render(
      <ContentForm
        onSubmit={vi.fn()}
        initial={{ category: '' }}
        categories={['Finance', 'Macro', 'Equity']}
      />
    );
    expect(screen.getByRole('option', { name: 'Finance' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Macro' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Equity' })).toBeInTheDocument();
  });

  it('renders only the blank option when categories is not provided', () => {
    render(<ContentForm onSubmit={vi.fn()} initial={{ category: '' }} />);
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveValue('');
  });

  it('calls onSubmit with form data when submitted', () => {
    const onSubmit = vi.fn();
    const { container } = render(<ContentForm onSubmit={onSubmit} />);
    fireEvent.submit(container.querySelector('form')!);
    expect(onSubmit).toHaveBeenCalledOnce();
  });

  it('includes updated title value in onSubmit payload', async () => {
    const onSubmit = vi.fn();
    const { container } = render(<ContentForm onSubmit={onSubmit} />);
    const titleInput = container.querySelector('input[type="text"]')!;
    await userEvent.type(titleInput, 'My Report');
    fireEvent.submit(container.querySelector('form')!);
    expect(onSubmit.mock.calls[0][0].title).toBe('My Report');
  });

  it('disables submit button and shows sending text when loading=true', () => {
    render(<ContentForm onSubmit={vi.fn()} loading />);
    const btn = screen.getByText('Sending...').closest('button')!;
    expect(btn).toBeDisabled();
  });

  it('pre-fills fields from initial prop', () => {
    render(
      <ContentForm
        onSubmit={vi.fn()}
        initial={{ title: 'Prefilled Title', summary: 'Prefilled Summary' }}
      />
    );
    expect(screen.getByDisplayValue('Prefilled Title')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Prefilled Summary')).toBeInTheDocument();
  });

  it('toggles preview mode when preview button is clicked', async () => {
    render(<ContentForm onSubmit={vi.fn()} />);
    expect(screen.queryByTestId('math-content')).not.toBeInTheDocument();
    await userEvent.click(screen.getByText('Preview'));
    expect(screen.getByTestId('math-content')).toBeInTheDocument();
  });
});
