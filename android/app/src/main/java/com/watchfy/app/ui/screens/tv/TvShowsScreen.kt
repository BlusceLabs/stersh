package com.watchfy.app.ui.screens.tv

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.watchfy.app.ui.components.MovieCard
import com.watchfy.app.domain.model.TvShow

@Composable
fun TvShowsScreen(
    onTvClick: (Int) -> Unit,
    viewModel: TvShowsViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    var sortExpanded by remember { mutableStateOf(false) }
    val sorts = listOf("popular" to "Popular", "top_rated" to "Top Rated", "airing_today" to "Airing Today", "on_the_air" to "On The Air")

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("TV Shows", style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onSurface)
            Box {
                TextButton(onClick = { sortExpanded = true }) {
                    Text(sorts.find { it.first == state.sort }?.second ?: "Sort")
                }
                DropdownMenu(expanded = sortExpanded, onDismissRequest = { sortExpanded = false }) {
                    sorts.forEach { (key, label) ->
                        DropdownMenuItem(text = { Text(label) }, onClick = { viewModel.setSort(key); sortExpanded = false })
                    }
                }
            }
        }

        when {
            state.loading -> Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
            }
            state.error != null -> Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(state.error ?: "Error", color = MaterialTheme.colorScheme.error)
            }
            else -> {
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(150.dp),
                    contentPadding = PaddingValues(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(state.shows, key = { it.id }) { show ->
                        MovieCard(
                            movie = MovieAdapter.fromTvShow(show),
                            onClick = { onTvClick(show.id) }
                        )
                    }
                }
            }
        }
    }
}

private object MovieAdapter {
    fun fromTvShow(show: TvShow) = com.watchfy.app.domain.model.Movie(
        id = show.id, title = show.name, overview = show.overview,
        posterPath = show.posterPath, backdropPath = show.backdropPath,
        voteAverage = show.voteAverage, releaseDate = show.firstAirDate,
        genreIds = show.genreIds
    )
}
