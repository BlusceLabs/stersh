import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import MovieCard from '$components/MovieCard.svelte';

describe('MovieCard', () => {
  const mockMovie = {
    id: 123,
    title: 'Inception',
    poster_path: '/inception.jpg',
    vote_average: 8.8,
    release_date: '2010-07-16',
    overview: 'A thief who steals corporate secrets.',
  };

  it('renders movie title', () => {
    render(MovieCard, { props: { movie: mockMovie } });
    expect(screen.getByText('Inception')).toBeInTheDocument();
  });

  it('renders vote average', () => {
    render(MovieCard, { props: { movie: mockMovie } });
    expect(screen.getByText(/8\.8/)).toBeInTheDocument();
  });

  it('renders release year', () => {
    render(MovieCard, { props: { movie: mockMovie } });
    expect(screen.getByText(/2010/)).toBeInTheDocument();
  });

  it('links to the correct movie page', () => {
    render(MovieCard, { props: { movie: mockMovie } });
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/movie/123');
  });
});
