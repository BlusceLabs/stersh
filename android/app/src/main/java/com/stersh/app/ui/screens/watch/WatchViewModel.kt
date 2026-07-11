package com.stersh.app.ui.screens.watch

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.stersh.app.data.repository.LocalRepository
import com.stersh.app.data.repository.SourceRepository
import com.stersh.app.data.repository.TmdbRepository
import com.stersh.app.domain.model.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class WatchUiState(
    val hlsUrl: String = "",
    val title: String = "",
    val posterPath: String? = null,
    val episodes: List<Episode> = emptyList(),
    val currentEpisode: Int = 1,
    val currentSeason: Int = 1,
    val totalSeasons: Int = 1,
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class WatchViewModel @Inject constructor(
    private val sourceRepository: SourceRepository,
    private val tmdbRepository: TmdbRepository,
    private val localRepository: LocalRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(WatchUiState())
    val state: StateFlow<WatchUiState> = _state.asStateFlow()

    private var currentTmdbId = 0
    private var currentMediaType = "movie"

    fun load(mediaType: String, tmdbId: Int, season: Int, episode: Int) {
        currentTmdbId = tmdbId
        currentMediaType = mediaType
        _state.update { it.copy(currentSeason = season, currentEpisode = episode, loading = true, error = null) }

        viewModelScope.launch {
            try {
                val result = sourceRepository.getSource(tmdbId, mediaType, season, episode)
                result.onSuccess { source ->
                    _state.update { it.copy(hlsUrl = source.url, loading = false) }
                }.onFailure { e ->
                    _state.update { it.copy(loading = false, error = e.message ?: "Stream unavailable") }
                }

                // Fetch title and metadata
                if (mediaType == "movie") {
                    val movie = tmdbRepository.getMovieDetails(tmdbId)
                    _state.update { it.copy(title = movie.title, posterPath = movie.posterPath) }
                } else {
                    val tv = tmdbRepository.getTvDetails(tmdbId)
                    val seasonDetails = tmdbRepository.getSeasonDetails(tmdbId, season)
                    _state.update {
                        it.copy(
                            title = tv.name, posterPath = tv.posterPath,
                            episodes = seasonDetails, totalSeasons = tv.numberOfSeasons,
                            loading = false
                        )
                    }
                }
            } catch (e: Exception) {
                _state.update { it.copy(loading = false, error = e.message ?: "Failed to load stream") }
            }
        }
    }

    fun updateProgress(currentTime: Long, duration: Long) {
        viewModelScope.launch {
            localRepository.updateProgress(
                ContinueWatchingItem(
                    tmdbId = currentTmdbId,
                    mediaType = currentMediaType,
                    title = _state.value.title,
                    posterPath = _state.value.posterPath,
                    season = _state.value.currentSeason,
                    episode = _state.value.currentEpisode,
                    currentTime = currentTime,
                    duration = duration,
                )
            )
        }
    }
}
