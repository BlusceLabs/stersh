package com.stersh.app.data.remote.dto

import com.google.gson.annotations.SerializedName

data class TmdbResponse<T>(
    val page: Int = 1,
    val results: List<T> = emptyList(),
    @SerializedName("total_pages") val totalPages: Int = 1,
    @SerializedName("total_results") val totalResults: Int = 0,
)

data class MovieDto(
    val id: Int,
    val title: String,
    val overview: String,
    @SerializedName("poster_path") val posterPath: String?,
    @SerializedName("backdrop_path") val backdropPath: String?,
    @SerializedName("vote_average") val voteAverage: Double = 0.0,
    @SerializedName("release_date") val releaseDate: String?,
    @SerializedName("genre_ids") val genreIds: List<Int> = emptyList(),
    val genres: List<GenreDto>? = null,
    val videos: TmdbResponse<VideoDto>? = null,
    val credits: CreditsDto? = null,
    val recommendations: TmdbResponse<MovieDto>? = null,
)

data class TvDto(
    val id: Int,
    val name: String,
    val overview: String,
    @SerializedName("poster_path") val posterPath: String?,
    @SerializedName("backdrop_path") val backdropPath: String?,
    @SerializedName("vote_average") val voteAverage: Double = 0.0,
    @SerializedName("first_air_date") val firstAirDate: String?,
    @SerializedName("genre_ids") val genreIds: List<Int> = emptyList(),
    val genres: List<GenreDto>? = null,
    @SerializedName("number_of_seasons") val numberOfSeasons: Int = 0,
    @SerializedName("number_of_episodes") val numberOfEpisodes: Int = 0,
    val seasons: List<SeasonDto>? = null,
    val videos: TmdbResponse<VideoDto>? = null,
    val credits: CreditsDto? = null,
    val recommendations: TmdbResponse<TvDto>? = null,
)

data class GenreDto(
    val id: Int,
    val name: String,
)

data class SeasonDto(
    val id: Int,
    @SerializedName("season_number") val seasonNumber: Int,
    val name: String,
    @SerializedName("episode_count") val episodeCount: Int,
    @SerializedName("poster_path") val posterPath: String?,
)

data class EpisodeDto(
    val id: Int,
    val name: String,
    val overview: String,
    @SerializedName("still_path") val stillPath: String?,
    @SerializedName("episode_number") val episodeNumber: Int,
    @SerializedName("season_number") val seasonNumber: Int,
    @SerializedName("vote_average") val voteAverage: Double = 0.0,
)

data class SeasonDetailsDto(
    val id: Int,
    @SerializedName("season_number") val seasonNumber: Int,
    val episodes: List<EpisodeDto> = emptyList(),
)

data class VideoDto(
    val key: String,
    val site: String,
    val type: String,
)

data class CreditsDto(
    val cast: List<CastDto> = emptyList(),
)

data class CastDto(
    val id: Int,
    val name: String,
    val character: String,
    @SerializedName("profile_path") val profilePath: String?,
)
