package com.stersh.app.data.local.dao

import androidx.room.*
import com.stersh.app.data.local.entity.ContinueWatchingEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ContinueWatchingDao {

    @Query("SELECT * FROM continue_watching ORDER BY updatedAt DESC")
    fun getAllFlow(): Flow<List<ContinueWatchingEntity>>

    @Query("SELECT * FROM continue_watching ORDER BY updatedAt DESC LIMIT 20")
    suspend fun getAll(): List<ContinueWatchingEntity>

    @Query("SELECT * FROM continue_watching WHERE `key` = :key")
    suspend fun getByKey(key: String): ContinueWatchingEntity?

    @Upsert
    suspend fun upsert(entity: ContinueWatchingEntity)

    @Query("DELETE FROM continue_watching WHERE `key` = :key")
    suspend fun deleteByKey(key: String)

    @Query("DELETE FROM continue_watching")
    suspend fun deleteAll()
}
