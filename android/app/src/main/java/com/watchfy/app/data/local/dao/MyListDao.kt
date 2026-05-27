package com.watchfy.app.data.local.dao

import androidx.room.*
import com.watchfy.app.data.local.entity.MyListEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface MyListDao {

    @Query("SELECT * FROM my_list ORDER BY addedAt DESC")
    fun getAllFlow(): Flow<List<MyListEntity>>

    @Query("SELECT * FROM my_list ORDER BY addedAt DESC")
    suspend fun getAll(): List<MyListEntity>

    @Query("SELECT EXISTS(SELECT 1 FROM my_list WHERE `key` = :key)")
    suspend fun exists(key: String): Boolean

    @Upsert
    suspend fun upsert(entity: MyListEntity)

    @Query("DELETE FROM my_list WHERE `key` = :key")
    suspend fun deleteByKey(key: String)

    @Query("DELETE FROM my_list")
    suspend fun deleteAll()
}
