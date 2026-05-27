package com.watchfy.app.ui.screens.search

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.watchfy.app.data.repository.TmdbRepository
import com.watchfy.app.domain.model.Movie
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SearchUiState(
    val query: String = "",
    val results: List<Movie> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class SearchViewModel @Inject constructor(
    private val repository: TmdbRepository
) : ViewModel() {

    private val _state = MutableStateFlow(SearchUiState())
    val state: StateFlow<SearchUiState> = _state.asStateFlow()

    private var searchJob: Job? = null

    fun onQueryChanged(query: String) {
        _state.update { it.copy(query = query) }
        searchJob?.cancel()
        if (query.isBlank()) {
            _state.update { it.copy(results = emptyList(), loading = false) }
            return
        }
        searchJob = viewModelScope.launch {
            delay(350)
            _state.update { it.copy(loading = true) }
            try {
                val response = repository.search(query)
                _state.update {
                    it.copy(results = response.results.map { dto ->
                        Movie(
                            id = dto.id, title = dto.title, overview = dto.overview,
                            posterPath = dto.posterPath, backdropPath = dto.backdropPath,
                            voteAverage = dto.voteAverage, releaseDate = dto.releaseDate,
                            genreIds = dto.genreIds
                        )
                    }, loading = false
                    )
                }
            } catch (e: Exception) {
                _state.update { it.copy(loading = false, error = e.message) }
            }
        }
    }
}
