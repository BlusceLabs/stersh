package com.watchfy.app.data.remote

import com.watchfy.app.data.remote.dto.*
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface WatchfyApi {

    // TMDB endpoints
    @GET("/api/tmdb/trending/{type}/{time}")
    suspend fun getTrending(
        @Path("type") type: String,
        @Path("time") time: String = "week",
        @Query("page") page: Int = 1
    ): TmdbResponse<MovieDto>

    @GET("/api/tmdb/movie/popular")
    suspend fun getMoviePopular(
        @Query("page") page: Int = 1
    ): TmdbResponse<MovieDto>

    @GET("/api/tmdb/movie/top_rated")
    suspend fun getMovieTopRated(
        @Query("page") page: Int = 1
    ): TmdbResponse<MovieDto>

    @GET("/api/tmdb/tv/popular")
    suspend fun getTvPopular(
        @Query("page") page: Int = 1
    ): TmdbResponse<TvDto>

    @GET("/api/tmdb/tv/top_rated")
    suspend fun getTvTopRated(
        @Query("page") page: Int = 1
    ): TmdbResponse<TvDto>

    @GET("/api/tmdb/movie/now_playing")
    suspend fun getNowPlaying(@Query("page") page: Int = 1): TmdbResponse<MovieDto>

    @GET("/api/tmdb/movie/upcoming")
    suspend fun getUpcoming(@Query("page") page: Int = 1): TmdbResponse<MovieDto>

    @GET("/api/tmdb/tv/airing_today")
    suspend fun getAiringToday(@Query("page") page: Int = 1): TmdbResponse<TvDto>

    @GET("/api/tmdb/tv/on_the_air")
    suspend fun getOnTheAir(@Query("page") page: Int = 1): TmdbResponse<TvDto>

    @GET("/api/tmdb/movie/{id}")
    suspend fun getMovieDetails(@Path("id") id: Int): MovieDto

    @GET("/api/tmdb/tv/{id}")
    suspend fun getTvDetails(@Path("id") id: Int): TvDto

    @GET("/api/tmdb/tv/{id}/season/{season}")
    suspend fun getSeasonDetails(
        @Path("id") id: Int,
        @Path("season") season: Int
    ): SeasonDetailsDto

    @GET("/api/tmdb/search")
    suspend fun search(
        @Query("query") query: String,
        @Query("type") type: String? = null,
        @Query("page") page: Int = 1
    ): TmdbResponse<MovieDto>

    @GET("/api/tmdb/genre/{type}/list")
    suspend fun getGenres(@Path("type") type: String): TmdbResponse<GenreDto>

    // Source extraction
    @GET("/api/white/source")
    suspend fun getSource(
        @Query("tmdbId") tmdbId: Int,
        @Query("mediaType") mediaType: String,
        @Query("season") season: Int = 1,
        @Query("episode") episode: Int = 1
    ): SourceResponse

    // Prewarm
    @GET("/api/white/prewarm/popular")
    suspend fun prewarmPopular(@Query("limit") limit: Int = 10)
}
