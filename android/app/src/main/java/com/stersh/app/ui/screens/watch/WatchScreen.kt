package com.stersh.app.ui.screens.watch

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.stersh.app.ui.player.ExoPlayerView

@Composable
fun WatchScreen(
    mediaType: String,
    tmdbId: Int,
    season: Int,
    episode: Int,
    onNavigateToEpisode: (Int, Int) -> Unit,
    onBack: () -> Unit,
    viewModel: WatchViewModel = hiltViewModel()
) {
    LaunchedEffect(mediaType, tmdbId, season, episode) {
        viewModel.load(mediaType, tmdbId, season, episode)
    }

    val state by viewModel.state.collectAsState()

    Column(modifier = Modifier.fillMaxSize().systemBarsPadding()) {
        // Top bar
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = MaterialTheme.colorScheme.onSurface)
            }
            Text(
                text = state.title,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.weight(1f)
            )
        }

        when {
            state.loading -> {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                }
            }
            state.error != null -> {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(state.error ?: "Error", color = MaterialTheme.colorScheme.error)
                }
            }
            state.hlsUrl.isNotEmpty() -> {
                ExoPlayerView(
                    hlsUrl = state.hlsUrl,
                    modifier = Modifier.fillMaxWidth(),
                    onProgress = { currentTime, duration ->
                        viewModel.updateProgress(currentTime, duration)
                    },
                    onNext = {
                        val nextEp = state.currentEpisode + 1
                        if (nextEp <= state.episodes.size) {
                            onNavigateToEpisode(state.currentSeason, nextEp)
                        }
                    },
                    onPrev = {
                        val prevEp = state.currentEpisode - 1
                        if (prevEp >= 1) {
                            onNavigateToEpisode(state.currentSeason, prevEp)
                        }
                    }
                )

                // Episode list
                if (state.episodes.isNotEmpty()) {
                    Text(
                        text = "Episodes",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                    )

                    androidx.compose.foundation.lazy.LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(horizontal = 16.dp)
                    ) {
                        items(state.episodes.size) { index ->
                            val ep = state.episodes[index]
                            Surface(
                                onClick = { onNavigateToEpisode(ep.seasonNumber, ep.episodeNumber) },
                                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                                shape = androidx.compose.foundation.shape.RoundedCornerShape(12.dp),
                                color = if (ep.episodeNumber == state.currentEpisode)
                                    MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)
                                else MaterialTheme.colorScheme.surfaceVariant
                            ) {
                                Row(modifier = Modifier.padding(12.dp).fillMaxWidth()) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            "${ep.episodeNumber}. ${ep.name}",
                                            color = MaterialTheme.colorScheme.onSurface,
                                            style = MaterialTheme.typography.bodyMedium
                                        )
                                        if (ep.overview.isNotEmpty()) {
                                            Text(
                                                ep.overview,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                                style = MaterialTheme.typography.bodySmall,
                                                maxLines = 2
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
