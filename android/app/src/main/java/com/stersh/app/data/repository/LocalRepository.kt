package com.stersh.app.data.repository

import com.stersh.app.data.local.dao.ContinueWatchingDao
import com.stersh.app.data.local.dao.MyListDao
import com.stersh.app.data.local.entity.ContinueWatchingEntity
import com.stersh.app.data.local.entity.MyListEntity
import com.stersh.app.domain.model.ContinueWatchingItem
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LocalRepository @Inject constructor(
    private val continueWatchingDao: ContinueWatchingDao,
    private val myListDao: MyListDao,
) {
    fun getContinueWatchingFlow(): Flow<List<ContinueWatchingItem>> =
        continueWatchingDao.getAllFlow().map { entities ->
            entities.map { it.toItem() }
        }

    suspend fun updateProgress(item: ContinueWatchingItem) {
        continueWatchingDao.upsert(
            ContinueWatchingEntity(
                key = "stersh:${item.mediaType}:${item.tmdbId}:${item.season}:${item.episode}",
                tmdbId = item.tmdbId, mediaType = item.mediaType,
                title = item.title, posterPath = item.posterPath,
                season = item.season, episode = item.episode,
                currentTime = item.currentTime, duration = item.duration,
                updatedAt = System.currentTimeMillis()
            )
        )
    }

    fun getMyListFlow(): Flow<List<MyListEntity>> = myListDao.getAllFlow()

    suspend fun isInMyList(type: String, id: Int): Boolean =
        myListDao.exists("stersh:mylist:$type:$id")

    suspend fun toggleMyList(type: String, id: Int) {
        val key = "stersh:mylist:$type:$id"
        if (myListDao.exists(key)) {
            myListDao.deleteByKey(key)
        } else {
            myListDao.upsert(MyListEntity(key = key, tmdbId = id, mediaType = type))
        }
    }

    private fun ContinueWatchingEntity.toItem() = ContinueWatchingItem(
        tmdbId = tmdbId, mediaType = mediaType, title = title,
        posterPath = posterPath, season = season, episode = episode,
        currentTime = currentTime, duration = duration, updatedAt = updatedAt
    )
}
