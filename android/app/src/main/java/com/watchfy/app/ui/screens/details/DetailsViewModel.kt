package com.watchfy.app.ui.screens.details

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.watchfy.app.data.repository.LocalRepository
import com.watchfy.app.data.repository.TmdbRepository
import com.watchfy.app.domain.model.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DetailsUiState(
    val movie: Movie? = null,
    val tvShow: TvShow? = null,
    val recommendations: List<Movie> = emptyList(),
    val seasons: List<Season> = emptyList(),
    val trailerKey: String? = null,
    val isInMyList: Boolean = false,
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class DetailsViewModel @Inject constructor(
    private val tmdbRepository: TmdbRepository,
    private val localRepository: LocalRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(DetailsUiState())
    val state: StateFlow<DetailsUiState> = _state.asStateFlow()

    fun load(type: String, id: Int) {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            try {
                if (type == "movie") {
                    val movie = tmdbRepository.getMovieDetails(id)
                    val trailer = tmdbRepository.getTrailerKey("movie", id)
                    val recs = tmdbRepository.getMovieRecommendations(id)
                    val inList = localRepository.isInMyList("movie", id)
                    _state.update {
                        it.copy(movie = movie, trailerKey = trailer, recommendations = recs, isInMyList = inList, loading = false)
                    }
                } else {
                    val tv = tmdbRepository.getTvDetails(id)
                    val trailer = tmdbRepository.getTrailerKey("tv", id)
                    val inList = localRepository.isInMyList("tv", id)
                    _state.update {
                        it.copy(tvShow = tv, seasons = tv.seasons, trailerKey = trailer, isInMyList = inList, loading = false)
                    }
                }
            } catch (e: Exception) {
                _state.update { it.copy(loading = false, error = e.message) }
            }
        }
    }

    fun toggleMyList(type: String, id: Int) {
        viewModelScope.launch {
            localRepository.toggleMyList(type, id)
            _state.update { it.copy(isInMyList = !it.isInMyList) }
        }
    }
}
