package com.watchfy.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.watchfy.app.data.local.dao.ContinueWatchingDao
import com.watchfy.app.data.local.dao.MyListDao
import com.watchfy.app.data.local.entity.ContinueWatchingEntity
import com.watchfy.app.data.local.entity.MyListEntity

@Database(
    entities = [ContinueWatchingEntity::class, MyListEntity::class],
    version = 1,
    exportSchema = false
)
abstract class WatchfyDatabase : RoomDatabase() {
    abstract fun continueWatchingDao(): ContinueWatchingDao
    abstract fun myListDao(): MyListDao
}
