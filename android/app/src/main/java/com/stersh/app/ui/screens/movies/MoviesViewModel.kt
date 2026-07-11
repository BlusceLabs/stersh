package com.stersh.app.ui.screens.movies

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.stersh.app.data.repository.TmdbRepository
import com.stersh.app.domain.model.Movie
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MoviesUiState(
    val movies: List<Movie> = emptyList(),
    val loading: Boolean = true,
    val error: String? = null,
    val sort: String = "popular",
    val page: Int = 1,
    val hasMore: Boolean = true,
)

@HiltViewModel
class MoviesViewModel @Inject constructor(
    private val repository: TmdbRepository
) : ViewModel() {

    private val _state = MutableStateFlow(MoviesUiState())
    val state: StateFlow<MoviesUiState> = _state.asStateFlow()

    init { loadMovies() }

    fun setSort(sort: String) {
        _state.update { MoviesUiState(sort = sort) }
        loadMovies()
    }

    fun loadMore() {
        if (_state.value.loading || !_state.value.hasMore) return
        _state.update { it.copy(page = it.page + 1) }
        loadMovies()
    }

    private fun loadMovies() {
        viewModelScope.launch {
            val s = _state.value
            _state.update { it.copy(loading = true, error = null) }
            try {
                val results = when (s.sort) {
                    "top_rated" -> repository.getTopRatedMovies(s.page)
                    "now_playing" -> repository.getNowPlaying(s.page)
                    "upcoming" -> repository.getUpcoming(s.page)
                    else -> repository.getPopularMovies(s.page)
                }
                _state.update {
                    it.copy(
                        movies = if (s.page == 1) results else it.movies + results,
                        loading = false,
                        hasMore = results.isNotEmpty()
                    )
                }
            } catch (e: Exception) {
                _state.update { it.copy(loading = false, error = e.message) }
            }
        }
    }
}
