package com.stersh.app.di

import android.content.Context
import androidx.room.Room
import com.stersh.app.data.local.StershDatabase
import com.stersh.app.data.local.dao.ContinueWatchingDao
import com.stersh.app.data.local.dao.MyListDao
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
    fun provideDatabase(@ApplicationContext context: Context): StershDatabase {
        return Room.databaseBuilder(
            context,
            StershDatabase::class.java,
            "stersh.db"
        ).build()
    }

    @Provides
    fun provideContinueWatchingDao(db: StershDatabase): ContinueWatchingDao =
        db.continueWatchingDao()

    @Provides
    fun provideMyListDao(db: StershDatabase): MyListDao =
        db.myListDao()
}
