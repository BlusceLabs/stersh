package com.watchfy.app.ui.screens.browse

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.watchfy.app.ui.components.HeroCarousel
import com.watchfy.app.ui.components.MediaRow
import com.watchfy.app.ui.components.MovieCard

@Composable
fun BrowseScreen(
    onMovieClick: (Int) -> Unit,
    onTvClick: (Int) -> Unit,
    viewModel: BrowseViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()

    when {
        state.loading -> {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = androidx.compose.ui.Alignment.Center) {
                CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
            }
        }
        state.error != null -> {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = androidx.compose.ui.Alignment.Center) {
                Text(
                    text = state.error ?: "Error",
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
        else -> {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(bottom = 16.dp)
            ) {
                item {
                    HeroCarousel(
                        movies = state.trending,
                        onClick = onMovieClick
                    )
                }

                if (state.continueWatching.isNotEmpty()) {
                    item { Spacer(modifier = Modifier.height(8.dp)) }
                    item {
                        Text(
                            text = "Continue Watching",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                        )
                    }
                    item {
                        androidx.compose.foundation.lazy.LazyRow(
                            contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 16.dp),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(state.continueWatching) { item ->
                                // Simplified continue watching card
                                Column(modifier = Modifier.width(150.dp)) {
                                    Box(
                                        modifier = Modifier
                                            .width(150.dp)
                                            .height(225.dp)
                                    ) {
                                        coil.compose.AsyncImage(
                                            model = "https://image.tmdb.org/t/p/w342${item.posterPath}",
                                            contentDescription = null,
                                            contentScale = androidx.compose.ui.layout.ContentScale.Cover,
                                            modifier = Modifier.fillMaxSize()
                                        )
                                    }
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = item.title,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurface,
                                        maxLines = 1
                                    )
                                }
                            }
                        }
                    }
                }

                item { Spacer(modifier = Modifier.height(8.dp)) }

                item {
                    MediaRow(
                        title = "Popular Movies",
                        movies = state.popular,
                        onClick = onMovieClick
                    )
                }

                item { Spacer(modifier = Modifier.height(8.dp)) }

                item {
                    MediaRow(
                        title = "Top Rated",
                        movies = state.topRated,
                        onClick = onMovieClick
                    )
                }
            }
        }
    }
}
