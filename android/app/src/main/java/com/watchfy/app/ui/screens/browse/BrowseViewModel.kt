package com.watchfy.app.ui.screens.browse

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.watchfy.app.data.repository.LocalRepository
import com.watchfy.app.data.repository.TmdbRepository
import com.watchfy.app.domain.model.ContinueWatchingItem
import com.watchfy.app.domain.model.Movie
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class BrowseUiState(
    val trending: List<Movie> = emptyList(),
    val popular: List<Movie> = emptyList(),
    val topRated: List<Movie> = emptyList(),
    val continueWatching: List<ContinueWatchingItem> = emptyList(),
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class BrowseViewModel @Inject constructor(
    private val tmdbRepository: TmdbRepository,
    private val localRepository: LocalRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(BrowseUiState())
    val state: StateFlow<BrowseUiState> = _state.asStateFlow()

    init {
        loadData()
    }

    private fun loadData() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            try {
                val trending = tmdbRepository.getTrending()
                val popular = tmdbRepository.getPopularMovies()
                val topRated = tmdbRepository.getTopRatedMovies()
                _state.update {
                    it.copy(
                        trending = trending,
                        popular = popular,
                        topRated = topRated,
                        loading = false
                    )
                }
            } catch (e: Exception) {
                _state.update {
                    it.copy(loading = false, error = e.message ?: "Failed to load")
                }
            }
        }

        viewModelScope.launch {
            localRepository.getContinueWatchingFlow().collect { items ->
                _state.update { it.copy(continueWatching = items) }
            }
        }
    }
}
