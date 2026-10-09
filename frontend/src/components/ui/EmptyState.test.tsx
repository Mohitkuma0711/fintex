import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('exposes its message and action accessibly', () => {
    render(
      <EmptyState
        icon={<span>?</span>}
        title="No calculations yet"
        description="Confirm a profile to get started."
        action={<button type="button">Confirm profile</button>}
      />,
    )

    expect(screen.getByRole('region', { name: 'No calculations yet' })).toBeInTheDocument()
    expect(screen.getByText('Confirm a profile to get started.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm profile' })).toBeEnabled()
  })
})
