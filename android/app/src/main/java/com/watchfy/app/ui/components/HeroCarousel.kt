package com.watchfy.app.ui.components

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.watchfy.app.domain.model.Movie
import kotlinx.coroutines.*

@Composable
fun HeroCarousel(
    movies: List<Movie>,
    onClick: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val pagerState = rememberPagerState(
        pageCount = { movies.size.coerceAtLeast(1) }
    )

    LaunchedEffect(pagerState) {
        while (isActive) {
            delay(7000)
            val next = (pagerState.currentPage + 1) % movies.size.coerceAtLeast(1)
            pagerState.animateScrollToPage(next)
        }
    }

    Box(modifier = modifier.fillMaxWidth().height(450.dp)) {
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.fillMaxSize()
        ) { page ->
            val movie = movies.getOrNull(page) ?: return@HorizontalPager

            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .clickable { onClick(movie.id) }
            ) {
                AsyncImage(
                    model = "https://image.tmdb.org/t/p/original${movie.backdropPath ?: movie.posterPath}",
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )

                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(
                            Brush.verticalGradient(
                                colors = listOf(
                                    Color.Transparent,
                                    Color(0xFF09090B)
                                ),
                                startY = 200f
                            )
                        )
                )

                Column(
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .padding(24.dp)
                        .fillMaxWidth()
                ) {
                    Text(
                        text = movie.title,
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Black,
                        color = Color.White,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )

                    Spacer(modifier = Modifier.height(4.dp))

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "★ ${"%.1f".format(movie.voteAverage)}",
                            style = MaterialTheme.typography.labelMedium,
                            color = Color(0xFFEF4444),
                            fontWeight = FontWeight.Bold
                        )
                        if (movie.releaseDate != null) {
                            Text(
                                text = " • ${movie.releaseDate.take(4)}",
                                style = MaterialTheme.typography.labelMedium,
                                color = Color.Gray
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        text = movie.overview,
                        style = MaterialTheme.typography.bodySmall,
                        color = Color.LightGray,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        lineHeight = 18.sp
                    )
                }
            }
        }

        // Page indicators
        Row(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            repeat(movies.size.coerceAtMost(10)) { index ->
                Box(
                    modifier = Modifier
                        .size(width = if (index == pagerState.currentPage) 16.dp else 6.dp, height = 6.dp)
                        .clip(RoundedCornerShape(3.dp))
                        .background(
                            if (index == pagerState.currentPage) Color(0xFFEF4444)
                            else Color.Gray.copy(alpha = 0.4f)
                        )
                )
            }
        }
    }
}
