package com.stersh.app.domain.model

data class Movie(
    val id: Int,
    val title: String,
    val overview: String,
    val posterPath: String?,
    val backdropPath: String?,
    val voteAverage: Double,
    val releaseDate: String?,
    val genreIds: List<Int> = emptyList(),
    val genres: List<Genre> = emptyList(),
)

data class TvShow(
    val id: Int,
    val name: String,
    val overview: String,
    val posterPath: String?,
    val backdropPath: String?,
    val voteAverage: Double,
    val firstAirDate: String?,
    val genreIds: List<Int> = emptyList(),
    val genres: List<Genre> = emptyList(),
    val numberOfSeasons: Int = 0,
    val numberOfEpisodes: Int = 0,
    val seasons: List<Season> = emptyList(),
)

data class Season(
    val id: Int,
    val seasonNumber: Int,
    val name: String,
    val episodeCount: Int,
    val posterPath: String?,
)

data class Episode(
    val id: Int,
    val name: String,
    val overview: String,
    val stillPath: String?,
    val episodeNumber: Int,
    val seasonNumber: Int,
    val voteAverage: Double,
)

data class Genre(
    val id: Int,
    val name: String,
)

data class Source(
    val url: String,
    val masterUrl: String,
    val quality: String = "Auto",
)

data class Video(
    val key: String,
    val site: String,
    val type: String,
)

data class ContinueWatchingItem(
    val tmdbId: Int,
    val mediaType: String,
    val title: String,
    val posterPath: String?,
    val season: Int = 1,
    val episode: Int = 1,
    val currentTime: Long = 0,
    val duration: Long = 0,
    val updatedAt: Long = System.currentTimeMillis(),
)

data class MyListItem(
    val tmdbId: Int,
    val mediaType: String,
)

enum class MediaType(val apiValue: String) {
    MOVIE("movie"), TV("tv")
}
