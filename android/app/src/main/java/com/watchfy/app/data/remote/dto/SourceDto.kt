package com.watchfy.app.data.remote.dto

import com.google.gson.annotations.SerializedName

data class SourceResponse(
    val sources: List<SourceItem>? = null,
    @SerializedName("master_url") val masterUrl: String? = null,
)

data class SourceItem(
    val url: String? = null,
    val quality: String? = null,
)
