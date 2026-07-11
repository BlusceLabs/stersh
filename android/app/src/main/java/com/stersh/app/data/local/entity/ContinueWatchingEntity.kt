package com.stersh.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "continue_watching")
data class ContinueWatchingEntity(
    @PrimaryKey val key: String,
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
