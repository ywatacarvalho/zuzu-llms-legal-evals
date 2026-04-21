import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from './badge';

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('merges custom className', () => {
    render(<Badge className="extra-class">Tag</Badge>);
    expect(screen.getByText('Tag')).toHaveClass('extra-class');
  });

  it('renders multiple badges independently', () => {
    render(
      <>
        <Badge>Alpha</Badge>
        <Badge>Beta</Badge>
      </>
    );
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
  });
});
