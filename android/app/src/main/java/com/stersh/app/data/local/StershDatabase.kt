package com.stersh.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.stersh.app.data.local.dao.ContinueWatchingDao
import com.stersh.app.data.local.dao.MyListDao
import com.stersh.app.data.local.entity.ContinueWatchingEntity
import com.stersh.app.data.local.entity.MyListEntity

@Database(
    entities = [ContinueWatchingEntity::class, MyListEntity::class],
    version = 1,
    exportSchema = false
)
abstract class StershDatabase : RoomDatabase() {
    abstract fun continueWatchingDao(): ContinueWatchingDao
    abstract fun myListDao(): MyListDao
}
