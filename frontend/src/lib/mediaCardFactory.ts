/**
 * Shared DOM factory for grid cards (search, movies, tv).
 * YouTube-style: 16:9 thumbnail (backdrop), title, channel, views, time.
 *
 * Returns an <a> element styled to match the MediaGridCard.svelte
 * visual language. Uses DOM APIs (not innerHTML) for safety.
 */
export interface MediaCardData {
  id: number;
  title?: string;
  name?: string;
  poster_path: string | null;
  backdrop_path?: string | null;
  vote_average?: number;
  vote_count?: number;
  release_date?: string;
  first_air_date?: string;
  media_type?: 'movie' | 'tv' | string;
  production_companies?: { name: string }[];
  credits?: { crew?: { job: string; name: string }[] };
  popularity?: number;
}

const SVG_NS = 'http://www.w3.org/2000/svg';

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, attrs?: Record<string, string>): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (attrs) for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

function formatViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M views`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K views`;
  if (n > 0) return `${n} views`;
  return '';
}

export function createMediaCardElement(item: MediaCardData): HTMLAnchorElement {
  const id = item.id;
  const explicitType: 'movie' | 'tv' =
    item.media_type === 'tv' || item.name ? 'tv' : 'movie';
  const title = item.title || item.name || 'Untitled';
  const thumb = item.backdrop_path || item.poster_path;
  const year = (item.release_date || item.first_air_date || '').split('-')[0] || '';
  const voteCount = item.vote_count || (item.popularity ? Math.round(item.popularity * 100) : 0);
  const channelName =
    item?.production_companies?.[0]?.name ||
    item?.credits?.crew?.find((c) => c.job === 'Director')?.name ||
    (explicitType === 'tv' ? 'Series' : 'Movie');

  const anchor = el('a', 'group block focus:outline-none');
  anchor.href = `/${explicitType}/${id}`;
  anchor.setAttribute('aria-label', `View ${title}`);

  // 16:9 Thumbnail
  const thumbWrap = el('div', 'relative w-full aspect-video rounded-xl overflow-hidden bg-base-2');
  if (thumb) {
    const img = el('img', 'w-full h-full object-cover transition-transform duration-300 group-hover:scale-105');
    img.src = `https://image.tmdb.org/t/p/w780${thumb}`;
    img.srcset = `https://image.tmdb.org/t/p/w342${thumb} 342w, https://image.tmdb.org/t/p/w780${thumb} 780w`;
    img.sizes = '(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw';
    img.alt = title;
    img.loading = 'lazy';
    img.decoding = 'async';
    thumbWrap.appendChild(img);
  } else {
    const empty = el('div', 'w-full h-full flex items-center justify-center bg-base-2 text-ink-muted');
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('class', 'w-12 h-12');
    svg.setAttribute('fill', 'currentColor');
    const p = document.createElementNS(SVG_NS, 'path');
    p.setAttribute('d', 'M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V4h-4z');
    svg.appendChild(p);
    empty.appendChild(svg);
    thumbWrap.appendChild(empty);
  }
  anchor.appendChild(thumbWrap);

  // Meta row
  const metaRow = el('div', 'flex gap-3 mt-3');

  // Channel avatar
  const avatar = el('div', 'flex-shrink-0 w-9 h-9 rounded-full bg-base-3 overflow-hidden flex items-center justify-center text-sm font-medium text-ink');
  avatar.textContent = channelName.charAt(0).toUpperCase();
  metaRow.appendChild(avatar);

  // Text column
  const col = el('div', 'flex-1 min-w-0');

  const h3 = el('h3', 'text-base font-medium text-ink leading-snug line-clamp-2');
  h3.textContent = title;
  col.appendChild(h3);

  const channelDiv = el('div', 'mt-1 text-sm text-ink-secondary hover:text-ink transition-colors duration-100 truncate');
  channelDiv.textContent = channelName;
  col.appendChild(channelDiv);

  const statsDiv = el('div', 'flex items-center gap-1 text-sm text-ink-secondary');
  const viewsLabel = formatViews(voteCount);
  if (viewsLabel) {
    const v = document.createElement('span');
    v.textContent = viewsLabel;
    statsDiv.appendChild(v);
    const dot = el('span', 'text-ink-muted');
    dot.textContent = '·';
    statsDiv.appendChild(dot);
  }
  if (year) {
    const y = document.createElement('span');
    y.textContent = year;
    statsDiv.appendChild(y);
  }
  if (!viewsLabel && item.vote_average) {
    const dot = el('span', 'text-ink-muted');
    dot.textContent = '·';
    statsDiv.appendChild(dot);
    const r = el('span', 'text-ink-muted');
    r.textContent = `★ ${item.vote_average.toFixed(1)}`;
    statsDiv.appendChild(r);
  }
  col.appendChild(statsDiv);

  metaRow.appendChild(col);
  anchor.appendChild(metaRow);

  return anchor;
}
