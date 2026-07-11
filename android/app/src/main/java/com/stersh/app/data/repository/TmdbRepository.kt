package com.stersh.app.data.repository

import com.stersh.app.data.remote.StershApi
import com.stersh.app.data.remote.dto.*
import com.stersh.app.domain.model.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TmdbRepository @Inject constructor(
    private val api: StershApi
) {
    suspend fun getTrending(time: String = "week", page: Int = 1): List<Movie> =
        api.getTrending("movie", time, page).results.map { it.toMovie() }

suspend fun getPopularMovies(page: Int = 1): List<Movie> =
         api.getMoviePopular(page).results.map { it.toMovie() }

    suspend fun getTopRatedMovies(page: Int = 1): List<Movie> =
         api.getMovieTopRated(page).results.map { it.toMovie() }

    suspend fun getNowPlaying(page: Int = 1): List<Movie> =
        api.getNowPlaying(page).results.map { it.toMovie() }

    suspend fun getUpcoming(page: Int = 1): List<Movie> =
        api.getUpcoming(page).results.map { it.toMovie() }

suspend fun getPopularTv(page: Int = 1): List<TvShow> =
         api.getTvPopular(page).results.map { it.toTvShow() }

    suspend fun getTopRatedTv(page: Int = 1): List<TvShow> =
         api.getTvTopRated(page).results.map { it.toTvShow() }

    suspend fun getAiringToday(page: Int = 1): List<TvShow> =
        api.getAiringToday(page).results.map { it.toTvShow() }

    suspend fun getOnTheAir(page: Int = 1): List<TvShow> =
        api.getOnTheAir(page).results.map { it.toTvShow() }

    suspend fun getMovieDetails(id: Int): Movie =
        api.getMovieDetails(id).toMovie()

    suspend fun getTvDetails(id: Int): TvShow =
        api.getTvDetails(id).toTvShow()

    suspend fun getSeasonDetails(tvId: Int, season: Int): List<Episode> =
        api.getSeasonDetails(tvId, season).episodes.map { it.toEpisode() }

    suspend fun search(query: String, type: String? = null, page: Int = 1): TmdbResponse<MovieDto> =
        api.search(query, type, page)

    suspend fun getTrailerKey(type: String, id: Int): String? {
        val videos = if (type == "movie") api.getMovieDetails(id).videos
        else api.getTvDetails(id).videos
        return videos?.results?.find { it.site == "YouTube" && (it.type == "Trailer" || it.type == "Teaser") }?.key
    }

    suspend fun getMovieRecommendations(id: Int): List<Movie> =
        api.getMovieDetails(id).recommendations?.results?.map { it.toMovie() } ?: emptyList()

    suspend fun getTvRecommendations(id: Int): List<TvShow> =
        api.getTvDetails(id).recommendations?.results?.map { it.toTvShow() } ?: emptyList()

    private fun MovieDto.toMovie() = Movie(
        id = id, title = title, overview = overview,
        posterPath = posterPath, backdropPath = backdropPath,
        voteAverage = voteAverage, releaseDate = releaseDate,
        genreIds = genreIds,
        genres = genres?.map { Genre(it.id, it.name) } ?: emptyList()
    )

    private fun TvDto.toTvShow() = TvShow(
        id = id, name = name, overview = overview,
        posterPath = posterPath, backdropPath = backdropPath,
        voteAverage = voteAverage, firstAirDate = firstAirDate,
        genreIds = genreIds,
        genres = genres?.map { Genre(it.id, it.name) } ?: emptyList(),
        numberOfSeasons = numberOfSeasons, numberOfEpisodes = numberOfEpisodes,
        seasons = seasons?.map { Season(it.id, it.seasonNumber, it.name, it.episodeCount, it.posterPath) } ?: emptyList()
    )

    private fun EpisodeDto.toEpisode() = Episode(
        id = id, name = name, overview = overview,
        stillPath = stillPath, episodeNumber = episodeNumber,
        seasonNumber = seasonNumber, voteAverage = voteAverage
    )
}
