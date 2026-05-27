package com.watchfy.app.data.repository

import com.watchfy.app.data.remote.WatchfyApi
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SourceRepository @Inject constructor(
    private val api: WatchfyApi
) {
    suspend fun getSource(
        tmdbId: Int, mediaType: String, season: Int = 1, episode: Int = 1
    ): Result<SourceResult> = runCatching {
        val response = api.getSource(tmdbId, mediaType, season, episode)
        val masterUrl = response.masterUrl ?: response.sources?.firstOrNull()?.url
            ?: throw IllegalStateException("No stream source available")
        SourceResult(
            masterUrl = masterUrl,
            proxyUrl = "/api/white/proxy/hls?url=${java.net.URLEncoder.encode(masterUrl, "UTF-8")}"
        )
    }

    suspend fun prewarmPopular(limit: Int = 10) {
        runCatching { api.prewarmPopular(limit) }
    }
}

data class SourceResult(
    val masterUrl: String,
    val proxyUrl: String,
)
