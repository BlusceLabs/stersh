/**
 * Shared DOM factory for grid cards (search, movies, tv).
 * Replaces three near-identical constructXxxCardElement functions
 * across movies.astro, tv.astro, and search.astro.
 *
 * Returns an <a> element styled to match the MediaGridCard.svelte
 * visual language. Uses DOM APIs (not innerHTML) for safety.
 */
export interface MediaCardData {
  id: number;
  title?: string;
  name?: string;
  poster_path: string | null;
  vote_average?: number;
  release_date?: string;
  first_air_date?: string;
  media_type?: 'movie' | 'tv' | string;
}

const SVG_NS = 'http://www.w3.org/2000/svg';

function makeSvgIcon(viewBox: string, path: string, classes: string): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', viewBox);
  svg.setAttribute('fill', 'currentColor');
  svg.setAttribute('class', classes);
  const p = document.createElementNS(SVG_NS, 'path');
  p.setAttribute('d', path);
  p.setAttribute('fill-rule', 'evenodd');
  p.setAttribute('clip-rule', 'evenodd');
  svg.appendChild(p);
  return svg;
}

function buildEmptyPoster(title: string): HTMLDivElement {
  const wrap = document.createElement('div');
  wrap.className = 'w-full h-full relative overflow-hidden';

  const bg = document.createElement('div');
  bg.className = 'absolute inset-0 bg-gradient-to-br from-surface-1 via-surface-2 to-surface-0';
  wrap.appendChild(bg);

  const orb1 = document.createElement('div');
  orb1.className = 'absolute -top-8 -right-8 w-32 h-32 rounded-full bg-brand-red/10 blur-2xl';
  wrap.appendChild(orb1);

  const orb2 = document.createElement('div');
  orb2.className = 'absolute -bottom-8 -left-8 w-32 h-32 rounded-full bg-brand-purple/10 blur-2xl';
  wrap.appendChild(orb2);

  const inner = document.createElement('div');
  inner.className = 'relative w-full h-full flex flex-col items-center justify-center text-ink-subtle gap-2 p-3';

  const icon = makeSvgIcon(
    '0 0 24 24',
    'M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5',
    'w-10 h-10 opacity-60',
  );
  inner.appendChild(icon);

  const label = document.createElement('span');
  label.className = 'text-[9px] font-bold tracking-[0.18em] uppercase opacity-60 text-center line-clamp-2 leading-tight';
  label.textContent = title;
  inner.appendChild(label);

  wrap.appendChild(inner);
  return wrap;
}

export function createMediaCardElement(item: MediaCardData): HTMLAnchorElement {
  const id = item.id;
  const explicitType: 'movie' | 'tv' =
    item.media_type === 'tv' || item.name ? 'tv' : 'movie';
  const title = item.title || item.name || 'Untitled Feature';
  const year = (item.release_date || item.first_air_date || '').split('-')[0] || '';
  const rating = item.vote_average || 0;
  const hasRating = rating > 0;
  const hasPoster = Boolean(item.poster_path);

  const anchor = document.createElement('a');
  anchor.href = `/${explicitType}/${id}`;
  anchor.className = 'group block focus:outline-none rounded-2xl';
  anchor.setAttribute('aria-label', `View details for ${title}`);

  const posterWrap = document.createElement('div');
  posterWrap.className =
    'relative aspect-[2/3] rounded-2xl overflow-hidden bg-surface-1 ' +
    'transition-all duration-500 ease-exo-out transform ' +
    'group-hover:-translate-y-1 group-hover:scale-[1.03] ' +
    'focus-visible:ring-2 focus-visible:ring-brand-red/50';

  if (hasPoster) {
    const img = document.createElement('img');
    img.src = `https://image.tmdb.org/t/p/w500${item.poster_path}`;
    img.alt = '';
    img.loading = 'lazy';
    img.decoding = 'async';
    img.className =
      'w-full h-full object-cover transition-transform duration-700 ease-exo-out ' +
      'group-hover:scale-[1.06] group-hover:brightness-110';
    posterWrap.appendChild(img);
  } else {
    posterWrap.appendChild(buildEmptyPoster(title));
  }

  if (hasRating) {
    const badge = document.createElement('div');
    badge.className =
      'absolute top-2 right-2 glass-strong text-accent-warm font-bold text-[11px] px-2 py-1 ' +
      'rounded-lg flex items-center gap-1 shadow-2';
    badge.setAttribute('aria-label', `Rating ${rating.toFixed(1)} out of 10`);

    const star = makeSvgIcon(
      '0 0 20 20',
      'M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.381c-.833.067-1.171 1.107-.536 1.651l3.6 3.1-.114 4.715c-.02.83.844 1.44 1.54 1.022l4.133-2.514 4.132 2.514c.695.418 1.56-.192 1.54-1.022l-.114-4.715 3.6-3.1c.635-.544.297-1.584-.536-1.65l-4.752-.382-1.831-4.401Z',
      'w-3 h-3',
    );
    badge.appendChild(star);

    const ratingText = document.createElement('span');
    ratingText.textContent = rating.toFixed(1);
    badge.appendChild(ratingText);

    posterWrap.appendChild(badge);
  }

  const gradient = document.createElement('div');
  gradient.className =
    'absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/70 via-black/20 to-transparent ' +
    'opacity-0 group-hover:opacity-100 transition-opacity duration-500 ease-exo-out pointer-events-none';
  gradient.setAttribute('aria-hidden', 'true');
  posterWrap.appendChild(gradient);

  anchor.appendChild(posterWrap);

  const meta = document.createElement('div');
  meta.className = 'mt-3 px-0.5';

  const h3 = document.createElement('h3');
  h3.className =
    'font-semibold text-ink-secondary group-hover:text-ink text-sm tracking-tight ' +
    'line-clamp-1 transition-colors duration-200';
  h3.textContent = title;
  meta.appendChild(h3);

  const metaRow = document.createElement('div');
  metaRow.className =
    'flex items-center gap-2 mt-1 text-[11px] font-medium text-ink-subtle ' +
    'group-hover:text-ink-muted transition-colors duration-200';

  if (year) {
    const yearSpan = document.createElement('span');
    yearSpan.textContent = year;
    metaRow.appendChild(yearSpan);

    const dot = document.createElement('span');
    dot.className = 'w-1 h-1 rounded-full bg-ink-faint';
    dot.setAttribute('aria-hidden', 'true');
    metaRow.appendChild(dot);
  }

  const badgeText = document.createElement('span');
  badgeText.className =
    'uppercase tracking-wider text-[10px] font-bold text-ink-faint ' +
    'group-hover:text-brand-red/80 transition-colors duration-200';
  badgeText.textContent = explicitType === 'tv' ? 'TV Series' : 'Movie';
  metaRow.appendChild(badgeText);

  meta.appendChild(metaRow);
  anchor.appendChild(meta);

  return anchor;
}
