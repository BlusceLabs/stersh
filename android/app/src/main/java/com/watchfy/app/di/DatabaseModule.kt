package com.watchfy.app.di

import android.content.Context
import androidx.room.Room
import com.watchfy.app.data.local.WatchfyDatabase
import com.watchfy.app.data.local.dao.ContinueWatchingDao
import com.watchfy.app.data.local.dao.MyListDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): WatchfyDatabase {
        return Room.databaseBuilder(
            context,
            WatchfyDatabase::class.java,
            "watchfy.db"
        ).build()
    }

    @Provides
    fun provideContinueWatchingDao(db: WatchfyDatabase): ContinueWatchingDao =
        db.continueWatchingDao()

    @Provides
    fun provideMyListDao(db: WatchfyDatabase): MyListDao =
        db.myListDao()
}
