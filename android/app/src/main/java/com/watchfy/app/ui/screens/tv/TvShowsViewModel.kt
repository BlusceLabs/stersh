package com.watchfy.app.ui.screens.tv

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.watchfy.app.data.repository.TmdbRepository
import com.watchfy.app.domain.model.TvShow
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class TvUiState(
    val shows: List<TvShow> = emptyList(),
    val loading: Boolean = true,
    val error: String? = null,
    val sort: String = "popular",
)

@HiltViewModel
class TvShowsViewModel @Inject constructor(
    private val repository: TmdbRepository
) : ViewModel() {

    private val _state = MutableStateFlow(TvUiState())
    val state: StateFlow<TvUiState> = _state.asStateFlow()

    init { load() }

    fun setSort(sort: String) {
        _state.update { it.copy(sort = sort) }
        load()
    }

    private fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            try {
                val results = when (_state.value.sort) {
                    "top_rated" -> repository.getTopRatedTv()
                    "airing_today" -> repository.getAiringToday()
                    "on_the_air" -> repository.getOnTheAir()
                    else -> repository.getPopularTv()
                }
                _state.update { it.copy(shows = results, loading = false) }
            } catch (e: Exception) {
                _state.update { it.copy(loading = false, error = e.message) }
            }
        }
    }
}
