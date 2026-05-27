package com.watchfy.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "my_list")
data class MyListEntity(
    @PrimaryKey val key: String,
    val tmdbId: Int,
    val mediaType: String,
    val addedAt: Long = System.currentTimeMillis(),
)
